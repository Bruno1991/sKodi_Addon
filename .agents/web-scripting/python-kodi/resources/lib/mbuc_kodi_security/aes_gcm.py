from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .errors import CorporateError

PREFIX = "v1."
NONCE_SIZE = 12
TAG_SIZE = 16


class KeyProvider(Protocol):
    def get_key(self) -> bytes:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class EnvironmentKeyProvider:
    variable_name: str = "MBUC_AES_KEY_BASE64"

    def get_key(self) -> bytes:
        encoded = os.environ.get(self.variable_name)
        if not encoded:
            raise CorporateError("missing_key", f"Environment variable {self.variable_name} is required.")
        try:
            key = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise CorporateError("invalid_key", f"Environment variable {self.variable_name} is not valid Base64.", cause=error) from error
        _validate_key(key)
        return key


class AesGcmService:
    def __init__(self, key_provider: KeyProvider) -> None:
        self._key_provider = key_provider

    def encrypt(self, plaintext: bytes, associated_data: bytes) -> str:
        _validate_aad(associated_data)
        key = self._key_provider.get_key()
        _validate_key(key)
        nonce = os.urandom(NONCE_SIZE)
        ciphertext_and_tag = AESGCM(key).encrypt(nonce, plaintext, associated_data)
        ciphertext, tag = ciphertext_and_tag[:-TAG_SIZE], ciphertext_and_tag[-TAG_SIZE:]
        return PREFIX + base64.urlsafe_b64encode(nonce + tag + ciphertext).rstrip(b"=").decode("ascii")

    def decrypt(self, envelope: str, associated_data: bytes) -> bytes:
        _validate_aad(associated_data)
        if not isinstance(envelope, str) or not envelope.startswith(PREFIX):
            raise CorporateError("invalid_envelope", "Unsupported crypto envelope version.")
        encoded = envelope[len(PREFIX):]
        try:
            payload = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        except (binascii.Error, ValueError) as error:
            raise CorporateError("invalid_envelope", "Envelope payload is not valid Base64URL.", cause=error) from error
        if len(payload) < NONCE_SIZE + TAG_SIZE:
            raise CorporateError("invalid_envelope", "Envelope payload is truncated.")
        nonce = payload[:NONCE_SIZE]
        tag = payload[NONCE_SIZE:NONCE_SIZE + TAG_SIZE]
        ciphertext = payload[NONCE_SIZE + TAG_SIZE:]
        key = self._key_provider.get_key()
        _validate_key(key)
        try:
            return AESGCM(key).decrypt(nonce, ciphertext + tag, associated_data)
        except InvalidTag as error:
            raise CorporateError("authentication_failed", "Envelope authentication failed.", cause=error) from error


def _validate_key(key: bytes) -> None:
    if len(key) != 32:
        raise CorporateError("invalid_key", "AES-256-GCM requires exactly 32 key bytes.")


def _validate_aad(associated_data: bytes) -> None:
    if not associated_data:
        raise CorporateError("invalid_aad", "Associated data is required.")
