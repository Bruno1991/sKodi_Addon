#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace mbuc::security {

class crypto_error final : public std::runtime_error {
public:
    crypto_error(std::string code, std::string message);
    [[nodiscard]] const std::string& code() const noexcept;
private:
    std::string code_;
};

class key_provider {
public:
    virtual ~key_provider() = default;
    [[nodiscard]] virtual std::array<std::uint8_t, 32> key() const = 0;
};

class environment_key_provider final : public key_provider {
public:
    [[nodiscard]] std::array<std::uint8_t, 32> key() const override;
};

class aes_gcm_service final {
public:
    explicit aes_gcm_service(const key_provider& provider) noexcept;
    [[nodiscard]] std::string encrypt(std::span<const std::uint8_t> plaintext, std::span<const std::uint8_t> associated_data) const;
    [[nodiscard]] std::vector<std::uint8_t> decrypt(const std::string& envelope, std::span<const std::uint8_t> associated_data) const;
private:
    const key_provider& provider_;
};

}
