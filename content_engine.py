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
CUSTOM_CORPUS_PATH = BASE_DIR / "data" / "custom_corpus.json"
USED_ARTICLES_PATH = BASE_DIR / "used_articles.json"


# ── 语料库加载 ─────────────────────────────────────────────────
def load_corpus(mode: str = "builtin") -> list[dict]:
    corpus = []
    
    if mode in ["builtin", "mixed"]:
        if LOCAL_CORPUS_PATH.exists():
            try:
                data = json.loads(LOCAL_CORPUS_PATH.read_text(encoding="utf-8"))
                corpus.extend(data)
            except Exception as e:
                print(f"解析内置语料库失败: {e}")
                
    if mode in ["custom", "mixed"]:
        if CUSTOM_CORPUS_PATH.exists():
            try:
                data = json.loads(CUSTOM_CORPUS_PATH.read_text(encoding="utf-8"))
                corpus.extend(data)
            except Exception as e:
                print(f"解析自定义语料库失败: {e}")
                
    if not corpus:
        raise FileNotFoundError(f"根据所选模式[{mode}]，最终加载的语料库为空！")
        
    return corpus

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
    def __init__(self, api_key: str, base_url: str, fast_model: str, core_model: str, corpus_mode: str = "builtin") -> None:
        self.fast_model = fast_model
        self.core_model = core_model
        self.llm_client = OpenAI(base_url=base_url, api_key=api_key)
        self.corpus = load_corpus(mode=corpus_mode)
        self._used_titles: set[str] = load_used_articles()
        self._last_validation_reason = ""

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
            {"role": "user", "content": user_prompt}
        ]
            
        if is_debug:
            import time
            prompt_content = system_prompt + "\n" + user_prompt
            print(f"\n---> [Debug] {step_name} 实际发送的 Prompt 长度: {len(prompt_content)} 字符")
            start_time = time.time()
        
        full_content = ""
        # 随机生成一个切断阈值，让截断点在 40 到 50 之间浮动
        max_cut_words = random.randint(40, 50) if step_name == "Step 1" else float('inf')
        for continuation_step in range(3):
            if check_stop_callback and check_stop_callback():
                raise InterruptedError("用户已手动停止任务")

            step_temp = 0.7
            step_max_tokens = 4096

            response = self.llm_client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=step_temp,
                max_tokens=step_max_tokens,
                timeout=150.0,
                stream=stream
            )
            
            chunk = ""
            finish_reason = "stop"
            if stream:
                print(f"---> [Debug] {step_name} 开始流式输出: \n", end="", flush=True)
                # 使用一个标志位记录是否进入了有效输出区域
                output_started = False
                for chunk_obj in response:
                    if check_stop_callback and check_stop_callback():
                        raise InterruptedError("用户已手动停止任务")
                    if chunk_obj.choices and len(chunk_obj.choices) > 0:
                        delta = chunk_obj.choices[0].delta
                        if delta:
                            reasoning = getattr(delta, 'reasoning_content', None)
                            if reasoning:
                                print(f"\033[90m{reasoning}\033[0m", end="", flush=True)
                            
                            if delta.content:
                                text = delta.content
                                print(text, end="", flush=True)
                                chunk += text
                        
                        # 物理熔断逻辑（应对大模型长篇大论的废话，只处理不在推理区块输出的情况）
                        # 我们统计纯输出中的字母+逗号的模式。由于大模型有时会附带 (not there), 或者序号，我们做更宽松的切割判断。
                        # 这里我们只统计当前正文（不算 reasoning），判断是否输出了足够多的单词。
                        word_count = len(re.findall(r'[a-zA-Z\'-]+', full_content + chunk))
                        if step_name == "Step 1" and word_count >= max_cut_words * 2: # 放宽两倍因为废话里也有字母
                            print(f"\n\n---> [Debug] 达到熔断保护阈值，物理熔断强制极速切断流。")
                            finish_reason = "stop"
                            if hasattr(response, 'close'):
                                response.close()
                            break
                            
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
                
                if step_name == "Step 1":
                    continuation_prompt = "请继续提取未写完的英文单词。请严格保持仅用逗号分隔的格式，最多补充到满足总量即可，千万不要说任何废话，也不要重复之前已经输出过的词。"
                else:
                    continuation_prompt = "请紧接着你刚才中断的地方继续输出，不要重复已经写过的内容，不要说多余的废话，直接接上正文。"
                    
                messages.append({
                    "role": "user", 
                    "content": continuation_prompt
                })
            else:
                break
                
        if is_debug:
            end_time = time.time()
            print(f"---> [Debug] {step_name} 精准耗时: {end_time - start_time:.2f} 秒\n")
            
        return full_content

    def _validate_translation(self, translated: str, original: str) -> bool:
        """验证纯中文翻译的结果质量。
        
        检查逻辑：
        1. 翻译结果不能为空
        2. 中文段落数不能严重少于英文段落数
        """
        self._last_validation_reason = ""

        if not translated or not translated.strip():
            self._last_validation_reason = "翻译结果为空"
            return False
            
        original_paragraphs = [p.strip() for p in original.split('\n\n') if p.strip()]
        translated_paragraphs = [p.strip() for p in translated.split('\n\n') if p.strip()]
        
        if len(translated_paragraphs) < len(original_paragraphs) * 0.7:
            self._last_validation_reason = (
                f"中文段落严重缺失: {len(translated_paragraphs)}/{len(original_paragraphs)} "
            )
            return False
            
        for idx, p in enumerate(translated_paragraphs, start=1):
            if re.search(r'[a-zA-Z]{5,}', p) and len(re.findall(r'[a-zA-Z]{3,}', p)) >= 5:
                # 依然警惕大段英文出现（纯中文里不该出现太长连续英文）
                if not re.search(r'[\u4e00-\u9fff]', p):
                    snippet = p.replace("\n", " ")[:80]
                    self._last_validation_reason = f"检测到未翻译的英文段: 第{idx}段, 内容片段: {snippet}"
                    return False
        return True

    def generate_article(self, words_data: list[dict], category: str = "history", level: str = "CET-4", log_callback=None, check_stop_callback=None):
        def _log(msg: str):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        source = self.pick_source_article(category=category)
        if not source:
            return f"Error: [该分类] 没有可用的未使用语料文章。", None, None

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
            # 第一步：智能选词 (Fast Model) — 带重试补偿机制
            # ==========================================
            import random
            import string

            MAX_RETRIES = 3
            MIN_WORDS_TARGET = 35
            final_selected: list[dict] = []

            # 构建一个"原始词库"的快照，用于重试时重新抽取
            original_words_data = words_data.copy()

            for retry in range(MAX_RETRIES):
                _log(f"[1/3] 正在使用 [{self.fast_model}] 进行智能选词 (尝试 {retry + 1}/{MAX_RETRIES})...")

                # ── 1. 抽取候选词（排除已选中的单词） ──
                excluded_words = {w.get("word", "").lower() for w in final_selected}
                available_words = [
                    w for w in original_words_data
                    if str(w.get("word", "")).strip()
                    and w.get("word", "").lower() not in excluded_words
                ]

                if len(available_words) < MIN_WORDS_TARGET:
                    _log(f"   ⚠️ 剩余可用单词不足 {MIN_WORDS_TARGET} 个，停止重试。")
                    break

                candidate_words = [str(w.get("word", "")).strip() for w in available_words]
                if len(candidate_words) > 120:
                    candidate_words = random.sample(candidate_words, 120)
                words_str = ", ".join(candidate_words)

                sys_1 = "你是一个词汇专家。你的任务是挑选合适的单词集合。"
                usr_1 = (
                    f"请阅读提供的文章前奏片段，并从候选词库中挑选出 35 到 50 个单词。\n"
                    f"【挑选准则极大放宽】：无需与文章当前片段强相关！只要你觉得这些词在后续的长文扩写中“沾点关系”、“有可能用上”，就果断选出来！保证最终植入时稍微自然即可。\n"
                    f"【重要指示】：请充分利用词库，尽可能多地挑选单词，绝对要向 50 个的上限靠拢！\n"
                    f"【文章片段】：{source_text[:300]}...\n\n"
                    f"【候选词库】：\n{words_str}\n\n"
                    "请直接且仅仅输出你选中的单词，用英文逗号分隔（例如: apple, banana, car），不要输出任何思考过程，绝对不要给每个词都写上 (not there) 或者加上序号！输出达到 50 个时务必停止！"
                )

                words_str_output = self._call_llm(sys_1, usr_1, "Step 1", self.fast_model, check_stop_callback, stream=True, is_debug=True)

                # ── 2. 容错提取 + 脏数据清理 ──
                # 兼容大模型啰嗦思考，我们直接正则提取所有英文组合
                selected_words_raw = re.findall(r'[a-zA-Z\'-]+', words_str_output)

                if not selected_words_raw or not isinstance(selected_words_raw, list):
                    _log(f"   ⚠️ 第 {retry + 1} 轮未返回有效单词列表，继续重试...")
                    continue

                # 清理：strip + 去除首尾标点
                selected_words_cleaned = []
                for w in selected_words_raw:
                    cleaned = w.strip().strip(string.punctuation).strip()
                    if cleaned:
                        selected_words_cleaned.append(cleaned)

                selected_words_lower = [w.lower() for w in selected_words_cleaned]

                # ── 3. 匹配词库详情 ──
                matched_this_round = []
                for w in available_words:
                    if w.get("word", "").lower() in selected_words_lower:
                        matched_this_round.append(w)

                matched_this_round = matched_this_round[:50]
                _log(f"   => 第 {retry + 1} 轮匹配成功 {len(matched_this_round)} 个单词。")

                # ── 4. 追加到累加器并去重 ──
                existing_words = {w.get("word", "").lower() for w in final_selected}
                for w in matched_this_round:
                    if w.get("word", "").lower() not in existing_words:
                        final_selected.append(w)
                        existing_words.add(w.get("word", "").lower())

                _log(f"   => 累计选中 {len(final_selected)} 个单词。")

                # ── 5. 检查是否达标 ──
                if len(final_selected) >= MIN_WORDS_TARGET:
                    _log(f"   ✅ 选词达标！共选中 {len(final_selected)} 个单词。")
                    break

                # 如果还有重试机会，继续下一轮
                if retry < MAX_RETRIES - 1:
                    _log(f"   🔄 单词不足 {MIN_WORDS_TARGET} 个，触发第 {retry + 2} 轮重试...")
                else:
                    _log(f"   ⚠️ 已达到最大重试次数，累计选中 {len(final_selected)} 个单词，继续执行。")

            # 兜底：即使不足 30 个，只要有至少 5 个就继续；否则才报错
            if len(final_selected) < 5:
                raise ValueError(f"解析选词失败，累加后合法单词仅 {len(final_selected)} 个，过少。")

            final_selected = final_selected[:50]
            selected_words_str = ", ".join([w.get("word", "") for w in final_selected])
            _log(f"   => 最终选词完成！共选中 {len(final_selected)} 个单词。")
            
            if check_stop_callback and check_stop_callback():
                raise InterruptedError("用户已手动停止任务")

            # ==========================================
            # 第二步：英文重写与植入 (Core Model)
            # ==========================================
            _log(f"[2/3] 正在使用 [{self.core_model}] 进行深度重写与植入... (这步耗时较长，请耐心等待)")
            sys_2 = "你现在是一位英语为母语的顶尖专栏作家。"
            usr_2 = (
                f"请根据我提供的原文章，重写并扩写出一篇 600-800 词的高质量英文长文。\n\n"
                f"【原文标题】：{title}\n"
                f"【原文内容（全文）】：\n{source_text}\n\n"
                f"【目标单词池】（共 {len(final_selected)} 个）：\n{selected_words_str}\n\n"
                "【核心写作约束】\n"
                "1. 绝对地道 (Authenticity)：彻底摒弃中式英语 (Chinglish) 和 AI 生成的机器味。\n"
                "2. 句式丰富 (Syntactic Variety)：巧妙交替使用长短句、从句等高级句式。\n"
                "3. 无痕植入与加粗：将我提供的【目标单词池】中的词融合进文章，并将它们（或它们的变形）进行 **加粗**。\n"
                "4. 纯英文输出（致命红线）：文章必须是 100% 纯英文。绝对禁止在英文中夹杂任何汉字（如拼出 'central权威' 这样的畸形句子）！如果原文中有难翻的词，必须用英文意译，只要输出哪怕一个汉字也就是彻底失败！不要有任何解释性中文废话。"
            )
            
            english_article = self._call_llm(sys_2, usr_2, "Step 2", self.core_model, check_stop_callback, stream=True, is_debug=True)

            # Step 2 兜底净化：若模型夹带汉字，先物理清理，避免污染传入 Step 3
            if re.search(r'[\u4e00-\u9fff]', english_article):
                _log("   ⚠️ Step 2 检测到中文污染，正在执行英文净化...")
                english_article = re.sub(r'[\u4e00-\u9fff]+', '', english_article)
                english_article = re.sub(r'[，。！？；：“”‘’（）【】《》、]', ' ', english_article)
                english_article = re.sub(r'\s{2,}', ' ', english_article)
            
            # --- 终极 Python 物理清洗：修复模型发疯式的全局乱加粗 ---
            # 1. 修复前后切段的加粗
            english_article = re.sub(r'\*\*([a-zA-Z\'-]+)\*\*([a-zA-Z\'-]+)', r'**\1\2**', english_article)
            english_article = re.sub(r'([a-zA-Z\'-]+)\*\*([a-zA-Z\'-]+)\*\*', r'**\1\2**', english_article)
            english_article = re.sub(r'\*\*([a-zA-Z\'-]+)\*\*\s+([\'’]s)', r'**\1\2**', english_article)
            
            # 2. 剥夺非法单词的加粗特权！
            target_words_lower = [w.get("word", "").lower() for w in final_selected]
            
            def filter_illegal_bolding(match):
                marked_text = match.group(1)
                
                # 防多词串联乱加粗 (如高亮了完整的一个短语: **a theory he**)
                word_tokens = re.findall(r'[a-zA-Z]+', marked_text)
                if len(word_tokens) >= 3:
                    return marked_text # 直接剥夺加粗
                    
                marked_clean = re.sub(r'[^a-zA-Z]', '', marked_text).lower()
                is_legal = False
                
                for tw in target_words_lower:
                    tw_clean = re.sub(r'[^a-zA-Z]', '', tw).lower()
                    if not tw_clean: continue
                    
                    if marked_clean == tw_clean:
                        is_legal = True
                        break
                        
                    # 计算公共前缀
                    prefix_len = 0
                    for c1, c2 in zip(marked_clean, tw_clean):
                        if c1 == c2: prefix_len += 1
                        else: break
                        
                    # 极度严苛的词干限制，防止 "the" 匹配 "them/theory", "for" 匹配 "forsaken"
                    if len(tw_clean) <= 3:
                        # 短词必须完全相等，最多加简单后缀
                        allowed = [tw_clean, tw_clean+'s', tw_clean+'es', tw_clean+'d', tw_clean+'ed', tw_clean+'ing', tw_clean+'y', tw_clean+'ly',
                                   tw_clean+tw_clean[-1]+'ed', tw_clean+tw_clean[-1]+'ing',
                                   tw_clean[:-1]+'ing', tw_clean[:-1]+'es']
                        if marked_clean in allowed:
                            is_legal = True
                            break
                    elif len(tw_clean) <= 5:
                        if prefix_len >= len(tw_clean) - 1 and abs(len(marked_clean) - len(tw_clean)) <= 4:
                            is_legal = True
                            break
                    else:
                        if prefix_len >= 4 and prefix_len >= len(tw_clean) - 3 and abs(len(marked_clean) - len(tw_clean)) <= 5:
                            is_legal = True
                            break
                            
                return f"**{marked_text}**" if is_legal else marked_text
                
            english_article = re.sub(r'\*\*(.*?)\*\*', filter_illegal_bolding, english_article)
            
            _log("   => 英文长文重写与格式自动修复完成！")
            
            _log("   => 英文长文重写与格式自动修复完成！")
            
            if check_stop_callback and check_stop_callback():
                raise InterruptedError("用户已手动停止任务")

            # ==========================================
            # 第三步：逐段精译与格式化 (Fast Model) — 带验证重试
            # ==========================================
            MAX_TRANSLATION_RETRIES = 2
            translated_article = ""
            
            for retry in range(MAX_TRANSLATION_RETRIES + 1):
                _log(f"[3/3] 正在使用 [{self.core_model}] 进行逐段翻译与排版... (尝试 {retry + 1}/{MAX_TRANSLATION_RETRIES + 1})")
                
                sys_3 = "你是一个英语教材翻译专家。"
                
                usr_3 = (
                    "请将我提供的这篇英文长文逐段翻译成中文。\n\n"
                    "【翻译要求】（极其重要，必须严格遵守）：\n"
                    "1. **只允许输出中文翻译！绝对不要复制或输出任何英文原文！**\n"
                    "2. **格式必须是纯中文段落！** 一段中文，空一行，下一段中文。\n"
                    "3. 必须精准对应。原文有几段，你就输出几段中文翻译！不要自行合并或拆分！\n"
                    "4. 原文英文里加粗的生词（**word**），在翻译成中文时，**中文译文中绝对不要加粗**！请保持中文句子的正常、纯净排版。\n"
                    "5. 直接开始输出中文翻译正文，绝对禁止输出标题、引言、总结或任何单独的词汇释义列表！\n\n"
                    f"【待翻译纯英文长文】：\n{english_article}\n"
                )
                
                translated_article = self._call_llm(sys_3, usr_3, "Step 3", self.core_model, check_stop_callback, stream=True, is_debug=True)
                
                # ── 验证翻译结果质量 ──────────────────────────
                if self._validate_translation(translated_article, english_article):
                    _log(f"   ✅ 翻译验证通过！")
                    
                    # 💡 【核心修改】：通过 Python 进行物理级绝对安全的中英交替拼装！彻底消灭模型拼接引发的幻觉！
                    eng_paras = [p.strip() for p in english_article.split('\n\n') if p.strip()]
                    zh_paras = [p.strip() for p in translated_article.split('\n\n') if p.strip()]
                    
                    bilingual_pairs = []
                    for i in range(max(len(eng_paras), len(zh_paras))):
                        if i < len(eng_paras): bilingual_pairs.append(eng_paras[i])
                        if i < len(zh_paras): bilingual_pairs.append(zh_paras[i])
                        
                    final_bilingual_text = '\n\n'.join(bilingual_pairs)
                    break
                else:
                    fail_reason = self._last_validation_reason or "未知校验失败"
                    if retry < MAX_TRANSLATION_RETRIES:
                        _log(f"   ⚠️ 翻译校验失败：{fail_reason}")
                        _log(f"   ↪ 触发第 {retry + 2} 次重试...")
                    else:
                        _log(f"   ❌ 翻译验证失败，已达到最大重试次数。原因：{fail_reason}")
                        raise ValueError(f"翻译校验失败：{fail_reason}")
            
            # Python 本地极速拼接最终 Markdown
            vocab_list_text = ""
            for w in final_selected:
                vocab_list_text += f"- **{w.get('word', '')}** {w.get('phonetic', '')} {w.get('definition', '')}\n"
                
            final_article = f"# {title}\n\n### 核心词汇\n\n{vocab_list_text}\n\n### 双语正文\n\n{final_bilingual_text}"
            
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