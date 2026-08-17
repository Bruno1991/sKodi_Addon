package com.example.corporate.security

import java.nio.ByteBuffer
import java.security.SecureRandom
import java.util.Base64
import javax.crypto.AEADBadTagException
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

class CryptoException(val code: String, message: String, cause: Throwable? = null) : RuntimeException(message, cause)

fun interface KeyProvider { fun keyBytes(): ByteArray }

class EnvironmentKeyProvider : KeyProvider {
    override fun keyBytes(): ByteArray {
        val encoded = System.getenv("MBUC_AES_KEY_BASE64")?.takeIf { it.isNotBlank() }
            ?: throw CryptoException("missing_key", "MBUC_AES_KEY_BASE64 is required.")
        val key = try { Base64.getDecoder().decode(encoded) } catch (error: IllegalArgumentException) {
            throw CryptoException("invalid_key", "MBUC_AES_KEY_BASE64 is not valid Base64.", error)
        }
        requireKey(key)
        return key
    }
}

class AesGcmCipher(private val keyProvider: KeyProvider, private val random: SecureRandom = SecureRandom()) {
    fun encrypt(plaintext: ByteArray, associatedData: ByteArray): String {
        requireAad(associatedData)
        val key = keyProvider.keyBytes()
        requireKey(key)
        val nonce = ByteArray(NONCE_SIZE).also(random::nextBytes)
        try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(TAG_SIZE * 8, nonce))
            cipher.updateAAD(associatedData)
            val encrypted = cipher.doFinal(plaintext)
            val ciphertextSize = encrypted.size - TAG_SIZE
            val payload = ByteBuffer.allocate(NONCE_SIZE + TAG_SIZE + ciphertextSize)
                .put(nonce).put(encrypted, ciphertextSize, TAG_SIZE).put(encrypted, 0, ciphertextSize).array()
            return PREFIX + Base64.getUrlEncoder().withoutPadding().encodeToString(payload)
        } catch (error: Exception) {
            throw CryptoException("encryption_failed", "Encryption failed.", error)
        } finally { key.fill(0) }
    }

    fun decrypt(envelope: String, associatedData: ByteArray): ByteArray {
        requireAad(associatedData)
        if (!envelope.startsWith(PREFIX)) throw CryptoException("invalid_envelope", "Unsupported crypto envelope version.")
        val payload = try { Base64.getUrlDecoder().decode(envelope.removePrefix(PREFIX)) } catch (error: IllegalArgumentException) {
            throw CryptoException("invalid_envelope", "Envelope payload is not valid Base64URL.", error)
        }
        if (payload.size < NONCE_SIZE + TAG_SIZE) throw CryptoException("invalid_envelope", "Envelope payload is truncated.")
        val key = keyProvider.keyBytes()
        requireKey(key)
        val nonce = payload.copyOfRange(0, NONCE_SIZE)
        val tag = payload.copyOfRange(NONCE_SIZE, NONCE_SIZE + TAG_SIZE)
        val ciphertext = payload.copyOfRange(NONCE_SIZE + TAG_SIZE, payload.size)
        val combined = ciphertext + tag
        try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(TAG_SIZE * 8, nonce))
            cipher.updateAAD(associatedData)
            return cipher.doFinal(combined)
        } catch (error: AEADBadTagException) {
            throw CryptoException("authentication_failed", "Envelope authentication failed.", error)
        } catch (error: Exception) {
            throw CryptoException("decryption_failed", "Decryption failed.", error)
        } finally { key.fill(0); combined.fill(0) }
    }

    companion object {
        private const val PREFIX = "v1."
        private const val NONCE_SIZE = 12
        private const val TAG_SIZE = 16
    }
}

private fun requireKey(key: ByteArray) { if (key.size != 32) throw CryptoException("invalid_key", "AES-256-GCM requires exactly 32 key bytes.") }
private fun requireAad(aad: ByteArray) { if (aad.isEmpty()) throw CryptoException("invalid_aad", "Associated data is required.") }
