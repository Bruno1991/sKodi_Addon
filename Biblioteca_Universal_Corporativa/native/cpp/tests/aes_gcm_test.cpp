#include "mbuc/security/aes_gcm.hpp"

#include <algorithm>
#include <cassert>
#include <cstdint>
#include <string>

class static_key final : public mbuc::security::key_provider {
public:
    std::array<std::uint8_t, 32> key() const override { std::array<std::uint8_t, 32> value{}; value.fill(7); return value; }
};

std::span<const std::uint8_t> bytes(const std::string& value) {
    return {reinterpret_cast<const std::uint8_t*>(value.data()), value.size()};
}

int main() {
    const static_key key;
    const mbuc::security::aes_gcm_service service(key);
    const std::string plaintext = "corporate secret";
    const std::string aad = "tenant:acme";
    const auto envelope = service.encrypt(bytes(plaintext), bytes(aad));
    const auto decrypted = service.decrypt(envelope, bytes(aad));
    assert(std::equal(decrypted.begin(), decrypted.end(), plaintext.begin(), plaintext.end()));
    bool rejected = false;
    try { const std::string wrong = "tenant:other"; static_cast<void>(service.decrypt(envelope, bytes(wrong))); }
    catch (const mbuc::security::crypto_error& error) { rejected = error.code() == "authentication_failed"; }
    assert(rejected);
    return 0;
}
