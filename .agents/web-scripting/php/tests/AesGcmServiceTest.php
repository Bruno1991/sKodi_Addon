<?php
declare(strict_types=1);

namespace Mbuc\Security\Tests;

use Mbuc\Security\AesGcmService;
use Mbuc\Security\CryptoException;
use Mbuc\Security\KeyProvider;
use PHPUnit\Framework\TestCase;
use Psr\Log\NullLogger;

final class AesGcmServiceTest extends TestCase
{
    private function service(): AesGcmService
    {
        return new AesGcmService(new class implements KeyProvider {
            public function keyBytes(): string { return str_repeat("\x07", 32); }
        }, new NullLogger());
    }

    public function testRoundTrip(): void
    {
        $service = $this->service();
        $envelope = $service->encrypt('corporate secret', 'tenant:acme');
        self::assertSame('corporate secret', $service->decrypt($envelope, 'tenant:acme'));
    }

    public function testWrongAadIsRejected(): void
    {
        $service = $this->service();
        $envelope = $service->encrypt('secret', 'tenant:acme');
        $this->expectException(CryptoException::class);
        $this->expectExceptionMessage('authentication');
        $service->decrypt($envelope, 'tenant:other');
    }
}
