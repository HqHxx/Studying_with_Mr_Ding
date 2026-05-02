"""SQLite 数据库管理模块（多词库版）。

支持 CET-4 / CET-6 / 考研 / 托福 四级词库，每个单词带 level 字段。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


class DBManager:
    """管理多级别词库：word + level + status(0=未学, 1=已学)。"""

    def __init__(self, db_path: str | Path = "cet4_words.db") -> None:
        self.db_path = str(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        """初始化数据表。自动迁移旧表（补 level 列）。"""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS words (
                    word TEXT,
                    phonetic TEXT,
                    definition TEXT,
                    level TEXT NOT NULL DEFAULT 'CET-4',
                    status INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (word, level)
                )
                """
            )
            # 兼容旧表：如果旧表没有 level 列，自动添加
            try:
                conn.execute("SELECT level FROM words LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE words ADD COLUMN level TEXT NOT NULL DEFAULT 'CET-4'")

            # 保留触发器
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_words_updated_at
                AFTER UPDATE ON words
                FOR EACH ROW
                BEGIN
                    UPDATE words SET updated_at = CURRENT_TIMESTAMP
                    WHERE word = OLD.word AND level = OLD.level;
                END;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS used_topics (
                    topic TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def mark_topic_used(self, topic: str) -> None:
        """将主题标记为已使用。"""
        if not topic:
            return
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO used_topics (topic) VALUES (?)", (topic,))
            conn.commit()

    def get_used_topics(self) -> list[str]:
        """获取所有已成功使用过的主题。"""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT topic FROM used_topics").fetchall()
        return [row["topic"] for row in rows]

    def upsert_words(self, word_data: Iterable[dict], level: str = "CET-4") -> int:
        """批量插入新单词（支持 level 字段）。返回成功插入数量。"""
        if not word_data:
            return 0

        with self._get_connection() as conn:
            before = conn.total_changes
            conn.executemany(
                "INSERT OR IGNORE INTO words (word, phonetic, definition, level, status) "
                "VALUES (?, ?, ?, ?, 0)",
                [
                    (
                        w.get("word", "").strip().lower(),
                        w.get("phonetic", ""),
                        w.get("definition", ""),
                        level,
                    )
                    for w in word_data
                ],
            )
            conn.commit()
            return conn.total_changes - before

    def get_unlearned_words(self, limit: int = 30, level: str | None = None) -> list[dict]:
        """随机抽取未学单词。如果指定 level 则只抽该级别。"""
        with self._get_connection() as conn:
            if level:
                rows = conn.execute(
                    "SELECT word, phonetic, definition FROM words "
                    "WHERE status = 0 AND level = ? ORDER BY RANDOM() LIMIT ?",
                    (level, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT word, phonetic, definition FROM words "
                    "WHERE status = 0 ORDER BY RANDOM() LIMIT ?",
                    (limit,),
                ).fetchall()
        return [
            {"word": row["word"], "phonetic": row["phonetic"], "definition": row["definition"]}
            for row in rows
        ]

    def mark_words_learned(self, words: list[str], level: str | None = None) -> int:
        """批量将单词标记为已学。如果指定 level 则精确匹配。"""
        if not words:
            return 0

        with self._get_connection() as conn:
            updated = 0
            for w in words:
                clean = w.strip().lower()
                if not clean:
                    continue
                if level:
                    cur = conn.execute(
                        "UPDATE words SET status = 1 WHERE word = ? AND level = ?",
                        (clean, level),
                    )
                else:
                    cur = conn.execute(
                        "UPDATE words SET status = 1 WHERE word = ?",
                        (clean,),
                    )
                updated += cur.rowcount
            conn.commit()
            return updated

    def count_words(self, level: str | None = None) -> tuple[int, int]:
        """返回 (总数, 未学数)。可按级别过滤。"""
        with self._get_connection() as conn:
            if level:
                total = conn.execute(
                    "SELECT COUNT(*) FROM words WHERE level = ?", (level,)
                ).fetchone()[0]
                unlearned = conn.execute(
                    "SELECT COUNT(*) FROM words WHERE status = 0 AND level = ?", (level,)
                ).fetchone()[0]
            else:
                total = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
                unlearned = conn.execute(
                    "SELECT COUNT(*) FROM words WHERE status = 0"
                ).fetchone()[0]
        return total, unlearned

    def get_all_levels(self) -> list[str]:
        """获取数据库中所有已导入的词库级别。"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT level FROM words ORDER BY level"
            ).fetchall()
        return [row["level"] for row in rows]

    def reset_all_progress(self, level: str | None = None) -> int:
        """将单词重置为未学状态。可按级别过滤。"""
        with self._get_connection() as conn:
            if level:
                cur = conn.execute("UPDATE words SET status = 0 WHERE level = ?", (level,))
            else:
                cur = conn.execute("UPDATE words SET status = 0")
            conn.commit()
            return cur.rowcount

    def reset_used_topics(self) -> int:
        """清空已使用主题记录。返回删除行数。"""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM used_topics")
            conn.commit()
            return cur.rowcount