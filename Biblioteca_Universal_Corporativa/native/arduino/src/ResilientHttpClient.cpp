#include "ResilientHttpClient.h"

#include <WiFiClientSecure.h>

namespace mbuc {
ResilientHttpClient::ResilientHttpClient(const char* ssid, const char* password, const char* caCertificate, std::uint8_t maxAttempts, std::uint32_t timeoutMs) noexcept
    : ssid_(ssid), password_(password), caCertificate_(caCertificate), maxAttempts_(maxAttempts ? maxAttempts : 1), timeoutMs_(timeoutMs ? timeoutMs : 1000) {}

bool ResilientHttpClient::ensureConnected(std::uint32_t deadlineMs) noexcept {
    if (WiFi.status() == WL_CONNECTED) return true;
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(ssid_, password_);
    while (WiFi.status() != WL_CONNECTED && static_cast<std::int32_t>(deadlineMs - millis()) > 0) delay(50);
    return WiFi.status() == WL_CONNECTED;
}

HttpResult ResilientHttpClient::get(const char* httpsUrl, char* body, std::size_t capacity) noexcept {
    if (!httpsUrl || strncmp(httpsUrl, "https://", 8) != 0 || !body || capacity < 2 || !caCertificate_ || !*caCertificate_) return {-1, 0, false};
    body[0] = '\0';
    for (std::uint8_t attempt = 0; attempt < maxAttempts_; ++attempt) {
        if (!ensureConnected(millis() + timeoutMs_)) { delay(nextDelay(attempt)); continue; }
        WiFiClientSecure transport;
        transport.setTimeout(timeoutMs_);
        transport.setCACert(caCertificate_);
        HTTPClient http;
        http.setTimeout(timeoutMs_);
        http.setReuse(false);
        if (!http.begin(transport, httpsUrl)) return {-2, 0, false};
        const int status = http.GET();
        if (status > 0 && status < 500 && status != 408 && status != 429) {
            WiFiClient* stream = http.getStreamPtr();
            std::size_t used = 0;
            while (http.connected() && (stream->available() || used == 0)) {
                while (stream->available()) {
                    const int value = stream->read();
                    if (value < 0) break;
                    if (used + 1 < capacity) body[used++] = static_cast<char>(value);
                    else { body[used] = '\0'; http.end(); return {status, used, true}; }
                }
                delay(1);
            }
            body[used] = '\0';
            http.end();
            return {status, used, false};
        }
        http.end();
        if (attempt + 1 < maxAttempts_) delay(nextDelay(attempt));
    }
    return {-3, 0, false};
}

std::uint32_t ResilientHttpClient::nextDelay(std::uint8_t attempt) const noexcept {
    const std::uint32_t exponential = 250UL << (attempt > 4 ? 4 : attempt);
    return exponential + static_cast<std::uint32_t>(esp_random() % 250UL);
}
}
