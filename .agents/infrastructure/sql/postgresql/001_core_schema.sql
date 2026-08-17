BEGIN;

CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email_canonical VARCHAR(320) NOT NULL CHECK (email_canonical = lower(email_canonical)),
    password_hash TEXT NOT NULL CHECK (length(password_hash) BETWEEN 20 AND 512),
    status VARCHAR(16) NOT NULL CHECK (status IN ('active', 'locked', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version_number BIGINT NOT NULL DEFAULT 1 CHECK (version_number > 0),
    CONSTRAINT uq_users_email UNIQUE (email_canonical)
);

CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash BYTEA NOT NULL CHECK (octet_length(token_hash) = 32),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    client_fingerprint_hash BYTEA NULL CHECK (client_fingerprint_hash IS NULL OR octet_length(client_fingerprint_hash) = 32),
    CONSTRAINT uq_sessions_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_sessions_expiry CHECK (expires_at > issued_at)
);

CREATE TABLE audit_logs (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(128) NOT NULL,
    outcome VARCHAR(16) NOT NULL CHECK (outcome IN ('success', 'failure', 'rejected', 'cancelled')),
    actor_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
    correlation_id VARCHAR(128) NOT NULL,
    source_ip INET NULL,
    resource_type VARCHAR(128) NULL,
    resource_id VARCHAR(256) NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details) = 'object')
);

CREATE INDEX ix_users_active_email ON users (email_canonical) WHERE status = 'active';
CREATE INDEX ix_sessions_user_expiry ON user_sessions (user_id, expires_at) WHERE revoked_at IS NULL;
CREATE INDEX ix_sessions_expiry ON user_sessions (expires_at) WHERE revoked_at IS NULL;
CREATE INDEX ix_audit_occurred_brin ON audit_logs USING BRIN (occurred_at);
CREATE INDEX ix_audit_correlation ON audit_logs (correlation_id);
CREATE INDEX ix_audit_actor_occurred ON audit_logs (actor_user_id, occurred_at DESC);

COMMIT;
