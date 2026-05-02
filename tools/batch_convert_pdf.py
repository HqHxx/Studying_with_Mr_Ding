import os
import traceback

from pdf_generator import export_to_pdf


ARCHIVE_ROOT = "archives"
MARKDOWN_DIR = os.path.join(ARCHIVE_ROOT, "markdown")
PDF_DIR = os.path.join(ARCHIVE_ROOT, "pdf")


def main() -> None:
    print("开始批量补救转换 PDF...")
    os.makedirs(ARCHIVE_ROOT, exist_ok=True)
    os.makedirs(MARKDOWN_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)

    for name in os.listdir(ARCHIVE_ROOT):
        src_path = os.path.join(ARCHIVE_ROOT, name)
        if not os.path.isfile(src_path):
            continue

        lower_name = name.lower()
        if lower_name.endswith(".md"):
            dst_path = os.path.join(MARKDOWN_DIR, name)
        elif lower_name.endswith(".pdf"):
            dst_path = os.path.join(PDF_DIR, name)
        else:
            continue

        if not os.path.exists(dst_path):
            os.replace(src_path, dst_path)

    converted = 0
    skipped = 0

    for filename in os.listdir(MARKDOWN_DIR):
        if not filename.lower().endswith(".md"):
            continue

        md_path = os.path.join(MARKDOWN_DIR, filename)
        pdf_path = os.path.join(PDF_DIR, filename[:-3] + ".pdf")

        if os.path.exists(pdf_path):
            skipped += 1
            continue

        try:
            with open(md_path, "r", encoding="utf-8") as file:
                article_text = file.read()
            export_to_pdf(article_text, pdf_path)
            converted += 1
            print(f"转换成功: {os.path.basename(pdf_path)}")
        except Exception:
            print(f"转换失败: {md_path}")
            traceback.print_exc()

    print(f"完成: 新增 {converted} 个 PDF，跳过 {skipped} 个已存在文件")


if __name__ == "__main__":
    main()