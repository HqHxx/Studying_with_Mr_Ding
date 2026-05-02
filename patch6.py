import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('logo_path = BASE_DIR / "logo.png"', 'logo_path = INTERNAL_DIR / "logo.png"')

init_target = 'self.minsize(900, 600)'
init_replacement = '''self.minsize(900, 600)
        
        # ── 设置窗口图标 ──
        icon_path = INTERNAL_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass'''
content = content.replace(init_target, init_replacement)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('build.spec', 'r', encoding='utf-8') as f:
    spec = f.read()

# Make sure both logo.png and icon.ico are bundled internally.
if "('icon.ico', '.')" not in spec:
    spec = spec.replace("('logo.png', '.'),", "('logo.png', '.'),\n        ('icon.ico', '.'),")

with open('build.spec', 'w', encoding='utf-8') as f:
    f.write(spec)
