const REDACTED = new Set(["key", "password", "secret", "token", "cookie", "authorization", "plaintext", "envelope"]);
export type Level = "DEBUG" | "INFO" | "WARN" | "ERROR";

export function logEvent(level: Level, event: string, message: string, context: Record<string, unknown>): void {
  const safe: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(context)) safe[key] = REDACTED.has(key.toLowerCase()) ? "[REDACTED]" : value;
  process.stdout.write(JSON.stringify({ timestamp: new Date().toISOString(), level, event, message, ...safe }) + "\n");
}
