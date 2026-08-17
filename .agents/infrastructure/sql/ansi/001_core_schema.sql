CREATE TABLE users (
    user_id CHAR(36) PRIMARY KEY,
    email_canonical VARCHAR(320) NOT NULL,
    password_hash VARCHAR(512) NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('active', 'locked', 'disabled')),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version_number BIGINT NOT NULL DEFAULT 1 CHECK (version_number > 0),
    CONSTRAINT uq_users_email UNIQUE (email_canonical)
);

CREATE TABLE user_sessions (
    session_id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    token_hash CHAR(64) NOT NULL,
    issued_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP NULL,
    client_fingerprint_hash CHAR(64) NULL,
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_sessions_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_sessions_expiry CHECK (expires_at > issued_at)
);

CREATE TABLE audit_logs (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at TIMESTAMP NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    outcome VARCHAR(16) NOT NULL CHECK (outcome IN ('success', 'failure', 'rejected', 'cancelled')),
    actor_user_id CHAR(36) NULL,
    correlation_id VARCHAR(128) NOT NULL,
    source_ip VARCHAR(64) NULL,
    resource_type VARCHAR(128) NULL,
    resource_id VARCHAR(256) NULL,
    details_json VARCHAR(4000) NULL,
    CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX ix_sessions_user_expiry ON user_sessions (user_id, expires_at);
CREATE INDEX ix_sessions_expiry ON user_sessions (expires_at);
CREATE INDEX ix_audit_occurred ON audit_logs (occurred_at);
CREATE INDEX ix_audit_correlation ON audit_logs (correlation_id);
CREATE INDEX ix_audit_actor_occurred ON audit_logs (actor_user_id, occurred_at);
