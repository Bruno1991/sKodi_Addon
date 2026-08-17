package com.example.corporate.security;

import java.time.Instant;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class StructuredLogger {
    private static final Set<String> REDACTED = Set.of("key", "password", "secret", "token", "cookie", "authorization", "plaintext", "envelope");
    private StructuredLogger() {}

    public static void log(String level, String event, String message, Map<String, ?> context) {
        var builder = new StringBuilder(256).append('{')
            .append("\"timestamp\":\"").append(Instant.now()).append("\",")
            .append("\"level\":\"").append(escape(level.toUpperCase(Locale.ROOT))).append("\",")
            .append("\"event\":\"").append(escape(event)).append("\",")
            .append("\"message\":\"").append(escape(message)).append('"');
        for (var entry : context.entrySet()) {
            builder.append(",\"").append(escape(entry.getKey())).append("\":");
            var value = REDACTED.contains(entry.getKey().toLowerCase(Locale.ROOT)) ? "[REDACTED]" : entry.getValue();
            if (value instanceof Number || value instanceof Boolean) builder.append(value);
            else builder.append('"').append(escape(String.valueOf(value))).append('"');
        }
        System.out.println(builder.append('}'));
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }
}
