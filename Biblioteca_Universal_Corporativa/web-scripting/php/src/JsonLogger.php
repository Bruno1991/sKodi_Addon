<?php
declare(strict_types=1);

namespace Mbuc\Security;

use Psr\Log\AbstractLogger;
use Stringable;

final class JsonLogger extends AbstractLogger
{
    private const REDACTED = ['key', 'password', 'secret', 'token', 'cookie', 'authorization', 'plaintext', 'envelope'];
    private $stream;

    public function __construct()
    {
        $stream = fopen('php://stdout', 'wb');
        if ($stream === false) throw new \RuntimeException('Unable to open standard output.');
        $this->stream = $stream;
    }

    public function log($level, string|Stringable $message, array $context = []): void
    {
        $event = [
            'timestamp' => (new \DateTimeImmutable('now', new \DateTimeZone('UTC')))->format('Y-m-d\\TH:i:s.u\\Z'),
            'level' => strtoupper((string) $level),
            'event' => (string) ($context['event'] ?? 'application.log'),
            'message' => (string) $message,
        ];
        foreach ($context as $name => $value) {
            $event[$name] = in_array(strtolower((string) $name), self::REDACTED, true) ? '[REDACTED]' : $value;
        }
        $json = json_encode($event, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        if (fwrite($this->stream, $json . "\n") === false) throw new \RuntimeException('Unable to write structured log.');
    }
}
