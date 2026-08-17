[CmdletBinding()]
param([string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$failures = 0
function Invoke-Step([string]$Component, [scriptblock]$Action) {
    Write-Output (@{level='INFO';event='build.command';component=$Component} | ConvertTo-Json -Compress)
    try { & $Action } catch { $script:failures++; Write-Error -ErrorAction Continue $_ }
}
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) { Invoke-Step verify { & $python.Source (Join-Path $Root 'infrastructure\scripts\verify-package.py') $Root } }
if (Get-Command cmake -ErrorAction SilentlyContinue) {
    Invoke-Step cpp-config { cmake -S (Join-Path $Root 'native\cpp') -B (Join-Path $Root '.build\cpp') -DBUILD_TESTING=ON }
    Invoke-Step cpp-build { cmake --build (Join-Path $Root '.build\cpp') --config Release }
    Invoke-Step cpp-test { ctest --test-dir (Join-Path $Root '.build\cpp') --output-on-failure -C Release }
}
if (Get-Command dotnet -ErrorAction SilentlyContinue) { Invoke-Step dotnet { dotnet test (Join-Path $Root 'managed\dotnet\Corporate.Security.Tests\Corporate.Security.Tests.csproj') -c Release } }
if ($python) { Invoke-Step python { & $python.Source -m pytest (Join-Path $Root 'web-scripting\python\tests') } }
if (Get-Command cargo -ErrorAction SilentlyContinue) { Invoke-Step rust { cargo test --manifest-path (Join-Path $Root 'systems\rust\Cargo.toml') } }
if (Get-Command pnpm -ErrorAction SilentlyContinue) { Invoke-Step typescript { Push-Location (Join-Path $Root 'web-scripting\typescript'); try { pnpm install --frozen-lockfile; pnpm test; pnpm run build } finally { Pop-Location } } }
if (Get-Command mvn -ErrorAction SilentlyContinue) { Invoke-Step java { mvn -q -f (Join-Path $Root 'managed\java\pom.xml') verify }; Invoke-Step kotlin { mvn -q -f (Join-Path $Root 'managed\kotlin\pom.xml') verify } }
if (Get-Command composer -ErrorAction SilentlyContinue) { Invoke-Step php { Push-Location (Join-Path $Root 'web-scripting\php'); try { composer install --no-interaction --prefer-dist; composer test; composer analyse } finally { Pop-Location } } }
if (Get-Command pio -ErrorAction SilentlyContinue) { Invoke-Step arduino { pio run -d (Join-Path $Root 'native\arduino') } }
if ($failures -gt 0) { throw "$failures build step(s) failed." }
Write-Output (@{level='INFO';event='build.completed';outcome='success'} | ConvertTo-Json -Compress)
