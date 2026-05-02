"""多词库初始化脚本：从 txt 文件批量导入四级/六级/考研/托福词库。

文件格式要求：每行一个单词，用 Tab 分隔单词和释义。
    word\tdefinition

运行方式: python init_db.py
"""

from __future__ import annotations

from pathlib import Path

from db_manager import DBManager

BASE_DIR = Path(__file__).resolve().parent

# ── 词库文件映射 ───────────────────────────────────────────────
# key = 数据库中的 level 标签，value = 文件名
WORD_FILES: dict[str, str] = {
    "CET-4": "cet4_words.txt",
    "CET-6": "4 六级-乱序.txt",
    "考研":  "5 考研-乱序.txt",
    "托福":  "6 托福-乱序.txt",
}


def parse_word_file(filepath: Path) -> list[dict]:
    """解析 Tab 分隔的单词文件。

    每行格式: word\\tdefinition
    返回: [{"word": ..., "phonetic": "", "definition": ...}, ...]
    """
    words: list[dict] = []
    if not filepath.exists():
        print(f"  [SKIP] File not found: {filepath.name}")
        return words

    # 尝试多种编码
    content = None
    for enc in ("utf-8", "gbk", "gb18030", "latin-1"):
        try:
            content = filepath.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, OSError):
            continue

    if content is None:
        print(f"  [ERROR] Cannot decode: {filepath.name}")
        return words

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        # 按 Tab 分割
        if "\t" in line:
            parts = line.split("\t", 1)
        else:
            # 降级：按第一个空格分割
            parts = line.split(None, 1)

        if len(parts) < 2:
            continue

        word = parts[0].strip().lower()
        definition = parts[1].strip()

        if not word or not word[0].isalpha():
            continue

        words.append({
            "word": word,
            "phonetic": "",
            "definition": definition,
        })

    return words


def main() -> None:
    print("=" * 60)
    print("  Multi-Level Word Database Initializer")
    print("=" * 60)

    db = DBManager(str(BASE_DIR / "cet4_words.db"))
    db.initialize()

    total_imported = 0

    for level, filename in WORD_FILES.items():
        filepath = BASE_DIR / filename
        print(f"\n[{level}] Parsing: {filename}")

        words = parse_word_file(filepath)
        if not words:
            print(f"  -> 0 words parsed, skipping")
            continue

        print(f"  -> {len(words)} words parsed")
        inserted = db.upsert_words(words, level=level)
        print(f"  -> {inserted} new words imported (duplicates skipped)")
        total_imported += inserted

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"  Import complete! {total_imported} new words added.")
    print()

    for level in WORD_FILES:
        total, unlearned = db.count_words(level=level)
        print(f"  [{level}] Total: {total}  |  Unlearned: {unlearned}")

    overall_total, overall_unlearned = db.count_words()
    print(f"\n  [ALL]  Total: {overall_total}  |  Unlearned: {overall_unlearned}")
    print("=" * 60)


if __name__ == "__main__":
    main()
