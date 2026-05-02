import os
from pathlib import Path
from ebooklib import epub
import markdown

def generate_epub(markdown_dir: Path, output_file: str = "知识学爆_特刊.epub") -> bool:
    """
    将目录下的所有 Markdown 文件打包成一个 EPUB 电子书。
    """
    if not markdown_dir.exists() or not markdown_dir.is_dir():
        return False

    md_files = sorted(
        [f for f in markdown_dir.iterdir() if f.suffix.lower() == ".md"],
        key=lambda p: os.path.getmtime(p)
    )

    if not md_files:
        return False

    book = epub.EpubBook()
    
    # 设置元数据
    book.set_identifier('id_zhishixuebao')
    book.set_title('知识学爆 - 专属英语特刊')
    book.set_language('en')
    book.add_author('知识学爆 Engine')

    chapters = []
    
    for i, file_path in enumerate(md_files):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
            
        if not content.strip():
            continue

        # 将 Markdown 转换为 HTML
        html_content = markdown.markdown(content)
        
        # 提取第一行作为章节标题
        lines = [line for line in content.split("\n") if line.strip()]
        chapter_title = lines[0].replace("#", "").strip() if lines else f"Chapter {i+1}"
        
        # 创建章节
        chapter = epub.EpubHtml(title=chapter_title, file_name=f'chap_{i+1}.xhtml', lang='en')
        
        # 包装 HTML
        chapter.content = f'''<html>
        <head>
            <title>{chapter_title}</title>
        </head>
        <body>
            {html_content}
        </body>
        </html>'''
        
        book.add_item(chapter)
        chapters.append(chapter)

    if not chapters:
        return False

    # 配置目录和导航
    book.toc = tuple(chapters)
    
    # 添加默认的 NCX 和 Nav 导航
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # 配置 spine (阅读顺序)
    spine = ['nav'] + chapters
    book.spine = spine

    # 输出 EPUB
    epub.write_epub(output_file, book, {})
    return True
