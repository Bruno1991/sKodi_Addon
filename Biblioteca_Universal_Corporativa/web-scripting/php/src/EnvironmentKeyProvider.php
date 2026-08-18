<?php
declare(strict_types=1);

namespace Mbuc\Security;

final class EnvironmentKeyProvider implements KeyProvider
{
    public function keyBytes(): string
    {
        $encoded = getenv('MBUC_AES_KEY_BASE64');
        if ($encoded === false || trim($encoded) === '') {
            throw new CryptoException('missing_key', 'MBUC_AES_KEY_BASE64 is required.');
        }
        $key = base64_decode($encoded, true);
        if ($key === false || strlen($key) !== 32) {
            throw new CryptoException('invalid_key', 'MBUC_AES_KEY_BASE64 must encode exactly 32 bytes.');
        }
        return $key;
    }
}
