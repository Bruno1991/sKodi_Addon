<?php
declare(strict_types=1);

namespace Mbuc\Security;

use Psr\Log\LoggerInterface;

final class AesGcmService
{
    private const PREFIX = 'v1.';
    private const NONCE_SIZE = 12;
    private const TAG_SIZE = 16;

    public function __construct(private readonly KeyProvider $keyProvider, private readonly LoggerInterface $logger) {}

    public function encrypt(string $plaintext, string $associatedData): string
    {
        if ($associatedData === '') throw new CryptoException('invalid_aad', 'Associated data is required.');
        $key = $this->keyProvider->keyBytes();
        if (strlen($key) !== 32) throw new CryptoException('invalid_key', 'AES-256-GCM requires exactly 32 key bytes.');
        $nonce = random_bytes(self::NONCE_SIZE);
        $tag = '';
        $ciphertext = openssl_encrypt($plaintext, 'aes-256-gcm', $key, OPENSSL_RAW_DATA, $nonce, $tag, $associatedData, self::TAG_SIZE);
        if ($ciphertext === false || strlen($tag) !== self::TAG_SIZE) throw new CryptoException('encryption_failed', 'Encryption failed.');
        $this->logger->info('AES-GCM encryption completed.', ['event' => 'crypto.encrypt', 'outcome' => 'success', 'plaintext_length' => strlen($plaintext)]);
        return self::PREFIX . self::base64UrlEncode($nonce . $tag . $ciphertext);
    }

    public function decrypt(string $envelope, string $associatedData): string
    {
        if ($associatedData === '') throw new CryptoException('invalid_aad', 'Associated data is required.');
        if (!str_starts_with($envelope, self::PREFIX)) throw new CryptoException('invalid_envelope', 'Unsupported crypto envelope version.');
        $payload = self::base64UrlDecode(substr($envelope, strlen(self::PREFIX)));
        if (strlen($payload) < self::NONCE_SIZE + self::TAG_SIZE) throw new CryptoException('invalid_envelope', 'Envelope payload is truncated.');
        $nonce = substr($payload, 0, self::NONCE_SIZE);
        $tag = substr($payload, self::NONCE_SIZE, self::TAG_SIZE);
        $ciphertext = substr($payload, self::NONCE_SIZE + self::TAG_SIZE);
        $key = $this->keyProvider->keyBytes();
        if (strlen($key) !== 32) throw new CryptoException('invalid_key', 'AES-256-GCM requires exactly 32 key bytes.');
        $plaintext = openssl_decrypt($ciphertext, 'aes-256-gcm', $key, OPENSSL_RAW_DATA, $nonce, $tag, $associatedData);
        if ($plaintext === false) {
            $this->logger->warning('AES-GCM authentication failed.', ['event' => 'crypto.decrypt', 'outcome' => 'failure', 'error_code' => 'authentication_failed']);
            throw new CryptoException('authentication_failed', 'Envelope authentication failed.');
        }
        return $plaintext;
    }

    private static function base64UrlEncode(string $value): string
    {
        return rtrim(strtr(base64_encode($value), '+/', '-_'), '=');
    }

    private static function base64UrlDecode(string $value): string
    {
        if (!preg_match('/^[A-Za-z0-9_-]+$/D', $value)) throw new CryptoException('invalid_envelope', 'Envelope payload is not valid Base64URL.');
        $padding = (4 - strlen($value) % 4) % 4;
        $decoded = base64_decode(strtr($value . str_repeat('=', $padding), '-_', '+/'), true);
        if ($decoded === false) throw new CryptoException('invalid_envelope', 'Envelope payload is not valid Base64URL.');
        return $decoded;
    }
}
