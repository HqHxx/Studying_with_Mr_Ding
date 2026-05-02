"""内容引擎（v4 Pipeline版）：智能选词 -> 英文重写 -> 逐段精译。"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

from openai import OpenAI
from app_paths import BASE_DIR, INTERNAL_DIR

LOCAL_CORPUS_PATH = INTERNAL_DIR / "local_corpus.json"
USED_ARTICLES_PATH = BASE_DIR / "used_articles.json"


# ── 语料库加载 ─────────────────────────────────────────────────
def load_corpus() -> list[dict]:
    if not LOCAL_CORPUS_PATH.exists():
        raise FileNotFoundError(f"本地语料库文件不存在: {LOCAL_CORPUS_PATH}")
    data = json.loads(LOCAL_CORPUS_PATH.read_text(encoding="utf-8"))
    return data

def load_used_articles() -> set[str]:
    if not USED_ARTICLES_PATH.exists():
        return set()
    try:
        data = json.loads(USED_ARTICLES_PATH.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()

def save_used_articles(titles: set[str]) -> None:
    USED_ARTICLES_PATH.write_text(
        json.dumps(sorted(titles), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class ContentEngine:
    def __init__(self, api_key: str, base_url: str, fast_model: str, core_model: str) -> None:
        self.fast_model = fast_model
        self.core_model = core_model
        self.llm_client = OpenAI(base_url=base_url, api_key=api_key)
        self.corpus = load_corpus()
        self._used_titles: set[str] = load_used_articles()

    def pick_source_article(self, category: str | None = None) -> dict | None:
        available = [
            entry for entry in self.corpus
            if entry.get("title", "") not in self._used_titles
            and (category is None or entry.get("category", "history") == category)
        ]
        if not available:
            return None
        chosen = random.choice(available)
        self._used_titles.add(chosen.get("title", ""))
        save_used_articles(self._used_titles)
        return chosen

    def _call_llm(self, system_prompt: str, user_prompt: str, step_name: str, target_model: str, check_stop_callback=None, stream=False, is_debug=False) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        if is_debug:
            import time
            prompt_content = system_prompt + "\n" + user_prompt
            print(f"\n---> [Debug] {step_name} 实际发送的 Prompt 长度: {len(prompt_content)} 字符")
            start_time = time.time()
        
        full_content = ""
        for continuation_step in range(3):
            if check_stop_callback and check_stop_callback():
                raise InterruptedError("用户已手动停止任务")

            response = self.llm_client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
                timeout=150.0,
                stream=stream
            )
            
            chunk = ""
            finish_reason = "stop"
            if stream:
                print(f"---> [Debug] {step_name} 开始流式输出: \n", end="", flush=True)
                for chunk_obj in response:
                    if check_stop_callback and check_stop_callback():
                        raise InterruptedError("用户已手动停止任务")
                    if chunk_obj.choices and len(chunk_obj.choices) > 0:
                        delta = chunk_obj.choices[0].delta
                        if delta:
                            # 兼容深度思考大模型 (如 DeepSeek-R1) 的内部思维链透出
                            reasoning = getattr(delta, 'reasoning_content', None)
                            if reasoning:
                                print(f"\033[90m{reasoning}\033[0m", end="", flush=True)
                            
                            if delta.content:
                                text = delta.content
                                print(text, end="", flush=True)
                                chunk += text
                        if chunk_obj.choices[0].finish_reason:
                            finish_reason = chunk_obj.choices[0].finish_reason
                print("\n---> [Debug] 流式输出结束。")
            else:
                chunk = response.choices[0].message.content or ""
                finish_reason = response.choices[0].finish_reason
            
            full_content += chunk
            stripped = full_content.strip()
            
            if not stripped:
                raise ValueError("大模型返回内容为空！")
                
            valid_endings = ('.', '!', '?', '"', "'", '”', '’', ']', ')', '。', '！', '？', '）', '】', '}', '_')
            is_complete = stripped.endswith(valid_endings)
            
            if finish_reason == "length" or (step_name != "Step 1" and not is_complete):
                print(f"[Engine] {step_name} - Output truncated at step {continuation_step + 1}. Requesting continuation...")
                messages.append({"role": "assistant", "content": chunk})
                messages.append({
                    "role": "user", 
                    "content": "请紧接着你刚才中断的地方继续输出，不要重复已经写过的内容，不要说多余的废话，直接接上正文。"
                })
            else:
                break
                
        if is_debug:
            end_time = time.time()
            print(f"---> [Debug] {step_name} 精准耗时: {end_time - start_time:.2f} 秒\n")
            
        return full_content

    def generate_article(self, words_data: list[dict], category: str = "history", level: str = "CET-4", log_callback=None, check_stop_callback=None, mode: str = "random", custom_text: str = ""):
        def _log(msg: str):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        if mode == "custom":
            title = "Custom_Article"
            source_text = custom_text
        else:
            source = self.pick_source_article(category=category)
            if not source:
                return f"Error: [{category}] 分类下没有可用的未使用文章。", None, None

            title = source.get("title", "Untitled")
            source_text = source.get("content", "")
            
            if not source_text.strip():
                return f"Error: 语料 [{title}] 正文为空。", None, None

        _log(f"\n[Engine] Starting Pipeline for [{category}/{level}]: {title}")
        import time
        pipeline_start_time = time.time()
        
        try:
            if check_stop_callback and check_stop_callback():
                raise InterruptedError("用户已手动停止任务")

            # ==========================================
            # 第一步：智能选词 (Fast Model)
            # ==========================================
            _log(f"[1/3] 正在使用 [{self.fast_model}] 进行智能选词 (25-50词)...")
            # 物理切除：最多只随机发送 100 个纯英文单词
            import random
            candidate_words = [str(w.get("word", "")).strip() for w in words_data if str(w.get("word", "")).strip()]
            if len(candidate_words) > 100:
                candidate_words = random.sample(candidate_words, 100)
            words_str = ", ".join(candidate_words)
            
            sys_1 = "你是一个词汇专家。"
            usr_1 = (
                f"请阅读提供的文章前奏片段，并从候选词库中挑选出 25 到 50 个最适合该语境的单词。\n"
                f"【文章片段】：{source_text[:300]}...\n\n"
                f"【候选词库】：\n{words_str}\n\n"
                "请直接用英文逗号分隔输出你选中的单词（例如: apple, banana, car），绝对不要有任何其他废话、标点或解释！"
            )
            
            words_str_output = self._call_llm(sys_1, usr_1, "Step 1", self.fast_model, check_stop_callback, stream=True, is_debug=True)
            
            # 容错提取（用正则找出所有英文单词）
            selected_words_raw = re.findall(r'[a-zA-Z\'-]+', words_str_output)
                
            if not selected_words_raw or not isinstance(selected_words_raw, list):
                raise ValueError("第一步未返回有效的单词列表。")
                
            selected_words_lower = [w.lower() for w in selected_words_raw]
            
            # 匹配词库详情
            final_selected = []
            for w in words_data:
                if w.get("word", "").lower() in selected_words_lower:
                    final_selected.append(w)
                    
            final_selected = final_selected[:50]
            if len(final_selected) < 10:
                raise ValueError("解析选词失败，选出的合法单词过少。")
                
            selected_words_str = ", ".join([w.get("word", "") for w in final_selected])
            _log(f"   => 选词完成！共选中 {len(final_selected)} 个单词。")
            
            if check_stop_callback and check_stop_callback():
                raise InterruptedError("用户已手动停止任务")

            # ==========================================
            # 第二步：英文重写与植入 (Core Model)
            # ==========================================
            _log(f"[2/3] 正在使用 [{self.core_model}] 进行深度重写与植入... (这步耗时较长，请耐心等待)")
            sys_2 = "你现在是一位英语为母语的顶尖专栏作家（如《经济学人》或《国家地理》的资深编辑）。"
            usr_2 = (
                f"请根据我提供的原文章，重写并扩写出一篇 600-800 词的高质量英文长文。\n\n"
                f"【原文标题】：{title}\n"
                f"【原文内容（全文）】：\n{source_text}\n\n"
                f"【目标单词池】（共 {len(final_selected)} 个）：\n{selected_words_str}\n\n"
                "【核心写作约束】\n"
                "1. 绝对地道 (Authenticity)：彻底摒弃中式英语 (Chinglish) 和 AI 生成的机器味。请使用英语母语者常用的地道搭配 (Collocations)、短语动词 (Phrasal verbs) 和恰当的习语 (Idioms)。\n"
                "2. 句式丰富 (Syntactic Variety)：不要全是简单的主谓宾结构。请巧妙地交替使用长短句、从句、分词伴随状语、倒装句等高级句式，让文章充满节奏感和文学张力。\n"
                "3. 无痕植入 (Seamless Integration)：将我提供的目标单词列表极其自然地融进文章中并用 ** 加粗。这些生词的出现必须完全符合逻辑流和语境，仿佛它们天生就长在这篇文章里，绝不能有为了凑词而强行生搬硬套的割裂感。\n"
                "4. 纯英文输出：只输出排版精美的 Markdown 纯英文正文，不要有任何解释性废话。"
            )
            
            english_article = self._call_llm(sys_2, usr_2, "Step 2", self.core_model, check_stop_callback, stream=True, is_debug=True)
            _log("   => 英文长文重写完成！")
            
            if check_stop_callback and check_stop_callback():
                raise InterruptedError("用户已手动停止任务")

            # ==========================================
            # 第三步：逐段精译与格式化 (Fast Model)
            # ==========================================
            _log(f"[3/3] 正在使用 [{self.fast_model}] 进行逐段翻译与排版...")
            sys_3 = "你是一个英语教材翻译专家。"
            
            usr_3 = (
                "请将我提供的这篇英文长文进行逐段翻译。\n\n"
                "翻译排版要求（极其重要，必须严格遵守）：\n"
                "1. 严格保持交替排版。\n"
                "2. **格式必须是：一段英文原文 -> 空一行 -> 一段中文翻译 -> 空一行 -> 下一段英文原文...**\n"
                "3. **绝对不要调换顺序！必须是先英文、后中文，绝对不能先中文后英文！**\n"
                "4. 绝对不能把英文和中文黏在同一段里！\n"
                "5. 绝对不要漏掉原文的任何一段，也不要自行合段！\n"
                "6. 原文英文里加粗的生词（**word**），在翻译成中文时，**中文译文中绝对不要加粗**！请保持中文句子的正常、纯净排版。\n"
                "7. 直接开始输出双语正文，绝对禁止输出标题、引言、总结或任何单独的词汇释义列表！\n\n"
                f"【待翻译纯英文长文】：\n{english_article}\n"
            )
            
            translated_article = self._call_llm(sys_3, usr_3, "Step 3", self.fast_model, check_stop_callback, stream=True, is_debug=True)
            _log("   => 精译完成！")
            
            # Python 本地极速拼接最终 Markdown
            vocab_list_text = ""
            for w in final_selected:
                vocab_list_text += f"- **{w.get('word', '')}** {w.get('phonetic', '')} {w.get('definition', '')}\n"
                
            final_article = f"# {title}\n\n### 核心词汇\n\n{vocab_list_text}\n\n### 双语正文\n\n{translated_article}"
            
            used_words = [w.get("word", "").lower() for w in final_selected]
            return final_article, used_words, title

        except InterruptedError as ie:
            _log(f"🛑 中断: {ie}")
            return f"Error: {ie}", None, None
        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = str(e)
            if "timeout" in err_msg.lower():
                _log("❌ API 请求超时！")
                return f"Error: API 请求超时", None, None
            return f"Error: {e}", None, None
        finally:
            pipeline_end_time = time.time()
            print(f"\n==========================================")
            print(f"---> [Debug] 三级流水线总精准耗时: {pipeline_end_time - pipeline_start_time:.2f} 秒")
            print(f"==========================================\n")