import re

with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('doubao-lite-32k', 'doubao-seed-2-0-code-preview-260215')
text = text.replace('doubao-pro-32k', 'deepseek-v3-2-251201')

text = text.replace('text="🔄 刷新"', 'text="🔄  刷新"')
text = text.replace('text="👁️ 预览"', 'text="🔍  预览"')
text = text.replace('text="📚 EPUB"', 'text="📚  EPUB"')
text = text.replace('text="🖨️ 排版"', 'text="🖨  排版"')

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(text)
