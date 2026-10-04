"""Read-only access to an external, pre-existing SQLite knowledge-base (e.g. a wiki export).

The DB location is fully configurable (config/config.yaml -> wiki_db.path) since it lives
elsewhere on disk. Schema is auto-detected: we inspect sqlite_master + PRAGMA table_info
to find text-like columns, then do a lightweight keyword search across them for RAG context.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

_TEXT_AFFINITIES = ("CHAR", "CLOB", "TEXT")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "and", "or", "of", "to", "in",
    "on", "for", "with", "what", "how", "why", "do", "does", "did", "can", "could",
    "please", "me", "about", "this", "that", "it", "my", "your",
}


def _is_text_column(declared_type: str) -> bool:
    declared_type = (declared_type or "").upper()
    return any(a in declared_type for a in _TEXT_AFFINITIES) or declared_type == ""


class WikiDB:
    """Opens the configured SQLite file in read-only mode and exposes a simple search()."""

    def __init__(self, db_path: Path, search_limit_per_table: int = 5, max_context_chars: int = 4000):
        self.db_path = db_path
        self.search_limit_per_table = search_limit_per_table
        self.max_context_chars = max_context_chars
        self.available = db_path.exists()
        self._schema: dict[str, list[str]] = {}
        if self.available:
            try:
                self._schema = self._discover_schema()
            except sqlite3.Error:
                self.available = False

    def _connect(self) -> sqlite3.Connection:
        # Read-only, immutable-ish connection so we never modify the user's wiki DB.
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        return sqlite3.connect(uri, uri=True)

    def _discover_schema(self) -> dict[str, list[str]]:
        schema: dict[str, list[str]] = {}
        with self._connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            for (table_name,) in tables:
                cols = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                text_cols = [c[1] for c in cols if _is_text_column(c[2])]
                if text_cols:
                    schema[table_name] = text_cols
        return schema

    @staticmethod
    def _extract_keywords(query: str, limit: int = 6) -> list[str]:
        words = re.findall(r"[A-Za-z0-9_]{3,}", query.lower())
        keywords = [w for w in words if w not in _STOPWORDS]
        return keywords[:limit] or words[:limit]

    def search(self, query: str) -> str:
        """Returns a trimmed text blob of matching rows, or '' if nothing found/available."""
        if not self.available or not self._schema:
            return ""

        keywords = self._extract_keywords(query)
        if not keywords:
            return ""

        chunks: list[str] = []
        with self._connect() as conn:
            for table, columns in self._schema.items():
                col_list = ", ".join(f'"{c}"' for c in columns)
                where_clause = " OR ".join(f'"{c}" LIKE ?' for c in columns)
                sql = (
                    f'SELECT {col_list} FROM "{table}" '
                    f'WHERE ({where_clause}) LIMIT ?'
                )
                # Match if ANY keyword appears in ANY text column.
                for keyword in keywords:
                    params = [f"%{keyword}%"] * len(columns) + [self.search_limit_per_table]
                    try:
                        rows = conn.execute(sql, params).fetchall()
                    except sqlite3.Error:
                        continue
                    for row in rows:
                        row_text = " | ".join(str(v) for v in row if v is not None)
                        if row_text and row_text not in chunks:
                            chunks.append(f"[{table}] {row_text}")

        if not chunks:
            return ""

        context = "\n".join(chunks)
        return context[: self.max_context_chars]
