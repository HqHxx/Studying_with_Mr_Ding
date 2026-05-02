import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Need to import PIL
if 'from PIL import Image' not in content:
    content = content.replace('import customtkinter as ctk', 'import customtkinter as ctk\nfrom PIL import Image\nimport os')

old_header = '''        # 标题栏
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 0))
        ctk.CTkLabel(
            header,
            text="📖  知识学爆",
            font=self.FONT_HERO,
        ).pack(side="left")'''

new_header = '''        # 标题栏
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 0))
        
        logo_path = BASE_DIR / "logo.png"
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
            ).pack(side="left")'''

content = content.replace(old_header, new_header)

# In spec file we also need to include logo.png if it exists.
with open('build.spec', 'r', encoding='utf-8') as sf:
    spec = sf.read()

    if "('logo.png', '.')" not in spec:
        spec = spec.replace("('local_corpus.json', '.'),", "('local_corpus.json', '.'),\n        # ── 你的图标图案 ──\n        ('logo.png', '.'),")

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('build.spec', 'w', encoding='utf-8') as f:
    f.write(spec)
