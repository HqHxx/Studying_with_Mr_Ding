import sys
with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_db = '''        # 确保数据库文件存在（从内部资源复制，以保留打包的词库）
        db_path = BASE_DIR / "cet4_words.db"'''

new_db = '''        # 确保数据库文件存在（从内部资源复制，以保留打包的词库）
        # 将生成的运行词库名改为“学习进度词库.db”并放入 data 文件夹下，保持根目录整洁
        data_dir = BASE_DIR / "data"
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "学习进度词库.db"'''

text = text.replace(old_db, new_db)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(text)
