#include "mbuc/security/aes_gcm.hpp"

#include <algorithm>
#include <cstdlib>
#include <limits>
#include <memory>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>

namespace mbuc::security {
namespace {
constexpr std::size_t nonce_size = 12;
constexpr std::size_t tag_size = 16;
constexpr auto prefix = "v1.";
using ctx_ptr = std::unique_ptr<EVP_CIPHER_CTX, decltype(&EVP_CIPHER_CTX_free)>;

void require_aad(std::span<const std::uint8_t> aad) { if (aad.empty()) throw crypto_error("invalid_aad", "Associated data is required."); }
int checked_size(std::size_t value) { if (value > static_cast<std::size_t>(std::numeric_limits<int>::max())) throw crypto_error("input_too_large", "Input exceeds OpenSSL API limits."); return static_cast<int>(value); }

std::string base64url_encode(std::span<const std::uint8_t> data) {
    std::string encoded(4 * ((data.size() + 2) / 3), '\0');
    const auto length = EVP_EncodeBlock(reinterpret_cast<unsigned char*>(encoded.data()), data.data(), checked_size(data.size()));
    if (length < 0) throw crypto_error("encoding_failed", "Base64 encoding failed.");
    encoded.resize(static_cast<std::size_t>(length));
    std::replace(encoded.begin(), encoded.end(), '+', '-');
    std::replace(encoded.begin(), encoded.end(), '/', '_');
    while (!encoded.empty() && encoded.back() == '=') encoded.pop_back();
    return encoded;
}

std::vector<std::uint8_t> base64url_decode(std::string encoded) {
    if (encoded.empty() || encoded.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_") != std::string::npos)
        throw crypto_error("invalid_envelope", "Envelope payload is not valid Base64URL.");
    std::replace(encoded.begin(), encoded.end(), '-', '+');
    std::replace(encoded.begin(), encoded.end(), '_', '/');
    while (encoded.size() % 4 != 0) encoded.push_back('=');
    std::vector<std::uint8_t> output((encoded.size() / 4) * 3);
    const auto length = EVP_DecodeBlock(output.data(), reinterpret_cast<const unsigned char*>(encoded.data()), checked_size(encoded.size()));
    if (length < 0) throw crypto_error("invalid_envelope", "Envelope payload is not valid Base64URL.");
    auto actual = static_cast<std::size_t>(length);
    if (!encoded.empty() && encoded.back() == '=') --actual;
    if (encoded.size() > 1 && encoded[encoded.size() - 2] == '=') --actual;
    output.resize(actual);
    return output;
}

std::vector<std::uint8_t> base64_standard_decode(std::string encoded) {
    if (encoded.empty() || encoded.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=") != std::string::npos || encoded.size() % 4 != 0)
        throw crypto_error("invalid_key", "MBUC_AES_KEY_BASE64 is not valid Base64.");
    std::vector<std::uint8_t> output((encoded.size() / 4) * 3);
    const auto length = EVP_DecodeBlock(output.data(), reinterpret_cast<const unsigned char*>(encoded.data()), checked_size(encoded.size()));
    if (length < 0) throw crypto_error("invalid_key", "MBUC_AES_KEY_BASE64 is not valid Base64.");
    auto actual = static_cast<std::size_t>(length);
    if (!encoded.empty() && encoded.back() == '=') --actual;
    if (encoded.size() > 1 && encoded[encoded.size() - 2] == '=') --actual;
    output.resize(actual);
    return output;
}
}

crypto_error::crypto_error(std::string code, std::string message) : std::runtime_error(std::move(message)), code_(std::move(code)) {}
const std::string& crypto_error::code() const noexcept { return code_; }

std::array<std::uint8_t, 32> environment_key_provider::key() const {
    const auto* value = std::getenv("MBUC_AES_KEY_BASE64");
    if (value == nullptr) throw crypto_error("missing_key", "MBUC_AES_KEY_BASE64 is required.");
    auto decoded = base64_standard_decode(value);
    if (decoded.size() != 32) throw crypto_error("invalid_key", "AES-256-GCM requires exactly 32 key bytes.");
    std::array<std::uint8_t, 32> result{};
    std::copy(decoded.begin(), decoded.end(), result.begin());
    OPENSSL_cleanse(decoded.data(), decoded.size());
    return result;
}

aes_gcm_service::aes_gcm_service(const key_provider& provider) noexcept : provider_(provider) {}

std::string aes_gcm_service::encrypt(std::span<const std::uint8_t> plaintext, std::span<const std::uint8_t> aad) const {
    require_aad(aad);
    auto key = provider_.key();
    std::array<std::uint8_t, nonce_size> nonce{};
    if (RAND_bytes(nonce.data(), checked_size(nonce.size())) != 1) throw crypto_error("rng_failed", "Secure random generation failed.");
    std::vector<std::uint8_t> ciphertext(plaintext.size());
    std::array<std::uint8_t, tag_size> tag{};
    ctx_ptr context(EVP_CIPHER_CTX_new(), EVP_CIPHER_CTX_free);
    if (!context) throw crypto_error("encryption_failed", "Encryption context allocation failed.");
    int length = 0;
    int total = 0;
    const bool ok = EVP_EncryptInit_ex(context.get(), EVP_aes_256_gcm(), nullptr, nullptr, nullptr) == 1
        && EVP_CIPHER_CTX_ctrl(context.get(), EVP_CTRL_GCM_SET_IVLEN, checked_size(nonce.size()), nullptr) == 1
        && EVP_EncryptInit_ex(context.get(), nullptr, nullptr, key.data(), nonce.data()) == 1
        && EVP_EncryptUpdate(context.get(), nullptr, &length, aad.data(), checked_size(aad.size())) == 1
        && EVP_EncryptUpdate(context.get(), ciphertext.data(), &length, plaintext.data(), checked_size(plaintext.size())) == 1;
    total = length;
    const bool finalized = ok && EVP_EncryptFinal_ex(context.get(), ciphertext.data() + total, &length) == 1;
    total += length;
    const bool tagged = finalized && EVP_CIPHER_CTX_ctrl(context.get(), EVP_CTRL_GCM_GET_TAG, checked_size(tag.size()), tag.data()) == 1;
    OPENSSL_cleanse(key.data(), key.size());
    if (!tagged) throw crypto_error("encryption_failed", "Encryption failed.");
    ciphertext.resize(static_cast<std::size_t>(total));
    std::vector<std::uint8_t> payload;
    payload.reserve(nonce.size() + tag.size() + ciphertext.size());
    payload.insert(payload.end(), nonce.begin(), nonce.end());
    payload.insert(payload.end(), tag.begin(), tag.end());
    payload.insert(payload.end(), ciphertext.begin(), ciphertext.end());
    return std::string(prefix) + base64url_encode(payload);
}

std::vector<std::uint8_t> aes_gcm_service::decrypt(const std::string& envelope, std::span<const std::uint8_t> aad) const {
    require_aad(aad);
    if (!envelope.starts_with(prefix)) throw crypto_error("invalid_envelope", "Unsupported crypto envelope version.");
    auto payload = base64url_decode(envelope.substr(3));
    if (payload.size() < nonce_size + tag_size) throw crypto_error("invalid_envelope", "Envelope payload is truncated.");
    const auto nonce = std::span(payload).first(nonce_size);
    const auto tag = std::span(payload).subspan(nonce_size, tag_size);
    const auto ciphertext = std::span(payload).subspan(nonce_size + tag_size);
    auto key = provider_.key();
    std::vector<std::uint8_t> plaintext(ciphertext.size());
    ctx_ptr context(EVP_CIPHER_CTX_new(), EVP_CIPHER_CTX_free);
    if (!context) throw crypto_error("decryption_failed", "Decryption context allocation failed.");
    int length = 0;
    int total = 0;
    const bool ok = EVP_DecryptInit_ex(context.get(), EVP_aes_256_gcm(), nullptr, nullptr, nullptr) == 1
        && EVP_CIPHER_CTX_ctrl(context.get(), EVP_CTRL_GCM_SET_IVLEN, checked_size(nonce.size()), nullptr) == 1
        && EVP_DecryptInit_ex(context.get(), nullptr, nullptr, key.data(), nonce.data()) == 1
        && EVP_DecryptUpdate(context.get(), nullptr, &length, aad.data(), checked_size(aad.size())) == 1
        && EVP_DecryptUpdate(context.get(), plaintext.data(), &length, ciphertext.data(), checked_size(ciphertext.size())) == 1;
    total = length;
    const bool tag_set = ok && EVP_CIPHER_CTX_ctrl(context.get(), EVP_CTRL_GCM_SET_TAG, checked_size(tag.size()), const_cast<std::uint8_t*>(tag.data())) == 1;
    const bool authenticated = tag_set && EVP_DecryptFinal_ex(context.get(), plaintext.data() + total, &length) == 1;
    OPENSSL_cleanse(key.data(), key.size());
    OPENSSL_cleanse(payload.data(), payload.size());
    if (!authenticated) { OPENSSL_cleanse(plaintext.data(), plaintext.size()); throw crypto_error("authentication_failed", "Envelope authentication failed."); }
    plaintext.resize(static_cast<std::size_t>(total + length));
    return plaintext;
}
}
