-- Schema de referência do script.module.saile.epg
PRAGMA foreign_keys = ON;

CREATE TABLE epg_channels (
    provider_id TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    epg_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    icon_url TEXT NOT NULL DEFAULT '',
    updated_at_utc INTEGER NOT NULL,
    PRIMARY KEY (provider_id, channel_key)
);

CREATE TABLE epg_programs (
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

CREATE INDEX idx_epg_programs_now
ON epg_programs(provider_id, channel_key, start_utc, end_utc);
