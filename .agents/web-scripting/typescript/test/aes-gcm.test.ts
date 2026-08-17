import assert from "node:assert/strict";
import test from "node:test";
import { AesGcmService, CorporateError, type KeyProvider } from "../src/index.js";

const provider: KeyProvider = { getKey: () => Buffer.from(Array.from({ length: 32 }, (_, index) => index)) };
const service = new AesGcmService(provider);

test("AES-GCM round trip", () => {
  const aad = Buffer.from("tenant:acme");
  const plaintext = Buffer.from("corporate secret");
  assert.deepEqual(service.decrypt(service.encrypt(plaintext, aad), aad), plaintext);
});

test("AES-GCM rejects wrong AAD", () => {
  const envelope = service.encrypt(Buffer.from("secret"), Buffer.from("tenant:acme"));
  assert.throws(() => service.decrypt(envelope, Buffer.from("tenant:other")), (error: unknown) => error instanceof CorporateError && error.code === "authentication_failed");
});
