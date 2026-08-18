package com.example.corporate.security;

import static org.junit.jupiter.api.Assertions.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

final class AesGcmCipherTest {
    private static final byte[] KEY = new byte[32];
    static { Arrays.fill(KEY, (byte) 7); }
    private final AesGcmCipher cipher = new AesGcmCipher(() -> KEY.clone());

    @Test void roundTrip() {
        var aad = "tenant:acme".getBytes(StandardCharsets.UTF_8);
        var envelope = cipher.encrypt("secret".getBytes(StandardCharsets.UTF_8), aad);
        assertArrayEquals("secret".getBytes(StandardCharsets.UTF_8), cipher.decrypt(envelope, aad));
    }

    @Test void rejectsWrongAad() {
        var envelope = cipher.encryptUtf8("secret", "tenant:acme");
        var error = assertThrows(CryptoException.class, () -> cipher.decryptUtf8(envelope, "tenant:other"));
        assertEquals("authentication_failed", error.code());
    }
}
