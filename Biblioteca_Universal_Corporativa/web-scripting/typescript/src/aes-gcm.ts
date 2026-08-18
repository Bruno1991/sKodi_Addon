import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";
import { CorporateError } from "./errors.js";

const PREFIX = "v1.";
const NONCE_SIZE = 12;
const TAG_SIZE = 16;

export interface KeyProvider { getKey(): Buffer; }

export class EnvironmentKeyProvider implements KeyProvider {
  public getKey(): Buffer {
    const encoded = process.env.MBUC_AES_KEY_BASE64;
    if (!encoded) throw new CorporateError("missing_key", "MBUC_AES_KEY_BASE64 is required.");
    const key = Buffer.from(encoded, "base64");
    validateKey(key);
    return key;
  }
}

export class AesGcmService {
  public constructor(private readonly keyProvider: KeyProvider) {}

  public encrypt(plaintext: Uint8Array, associatedData: Uint8Array): string {
    validateAad(associatedData);
    const key = this.keyProvider.getKey();
    validateKey(key);
    const nonce = randomBytes(NONCE_SIZE);
    try {
      const cipher = createCipheriv("aes-256-gcm", key, nonce, { authTagLength: TAG_SIZE });
      cipher.setAAD(Buffer.from(associatedData));
      const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
      const tag = cipher.getAuthTag();
      return PREFIX + Buffer.concat([nonce, tag, ciphertext]).toString("base64url");
    } catch (cause) {
      throw new CorporateError("encryption_failed", "Encryption failed.", { cause });
    } finally { key.fill(0); }
  }

  public decrypt(envelope: string, associatedData: Uint8Array): Buffer {
    validateAad(associatedData);
    if (!envelope.startsWith(PREFIX)) throw new CorporateError("invalid_envelope", "Unsupported crypto envelope version.");
    const encoded = envelope.slice(PREFIX.length);
    if (!/^[A-Za-z0-9_-]+$/u.test(encoded)) throw new CorporateError("invalid_envelope", "Envelope payload is not valid Base64URL.");
    const payload = Buffer.from(encoded, "base64url");
    if (payload.length < NONCE_SIZE + TAG_SIZE) throw new CorporateError("invalid_envelope", "Envelope payload is truncated.");
    const nonce = payload.subarray(0, NONCE_SIZE);
    const tag = payload.subarray(NONCE_SIZE, NONCE_SIZE + TAG_SIZE);
    const ciphertext = payload.subarray(NONCE_SIZE + TAG_SIZE);
    const key = this.keyProvider.getKey();
    validateKey(key);
    try {
      const decipher = createDecipheriv("aes-256-gcm", key, nonce, { authTagLength: TAG_SIZE });
      decipher.setAAD(Buffer.from(associatedData));
      decipher.setAuthTag(tag);
      return Buffer.concat([decipher.update(ciphertext), decipher.final()]);
    } catch (cause) {
      throw new CorporateError("authentication_failed", "Envelope authentication failed.", { cause });
    } finally { key.fill(0); }
  }
}

function validateKey(key: Uint8Array): void { if (key.length !== 32) throw new CorporateError("invalid_key", "AES-256-GCM requires exactly 32 key bytes."); }
function validateAad(aad: Uint8Array): void { if (aad.length === 0) throw new CorporateError("invalid_aad", "Associated data is required."); }
