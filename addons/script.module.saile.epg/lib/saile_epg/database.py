from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS epg_channels (
    provider_id TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    epg_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    icon_url TEXT NOT NULL DEFAULT '',
    updated_at_utc INTEGER NOT NULL,
    PRIMARY KEY (provider_id, channel_key)
);

CREATE INDEX IF NOT EXISTS idx_epg_channels_id
ON epg_channels(provider_id, epg_id COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_epg_channels_name
ON epg_channels(provider_id, normalized_name);

CREATE TABLE IF NOT EXISTS epg_programs (
    provider_id TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    start_utc INTEGER NOT NULL,
    end_utc INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    icon_url TEXT NOT NULL DEFAULT '',
    fetched_at_utc INTEGER NOT NULL,
    PRIMARY KEY (provider_id, channel_key, start_utc),
    FOREIGN KEY (provider_id, channel_key)
        REFERENCES epg_channels(provider_id, channel_key)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_epg_programs_now
ON epg_programs(provider_id, channel_key, start_utc, end_utc);

CREATE TABLE IF NOT EXISTS epg_sync_state (
    provider_id TEXT PRIMARY KEY,
    synced_at_utc INTEGER NOT NULL,
    channel_count INTEGER NOT NULL,
    program_count INTEGER NOT NULL
);
"""


class EpgDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 15000")
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
            row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
            elif int(row["version"]) != SCHEMA_VERSION:
                raise RuntimeError(f"Schema EPG não suportado: {row['version']}")

    def optimize(self) -> None:
        """Executa otimização de estatísticas e query planner no SQLite."""
        try:
            with self.connect() as connection:
                connection.execute("PRAGMA optimize")
        except Exception:
            pass
