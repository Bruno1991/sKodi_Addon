#pragma once

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <cstddef>
#include <cstdint>

namespace mbuc {
struct HttpResult { int status; std::size_t bodyLength; bool truncated; };

class ResilientHttpClient final {
public:
    ResilientHttpClient(const char* ssid, const char* password, const char* caCertificate, std::uint8_t maxAttempts = 3, std::uint32_t timeoutMs = 5000) noexcept;
    bool ensureConnected(std::uint32_t deadlineMs) noexcept;
    HttpResult get(const char* httpsUrl, char* body, std::size_t capacity) noexcept;
private:
    const char* ssid_;
    const char* password_;
    const char* caCertificate_;
    std::uint8_t maxAttempts_;
    std::uint32_t timeoutMs_;
    std::uint32_t nextDelay(std::uint8_t attempt) const noexcept;
};
}
