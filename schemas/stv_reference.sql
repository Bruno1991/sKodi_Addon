-- Schema de referência do plugin.video.stv (v8)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    media_type TEXT NOT NULL,
    category_id TEXT NOT NULL,
    name TEXT NOT NULL,
    parent_id TEXT NOT NULL DEFAULT '0',
    generation_id INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_type, category_id)
);

CREATE INDEX IF NOT EXISTS idx_categories_order
ON categories(media_type, name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS media_items (
    media_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    category_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    fanart TEXT NOT NULL DEFAULT '',
    plot TEXT NOT NULL DEFAULT '',
    extension TEXT NOT NULL DEFAULT '',
    epg_id TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL DEFAULT '',
    normalized_name TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    generation_id INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_type, item_id)
);

CREATE INDEX IF NOT EXISTS idx_media_items_category
ON media_items(media_type, category_id, name COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_media_items_search
ON media_items(media_type, name COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_media_items_normalized
ON media_items(media_type, normalized_name);

CREATE TABLE IF NOT EXISTS favorites (
    media_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_type, item_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_order
ON favorites(media_type, created_at DESC, item_id);

CREATE TABLE IF NOT EXISTS live_channel_favorites (
    channel_key TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS catalog_sync_state (
    media_type TEXT PRIMARY KEY,
    generation_id INTEGER NOT NULL,
    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS playback_progress (
    media_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    position REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_type, item_id)
);

CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS media_items_fts USING fts5(
    media_type UNINDEXED,
    item_id UNINDEXED,
    name,
    plot,
    category_id UNINDEXED,
    content='media_items',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);

