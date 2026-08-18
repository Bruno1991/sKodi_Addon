#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
failures=0
run() { printf '{"level":"INFO","event":"build.command","component":"%s"}\n' "$1"; shift; "$@" || failures=$((failures + 1)); }
command -v python3 >/dev/null && run verify python3 "$root/infrastructure/scripts/verify-package.py" "$root"
command -v cmake >/dev/null && run cpp-config cmake -S "$root/native/cpp" -B "$root/.build/cpp" -DBUILD_TESTING=ON
test -f "$root/.build/cpp/CMakeCache.txt" && run cpp-build cmake --build "$root/.build/cpp" --config Release && run cpp-test ctest --test-dir "$root/.build/cpp" --output-on-failure -C Release
command -v dotnet >/dev/null && run dotnet dotnet test "$root/managed/dotnet/Corporate.Security.Tests/Corporate.Security.Tests.csproj" -c Release
command -v python3 >/dev/null && run python python3 -m pytest "$root/web-scripting/python/tests"
command -v cargo >/dev/null && run rust cargo test --manifest-path "$root/systems/rust/Cargo.toml"
command -v pnpm >/dev/null && run typescript-install bash -c 'cd "$1" && pnpm install --frozen-lockfile' _ "$root/web-scripting/typescript"
command -v pnpm >/dev/null && run typescript-test bash -c 'cd "$1" && pnpm test' _ "$root/web-scripting/typescript"
command -v pnpm >/dev/null && run typescript-build bash -c 'cd "$1" && pnpm run build' _ "$root/web-scripting/typescript"
command -v mvn >/dev/null && run java mvn -q -f "$root/managed/java/pom.xml" verify
command -v mvn >/dev/null && run kotlin mvn -q -f "$root/managed/kotlin/pom.xml" verify
command -v composer >/dev/null && run php-install bash -c 'cd "$1" && composer install --no-interaction --prefer-dist' _ "$root/web-scripting/php"
command -v composer >/dev/null && run php-test bash -c 'cd "$1" && composer test' _ "$root/web-scripting/php"
command -v composer >/dev/null && run php-analyse bash -c 'cd "$1" && composer analyse' _ "$root/web-scripting/php"
command -v pio >/dev/null && run arduino pio run -d "$root/native/arduino"
(( failures == 0 )) || { printf '{"level":"ERROR","event":"build.failed","failures":%d}\n' "$failures" >&2; exit 1; }
printf '{"level":"INFO","event":"build.completed","outcome":"success"}\n'
