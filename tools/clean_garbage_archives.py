#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据清洗脚本 — 修复大模型生成的"无英文"垃圾文件导致的数据污染。

功能：
1. 扫描 archives/markdown/ 下的 .md 文件，判定缺少英文正文的垃圾文件
2. 提取垃圾文件中的核心词汇，回滚数据库学习进度（status = 0）
3. 逆向匹配 used_topics 表，释放被占用的文章标题
4. 同步清理 used_articles.json
5. 物理删除垃圾文件（.md + 同名 .pdf + 同名 .epub）

用法：
    python tools/clean_garbage_archives.py
"""

import json
import re
import sqlite3
from pathlib import Path


# ── 路径配置 ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

MARKDOWN_DIR = BASE_DIR / "archives" / "markdown"
PDF_DIR = BASE_DIR / "archives" / "pdf"
EPUB_DIR = BASE_DIR / "archives" / "epub"
DB_PATH = BASE_DIR / "data" / "学习进度词库.db"
USED_ARTICLES_PATH = BASE_DIR / "used_articles.json"

# 判定阈值：英文字母数量小于此值视为垃圾文件
ENGLISH_CHAR_THRESHOLD = 800


# ── 工具函数 ──────────────────────────────────────────────────
def sanitize_filename(text: str) -> str:
    """将主题转为适合文件名的安全字符串（与主程序逻辑保持一致）。"""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", text.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "untitled"


def extract_vocab_words(content: str) -> list[str]:
    """从 Markdown 内容中提取核心词汇列表。"""
    return re.findall(r"-\s*\*\*(.*?)\*\*", content)


def is_garbage_file(content: str) -> bool:
    """判定文件是否为缺少英文正文的垃圾文件。"""
    english_chars = len(re.findall(r"[a-zA-Z]", content))
    return english_chars < ENGLISH_CHAR_THRESHOLD


# ── 数据库操作 ────────────────────────────────────────────────
def rollback_word_status(words: list[str]) -> int:
    """将单词列表的学习状态回滚为未学（status = 0）。"""
    if not words or not DB_PATH.exists():
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        updated = 0
        for word in words:
            clean = word.strip().lower()
            if not clean:
                continue
            cur = conn.execute(
                "UPDATE words SET status = 0 WHERE LOWER(word) = LOWER(?)",
                (clean,),
            )
            updated += cur.rowcount
        conn.commit()
        return updated
    finally:
        conn.close()


def release_used_topic_by_filename(md_filename: str) -> str | None:
    """
    根据垃圾文件的文件名，逆向匹配 used_topics 表中的文章标题。
    如果匹配成功，从数据库中删除该记录并返回标题。
    """
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute("SELECT topic FROM used_topics").fetchall()
        for (topic,) in rows:
            safe_name = sanitize_filename(topic)
            # 检查安全文件名是否出现在 md 文件名中
            if safe_name in md_filename:
                conn.execute("DELETE FROM used_topics WHERE topic = ?", (topic,))
                conn.commit()
                return topic
        return None
    finally:
        conn.close()


def load_used_articles_json() -> set[str]:
    """从 JSON 文件加载已使用文章标题集合。"""
    if not USED_ARTICLES_PATH.exists():
        return set()
    try:
        data = json.loads(USED_ARTICLES_PATH.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()


def save_used_articles_json(titles: set[str]) -> None:
    """保存已使用文章标题集合到 JSON 文件。"""
    USED_ARTICLES_PATH.write_text(
        json.dumps(sorted(titles), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── 文件清理 ──────────────────────────────────────────────────
def delete_related_files(md_path: Path) -> dict[str, list[str]]:
    """删除 .md 文件及其同名的 .pdf 和 .epub 文件。"""
    deleted = {"md": [], "pdf": [], "epub": []}

    # 删除 Markdown
    if md_path.exists():
        md_path.unlink()
        deleted["md"].append(md_path.name)

    # 删除同名 PDF
    pdf_path = PDF_DIR / md_path.name.replace(".md", ".pdf")
    if pdf_path.exists():
        pdf_path.unlink()
        deleted["pdf"].append(pdf_path.name)

    # 删除同名 EPUB（如果有的话）
    epub_path = EPUB_DIR / md_path.name.replace(".md", ".epub")
    if epub_path.exists():
        epub_path.unlink()
        deleted["epub"].append(epub_path.name)

    return deleted


# ── 主流程 ────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("🧹  知识学爆 — 垃圾归档文件清洗工具")
    print("=" * 60)

    if not MARKDOWN_DIR.is_dir():
        print(f"\n⚠️  归档目录不存在：{MARKDOWN_DIR}")
        return

    # 统计
    garbage_files: list[Path] = []
    total_words_recovered = 0
    total_topics_released = 0
    all_deleted_files: dict[str, list[str]] = {"md": [], "pdf": [], "epub": []}

    # 加载当前 used_articles.json（用于后续移除）
    used_articles = load_used_articles_json()
    original_article_count = len(used_articles)

    # 遍历所有 Markdown 文件
    md_files = sorted(MARKDOWN_DIR.glob("*.md"))
    print(f"\n📁 发现 {len(md_files)} 个 Markdown 归档文件，开始扫描...\n")

    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8")

        if not is_garbage_file(content):
            continue

        garbage_files.append(md_path)
        print(f"  🗑  垃圾文件: {md_path.name}")
        print(f"      └─ 英文字母数: {len(re.findall(r'[a-zA-Z]', content))} (阈值: {ENGLISH_CHAR_THRESHOLD})")

        # 1. 提取并回滚单词进度
        words = extract_vocab_words(content)
        if words:
            recovered = rollback_word_status(words)
            total_words_recovered += recovered
            print(f"      └─ 提取词汇: {len(words)} 个，回滚成功: {recovered} 个")
        else:
            print(f"      └─ 未提取到词汇")

        # 2. 逆向释放文章占用
        released_topic = release_used_topic_by_filename(md_path.name)
        if released_topic:
            total_topics_released += 1
            used_articles.discard(released_topic)
            print(f"      └─ 释放文章占用: {released_topic}")
        else:
            print(f"      └─ 未匹配到 used_topics 记录")

        # 3. 物理删除文件
        deleted = delete_related_files(md_path)
        for ftype, fnames in deleted.items():
            all_deleted_files[ftype].extend(fnames)

        print()

    # 保存更新后的 used_articles.json
    if len(used_articles) != original_article_count:
        save_used_articles_json(used_articles)
        print(f"  💾 已更新 used_articles.json（移除 {original_article_count - len(used_articles)} 条记录）\n")

    # ── 最终统计报告 ──────────────────────────────────────
    print("=" * 60)
    print("📊  清洗报告")
    print("=" * 60)
    print(f"  扫描文件总数:     {len(md_files)}")
    print(f"  发现垃圾文件:     {len(garbage_files)}")
    print(f"  回滚单词进度:     {total_words_recovered} 个")
    print(f"  释放文章占用:     {total_topics_released} 篇")
    print(f"  删除 Markdown:    {len(all_deleted_files['md'])} 个")
    print(f"  删除 PDF:         {len(all_deleted_files['pdf'])} 个")
    print(f"  删除 EPUB:        {len(all_deleted_files['epub'])} 个")
    print("=" * 60)

    if garbage_files:
        print("\n🗑  已清理的垃圾文件列表:")
        for f in garbage_files:
            print(f"     - {f.name}")
    else:
        print("\n✅ 未发现垃圾文件，数据干净！")

    print("\n✨ 清洗完成！")


if __name__ == "__main__":
    main()
