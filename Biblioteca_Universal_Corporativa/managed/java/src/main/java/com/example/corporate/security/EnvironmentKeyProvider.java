package com.example.corporate.security;

import java.util.Base64;

public final class EnvironmentKeyProvider implements KeyProvider {
    public static final String VARIABLE_NAME = "MBUC_AES_KEY_BASE64";
    private final byte[] key;

    public EnvironmentKeyProvider() {
        var encoded = System.getenv(VARIABLE_NAME);
        if (encoded == null || encoded.isBlank()) throw new CryptoException("missing_key", VARIABLE_NAME + " is required.");
        try { key = Base64.getDecoder().decode(encoded); }
        catch (IllegalArgumentException exception) { throw new CryptoException("invalid_key", VARIABLE_NAME + " is not valid Base64.", exception); }
        if (key.length != 32) throw new CryptoException("invalid_key", "AES-256-GCM requires exactly 32 key bytes.");
    }

    @Override public byte[] keyBytes() { return key.clone(); }
}
