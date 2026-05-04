"""CET-4/6 学习助手 — CustomTkinter 桌面端主入口。

阶段三：三端联动 — 多词库 + 多分类 + 动态选词植入。
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import shutil
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image
import os

from content_engine import ContentEngine, save_used_articles
from db_manager import DBManager
from pdf_generator import export_to_pdf
from app_paths import BASE_DIR, INTERNAL_DIR

# ── 全局路径与常量 ─────────────────────────────────────────────
ARCHIVE_ROOT = BASE_DIR / "archives"
MARKDOWN_ARCHIVE_DIR = ARCHIVE_ROOT / "markdown"
PDF_ARCHIVE_DIR = ARCHIVE_ROOT / "pdf"
EPUB_ARCHIVE_DIR = ARCHIVE_ROOT / "epub"
API_CONFIG_PATH = BASE_DIR / ".api_config.json"
LOCAL_CORPUS_PATH = INTERNAL_DIR / "local_corpus.json"

# 确保目录存在
ARCHIVE_ROOT.mkdir(exist_ok=True)
MARKDOWN_ARCHIVE_DIR.mkdir(exist_ok=True)
PDF_ARCHIVE_DIR.mkdir(exist_ok=True)
EPUB_ARCHIVE_DIR.mkdir(exist_ok=True)

# ── 主题 / 外观 ───────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 尝试设置高 DPI 感知（仅 Windows）
if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


# ── API 配置 持久化 ────────────────────────────────────────────
def load_api_config() -> dict:
    """读取多配置 API 文件。"""
    if not API_CONFIG_PATH.exists():
        return {"profiles": {}, "last_used": ""}
    try:
        data = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        if "profiles" not in data:
            data = {"profiles": {"默认配置": data}, "last_used": "默认配置"}
            API_CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
    except (OSError, json.JSONDecodeError):
        return {"profiles": {}, "last_used": ""}




def sanitize_filename(text: str) -> str:
    """将主题转为适合文件名的安全字符串。"""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", text.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "untitled"


# ── 主窗口 ─────────────────────────────────────────────────────
# 可选的难度级别和文章题材
LEVEL_OPTIONS = ["CET-4", "CET-6", "考研", "托福"]
CATEGORY_OPTIONS = ["history", "science"]


class App(ctk.CTk):
    """知识学爆桌面端主窗口。"""

    WINDOW_TITLE = "知识学爆"
    WINDOW_SIZE = (1100, 780)

    def __init__(self) -> None:
        super().__init__()

        self.title(self.WINDOW_TITLE)
        self.geometry(f"{self.WINDOW_SIZE[0]}x{self.WINDOW_SIZE[1]}")
        self.minsize(900, 600)
        
        # ── 设置窗口图标 ──
        icon_path = INTERNAL_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # 确保数据库文件存在（从内部资源复制，以保留打包的词库）
        # 将生成的运行词库名改为"学习进度词库.db"并放入 data 文件夹下，保持根目录整洁
        data_dir = BASE_DIR / "data"
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "学习进度词库.db"
        if not db_path.exists():
            # 优先从 data/cet4_words.db 读取模板（开发环境）
            tmpl_db = data_dir / "cet4_words.db"
            if not tmpl_db.exists():
                # 回退到内部资源目录（PyInstaller 打包环境）
                tmpl_db = INTERNAL_DIR / "data" / "cet4_words.db"
            if tmpl_db.exists():
                shutil.copy(tmpl_db, db_path)

        # 数据库
        self.db = DBManager(str(db_path))
        self.db.initialize()

        # 加载 API 配置
        self._api_config = load_api_config()

        # ── 多线程控制 ────────────────────────────────────────
        self._stop_flag = threading.Event()   # 紧急刹车信号
        self._worker_thread: threading.Thread | None = None
        self.current_task_id: str | None = None

        # 构建界面
        self._build_ui()

    # ── 字体常量 ──────────────────────────────────────────────
    FONT_UI = ("Microsoft YaHei", 13)
    FONT_UI_BOLD = ("Microsoft YaHei", 13, "bold")
    FONT_TITLE = ("Microsoft YaHei", 16, "bold")
    FONT_HERO = ("Microsoft YaHei", 26, "bold")
    FONT_BTN_BIG = ("Microsoft YaHei", 20, "bold")
    FONT_BTN_MED = ("Microsoft YaHei", 14, "bold")
    FONT_TEXT = ("Microsoft YaHei", 14)
    FONT_TEXT_BOLD = ("Microsoft YaHei", 14, "bold")
    FONT_HEADING = ("Microsoft YaHei", 18, "bold")

    # ── 界面构建 ──────────────────────────────────────────────
    def _build_ui(self) -> None:
        # 标题栏
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 0))
        
        logo_path = INTERNAL_DIR / "logo.png"
        app_image = None
        if logo_path.exists():
            try:
                pil_image = Image.open(logo_path)
                app_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(32, 32))
            except Exception:
                pass
                
        if app_image:
            ctk.CTkLabel(
                header,
                text="  知识学爆",
                image=app_image,
                compound="left",
                font=self.FONT_HERO,
            ).pack(side="left")
        else:
            ctk.CTkLabel(
                header,
                text="📖  知识学爆",
                font=self.FONT_HERO,
            ).pack(side="left")

        # 学习进度概要（右上角）
        self._progress_label = ctk.CTkLabel(
            header,
            text="",
            font=self.FONT_UI,
            text_color=("gray40", "gray70"),
        )
        self._progress_label.pack(side="right", padx=10)
        self._refresh_progress_label()

        # ── TabView ───────────────────────────────────────────
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(12, 20))

        self.tab_generate = self.tabview.add("🚀 批量生成中心")
        self.tab_archive = self.tabview.add("📚 历史归档阅读")

        self._build_tab_generate()
        self._build_tab_archive()

    # ── Tab 1: 批量生成中心 ───────────────────────────────────
    def _build_tab_generate(self) -> None:
        tab = self.tab_generate

        # ── 顶部容器（支持自然压缩） ──
        self.top_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.top_container.pack(side="top", fill="both", expand=True)

        # ── API 配置区域 ──────────────────────────────────────
        self.api_frame = ctk.CTkFrame(self.top_container, corner_radius=10)
        self.api_frame.pack(fill="x", padx=16, pady=(12, 8))
        self.api_frame.grid_columnconfigure(1, weight=1)
        self.api_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            self.api_frame, text="⚙️  模型 API 配置", font=self.FONT_TITLE,
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=14, pady=(12, 10))

        profiles = list(self._api_config.get("profiles", {}).keys())
        last_used = self._api_config.get("last_used", "默认配置")
        if not profiles:
            profiles = ["默认配置"]

        self._current_profile_data = self._api_config.get("profiles", {}).get(last_used, {})

        # Row 1: Profile Selector + Name Entry + Save Button
        ctk.CTkLabel(self.api_frame, text="配置预设", font=self.FONT_UI).grid(
            row=1, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.combo_profile = ctk.CTkComboBox(
            self.api_frame, values=profiles, command=self._on_profile_selected
        )
        self.combo_profile.set(last_used if last_used in profiles else profiles[0])
        self.combo_profile.grid(row=1, column=1, sticky="ew", padx=(4, 20), pady=8)

        ctk.CTkButton(
            self.api_frame, text="🗑️ 删除", width=70, font=self.FONT_UI,
            command=self._on_delete_profile, fg_color="#C82B2B", hover_color="#8f1b1b"
        ).grid(row=1, column=2, padx=(4, 14), pady=8, sticky="w")

        # Row 2: Base URL
        ctk.CTkLabel(self.api_frame, text="Base URL", font=self.FONT_UI).grid(
            row=2, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.entry_base_url = ctk.CTkEntry(self.api_frame, placeholder_text="https://...", font=self.FONT_UI)
        self.entry_base_url.grid(row=2, column=1, columnspan=4, sticky="ew", padx=(4, 14), pady=8)
        self.entry_base_url.insert(0, self._current_profile_data.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"))

        # Row 3: Fast Model (left) + Core Model (right)
        ctk.CTkLabel(self.api_frame, text="Fast Model", font=self.FONT_UI).grid(
            row=3, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.entry_fast_model = ctk.CTkEntry(self.api_frame, placeholder_text="轻量级模型", font=self.FONT_UI)
        self.entry_fast_model.grid(row=3, column=1, sticky="ew", padx=(4, 20), pady=8)
        self.entry_fast_model.insert(0, self._current_profile_data.get("fast_model", "doubao-seed-2-0-code-preview-260215"))

        ctk.CTkLabel(self.api_frame, text="Core Model", font=self.FONT_UI).grid(
            row=3, column=2, sticky="e", padx=(20, 8), pady=8
        )
        self.entry_core_model = ctk.CTkEntry(self.api_frame, placeholder_text="强推理模型", font=self.FONT_UI)
        self.entry_core_model.grid(row=3, column=3, sticky="ew", padx=(4, 14), pady=8)
        self.entry_core_model.insert(0, self._current_profile_data.get("core_model", "deepseek-v3-2-251201"))

        # Row 4: API Key + Save button
        ctk.CTkLabel(self.api_frame, text="API Key", font=self.FONT_UI).grid(
            row=4, column=0, sticky="e", padx=(14, 8), pady=(8, 14)
        )
        self.entry_api_key = ctk.CTkEntry(
            self.api_frame, placeholder_text="sk-...", show="*", font=self.FONT_UI
        )
        self.entry_api_key.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(4, 10), pady=(8, 14))
        self.entry_api_key.insert(0, self._current_profile_data.get("api_key", ""))

        ctk.CTkButton(
            self.api_frame, text="💾 保存/覆盖当前名称预设", width=150, font=self.FONT_UI,
            command=self._on_save_profile,
        ).grid(row=4, column=4, padx=(5, 14), pady=(8, 14), sticky="e")
        # ── 生成控制区 ────────────────────────────────────────
        self.ctrl_frame = ctk.CTkFrame(self.top_container, corner_radius=10)
        self.ctrl_frame.pack(fill="x", padx=16, pady=8)
        self.ctrl_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.ctrl_frame, text="📝  生成设置", font=self.FONT_TITLE,
        ).grid(row=0, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 10))

        # 模式切换与批量导入
        mode_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        mode_frame.grid(row=1, column=0, columnspan=6, sticky="w", padx=14, pady=(0, 6))
        
        ctk.CTkLabel(mode_frame, text="语料来源:", font=self.FONT_UI).pack(side="left", padx=(0, 10))
        
        self.source_mode_var = ctk.StringVar(value="builtin")
        ctk.CTkRadioButton(mode_frame, text="内置系统语料", font=self.FONT_UI, variable=self.source_mode_var, value="builtin").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(mode_frame, text="仅自定义语料", font=self.FONT_UI, variable=self.source_mode_var, value="custom").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(mode_frame, text="混合抽取", font=self.FONT_UI, variable=self.source_mode_var, value="mixed").pack(side="left", padx=(0, 30))
        
        # 批量导入按钮与帮助
        ctk.CTkButton(mode_frame, text="📁 批量导入本地文件", font=self.FONT_UI, width=140, fg_color="#3498db", hover_color="#2980b9", command=self._on_import_custom_corpus).pack(side="left", padx=(10, 5))
        ctk.CTkButton(mode_frame, text="[?]", font=self.FONT_UI, width=28, command=self._on_show_import_help).pack(side="left")

        # 随机抽取参数区
        self.random_param_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        self.random_param_frame.grid(row=2, column=0, columnspan=6, sticky="w", pady=(0, 14))

        # 生成篇数
        ctk.CTkLabel(self.random_param_frame, text="生成篇数", font=self.FONT_UI).grid(
            row=0, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.count_var = ctk.StringVar(value="1")
        self.entry_count = ctk.CTkEntry(self.random_param_frame, width=80, textvariable=self.count_var, font=self.FONT_UI)
        self.entry_count.grid(row=0, column=1, sticky="w", padx=(4, 10), pady=8)

        # 目标难度
        ctk.CTkLabel(self.random_param_frame, text="目标难度", font=self.FONT_UI).grid(
            row=0, column=2, sticky="e", padx=(20, 8), pady=8
        )
        self.combo_level = ctk.CTkComboBox(
            self.random_param_frame, width=120, values=LEVEL_OPTIONS, state="readonly",
            font=self.FONT_UI, command=self._on_level_changed
        )
        self.combo_level.grid(row=0, column=3, sticky="w", padx=(4, 10), pady=8)
        self.combo_level.set("CET-4")

        # 文章题材
        ctk.CTkLabel(self.random_param_frame, text="文章题材", font=self.FONT_UI).grid(
            row=0, column=4, sticky="e", padx=(20, 8), pady=8
        )
        self.combo_category = ctk.CTkComboBox(
            self.random_param_frame, width=120, values=CATEGORY_OPTIONS, state="readonly",
            font=self.FONT_UI,
        )
        self.combo_category.grid(row=0, column=5, sticky="w", padx=(4, 14), pady=8)
        self.combo_category.set("history")


        # ── 按钮区域（开始 + 停止） ──────────────────────────
        self.btn_frame = ctk.CTkFrame(self.top_container, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=16, pady=(8, 6))

        self.btn_start = ctk.CTkButton(
            self.btn_frame,
            text="✨  开 始 生 成",
            font=self.FONT_BTN_BIG,
            height=56,
            corner_radius=14,
            command=self._on_start_generate,
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            self.btn_frame,
            text="🛑 停止",
            font=self.FONT_BTN_MED,
            height=56,
            corner_radius=14,
            fg_color="#8B0000",
            hover_color="#B22222",
            state="disabled",
            command=self._on_stop_generate,
        )
        self.btn_stop.pack(side="right", ipadx=16)

        # ── 重置进度区域 ──────────────────────────────────────
        self.reset_frame = ctk.CTkFrame(self.top_container, corner_radius=10)
        self.reset_frame.pack(fill="x", padx=16, pady=(4, 8))

        ctk.CTkLabel(
            self.reset_frame, text="🔄  学习进度管理", font=self.FONT_TITLE,
        ).pack(anchor="w", padx=14, pady=(10, 8))

        reset_btn_row = ctk.CTkFrame(self.reset_frame, fg_color="transparent")
        reset_btn_row.pack(fill="x", padx=14, pady=(0, 10))

        self.btn_reset_words = ctk.CTkButton(
            reset_btn_row,
            text="📝 重置单词进度",
            font=self.FONT_UI,
            width=160,
            fg_color="#6c5ce7",
            hover_color="#5b4cdb",
            command=self._on_reset_words,
        )
        self.btn_reset_words.pack(side="left", padx=(0, 10))

        self.btn_reset_topics = ctk.CTkButton(
            reset_btn_row,
            text="📄 重置文章记录",
            font=self.FONT_UI,
            width=160,
            fg_color="#00b894",
            hover_color="#00a383",
            command=self._on_reset_topics,
        )
        self.btn_reset_topics.pack(side="left", padx=(0, 10))

        self.btn_reset_all = ctk.CTkButton(
            reset_btn_row,
            text="💥 重置全部",
            font=self.FONT_UI,
            width=120,
            fg_color="#C82B2B",
            hover_color="#8f1b1b",
            command=self._on_reset_all,
        )
        self.btn_reset_all.pack(side="left")

        # ── 日志输出（先 pack，沉在最底） ──────────────────────
        self.log_textbox = ctk.CTkTextbox(
            tab,
            font=self.FONT_TEXT,
            corner_radius=10,
            state="disabled",
            wrap="word",
            height=150
        )
        self.log_textbox.pack(side="bottom", fill="x", padx=16, pady=(0, 12))

        self.log_textbox.tag_config("red", foreground="#ff4757")
        self.log_textbox.tag_config("green", foreground="#2ed573")
        self.log_textbox.tag_config("white", foreground="white")

        # ── 可拖拽分割线（后 pack，叠在日志框上方） ────────────
        self.sash = ctk.CTkFrame(tab, height=5, corner_radius=2, fg_color="gray30", cursor="sb_v_double_arrow")
        self.sash.pack(side="bottom", fill="x", padx=60, pady=(4, 4))
        self.sash.bind("<B1-Motion>", self._on_sash_drag)
        self.sash.bind("<Button-1>", self._on_sash_press)

        self.sash.bind("<Enter>", lambda e: self.sash.configure(fg_color="#3498db"))
        self.sash.bind("<Leave>", lambda e: self.sash.configure(fg_color="gray30"))

        self.log_message("就绪。请配置 API 参数后点击「开始生成」。", level="info")

    # ── Tab 2: 历史归档阅读 ───────────────────────────────────
    def _build_tab_archive(self) -> None:
        tab = self.tab_archive

        # 控制栏 (Grid layout for stretch)
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(12, 8))
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="选择归档文件：", font=self.FONT_UI).grid(
            row=0, column=0, padx=(0, 8), pady=8
        )

        # ── 文件名显示 + 选择按钮 ────────────────────────────
        self.archive_display = ctk.CTkEntry(
            bar, font=self.FONT_UI, state="readonly", width=400
        )
        self.archive_display.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=8)
        self.archive_display.configure(state="normal")
        self.archive_display.insert(0, "（点击右侧按钮选择）")
        self.archive_display.configure(state="readonly")

        self.btn_select_archive = ctk.CTkButton(
            bar, text="📂 选择归档 ▼", width=120, font=self.FONT_UI,
            command=self._open_file_selector,
        )
        self.btn_select_archive.grid(row=0, column=2, padx=5, pady=8)

        btn_w = 100
        ctk.CTkButton(
            bar, text="  预览", width=btn_w, font=self.FONT_UI,
            command=self._on_preview_archive,
        ).grid(row=0, column=3, padx=5, pady=8)

        ctk.CTkButton(
            bar, text="📚  EPUB", width=btn_w, font=self.FONT_UI,
            fg_color="#27ae60", hover_color="#2ecc71",
            command=self._on_export_epub,
        ).grid(row=0, column=4, padx=5, pady=8)

        ctk.CTkButton(
            bar, text="🖨  排版", width=btn_w, font=self.FONT_UI,
            fg_color="#e67e22", hover_color="#d35400",
            command=self._on_regenerate_pdfs,
        ).grid(row=0, column=5, padx=5, pady=8)

        # 预览文本框（只读 + 占位提示）
        self.preview_textbox = ctk.CTkTextbox(
            tab,
            font=self.FONT_TEXT,
            corner_radius=10,
            state="normal",
            wrap="word",
            spacing2=3,
            spacing3=6,
        )
        self.preview_textbox.pack(fill="both", expand=True, padx=16, pady=(4, 12))
        # 配置富文本 tag
        self.preview_textbox._textbox.tag_configure("bold", font=self.FONT_TEXT_BOLD)
        self.preview_textbox._textbox.tag_configure("heading", font=self.FONT_HEADING, spacing1=10, spacing3=6)
        self.preview_textbox.insert("1.0", "\n\n\n\n\t\t\t\t👈 请在上方选择一份历史特刊进行预览...")
        self.preview_textbox.configure(state="disabled")

        # 初始加载归档列表（静默更新内部缓存，不弹窗）
        self._refresh_archive_cache()


    # ── 分割线与导入功能 ──────────────────────────────────────
    def _on_sash_press(self, event) -> None:
        self._sash_start_y = event.y_root
        self._log_start_height = self.log_textbox.winfo_height()

    def _on_sash_drag(self, event) -> None:
        dy = self._sash_start_y - event.y_root  # 向上拖动为正值
        new_height = self._log_start_height + dy
        max_height = self.winfo_height() / 2.5
        if new_height < 60: new_height = 60
        if new_height > max_height: new_height = max_height
        self.log_textbox.configure(height=int(new_height))

    def _on_show_import_help(self) -> None:
        top = ctk.CTkToplevel(self)
        top.title("📖 语料导入标准说明")
        top.geometry("450x260")
        top.attributes("-topmost", True)
        
        msg = (
            "【批量导入本地文件规则】\n\n"
            "1. 支持的格式：仅限 .txt 和 .md 纯文本文件。\n\n"
            "2. 编码建议：强烈推荐使用 UTF-8 编码，\n"
            "   若文件存在特殊字符导致解析失败将自动跳过。\n\n"
            "3. 解析规则：系统会自动以“文件名”（去后缀）\n"
            "   作为文章标题，请尽量保持文件名简洁，\n"
            "   文件内容将作为正文导入自定义语料库。\n\n"
            "导入的数据保存在 data/custom_corpus.json 中，\n"
            "不会影响自带的 local_corpus.json。"
        )
        lbl = ctk.CTkLabel(top, text=msg, font=self.FONT_TEXT, justify="left", wraplength=400)
        lbl.pack(padx=20, pady=20, expand=True, fill="both")

    def _on_import_custom_corpus(self) -> None:
        from tkinter import filedialog
        import json
        file_paths = filedialog.askopenfilenames(
            title="选择文本或Markdown文件",
            filetypes=[("Text Files", "*.txt"), ("Markdown", "*.md"), ("All Files", "*.*")]
        )
        if not file_paths:
            return
            
        success_count = 0
        skip_count = 0
        
        custom_db_path = BASE_DIR / "data" / "custom_corpus.json"
        
        # 加载已有
        existing_data = []
        if custom_db_path.exists():
            try:
                existing_data = json.loads(custom_db_path.read_text(encoding="utf-8"))
            except Exception:
                pass
                
        for fp in file_paths:
            p = Path(fp)
            if p.suffix.lower() not in [".txt", ".md"]:
                skip_count += 1
                continue
                
            content = ""
            try:
                content = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    content = p.read_text(encoding="gbk")
                except Exception:
                    self.log_message(f"跳过文件 {p.name}: 编码无法识别", level="error")
                    skip_count += 1
                    continue
            
            content = content.strip()
            if not content:
                skip_count += 1
                continue
                
            existing_data.append({
                "title": p.stem,
                "content": content,
                "category": "custom"
            })
            success_count += 1
            
        if success_count > 0:
            custom_db_path.parent.mkdir(parents=True, exist_ok=True)
            custom_db_path.write_text(json.dumps(existing_data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.log_message(f"导入成功: {success_count} 篇文章已添加到自定义语料库。", level="success")
        if skip_count > 0:
            self.log_message(f"跳过了 {skip_count} 个不符合要求的文件。", level="error")

    # ══════════════════════════════════════════════════════════
    #  回调方法
    # ══════════════════════════════════════════════════════════
    def _on_profile_selected(self, choice: str) -> None:
        profiles = self._api_config.get("profiles", {})
        if choice in profiles:
            data = profiles[choice]
            self.entry_base_url.delete(0, "end")
            self.entry_base_url.insert(0, data.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"))
            self.entry_fast_model.delete(0, "end")
            self.entry_fast_model.insert(0, data.get("fast_model", "doubao-seed-2-0-code-preview-260215"))
            self.entry_core_model.delete(0, "end")
            self.entry_core_model.insert(0, data.get("core_model", "deepseek-v3-2-251201"))
            self.entry_api_key.delete(0, "end")
            self.entry_api_key.insert(0, data.get("api_key", ""))
            
            self._api_config["last_used"] = choice
            self._save_api_config_file()
            self._log(f"✅ 已加载预设: {choice}")
            
    def _on_delete_profile(self) -> None:
        choice = self.combo_profile.get().strip()
        if choice in self._api_config.get("profiles", {}):
            del self._api_config["profiles"][choice]
            if len(self._api_config["profiles"]) == 0:
                self._api_config["profiles"]["默认配置"] = {}
                last = "默认配置"
            else:
                last = list(self._api_config["profiles"].keys())[0]
            self._api_config["last_used"] = last
            self._save_api_config_file()
            self.combo_profile.configure(values=list(self._api_config["profiles"].keys()))
            self.combo_profile.set(last)
            self._on_profile_selected(last)
            self._log(f"🗑️ 已删除预设: {choice}")

    def _on_save_profile(self) -> None:
        """保存或覆盖组合框上名称对应的配置。"""
        choice = self.combo_profile.get().strip()
        if not choice:
            self._log("⚠️ 请在预设下拉框中输入或选择一个名称（如: 通义千问配置）！")
            return
            
        profiles = self._api_config.get("profiles", {})
        if choice not in profiles and len(profiles) >= 10:
            self._log("⚠️ 最多只能保存 10 组预设，请先选择需要删除的预设点 [删除]。")
            return
            
        config = {
            "base_url": self.entry_base_url.get().strip(),
            "fast_model": self.entry_fast_model.get().strip(),
            "core_model": self.entry_core_model.get().strip(),
            "api_key": self.entry_api_key.get().strip(),
        }
        profiles[choice] = config
        self._api_config["profiles"] = profiles
        self._api_config["last_used"] = choice
        self._save_api_config_file()
        
        self.combo_profile.configure(values=list(profiles.keys()))
        self.combo_profile.set(choice)
        self._log(f"✅ 配置 `{choice}` 已保存（最多支持10组）。")

    def _save_api_config_file(self) -> None:
        try:
            API_CONFIG_PATH.write_text(
                json.dumps(self._api_config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass
    # ── 开始生成 ────────────────────────────────────────────────────────────
    def _on_start_generate(self) -> None:
        """校验参数并启动后台生成线程。"""
        try:
            try:
                base_url = self.entry_base_url.get().strip()
                fast_model = self.entry_fast_model.get().strip()
                core_model = self.entry_core_model.get().strip()
                api_key = self.entry_api_key.get().strip()

                if not base_url or not fast_model or not core_model or not api_key:
                    self._log("⚠️ 请先填写完整的 API 配置（Base URL、Fast Model、Core Model、API Key）。", level="red")
                    return

                mode = self.source_mode_var.get()
                level = self.combo_level.get()
                category = self.combo_category.get()
                
                try:
                    count = int(self.count_var.get().strip())
                    if count < 1: raise ValueError
                except ValueError:
                    self._log("⚠️ 生成篇数必须为正整数。", level="red")
                    return

                import pathlib
                LOCAL_CORPUS_PATH = pathlib.Path("local_corpus.json")
                CUSTOM_CORPUS_PATH = pathlib.Path("custom_corpus.json")

                if mode in ("builtin", "mixed") and not LOCAL_CORPUS_PATH.exists():
                    self._log("⚠️ 未找到 local_corpus.json，请先运行工具生成测试语料库。", level="red")
                    if mode == "builtin": return

                if mode in ("custom", "mixed") and not CUSTOM_CORPUS_PATH.exists():
                    self._log("⚠️ 未找到 custom_corpus.json，请先批量导入自定义语料。", level="red")
                    if mode == "custom": return

                self._set_running(True)
                self._stop_flag.clear()
                
                import time
                self.current_task_id = str(time.time())
                task_id = self.current_task_id

                self._log("━" * 50)
                self._log(f"🚀 生成任务启动  |  来源模式: {mode}  |  目标: {count} 篇  |  {level} / {category}")
                self._log(f"   Base URL   : {base_url}")
                self._log(f"   Fast Model : {fast_model}")
                self._log(f"   Core Model : {core_model}")

                import threading
                self._worker_thread = threading.Thread(
                    target=self._batch_generate_worker,
                    args=(base_url, fast_model, core_model, api_key, count, level, category, task_id, mode),
                    daemon=True,
                )
                self._worker_thread.start()
            except Exception as inner_e:
                self._log(f"[UI 错误] 无法启动生成任务: {str(inner_e)}", level="red")
                raise
        except Exception as e:
            try:
                self._log(f"[UI 致命错误] {str(e)}", level="red")
            except Exception as log_fail:
                print(f"[致命错误] 日志输出也失败了: {log_fail}")
                print(f"[原始错误] {e}")
                import traceback
                traceback.print_exc()

    # ── 停止生成 ──────────────────────────────────────────────
    def _on_stop_generate(self) -> None:
        """立刻将当前任务设为遗弃状态，前台瞬间恢复可用。"""
        self._stop_flag.set()
        self.current_task_id = None
        
        # 不要通过 after，因为我们要瞬间响应！可以直接写底层 log 或由 after 代理
        # 我们用 _log 直接强制写进 UI
        self._log("🛑 [强制终止] 任务已切断！")
        self._set_running(False)

    # ══════════════════════════════════════════════════════════
    #  后台批量生成 Worker（在子线程中运行）
    # ══════════════════════════════════════════════════════════
    def _batch_generate_worker(
        self, base_url: str, fast_model: str, core_model: str, api_key: str, count: int,
        level: str, category: str, task_id: str, mode: str = "builtin"
    ) -> None:
        """在独立线程中运行的批量生成循环。所有 UI 操作通过 after() 调度。"""
        def is_orphaned() -> bool:
            return self.current_task_id != task_id or self._stop_flag.is_set()

        def task_safe_log(msg: str):
            if not is_orphaned():
                self._safe_log(msg)

        success_count = 0
        failed_count = 0

        try:
            engine = ContentEngine(
                api_key=api_key,
                base_url=base_url,
                fast_model=fast_model,
                core_model=core_model,
                corpus_mode=mode,
            )
            task_safe_log(f"📚 本地语料库已加载，共 {len(engine.corpus)} 篇素材")
            task_safe_log(f"   词库级别: {level}  |  文章分类: {category}")

            for i in range(count):
                # ── 检查点 1: 循环开始 ────────────────────────
                if is_orphaned():
                    return

                task_safe_log(f"\n{'─'*40}")
                task_safe_log(f"📄 正在处理第 {i + 1}/{count} 篇...")

                # ── 按级别抽取候选生词（300 个） ──────────────
                words_pool = self.db.get_unlearned_words(limit=300, level=level)
                if not words_pool:
                    task_safe_log(f"⚠️ [{level}] 未学生词不足，任务提前结束。")
                    break

                task_safe_log(f"   候选生词池: {len(words_pool)} 个 ({level})")

                # ── 检查点 2: API 调用前 ──────────────────────
                if is_orphaned():
                    return

                # ── 调用大模型重写文章（引擎内部按分类选文） ──
                task_safe_log(f"   正在从 [{category}] 分类中选文并调用大模型...")

                try:
                    article, used_words, title = engine.generate_article(
                        words_pool, category=category, level=level,
                        log_callback=task_safe_log,
                        check_stop_callback=is_orphaned,
                        
                    )
                except InterruptedError as ie:
                    if is_orphaned(): return
                    task_safe_log(f"   🛑 {ie}")
                    break
                except Exception as exc:
                    if is_orphaned(): return
                    failed_count += 1
                    task_safe_log(f"   ❌ 大模型调用异常: {exc}")
                    continue

                if not article or str(article).startswith("Error") or not used_words:
                    if is_orphaned(): return
                    failed_count += 1
                    # 如果翻译失败，释放已占用的语料文章，下次可重新使用
                    if title and hasattr(engine, '_used_titles') and title in engine._used_titles:
                        engine._used_titles.discard(title)
                        save_used_articles(engine._used_titles)
                        task_safe_log(f"   🔄 已释放语料文章 [{title}]，下次可重新使用。")
                    task_safe_log(f"   ❌ 返回内容无效，已跳过（不扣词）。")
                    if article:
                        task_safe_log(f"      原因: {article[:120]}")
                    continue

                task_safe_log(f"   ✅ 大模型返回成功，选词 {len(used_words)} 个")

                # ── 检查点 3: 文件写入前 ──────────────────────
                if is_orphaned():
                    return

                # ── 保存 Markdown ─────────────────────────────
                safe_topic = sanitize_filename(title)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                md_filename = f"{timestamp}_{safe_topic}.md"
                md_path = MARKDOWN_ARCHIVE_DIR / md_filename

                try:
                    md_path.write_text(article, encoding="utf-8")
                    task_safe_log(f"   💾 Markdown 已保存: {md_filename}")
                except OSError as exc:
                    failed_count += 1
                    task_safe_log(f"   ❌ Markdown 写入失败: {exc}")
                    continue

                # ── 检查点 4: PDF 生成前 ──────────────────────
                if is_orphaned():
                    return

                # ── 生成 PDF ──────────────────────────────────
                pdf_filename = f"{timestamp}_{safe_topic}.pdf"
                pdf_path = PDF_ARCHIVE_DIR / pdf_filename
                task_safe_log(f"   正在生成暗黑 PDF...")

                try:
                    export_to_pdf(article, str(pdf_path))
                    task_safe_log(f"   💾 PDF 已保存: {pdf_filename}")
                except Exception as exc:
                    task_safe_log(f"   ⚠️ PDF 生成失败（MD 已保存，不影响进度）: {exc}")

                # ── 检查点 5: DB 结算前 ──────────────────────
                if is_orphaned():
                    return

                # ── 数据库结算 ────────────────────────────────
                marked = self.db.mark_words_learned(used_words, level=level)
                self.db.mark_topic_used(title)
                success_count += 1
                task_safe_log(
                    f"   ✅ 第 {i + 1} 篇完成！主题: {title}  |  学词: {marked}/{len(used_words)}"
                )

        except Exception as exc:
            if not is_orphaned():
                task_safe_log(f"\n💥 批量生成遇到致命错误: {exc}")
        finally:
            if is_orphaned():
                return
            # ── 任务结束汇总 ──────────────────────────────────
            task_safe_log(f"\n{'━'*50}")
            task_safe_log(
                f"🏁 批量生成完成  |  成功: {success_count}  |  失败: {failed_count}"
            )

            # 恢复 UI 状态（必须通过 after 调度到主线程）
            self.after(0, self._on_batch_finished)

    def _on_batch_finished(self) -> None:
        """批量任务结束后，恢复按钮状态并刷新进度。"""
        self._set_running(False)
        self._refresh_progress_label()

    # ══════════════════════════════════════════════════════════
    #  重置进度回调（带二次确认）
    # ══════════════════════════════════════════════════════════
    def _show_confirm_dialog(self, title: str, message: str, on_confirm) -> None:
        """显示二次确认对话框。"""
        import tkinter as tk
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x180")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.after(10, lambda: dialog.focus_force())

        ctk.CTkLabel(
            dialog, text="⚠️ " + title, font=self.FONT_TITLE,
        ).pack(pady=(20, 6))
        ctk.CTkLabel(
            dialog, text=message, font=self.FONT_UI, wraplength=360,
        ).pack(pady=(0, 16))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(0, 16))
        ctk.CTkButton(
            btn_row, text="确认", font=self.FONT_UI, width=100,
            fg_color="#C82B2B", hover_color="#8f1b1b",
            command=lambda: (on_confirm(), dialog.destroy()),
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            btn_row, text="取消", font=self.FONT_UI, width=100,
            fg_color="gray40", hover_color="gray50",
            command=dialog.destroy,
        ).pack(side="left", padx=10)

    def _on_reset_words(self) -> None:
        """重置当前选中级别的单词学习进度。"""
        level = self.combo_level.get()
        total, unlearned = self.db.count_words(level=level)
        learned = total - unlearned

        if learned == 0:
            self._log(f"ℹ️ 【{level}】没有已学习的单词，无需重置。")
            return

        def do_reset():
            count = self.db.reset_all_progress(level=level)
            self._refresh_progress_label()
            self._log(f"✅ 【{level}】已重置 {count} 个单词的学习进度！")

        self._show_confirm_dialog(
            "确认重置单词进度",
            f"即将重置【{level}】的 {learned} 个已学单词为未学状态。\n此操作不可撤销！",
            do_reset,
        )

    def _on_reset_topics(self) -> None:
        """重置已使用文章记录。"""
        used = self.db.get_used_topics()
        if not used:
            self._log("ℹ️ 没有已使用的文章记录，无需重置。")
            return

        def do_reset():
            # 1. 清空数据库中的已使用主题
            db_count = self.db.reset_used_topics()
            # 2. 清空本地 used_articles.json
            from content_engine import USED_ARTICLES_PATH
            if USED_ARTICLES_PATH.exists():
                USED_ARTICLES_PATH.write_text("[]", encoding="utf-8")
            self._log(f"✅ 已清空 {db_count} 条文章使用记录！")

        self._show_confirm_dialog(
            "确认重置文章记录",
            f"即将清空 {len(used)} 条已使用文章记录。\n此操作不可撤销！",
            do_reset,
        )

    def _on_reset_all(self) -> None:
        """重置所有级别的单词进度和文章记录。"""
        total, unlearned = self.db.count_words()
        learned = total - unlearned
        used = self.db.get_used_topics()

        if learned == 0 and not used:
            self._log("ℹ️ 没有任何学习进度，无需重置。")
            return

        def do_reset():
            # 重置所有单词
            word_count = self.db.reset_all_progress()
            # 重置文章记录
            topic_count = self.db.reset_used_topics()
            from content_engine import USED_ARTICLES_PATH
            if USED_ARTICLES_PATH.exists():
                USED_ARTICLES_PATH.write_text("[]", encoding="utf-8")
            self._refresh_progress_label()
            self._log(f"💥 全部重置完成！单词: {word_count} 个，文章记录: {topic_count} 条。")

        self._show_confirm_dialog(
            "确认重置全部进度",
            f"即将重置所有级别的 {learned} 个已学单词\n以及 {len(used)} 条文章使用记录。\n此操作不可撤销！",
            do_reset,
        )

    # ══════════════════════════════════════════════════════════
    #  归档 Tab 回调
    # ══════════════════════════════════════════════════════════
    def _refresh_archive_cache(self) -> list[str]:
        """刷新归档文件缓存，返回按时间倒序的文件名列表。"""
        md_dir = MARKDOWN_ARCHIVE_DIR
        if not md_dir.is_dir():
            return []
        return sorted(
            [f.name for f in md_dir.iterdir() if f.suffix.lower() == ".md"],
            key=lambda name: os.path.getmtime(md_dir / name),
            reverse=True,
        )

    def _open_file_selector(self) -> None:
        """弹出模态窗口，使用 CTkScrollableFrame 展示归档列表供选择。"""
        md_files = self._refresh_archive_cache()

        # ── 创建模态弹窗 ────────────────────────────────────
        dialog = ctk.CTkToplevel(self)
        dialog.title("请选择历史归档")
        dialog.geometry("700x500")
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # ── 标题栏 ──────────────────────────────────────────
        ctk.CTkLabel(
            dialog, text=f"📂 历史归档（共 {len(md_files)} 篇）",
            font=self.FONT_HEADING,
        ).pack(pady=(16, 8))

        if not md_files:
            ctk.CTkLabel(
                dialog, text="暂无归档文件", font=self.FONT_UI,
                text_color="gray60",
            ).pack(expand=True)
            ctk.CTkButton(
                dialog, text="关闭", width=100, command=dialog.destroy,
            ).pack(pady=16)
            return

        # ── 可滚动列表区域 ──────────────────────────────────
        scroll_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        for fname in md_files:
            btn = ctk.CTkButton(
                scroll_frame,
                text=f"  {fname}",
                font=self.FONT_UI,
                fg_color="transparent",
                hover_color="gray30",
                anchor="w",
                height=32,
                corner_radius=4,
                command=lambda f=fname: self._on_select_archive(f, dialog),
            )
            btn.pack(fill="x", pady=(0, 2))

        # ── 底部关闭按钮 ────────────────────────────────────
        ctk.CTkButton(
            dialog, text="取消", width=100, command=dialog.destroy,
        ).pack(pady=(0, 16))

    def _on_select_archive(self, filename: str, dialog: ctk.CTkToplevel) -> None:
        """用户从弹窗中选择了一个文件。"""
        self.archive_display.configure(state="normal")
        self.archive_display.delete(0, "end")
        self.archive_display.insert(0, filename)
        self.archive_display.configure(state="readonly")
        dialog.destroy()

    def _on_preview_archive(self) -> None:
        """加载选中的归档文件内容到预览文本框。"""
        selected = self.archive_display.get()
        if not selected or selected.startswith("（"):
            self._set_preview("请先选择一个归档文件。")
            return

        file_path = MARKDOWN_ARCHIVE_DIR / selected
        if not file_path.exists():
            self._set_preview(f"文件不存在：{file_path}")
            return

        try:
            content = file_path.read_text(encoding="utf-8")
            self._set_preview(content if content.strip() else "（文件内容为空）")
        except OSError as exc:
            self._set_preview(f"读取失败：{exc}")

    def _open_folder(self, folder_path: Path) -> None:
        """在 Windows 资源管理器中打开指定文件夹。"""
        try:
            os.startfile(str(folder_path))
        except Exception:
            pass

    def _show_success_dialog(self, title: str, message: str, folder: Path) -> None:
        """弹出成功提示窗口，附带「打开文件夹」按钮。"""
        import tkinter as tk
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("420x180")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        # 居中于主窗口
        dialog.after(10, lambda: dialog.focus_force())

        ctk.CTkLabel(
            dialog, text="✅ " + title, font=self.FONT_TITLE,
        ).pack(pady=(20, 6))
        ctk.CTkLabel(
            dialog, text=message, font=self.FONT_UI, wraplength=380,
        ).pack(pady=(0, 16))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(0, 16))
        ctk.CTkButton(
            btn_row, text="📂 打开文件夹", font=self.FONT_UI, width=140,
            fg_color="#27ae60", hover_color="#2ecc71",
            command=lambda: (self._open_folder(folder), dialog.destroy()),
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            btn_row, text="关闭", font=self.FONT_UI, width=100,
            fg_color="gray40", hover_color="gray50",
            command=dialog.destroy,
        ).pack(side="left", padx=10)

    def _on_export_epub(self) -> None:
        """非阻塞式后台打包 EPUB。"""
        self._log("📚 正在后台打包所有归档文章为 EPUB 特刊...")
        
        def _worker():
            try:
                from epub_generator import generate_epub
                from datetime import datetime
                epub_filename = f"知识学爆_特刊_{datetime.now().strftime('%Y%m%d_%H%M%S')}.epub"
                epub_path = EPUB_ARCHIVE_DIR / epub_filename
                success = generate_epub(MARKDOWN_ARCHIVE_DIR, output_file=str(epub_path))
                if success:
                    self.after(0, lambda: self._log(f"🎉 EPUB 电子书打包成功！已保存至 archives/epub/"))
                    self.after(0, lambda: self._show_success_dialog(
                        "EPUB 打包成功",
                        f"电子书已保存至 archives/epub/ 目录。",
                        EPUB_ARCHIVE_DIR,
                    ))
                else:
                    self.after(0, lambda: self._log("⚠️ 导出失败：目录中可能没有 Markdown 文章。"))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.after(0, lambda e=e: self._log(f"❌ EPUB 导出报错：{e}"))
                
        threading.Thread(target=_worker, daemon=True).start()

    def _on_regenerate_pdfs(self) -> None:
        """从本地所有的 Markdown 归档中，使用最新的渲染引擎重新生成所有的 PDF。"""
        md_files = list(MARKDOWN_ARCHIVE_DIR.glob("*.md"))
        if not md_files:
            self._log("⚠️ 历史归档为空，没有可以重新生成的 PDF。")
            return
            
        self._log("━" * 50)
        self._log(f"🖨️ 开始使用最新排版引擎重新生成 {len(md_files)} 个 PDF 文件...")
        
        def _worker():
            try:
                from pdf_generator import export_to_pdf
                success_count = 0
                for md_path in md_files:
                    try:
                        pdf_filename = md_path.name.replace(".md", ".pdf")
                        pdf_path = PDF_ARCHIVE_DIR / pdf_filename
                        content = md_path.read_text(encoding="utf-8")
                        export_to_pdf(content, str(pdf_path))
                        success_count += 1
                        self.after(0, lambda m=md_path.name: self._log(f"   => 成功重刷: {m}"))
                    except Exception as e:
                        self.after(0, lambda m=md_path.name, err=e: self._log(f"   ❌ 重刷失败 {m}: {err}"))

                total = len(md_files)
                self.after(0, lambda: self._log(f"🎉 批量重新排版完成！成功: {success_count}/{total}"))
                self.after(0, lambda: self._show_success_dialog(
                    "PDF 排版完成",
                    f"成功重排 {success_count}/{total} 个文件。",
                    PDF_ARCHIVE_DIR,
                ))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.after(0, lambda err=e: self._log(f"❌ 批量重刷引擎报错：{err}"))
                
        threading.Thread(target=_worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    #  辅助方法
    # ══════════════════════════════════════════════════════════
    def log_message(self, message: str, level: str = "info") -> None:
        """向日志面板追加一行（仅限主线程调用）。支持 level: "info", "success", "error" """
        self.log_textbox.configure(state="normal")
        
        current_index = self.log_textbox.index("end-1c")
        self.log_textbox.insert("end", message + "\n")
        new_index = self.log_textbox.index("end")
        
        color_map = {"info": "white", "success": "green", "error": "red"}
        tag = color_map.get(level, "white")
        self.log_textbox.tag_add(tag, current_index, new_index)
            
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _log(self, message: str, level: str = "info") -> None:
        """兼容老代码的直接调用"""
        if ("❌" in message or "💥" in message or "⚠️" in message) and level == "info":
            level = "error"
        if ("✅" in message or "🎉" in message) and level == "info":
            level = "success"
        self.log_message(message, level)

    def _safe_log(self, message: str, level: str = "info") -> None:
        """线程安全的日志写入：通过 after() 调度到主线程执行。"""
        if ("❌" in message or "💥" in message or "⚠️" in message) and level == "info":
            level = "error"
        if ("✅" in message or "🎉" in message) and level == "info":
            level = "success"
        self.after(0, self.log_message, message, level)

    def _set_preview(self, text: str) -> None:
        """设置预览文本框的内容，简易渲染 Markdown 标记。"""
        self.preview_textbox.configure(state="normal")
        self.preview_textbox.delete("1.0", "end")

        # 逐行解析并渲染
        for line in text.split("\n"):
            stripped = line.strip()
            # Markdown 标题行 (# / ## / ###)
            if stripped.startswith("#"):
                heading_text = stripped.lstrip("# ").strip()
                self.preview_textbox._textbox.insert("end", heading_text + "\n", "heading")
            else:
                # 处理行内 **bold** 标记
                import re
                parts = re.split(r'(\*\*.*?\*\*)', line)
                for part in parts:
                    if part.startswith("**") and part.endswith("**"):
                        clean = part[2:-2]
                        self.preview_textbox._textbox.insert("end", clean, "bold")
                    else:
                        self.preview_textbox.insert("end", part)
                self.preview_textbox.insert("end", "\n")

        self.preview_textbox.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        """切换按钮状态：运行中禁用开始、启用停止，反之亦然。"""
        if running:
            self.btn_start.configure(state="disabled", text="⏳ 生成中...")
            self.btn_stop.configure(state="normal")
            
            # 隐藏上面的配置框以腾出空间 (Immersive Terminal Mode)
            if hasattr(self, 'api_frame'):
                self.api_frame.pack_forget()
            if hasattr(self, 'ctrl_frame'):
                self.ctrl_frame.pack_forget()
        else:
            self.btn_start.configure(state="normal", text="✨  开 始 生 成")
            self.btn_stop.configure(state="disabled")
            
            # 重新显示配置框
            if hasattr(self, 'api_frame') and hasattr(self, 'ctrl_frame') and hasattr(self, 'btn_frame') and hasattr(self, 'log_textbox'):
                # 重新按正确的顺序打包回去：必须先 log_textbox，再 sash
                self.btn_frame.pack_forget()
                if hasattr(self, 'sash'):
                    self.sash.pack_forget()
                self.log_textbox.pack_forget()

                self.api_frame.pack(fill="x", padx=16, pady=(12, 8))
                self.ctrl_frame.pack(fill="x", padx=16, pady=8)
                self.btn_frame.pack(fill="x", padx=16, pady=(8, 6))
                self.log_textbox.pack(side="bottom", fill="x", padx=16, pady=(0, 12))
                if hasattr(self, 'sash'):
                    self.sash.pack(side="bottom", fill="x", padx=60, pady=(4, 4))

    def _on_level_changed(self, choice: str) -> None:
        """当用户在下拉框切换难度时，实时刷新右上角的进度显示。"""
        self._refresh_progress_label()

    def _refresh_progress_label(self) -> None:
        """刷新右上角的词库进度概要（强制解耦，只显示当前选中的词库数据）。"""
        try:
            # 获取当前选中级别的统计
            level = getattr(self, 'combo_level', None)
            if level:
                lv = level.get()
                lv_total, lv_unlearned = self.db.count_words(level=lv)
                lv_learned = lv_total - lv_unlearned
                self._progress_label.configure(
                    text=f"【{lv}】词汇库总量: {lv_total}  |  已掌握: {lv_learned}  |  待学习: {lv_unlearned}"
                )
            else:
                total, unlearned = self.db.count_words()
                learned = total - unlearned
                self._progress_label.configure(
                    text=f"总词库 {total}  |  已学 {learned}  |  未学 {unlearned}"
                )
        except Exception:
            self._progress_label.configure(text="词库状态未知")


# ── 入口 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
