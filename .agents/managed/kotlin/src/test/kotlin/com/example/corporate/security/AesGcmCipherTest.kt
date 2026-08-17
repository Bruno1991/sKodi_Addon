package com.example.corporate.security

import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class AesGcmCipherTest {
    private val cipher = AesGcmCipher(KeyProvider { ByteArray(32) { 9 } })

    @Test fun roundTrip() {
        val plaintext = "corporate secret".encodeToByteArray()
        val aad = "tenant:acme".encodeToByteArray()
        assertContentEquals(plaintext, cipher.decrypt(cipher.encrypt(plaintext, aad), aad))
    }

    @Test fun rejectsWrongAad() {
        val envelope = cipher.encrypt("secret".encodeToByteArray(), "tenant:acme".encodeToByteArray())
        val error = assertFailsWith<CryptoException> { cipher.decrypt(envelope, "tenant:other".encodeToByteArray()) }
        assertEquals("authentication_failed", error.code)
    }
}
