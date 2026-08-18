use aes_gcm::aead::{Aead, KeyInit, Payload};
use aes_gcm::{Aes256Gcm, Nonce};
use base64::engine::general_purpose::{STANDARD, URL_SAFE_NO_PAD};
use base64::Engine;
use rand_core::{OsRng, RngCore};
use thiserror::Error;
use zeroize::Zeroize;

const PREFIX: &str = "v1.";
const NONCE_SIZE: usize = 12;
const TAG_SIZE: usize = 16;

#[derive(Debug, Error)]
pub enum CryptoError {
    #[error("MBUC_AES_KEY_BASE64 is required")]
    MissingKey,
    #[error("AES-256-GCM requires exactly 32 key bytes")]
    InvalidKey,
    #[error("associated data is required")]
    InvalidAad,
    #[error("crypto envelope is invalid or unsupported")]
    InvalidEnvelope,
    #[error("encryption failed")]
    EncryptionFailed,
    #[error("envelope authentication failed")]
    AuthenticationFailed,
}

pub struct KeyMaterial([u8; 32]);

impl KeyMaterial {
    pub fn new(bytes: [u8; 32]) -> Self { Self(bytes) }
    fn as_bytes(&self) -> &[u8; 32] { &self.0 }
}

impl Drop for KeyMaterial {
    fn drop(&mut self) { self.0.zeroize(); }
}

pub trait KeyProvider: Send + Sync {
    fn key(&self) -> Result<KeyMaterial, CryptoError>;
}

pub struct EnvironmentKeyProvider;

impl KeyProvider for EnvironmentKeyProvider {
    fn key(&self) -> Result<KeyMaterial, CryptoError> {
        let encoded = std::env::var("MBUC_AES_KEY_BASE64").map_err(|_| CryptoError::MissingKey)?;
        let decoded = STANDARD.decode(encoded).map_err(|_| CryptoError::InvalidKey)?;
        let bytes: [u8; 32] = decoded.try_into().map_err(|_| CryptoError::InvalidKey)?;
        Ok(KeyMaterial::new(bytes))
    }
}

pub struct AesGcmService<P: KeyProvider> {
    provider: P,
}

impl<P: KeyProvider> AesGcmService<P> {
    pub fn new(provider: P) -> Self { Self { provider } }

    pub fn encrypt(&self, plaintext: &[u8], associated_data: &[u8]) -> Result<String, CryptoError> {
        if associated_data.is_empty() { return Err(CryptoError::InvalidAad); }
        let key = self.provider.key()?;
        let cipher = Aes256Gcm::new_from_slice(key.as_bytes()).map_err(|_| CryptoError::InvalidKey)?;
        let mut nonce_bytes = [0u8; NONCE_SIZE];
        OsRng.fill_bytes(&mut nonce_bytes);
        let encrypted = cipher.encrypt(Nonce::from_slice(&nonce_bytes), Payload { msg: plaintext, aad: associated_data })
            .map_err(|_| CryptoError::EncryptionFailed)?;
        if encrypted.len() < TAG_SIZE { return Err(CryptoError::EncryptionFailed); }
        let split = encrypted.len() - TAG_SIZE;
        let (ciphertext, tag) = encrypted.split_at(split);
        let mut payload = Vec::with_capacity(NONCE_SIZE + TAG_SIZE + ciphertext.len());
        payload.extend_from_slice(&nonce_bytes);
        payload.extend_from_slice(tag);
        payload.extend_from_slice(ciphertext);
        Ok(format!("{PREFIX}{}", URL_SAFE_NO_PAD.encode(payload)))
    }

    pub fn decrypt(&self, envelope: &str, associated_data: &[u8]) -> Result<Vec<u8>, CryptoError> {
        if associated_data.is_empty() { return Err(CryptoError::InvalidAad); }
        let encoded = envelope.strip_prefix(PREFIX).ok_or(CryptoError::InvalidEnvelope)?;
        let payload = URL_SAFE_NO_PAD.decode(encoded).map_err(|_| CryptoError::InvalidEnvelope)?;
        if payload.len() < NONCE_SIZE + TAG_SIZE { return Err(CryptoError::InvalidEnvelope); }
        let nonce = &payload[..NONCE_SIZE];
        let tag = &payload[NONCE_SIZE..NONCE_SIZE + TAG_SIZE];
        let ciphertext = &payload[NONCE_SIZE + TAG_SIZE..];
        let mut combined = Vec::with_capacity(ciphertext.len() + TAG_SIZE);
        combined.extend_from_slice(ciphertext);
        combined.extend_from_slice(tag);
        let key = self.provider.key()?;
        let cipher = Aes256Gcm::new_from_slice(key.as_bytes()).map_err(|_| CryptoError::InvalidKey)?;
        let result = cipher.decrypt(Nonce::from_slice(nonce), Payload { msg: &combined, aad: associated_data })
            .map_err(|_| CryptoError::AuthenticationFailed);
        combined.zeroize();
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct StaticKey;
    impl KeyProvider for StaticKey { fn key(&self) -> Result<KeyMaterial, CryptoError> { Ok(KeyMaterial::new([7u8; 32])) } }

    #[test]
    fn round_trip() {
        let service = AesGcmService::new(StaticKey);
        let envelope = service.encrypt(b"corporate secret", b"tenant:acme").expect("encryption must succeed");
        assert_eq!(service.decrypt(&envelope, b"tenant:acme").expect("decryption must succeed"), b"corporate secret");
    }

    #[test]
    fn wrong_aad_is_rejected() {
        let service = AesGcmService::new(StaticKey);
        let envelope = service.encrypt(b"secret", b"tenant:acme").expect("encryption must succeed");
        assert!(matches!(service.decrypt(&envelope, b"tenant:other"), Err(CryptoError::AuthenticationFailed)));
    }

    #[test]
    fn tampering_is_rejected() {
        let service = AesGcmService::new(StaticKey);
        let envelope = service.encrypt(b"secret", b"tenant:acme").expect("encryption must succeed");
        let mut bytes = envelope.into_bytes();
        let last = bytes.len() - 1;
        bytes[last] = if bytes[last] == b'A' { b'B' } else { b'A' };
        let tampered = String::from_utf8(bytes).expect("envelope is ASCII");
        assert!(matches!(service.decrypt(&tampered, b"tenant:acme"), Err(CryptoError::AuthenticationFailed)));
    }
}
