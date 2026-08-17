PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

BEGIN IMMEDIATE;

CREATE TABLE users (
    user_id TEXT PRIMARY KEY CHECK (length(user_id) = 36),
    email_canonical TEXT NOT NULL CHECK (length(email_canonical) BETWEEN 3 AND 320 AND email_canonical = lower(email_canonical)),
    password_hash TEXT NOT NULL CHECK (length(password_hash) BETWEEN 20 AND 512),
    status TEXT NOT NULL CHECK (status IN ('active', 'locked', 'disabled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1 CHECK (version_number > 0),
    CONSTRAINT uq_users_email UNIQUE (email_canonical)
) STRICT;

CREATE TABLE user_sessions (
    session_id TEXT PRIMARY KEY CHECK (length(session_id) = 36),
    user_id TEXT NOT NULL,
    token_hash BLOB NOT NULL CHECK (length(token_hash) = 32),
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT NULL,
    client_fingerprint_hash BLOB NULL CHECK (client_fingerprint_hash IS NULL OR length(client_fingerprint_hash) = 32),
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_sessions_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_sessions_expiry CHECK (expires_at > issued_at)
) STRICT;

CREATE TABLE audit_logs (
    audit_id INTEGER PRIMARY KEY,
    occurred_at TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 128),
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure', 'rejected', 'cancelled')),
    actor_user_id TEXT NULL,
    correlation_id TEXT NOT NULL CHECK (length(correlation_id) BETWEEN 8 AND 128),
    source_ip TEXT NULL,
    resource_type TEXT NULL,
    resource_id TEXT NULL,
    details_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(details_json) AND json_type(details_json) = 'object'),
    CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users(user_id) ON DELETE SET NULL
) STRICT;

CREATE INDEX ix_sessions_user_expiry ON user_sessions (user_id, expires_at) WHERE revoked_at IS NULL;
CREATE INDEX ix_sessions_expiry ON user_sessions (expires_at) WHERE revoked_at IS NULL;
CREATE INDEX ix_audit_occurred ON audit_logs (occurred_at);
CREATE INDEX ix_audit_correlation ON audit_logs (correlation_id);
CREATE INDEX ix_audit_actor_occurred ON audit_logs (actor_user_id, occurred_at DESC);

COMMIT;
