# Estado de validação da entrega

## Executado no ambiente de geração

- Validação estrutural de arquivos obrigatórios e cobertura dos ecossistemas.
- Parsing de todos os documentos JSON e XML.
- Compilação sintática de todos os arquivos Python.
- Smoke test real de AES-256-GCM e circuit breaker em Python.
- Compilação com warnings como erro e smoke test real do módulo Java.
- Testes reais de AES-256-GCM e compilação TypeScript em modo strict.
- Verificação sintática dos módulos JavaScript Web Vanilla.
- Extração do ZIP e conferência de todos os checksums no fechamento.

## Delegado à CI por ausência de toolchain local

O ambiente de geração não possui SDK .NET 8, Rust/Cargo, CMake/compilador C++, Maven/Kotlin, PHP/Composer, PlatformIO ou Docker. Os respectivos arquivos de teste e jobs de CI foram incluídos, mas seus resultados só devem ser considerados aprovados depois que o workflow executar em runners com esses toolchains. Esta limitação não deve ser ocultada em um release real.
