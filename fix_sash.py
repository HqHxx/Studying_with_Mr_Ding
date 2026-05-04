
with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

sash_block = '''        # ── 可拖拽分割线 ──────────────────────────────────────
        self.sash = ctk.CTkFrame(tab, height=6, corner_radius=3, fg_color=\"gray30\", cursor=\"sb_v_double_arrow\")
        self.sash.pack(side=\"bottom\", fill=\"x\", padx=60, pady=(4, 4))
        self.sash.bind(\"<B1-Motion>\", self._on_sash_drag)
        self.sash.bind(\"<Button-1>\", self._on_sash_press)
        
        self.sash.bind(\"<Enter>\", lambda e: self.sash.configure(fg_color=\"#3498db\"))
        self.sash.bind(\"<Leave>\", lambda e: self.sash.configure(fg_color=\"gray30\"))'''

log_block = '''        # ── 日志输出 ──────────────────────────────────────────
        self.log_textbox = ctk.CTkTextbox(
            tab,
            font=self.FONT_TEXT,
            corner_radius=10,
            state=\"disabled\",
            wrap=\"word\",
            height=150
        )
        self.log_textbox.pack(side=\"bottom\", fill=\"x\", padx=16, pady=(0, 12))
        
        self.log_textbox.tag_config(\"red\", foreground=\"#ff4757\")
        self.log_textbox.tag_config(\"green\", foreground=\"#2ed573\")
        self.log_textbox.tag_config(\"white\", foreground=\"white\")'''

if sash_block in text and log_block in text:
    text = text.replace(sash_block, 'INSERT_LOG_BLOCK_HERE')
    text = text.replace(log_block, sash_block)
    text = text.replace('INSERT_LOG_BLOCK_HERE', log_block)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(text)

