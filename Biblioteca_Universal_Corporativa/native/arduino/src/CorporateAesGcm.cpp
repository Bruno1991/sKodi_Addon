#include "CorporateAesGcm.h"

#include <esp_system.h>
#include <mbedtls/gcm.h>
#include <cstring>

namespace mbuc {
CryptoStatus CorporateAesGcm::encrypt(const std::uint8_t key[KeySize], const std::uint8_t* plaintext, std::size_t plaintextLength,
    const std::uint8_t* aad, std::size_t aadLength, std::uint8_t nonce[NonceSize], std::uint8_t tag[TagSize],
    std::uint8_t* ciphertext, std::size_t ciphertextCapacity) noexcept {
    if (!key || (!plaintext && plaintextLength) || !aad || aadLength == 0 || !nonce || !tag || (!ciphertext && plaintextLength)) return CryptoStatus::InvalidArgument;
    if (ciphertextCapacity < plaintextLength) return CryptoStatus::BufferTooSmall;
    esp_fill_random(nonce, NonceSize);
    mbedtls_gcm_context context;
    mbedtls_gcm_init(&context);
    int result = mbedtls_gcm_setkey(&context, MBEDTLS_CIPHER_ID_AES, key, KeySize * 8);
    if (result == 0) result = mbedtls_gcm_crypt_and_tag(&context, MBEDTLS_GCM_ENCRYPT, plaintextLength, nonce, NonceSize, aad, aadLength, plaintext, ciphertext, TagSize, tag);
    mbedtls_gcm_free(&context);
    return result == 0 ? CryptoStatus::Ok : CryptoStatus::EncryptionFailure;
}

CryptoStatus CorporateAesGcm::decrypt(const std::uint8_t key[KeySize], const std::uint8_t* ciphertext, std::size_t ciphertextLength,
    const std::uint8_t* aad, std::size_t aadLength, const std::uint8_t nonce[NonceSize], const std::uint8_t tag[TagSize],
    std::uint8_t* plaintext, std::size_t plaintextCapacity) noexcept {
    if (!key || (!ciphertext && ciphertextLength) || !aad || aadLength == 0 || !nonce || !tag || (!plaintext && ciphertextLength)) return CryptoStatus::InvalidArgument;
    if (plaintextCapacity < ciphertextLength) return CryptoStatus::BufferTooSmall;
    mbedtls_gcm_context context;
    mbedtls_gcm_init(&context);
    int result = mbedtls_gcm_setkey(&context, MBEDTLS_CIPHER_ID_AES, key, KeySize * 8);
    if (result == 0) result = mbedtls_gcm_auth_decrypt(&context, ciphertextLength, nonce, NonceSize, aad, aadLength, tag, TagSize, ciphertext, plaintext);
    mbedtls_gcm_free(&context);
    if (result != 0 && plaintext && ciphertextLength) std::memset(plaintext, 0, ciphertextLength);
    return result == 0 ? CryptoStatus::Ok : CryptoStatus::AuthenticationFailure;
}
}
