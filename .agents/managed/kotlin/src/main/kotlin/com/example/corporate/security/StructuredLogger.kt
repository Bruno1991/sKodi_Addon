package com.example.corporate.security

import java.time.Instant

object StructuredLogger {
    private val redacted = setOf("key", "password", "secret", "token", "cookie", "authorization", "plaintext", "envelope")

    fun log(level: String, event: String, message: String, context: Map<String, Any?> = emptyMap()) {
        val fields = linkedMapOf<String, Any?>("timestamp" to Instant.now().toString(), "level" to level.uppercase(), "event" to event, "message" to message)
        context.forEach { (name, value) -> fields[name] = if (name.lowercase() in redacted) "[REDACTED]" else value }
        println(fields.entries.joinToString(prefix = "{", postfix = "}") { (name, value) -> "\"${escape(name)}\":${encode(value)}" })
    }

    private fun encode(value: Any?): String = when (value) {
        null -> "null"
        is Number, is Boolean -> value.toString()
        else -> "\"${escape(value.toString())}\""
    }

    private fun escape(value: String): String = value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
}
