
with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('self.top_container.pack(fill=\"both\", expand=True)', 'self.top_container.pack(side=\"top\", fill=\"both\", expand=True)')
text = text.replace('self.sash.pack(fill=\"x\", padx=60, pady=(4, 4))', 'self.sash.pack(side=\"bottom\", fill=\"x\", padx=60, pady=(4, 4))')
text = text.replace('self.log_textbox.pack(fill=\"x\", padx=16, pady=(0, 12))', 'self.log_textbox.pack(side=\"bottom\", fill=\"x\", padx=16, pady=(0, 12))')
text = text.replace('mode=mode, custom_text=custom_text', '')

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(text)

