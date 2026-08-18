const encoder = new TextEncoder();
const PREFIX = "v1.";

export async function generateKey() {
  return crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}

export async function encrypt(key, plaintext, aad) {
  if (!(key instanceof CryptoKey) || aad.length === 0) throw new TypeError("A CryptoKey and non-empty AAD are required.");
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce, additionalData: aad, tagLength: 128 }, key, plaintext));
  const ciphertext = encrypted.slice(0, -16);
  const tag = encrypted.slice(-16);
  return PREFIX + toBase64Url(concat(nonce, tag, ciphertext));
}

export async function decrypt(key, envelope, aad) {
  if (!envelope.startsWith(PREFIX) || aad.length === 0) throw new TypeError("A v1 envelope and non-empty AAD are required.");
  const payload = fromBase64Url(envelope.slice(PREFIX.length));
  if (payload.length < 28) throw new TypeError("Envelope payload is truncated.");
  const nonce = payload.slice(0, 12);
  const tag = payload.slice(12, 28);
  const ciphertext = payload.slice(28);
  return new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: nonce, additionalData: aad, tagLength: 128 }, key, concat(ciphertext, tag)));
}

export function utf8(value) { return encoder.encode(value); }
function concat(...parts) { const result = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0)); let offset = 0; for (const part of parts) { result.set(part, offset); offset += part.length; } return result; }
function toBase64Url(value) { let binary = ""; for (const byte of value) binary += String.fromCharCode(byte); return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/u, ""); }
function fromBase64Url(value) { if (!/^[A-Za-z0-9_-]+$/u.test(value)) throw new TypeError("Invalid Base64URL payload."); const normalized = value.replaceAll("-", "+").replaceAll("_", "/").padEnd(Math.ceil(value.length / 4) * 4, "="); return Uint8Array.from(atob(normalized), character => character.charCodeAt(0)); }
