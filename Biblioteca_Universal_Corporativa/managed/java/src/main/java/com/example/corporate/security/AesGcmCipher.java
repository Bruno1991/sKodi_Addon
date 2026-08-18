package com.example.corporate.security;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public final class AesGcmCipher {
    private static final int NONCE_SIZE = 12;
    private static final int TAG_SIZE = 16;
    private static final String PREFIX = "v1.";
    private final KeyProvider keyProvider;
    private final SecureRandom random;

    public AesGcmCipher(KeyProvider keyProvider) { this(keyProvider, new SecureRandom()); }
    AesGcmCipher(KeyProvider keyProvider, SecureRandom random) { this.keyProvider = keyProvider; this.random = random; }

    public String encrypt(byte[] plaintext, byte[] associatedData) {
        requireAad(associatedData);
        var key = keyProvider.keyBytes();
        requireKey(key);
        var nonce = new byte[NONCE_SIZE];
        random.nextBytes(nonce);
        try {
            var cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(TAG_SIZE * 8, nonce));
            cipher.updateAAD(associatedData);
            var ciphertextAndTag = cipher.doFinal(plaintext);
            var ciphertextLength = ciphertextAndTag.length - TAG_SIZE;
            var payload = ByteBuffer.allocate(NONCE_SIZE + TAG_SIZE + ciphertextLength)
                .put(nonce)
                .put(ciphertextAndTag, ciphertextLength, TAG_SIZE)
                .put(ciphertextAndTag, 0, ciphertextLength)
                .array();
            return PREFIX + Base64.getUrlEncoder().withoutPadding().encodeToString(payload);
        } catch (GeneralSecurityException exception) {
            throw new CryptoException("encryption_failed", "Encryption failed.", exception);
        } finally { Arrays.fill(key, (byte) 0); }
    }

    public byte[] decrypt(String envelope, byte[] associatedData) {
        requireAad(associatedData);
        if (envelope == null || !envelope.startsWith(PREFIX)) throw new CryptoException("invalid_envelope", "Unsupported crypto envelope version.");
        final byte[] payload;
        try { payload = Base64.getUrlDecoder().decode(envelope.substring(PREFIX.length())); }
        catch (IllegalArgumentException exception) { throw new CryptoException("invalid_envelope", "Envelope payload is not valid Base64URL.", exception); }
        if (payload.length < NONCE_SIZE + TAG_SIZE) throw new CryptoException("invalid_envelope", "Envelope payload is truncated.");
        var key = keyProvider.keyBytes();
        requireKey(key);
        var nonce = Arrays.copyOfRange(payload, 0, NONCE_SIZE);
        var tag = Arrays.copyOfRange(payload, NONCE_SIZE, NONCE_SIZE + TAG_SIZE);
        var ciphertext = Arrays.copyOfRange(payload, NONCE_SIZE + TAG_SIZE, payload.length);
        var ciphertextAndTag = ByteBuffer.allocate(ciphertext.length + TAG_SIZE).put(ciphertext).put(tag).array();
        try {
            var cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(TAG_SIZE * 8, nonce));
            cipher.updateAAD(associatedData);
            return cipher.doFinal(ciphertextAndTag);
        } catch (GeneralSecurityException exception) {
            throw new CryptoException("authentication_failed", "Envelope authentication failed.", exception);
        } finally { Arrays.fill(key, (byte) 0); Arrays.fill(ciphertextAndTag, (byte) 0); }
    }

    public String encryptUtf8(String plaintext, String associatedData) { return encrypt(plaintext.getBytes(StandardCharsets.UTF_8), associatedData.getBytes(StandardCharsets.UTF_8)); }
    public String decryptUtf8(String envelope, String associatedData) { return new String(decrypt(envelope, associatedData.getBytes(StandardCharsets.UTF_8)), StandardCharsets.UTF_8); }

    private static void requireKey(byte[] key) { if (key.length != 32) throw new CryptoException("invalid_key", "AES-256-GCM requires exactly 32 key bytes."); }
    private static void requireAad(byte[] aad) { if (aad == null || aad.length == 0) throw new CryptoException("invalid_aad", "Associated data is required."); }
}
