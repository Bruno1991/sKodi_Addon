<?php
declare(strict_types=1);

namespace Mbuc\Security;

interface KeyProvider
{
    public function keyBytes(): string;
}
