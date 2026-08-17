CREATE TABLE users (
    user_id BINARY(16) NOT NULL,
    email_canonical VARCHAR(320) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    password_hash VARCHAR(512) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    status ENUM('active', 'locked', 'disabled') NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    version_number BIGINT UNSIGNED NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_email (email_canonical),
    CONSTRAINT ck_users_version CHECK (version_number > 0)
) ENGINE=InnoDB;

CREATE TABLE user_sessions (
    session_id BINARY(16) NOT NULL,
    user_id BINARY(16) NOT NULL,
    token_hash BINARY(32) NOT NULL,
    issued_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    expires_at TIMESTAMP(6) NOT NULL,
    revoked_at TIMESTAMP(6) NULL,
    client_fingerprint_hash BINARY(32) NULL,
    PRIMARY KEY (session_id),
    UNIQUE KEY uq_sessions_token_hash (token_hash),
    KEY ix_sessions_user_expiry (user_id, expires_at),
    KEY ix_sessions_expiry (expires_at),
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT ck_sessions_expiry CHECK (expires_at > issued_at)
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
    audit_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    occurred_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    event_type VARCHAR(128) NOT NULL,
    outcome ENUM('success', 'failure', 'rejected', 'cancelled') NOT NULL,
    actor_user_id BINARY(16) NULL,
    correlation_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    source_ip VARBINARY(16) NULL,
    resource_type VARCHAR(128) NULL,
    resource_id VARCHAR(256) NULL,
    details JSON NOT NULL,
    PRIMARY KEY (audit_id),
    KEY ix_audit_occurred (occurred_at),
    KEY ix_audit_correlation (correlation_id),
    KEY ix_audit_actor_occurred (actor_user_id, occurred_at),
    CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;
