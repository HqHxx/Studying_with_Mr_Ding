import os
import re

from fpdf import FPDF
from app_paths import INTERNAL_DIR


class DarkPDF(FPDF):
    def header(self) -> None:
        # 每页开始时先铺设暗黑背景。
        self.set_fill_color(24, 24, 24)
        self.rect(0, 0, self.w, self.h, style="F")
        self.set_text_color(204, 204, 204)


def export_to_pdf(article_text: str, pdf_file_path: str) -> None:
    """将 Markdown 文章或 Markdown 文件导出为护眼暗黑 PDF。"""
    if not isinstance(article_text, str):
        article_text = str(article_text or "")

    if os.path.isfile(article_text) and article_text.lower().endswith(".md"):
        with open(article_text, "r", encoding="utf-8") as file:
            article_text = file.read()

    if not article_text.strip():
        raise ValueError("文章内容为空，无法导出 PDF")

    def sanitize_text(text: str) -> str:
        """强制替换容易导致字体越界的富文本符号为标准 ASCII 符号。"""
        replacements = {
            '‘': "'", '’': "'",
            '“': '"', '”': '"',
            '…': "...",
            # 修复语料库中被错误按 Latin-1 解码的 UTF-8 字符 (Mojibake)
            'â\x80\x94': "—",
            'â\x80\x93': "–",
            'â\x80\x99': "'",
            'â\x80\x98': "'",
            'â\x80\x9c': '"',
            'â\x80\x9d': '"',
            'â\x80\xa6': "...",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # --- 修复 Markdown 碎纸机式硬换行 ---
        # 0. 保护标题的独立性：如果大模型在标题后漏打双回车，强制修补为双回车隔离
        text = re.sub(r'(?m)^(#+ .*?)\n(?!\n)', r'\1<PARA>', text)
        
        # 1. 保护正常的段落间距（双换行）
        text = re.sub(r'\n{2,}', '<PARA>', text)
        
        # 1.5 保护列表的单换行（如果换行后紧跟 -、* 或 # 或数字.）
        text = re.sub(r'\n(?=\s*[-*#]|\s*\d+\.)', '<LINE_BREAK>', text)
        
        # 2. 将段落内的单换行替换为智能空格（英文变空格，中文变无缝）
        text = text.replace('\n', ' ')
        # 消除中文之间或中文与标点之间的空格
        text = re.sub(r'([\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef])\s+', r'\1', text)
        text = re.sub(r'\s+([\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef])', r'\1', text)
        
        # 2.5 强制拆解中英文粘连（防止 fpdf2 词法分析器将其误认成超长英文单词导致无法换行和两端对齐拉伸）
        text = re.sub(r'([A-Za-z0-9)\]>.!?])([\u4e00-\u9fa5])', r'\1 \2', text)
        text = re.sub(r'([\u4e00-\u9fa5])([A-Za-z0-9(\[<])', r'\1 \2', text)
        
        # 3. 恢复真正的换行符
        text = text.replace('<PARA>', '\n\n')
        text = text.replace('<LINE_BREAK>', '\n')
        
        return text

    article_text = sanitize_text(article_text)

    pdf = DarkPDF(format="A4")
    # 强制设置 25 的下边距，防止贴边被切断
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.set_margins(15, 15, 25)
    pdf.add_page()

    # 第一页显式绘制背景，确保效果稳定。
    pdf.set_fill_color(24, 24, 24)
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")
    pdf.set_text_color(204, 204, 204)

    import warnings
    main_font_loaded = False
    try:
        base_dir = str(INTERNAL_DIR)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pdf.add_font("TimesNewRoman", style="", fname=os.path.join(base_dir, "times.ttf"))
            pdf.add_font("TimesNewRoman", style="B", fname=os.path.join(base_dir, "timesbd.ttf"))
            pdf.add_font("TimesNewRoman", style="I", fname=os.path.join(base_dir, "timesi.ttf"))
            pdf.add_font("TimesNewRoman", style="BI", fname=os.path.join(base_dir, "timesbi.ttf"))
        pdf.set_font("TimesNewRoman", size=14)
        main_font_loaded = True
    except Exception as e:
        print(f"Error loading Times fonts: {e}")
        pdf.set_font("Helvetica", size=14)

    try:
        simkai_path = os.path.join(str(INTERNAL_DIR), "simkai.ttf")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # 为中文字体也注册常规和加粗（直接复用楷体，fpdf2 会处理）
            pdf.add_font("SimKai", style="", fname=simkai_path)
            pdf.add_font("SimKai", style="B", fname=simkai_path)
            pdf.add_font("SimKai", style="I", fname=simkai_path)
            pdf.add_font("SimKai", style="BI", fname=simkai_path)
            pdf.set_fallback_fonts(["SimKai"])
    except Exception as e:
        print(f"Error loading SimKai font: {e}")

    def has_chinese(text: str) -> bool:
        return any(
            '\u4e00' <= char <= '\u9fff' or
            '\u3000' <= char <= '\u303f' or
            '\uff00' <= char <= '\uffef'
            for char in text
        )

    for raw_line in article_text.splitlines():
        line = raw_line.strip()

        # 核心防御机制：先清理超出 BMP 的字符
        line = re.sub(r"[^\u0000-\uFFFF]", "", line)

        # 规范化 Markdown 降级处理：过滤掉单星号和单下划线，只保留粗体 **
        # 把加粗临时替换为安全占位符
        line = line.replace("**", "\0BOLD\0")
        line = line.replace("__", "\0BOLD\0")
        # 彻底清除所有的星号和下划线（核弹级清除，防止任何长下划线/斜体跨页导致引擎崩溃截断）
        line = line.replace("*", "")
        line = line.replace("_", "")
        # 恢复粗体占位符为标准 Markdown 加粗
        line = line.replace("\0BOLD\0", "**")

        if not line:
            pdf.ln(4)
            continue

        is_chinese_line = has_chinese(line)

        if line.startswith("#"):
            # 标题处理（根据 # 的数量计算级别）
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip() or "Untitled"
            
            font_size = 22 if level == 1 else (18 if level == 2 else 16)
            
            if main_font_loaded:
                pdf.set_font("TimesNewRoman", style="B", size=font_size)
            else:
                pdf.set_font("Helvetica", style="B", size=font_size)

            pdf.multi_cell(0, 10, text=title, align="C" if level == 1 else "L", markdown=True)
            pdf.ln(2)
            
            # 恢复正文字体
            if main_font_loaded:
                pdf.set_font("TimesNewRoman", size=14)
            else:
                pdf.set_font("Helvetica", size=14)
            continue

        # 渲染正文（启用 Markdown 解析以支持加粗）
        if main_font_loaded:
            pdf.set_font("TimesNewRoman", size=14)
        else:
            pdf.set_font("Helvetica", size=14)

        # 移除之前的强制插空格逻辑，交由 fpdf2 的内置 CJK 支持去正确处理换行

        try:
            pdf.multi_cell(0, 8, text=line, markdown=True, align="L")
        except Exception:
            try:
                # 降级不带 markdown，防止语法错误导致崩溃
                pdf.multi_cell(0, 8, text=line, align="L")
            except Exception as e:
                # 终极防御：如果发生极其罕见的不可截断超长字符串错误，强制暴力截断
                safe_text = line[:80] + "... [Text Truncated due to FPDF render limits]"
                pdf.multi_cell(0, 8, text=safe_text, align="L")
            
        pdf.ln(1)

    pdf.output(pdf_file_path)