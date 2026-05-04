import os

with open("main.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Archive dropdown
text = text.replace(
    'self.archive_combo = ctk.CTkComboBox(\n            bar, values=["（点击刷新加载）"], state="readonly", font=self.FONT_UI,\n        )',
    'self.archive_combo = ctk.CTkComboBox(\n            bar, values=["（点击刷新加载）"], state="readonly", font=self.FONT_UI, dropdown_height=300\n        )'
)

# 2. Add top_container and indentation. We can achieve this by inserting it at the beginning of _build_tab_generate
text = text.replace(
    '# ── API 配置区域 ──',
    '# ── 顶部容器（支持自然压缩） ──\n        self.top_container = ctk.CTkFrame(tab, fg_color="transparent")\n        self.top_container.pack(fill="both", expand=True)\n\n        # ── API 配置区域 ──'
)

# 3. Replace all `ctk.CTkFrame(tab, ...)` with `ctk.CTkFrame(self.top_container, ...)` inside _build_tab_generate
# but avoiding the tab_archive parts.
text = text.replace('self.api_frame = ctk.CTkFrame(tab, corner_radius=10)', 'self.api_frame = ctk.CTkFrame(self.top_container, corner_radius=10)')
text = text.replace('self.ctrl_frame = ctk.CTkFrame(tab, corner_radius=10)', 'self.ctrl_frame = ctk.CTkFrame(self.top_container, corner_radius=10)')
text = text.replace('self.btn_frame = ctk.CTkFrame(tab, fg_color="transparent")', 'self.btn_frame = ctk.CTkFrame(self.top_container, fg_color="transparent")')
text = text.replace('self.reset_frame = ctk.CTkFrame(tab, corner_radius=10)', 'self.reset_frame = ctk.CTkFrame(self.top_container, corner_radius=10)')

# 4. Modify the generation mode section
target_old_mode = '''        # 模式切换
        mode_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        mode_frame.grid(row=1, column=0, columnspan=6, sticky="w", padx=14, pady=(0, 6))
        
        self.source_mode_var = ctk.StringVar(value="random")
        ctk.CTkRadioButton(mode_frame, text="随机题库抽取", font=self.FONT_UI, variable=self.source_mode_var, value="random", command=self._on_source_mode_changed).pack(side="left", padx=(0, 30))
        ctk.CTkRadioButton(mode_frame, text="自定义文章", font=self.FONT_UI, variable=self.source_mode_var, value="custom", command=self._on_source_mode_changed).pack(side="left")'''

new_mode_html = '''        # 模式切换与批量导入
        mode_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        mode_frame.grid(row=1, column=0, columnspan=6, sticky="w", padx=14, pady=(0, 6))
        
        ctk.CTkLabel(mode_frame, text="语料来源:", font=self.FONT_UI).pack(side="left", padx=(0, 10))
        
        self.source_mode_var = ctk.StringVar(value="builtin")
        ctk.CTkRadioButton(mode_frame, text="内置系统语料", font=self.FONT_UI, variable=self.source_mode_var, value="builtin").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(mode_frame, text="仅自定义语料", font=self.FONT_UI, variable=self.source_mode_var, value="custom").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(mode_frame, text="混合抽取", font=self.FONT_UI, variable=self.source_mode_var, value="mixed").pack(side="left", padx=(0, 30))
        
        # 批量导入按钮与帮助
        ctk.CTkButton(mode_frame, text="📁 批量导入本地文件", font=self.FONT_UI, width=140, fg_color="#3498db", hover_color="#2980b9", command=self._on_import_custom_corpus).pack(side="left", padx=(10, 5))
        ctk.CTkButton(mode_frame, text="[?]", font=self.FONT_UI, width=28, command=self._on_show_import_help).pack(side="left")'''

text = text.replace(target_old_mode, new_mode_html)

# 5. Remove custom text frame
custom_text_frame_code = """
        # 自定义文章输入区
        self.custom_text_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        self.custom_text_frame.grid(row=3, column=0, columnspan=6, sticky="nsew", padx=14, pady=(0, 14))
        self.custom_text_frame.grid_remove() # 默认隐藏
        
        ctk.CTkLabel(self.custom_text_frame, text="请在此输入您的英文原文 (800 - 5000 字符):", text_color="gray", font=self.FONT_UI).pack(anchor="w", pady=(0, 6))
        self.custom_textbox = ctk.CTkTextbox(self.custom_text_frame, height=220, wrap="word", font=self.FONT_TEXT)
        self.custom_textbox.pack(fill="both", expand=True)"""
text = text.replace(custom_text_frame_code, "")

# 6. Delete _on_source_mode_changed hook
text = text.replace("""
    def _on_source_mode_changed(self):
        \"\"\"处理来源模式切换\"\"\"
        if self.source_mode_var.get() == "random":
            self.custom_text_frame.grid_remove()
            self.random_param_frame.grid()
        else:
            self.random_param_frame.grid_remove()
            self.custom_text_frame.grid()
""", "")

# 7. Modify log setup inside _build_tab_generate
old_log_setup = """        # ── 日志输出 ──────────────────────────────────────────
        self.log_textbox = ctk.CTkTextbox(
            tab,
            font=self.FONT_TEXT,
            corner_radius=10,
            state="disabled",
            wrap="word",
        )
        self.log_textbox.pack(fill="both", expand=True, padx=16, pady=(4, 12))
        self._log("就绪。请配置 API 参数后点击「开始生成」。")"""

new_log_setup = """        # ── 可拖拽分割线 ──────────────────────────────────────
        self.sash = ctk.CTkFrame(tab, height=6, corner_radius=3, fg_color="gray30", cursor="sb_v_double_arrow")
        self.sash.pack(fill="x", padx=60, pady=(4, 4))
        self.sash.bind("<B1-Motion>", self._on_sash_drag)
        self.sash.bind("<Button-1>", self._on_sash_press)
        
        self.sash.bind("<Enter>", lambda e: self.sash.configure(fg_color="#3498db"))
        self.sash.bind("<Leave>", lambda e: self.sash.configure(fg_color="gray30"))

        # ── 日志输出 ──────────────────────────────────────────
        self.log_textbox = ctk.CTkTextbox(
            tab,
            font=self.FONT_TEXT,
            corner_radius=10,
            state="disabled",
            wrap="word",
            height=150
        )
        self.log_textbox.pack(fill="x", padx=16, pady=(0, 12))
        
        self.log_textbox.tag_config("red", foreground="#ff4757")
        self.log_textbox.tag_config("green", foreground="#2ed573")
        self.log_textbox.tag_config("white", foreground="white")

        self.log_message("就绪。请配置 API 参数后点击「开始生成」。", level="info")"""
text = text.replace(old_log_setup, new_log_setup)

# 8. Add split line drag methods and batch import methods at callback section
sash_callbacks = """
    # ── 分割线与导入功能 ──────────────────────────────────────
    def _on_sash_press(self, event) -> None:
        self._sash_start_y = event.y_root
        self._log_start_height = self.log_textbox.winfo_height()

    def _on_sash_drag(self, event) -> None:
        dy = event.y_root - self._sash_start_y
        new_height = self._log_start_height - dy
        max_height = self.winfo_height() / 3
        if new_height < 60: new_height = 60
        if new_height > max_height: new_height = max_height
        self.log_textbox.configure(height=new_height)

    def _on_show_import_help(self) -> None:
        top = ctk.CTkToplevel(self)
        top.title("📖 语料导入标准说明")
        top.geometry("450x260")
        top.attributes("-topmost", True)
        
        msg = (
            "【批量导入本地文件规则】\\n\\n"
            "1. 支持的格式：仅限 .txt 和 .md 纯文本文件。\\n\\n"
            "2. 编码建议：强烈推荐使用 UTF-8 编码，\\n"
            "   若文件存在特殊字符导致解析失败将自动跳过。\\n\\n"
            "3. 解析规则：系统会自动以“文件名”（去后缀）\\n"
            "   作为文章标题，请尽量保持文件名简洁，\\n"
            "   文件内容将作为正文导入自定义语料库。\\n\\n"
            "导入的数据保存在 data/custom_corpus.json 中，\\n"
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
"""
text = text.replace("    # ══════════════════════════════════════════════════════════\n    #  回调方法", sash_callbacks + "\n    # ══════════════════════════════════════════════════════════\n    #  回调方法")

# 9. Modify start generate callback hook checking logic to block empty custom corpus
validation_check = """
    def _on_start_generate(self) -> None:
        if self.current_task_id:
            return

        choice = self.combo_profile.get()
        data = self._api_config.get("profiles", {}).get(choice, {})
        base_url = data.get("base_url", "")
        fast_model = data.get("fast_model", "")
        core_model = data.get("core_model", "")
        api_key = data.get("api_key", "")

        if not all([base_url, fast_model, core_model, api_key]):
            self._log("⚠️ 请先填写完整的 API 配置（Base URL、Fast Model、Core Model、API Key）。", level="error")
            return"""
new_validation_check = """
    def _on_start_generate(self) -> None:
        if self.current_task_id:
            return

        choice = self.combo_profile.get()
        data = self._api_config.get("profiles", {}).get(choice, {})
        base_url = data.get("base_url", "")
        fast_model = data.get("fast_model", "")
        core_model = data.get("core_model", "")
        api_key = data.get("api_key", "")

        if not all([base_url, fast_model, core_model, api_key]):
            self._log("⚠️ 请先填写完整的 API 配置（Base URL、Fast Model、Core Model、API Key）。", level="error")
            return
            
        mode = self.source_mode_var.get()
        if mode in ["custom", "mixed"]:
            custom_db_path = BASE_DIR / "data" / "custom_corpus.json"
            if not custom_db_path.exists() or len(custom_db_path.read_text(encoding="utf-8").strip()) < 5:
                self.log_message("⚠️ 自定义语料库为空！请先点击【批量导入本地文件】。", level="error")
                return"""
text = text.replace(validation_check, new_validation_check)

# 10. Replace params inside `_on_start_generate`
text = text.replace(
'''            threading.Thread(
                target=self._batch_generate_worker,
                args=(base_url, fast_model, core_model, api_key, count, level, category, task_id, mode, custom_text),
                daemon=True,
            ).start()''',
'''            threading.Thread(
                target=self._batch_generate_worker,
                args=(base_url, fast_model, core_model, api_key, count, level, category, task_id, mode),
                daemon=True,
            ).start()'''
)

text = text.replace(
'''    def _batch_generate_worker(
        self, base_url: str, fast_model: str, core_model: str, api_key: str, count: int,
        level: str, category: str, task_id: str, mode: str = "random", custom_text: str = ""
    ) -> None:''',
'''    def _batch_generate_worker(
        self, base_url: str, fast_model: str, core_model: str, api_key: str, count: int,
        level: str, category: str, task_id: str, mode: str = "builtin"
    ) -> None:'''
)

# 11. Overwrite _batch_generate_worker instantiation payload
worker_start_old = """        try:
            engine = ContentEngine(
                api_key=api_key,
                base_url=base_url,
                fast_model=fast_model,
                core_model=core_model,
            )"""
            
worker_start_new = """        try:
            engine = ContentEngine(
                api_key=api_key,
                base_url=base_url,
                fast_model=fast_model,
                core_model=core_model,
                corpus_mode=mode,
            )"""
text = text.replace(worker_start_old, worker_start_new)

# 12. Rewrite safe log and direct log to support info / error / success instead of white red green
log_functions_old = """    def _log(self, message: str) -> None:
        \"\"\"向日志面板追加一行（仅限主线程调用）。\"\"\"
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _safe_log(self, message: str) -> None:
        \"\"\"线程安全的日志写入：通过 after() 调度到主线程执行。\"\"\"
        self.after(0, self._log, message)"""
        
log_functions_new = """    def log_message(self, message: str, level: str = "info") -> None:
        \"\"\"向日志面板追加一行（仅限主线程调用）。支持 level: "info", "success", "error" \"\"\"
        self.log_textbox.configure(state="normal")
        
        current_index = self.log_textbox.index("end-1c")
        self.log_textbox.insert("end", message + "\\n")
        new_index = self.log_textbox.index("end")
        
        color_map = {"info": "white", "success": "green", "error": "red"}
        tag = color_map.get(level, "white")
        self.log_textbox.tag_add(tag, current_index, new_index)
            
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _log(self, message: str, level: str = "info") -> None:
        \"\"\"兼容老代码的直接调用\"\"\"
        if ("❌" in message or "💥" in message or "⚠️" in message) and level == "info":
            level = "error"
        if ("✅" in message or "🎉" in message) and level == "info":
            level = "success"
        self.log_message(message, level)

    def _safe_log(self, message: str, level: str = "info") -> None:
        \"\"\"线程安全的日志写入：通过 after() 调度到主线程执行。\"\"\"
        if ("❌" in message or "💥" in message or "⚠️" in message) and level == "info":
            level = "error"
        if ("✅" in message or "🎉" in message) and level == "info":
            level = "success"
        self.after(0, self.log_message, message, level)"""
        
text = text.replace(log_functions_old, log_functions_new)


with open("main.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Patch applied successfully.")
