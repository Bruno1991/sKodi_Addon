from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS categories (
    media_type TEXT NOT NULL,
    category_id TEXT NOT NULL,
    name TEXT NOT NULL,
    parent_id TEXT NOT NULL DEFAULT '0',
    generation_id INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_type, category_id)
);
CREATE TABLE IF NOT EXISTS media_items (
    media_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    category_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    fanart TEXT NOT NULL DEFAULT '',
    plot TEXT NOT NULL DEFAULT '',
    extension TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    generation_id INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_type, item_id)
);
CREATE INDEX IF NOT EXISTS idx_media_items_category
ON media_items(media_type, category_id, name COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS favorites (
    media_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_type, item_id)
);
CREATE TABLE IF NOT EXISTS playback_progress (
    media_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    position REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_type, item_id)
);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            row = connection.execute("SELECT COUNT(*) AS total FROM schema_version").fetchone()
            if row["total"] == 0:
                connection.execute("INSERT INTO schema_version(version) VALUES (1)")
