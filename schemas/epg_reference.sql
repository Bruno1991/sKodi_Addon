-- Schema de referência do script.module.saile.epg (v1)
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
