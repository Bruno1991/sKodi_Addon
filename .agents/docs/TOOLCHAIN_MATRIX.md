# Matriz de toolchains

| Módulo | Baseline | Build/test |
|---|---|---|
| C++ | C++20, CMake 3.24, OpenSSL 3 | CMake/CTest |
| Arduino ESP32 | PlatformIO, framework Arduino, mbedTLS do core | pio test/run |
| .NET | .NET 8 LTS | dotnet test |
| Python/Kodi | Python 3.11+; Kodi conforme addon.xml | pytest/build script |
| Java | JDK 21 LTS, Maven 3.9 | mvn verify |
| Kotlin | JDK 21, Kotlin/JVM via Maven | mvn verify |
| TypeScript | Node 22, npm lockfile | npm ci/test/build |
| PHP | PHP 8.3, Composer 2 | composer test/analyse |
| Rust | stable, edition 2021 | cargo test/clippy |
| Web Vanilla | navegadores evergreen definidos pelo consumidor | node --test |
| SQL | PostgreSQL 16+, MySQL 8.0+, SQLite 3.40+ | engine real |
| Assembly | GNU assembler x86_64 SysV | CMake/CTest |

Versões são baselines reprodutíveis do pacote, não alegação de “mais recente”. O consumidor pode elevar versões após testar a matriz.
