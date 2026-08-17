-- Schema de referência do plugin.video.stv
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    media_type TEXT NOT NULL CHECK (media_type IN ('live','vod','series')),
    provider_category_id TEXT NOT NULL,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    sync_generation INTEGER NOT NULL,
    PRIMARY KEY (media_type, provider_category_id)
);

CREATE TABLE IF NOT EXISTS media_items (
    media_type TEXT NOT NULL CHECK (media_type IN ('live','vod','series','episode')),
    provider_item_id TEXT NOT NULL,
    provider_category_id TEXT,
    parent_item_id TEXT,
    season_number INTEGER,
    episode_number INTEGER,
    title TEXT NOT NULL,
    plot TEXT,
    icon_url TEXT,
    container_extension TEXT,
    release_year INTEGER,
    tmdb_id INTEGER,
    raw_json TEXT,
    sync_generation INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (media_type, provider_item_id)
);

CREATE INDEX IF NOT EXISTS idx_stv_items_category
ON media_items(media_type, provider_category_id, title);

CREATE TABLE IF NOT EXISTS favorites (
    media_type TEXT NOT NULL,
    provider_item_id TEXT NOT NULL,
    title_snapshot TEXT NOT NULL,
    art_snapshot TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (media_type, provider_item_id)
);

CREATE TABLE IF NOT EXISTS playback_progress (
    media_type TEXT NOT NULL CHECK (media_type IN ('vod','episode')),
    provider_item_id TEXT NOT NULL,
    position_seconds REAL NOT NULL CHECK (position_seconds >= 0),
    duration_seconds REAL NOT NULL CHECK (duration_seconds >= 0),
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0,1)),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (media_type, provider_item_id)
);

CREATE TABLE IF NOT EXISTS metadata_cache (
    media_type TEXT NOT NULL,
    provider_item_id TEXT NOT NULL,
    tmdb_id INTEGER,
    payload_json TEXT,
    match_score REAL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (media_type, provider_item_id)
);
