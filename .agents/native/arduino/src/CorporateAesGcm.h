#pragma once

#include <Arduino.h>
#include <cstddef>
#include <cstdint>

namespace mbuc {

enum class CryptoStatus : std::uint8_t { Ok, InvalidArgument, BufferTooSmall, RandomFailure, EncryptionFailure, AuthenticationFailure };

class CorporateAesGcm final {
public:
    static constexpr std::size_t KeySize = 32;
    static constexpr std::size_t NonceSize = 12;
    static constexpr std::size_t TagSize = 16;

    static CryptoStatus encrypt(const std::uint8_t key[KeySize], const std::uint8_t* plaintext, std::size_t plaintextLength,
        const std::uint8_t* aad, std::size_t aadLength, std::uint8_t nonce[NonceSize], std::uint8_t tag[TagSize],
        std::uint8_t* ciphertext, std::size_t ciphertextCapacity) noexcept;

    static CryptoStatus decrypt(const std::uint8_t key[KeySize], const std::uint8_t* ciphertext, std::size_t ciphertextLength,
        const std::uint8_t* aad, std::size_t aadLength, const std::uint8_t nonce[NonceSize], const std::uint8_t tag[TagSize],
        std::uint8_t* plaintext, std::size_t plaintextCapacity) noexcept;
};
}
