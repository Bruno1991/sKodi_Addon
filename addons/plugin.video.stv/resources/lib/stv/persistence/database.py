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

CREATE INDEX IF NOT EXISTS idx_media_items_search
ON media_items(media_type, name COLLATE NOCASE);

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

CREATE TABLE IF NOT EXISTS epg_programs (
    channel_key TEXT NOT NULL,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    synopsis TEXT NOT NULL DEFAULT '',
    duration INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (channel_key, start_time)
);

CREATE INDEX IF NOT EXISTS idx_epg_channel_time
ON epg_programs(channel_key, start_time, end_time);
"""

FTS5_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS media_items_fts USING fts5(
    media_type UNINDEXED,
    item_id UNINDEXED,
    name,
    plot,
    category_id UNINDEXED,
    content='media_items',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS trg_media_items_ai AFTER INSERT ON media_items BEGIN
    INSERT INTO media_items_fts(rowid, media_type, item_id, name, plot, category_id)
    VALUES (new.rowid, new.media_type, new.item_id, new.name, new.plot, new.category_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_media_items_ad AFTER DELETE ON media_items BEGIN
    INSERT INTO media_items_fts(media_items_fts, rowid, media_type, item_id, name, plot, category_id)
    VALUES ('delete', old.rowid, old.media_type, old.item_id, old.name, old.plot, old.category_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_media_items_au AFTER UPDATE ON media_items BEGIN
    INSERT INTO media_items_fts(media_items_fts, rowid, media_type, item_id, name, plot, category_id)
    VALUES ('delete', old.rowid, old.media_type, old.item_id, old.name, old.plot, old.category_id);
    INSERT INTO media_items_fts(rowid, media_type, item_id, name, plot, category_id)
    VALUES (new.rowid, new.media_type, new.item_id, new.name, new.plot, new.category_id);
END;
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fts_available = False

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
            
            # Tenta inicializar a tabela de busca FTS5 com fallback seguro
            try:
                connection.executescript(FTS5_SCHEMA)
                self.fts_available = True
            except sqlite3.OperationalError:
                self.fts_available = False

            row = connection.execute("SELECT COUNT(*) AS total FROM schema_version").fetchone()
            if row["total"] == 0:
                connection.execute("INSERT INTO schema_version(version) VALUES (3)")
            else:
                connection.execute("UPDATE schema_version SET version = 3")

