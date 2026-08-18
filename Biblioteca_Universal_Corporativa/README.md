# Mega_Biblioteca_Universal_Corporativa

> **Escopo:** monorepo de componentes corporativos reutilizáveis para segurança, resiliência, contratos, dados, observabilidade e automação multilíngue.  
> **Stack principal:** C/C++, Arduino C/C++, C#/.NET, Python/Kodi, Java, Kotlin, HTML/CSS/JavaScript, TypeScript, PHP, Rust, Bash, PowerShell, POSIX Shell, SQL e Assembly x86_64.

## 1. Árvore de diretórios

A árvore exata, gerada a partir dos arquivos entregues, está em `docs/PROJECT_TREE.md`. As raízes são:

- `native/`: C++, Arduino e Assembly;
- `managed/`: .NET, Java e Kotlin;
- `web-scripting/`: TypeScript, Web Vanilla, Python/Kodi e PHP;
- `systems/`: Rust;
- `infrastructure/`: SQL, containers e automação de CLI;
- `services/`: API de referência pronta para container;
- `contracts/`: envelopes interoperáveis de erro, log e criptografia;
- `docs/`: arquitetura, segurança, operação e matriz de toolchains.

## 2. Documentação técnica e arquitetura

Comece por `docs/ARCHITECTURE.md`, `docs/SECURITY_RESILIENCE_CONTRACT.md` e `docs/ERROR_AND_LOGGING_CONTRACT.md`. Módulos não compartilham banco ou memória entre linguagens. A integração ocorre por contratos versionados, HTTP/TLS ou uma ABI C estreita quando o processo exige interoperabilidade nativa.

## 3. Implementações principais

Os módulos de criptografia usam AES-256-GCM de bibliotecas revisadas de cada plataforma. Nenhuma primitiva criptográfica foi reimplementada. O envelope interoperável é `v1.<base64url(nonce || tag || ciphertext)>`; o AAD é obrigatório e não é armazenado no envelope.

Clientes resilientes estão em TypeScript e Python. O driver Arduino cobre reconexão Wi-Fi e HTTP com limites. Schemas SQL separados cobrem ANSI, MySQL, PostgreSQL e SQLite. A rotina Assembly x86_64 implementa cópia com validação de capacidade e sem frame de pilha.

## 4. Estratégia de testes

Há testes executáveis de criptografia e adulteração para xUnit, PyTest e Cargo, além de testes nativos e TypeScript. `docs/TEST_STRATEGY.md` define a matriz completa.

## 5. DevOps e containerização

Execute um dos orquestradores em `infrastructure/scripts/`: Bash, PowerShell ou POSIX Shell. O `Dockerfile` raiz é multi-stage, roda como usuário não privilegiado e empacota a API Python de referência com endpoints `/health` e `/ready`. A CI está em `.github/workflows/ci.yml`.

## Segurança operacional

Forneça a chave por `MBUC_AES_KEY_BASE64` com exatamente 32 bytes após Base64. Nunca grave a chave em arquivo versionado. Gere uma chave para desenvolvimento com uma ferramenta criptograficamente segura e use um secret manager no ambiente real.

## Verificação

`infrastructure/scripts/verify-package.py` valida estrutura, JSON, XML, frontmatter de contratos, ausência de segredos de exemplo e checksums do pacote. Builds dependentes de toolchains externos só são confirmados quando o respectivo SDK estiver instalado.
