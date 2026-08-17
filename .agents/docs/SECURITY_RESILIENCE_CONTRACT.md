# Contrato de segurança e resiliência

## Criptografia

- Algoritmo: AES-256-GCM; chave de 32 bytes; nonce aleatório de 12 bytes; tag de 16 bytes.
- Envelope: ASCII `v1.` seguido de Base64 URL-safe sem padding de `nonce || tag || ciphertext`.
- AAD: obrigatório, estável, específico ao contexto e fornecido novamente na decriptação.
- Limite: cada biblioteca rejeita chave, envelope, nonce ou tag fora do contrato.
- Gestão: chave nasce em CSPRNG, vive em secret manager/HSM quando disponível, possui `kid`, rotação e revogação. O envelope v1 não inclui `kid`; o serviço deve associá-lo no registro externo ou usar um provider de chave versionado antes de suportar múltiplas chaves.

AES-GCM não é hashing de senha. Senhas devem usar Argon2id por biblioteca dedicada, com parâmetros calibrados no hardware. O pacote escolhe AES-GCM porque o requisito é proteção reversível de dados.

## OWASP e fronteiras

- SQL sempre parametrizado; nomes dinâmicos vêm de allow-list.
- HTML usa text nodes/escaping por contexto; CSP e cookies seguros pertencem ao serviço web.
- SSRF é mitigado por allow-list de esquemas/hosts, resolução controlada e bloqueio de redes internas quando a URL vier de usuário.
- CSRF é exigido em autenticação por cookie; APIs bearer não devem misturar cookies implícitos.
- Autenticação e autorização são controles distintos; negar por padrão e testar objeto/tenant.

## Retry, circuit breaker e rate limiting

Retry aceita somente falhas transitórias: timeout, 408, 429 e 5xx selecionados. Operações não idempotentes exigem idempotency key. O atraso é exponencial com jitter, limitado por tentativas e deadline. `Retry-After` prevalece quando válido.

O circuit breaker abre após falhas consecutivas, rejeita chamadas durante cooldown e permite uma tentativa half-open. Sucesso fecha e zera contadores. O estado é por destino/instância; não use uma chave global para serviços diferentes.

Rate limiting primário fica no gateway. O cliente também limita concorrência e tamanho. Connection pools devem ter tamanho, timeout, validação e métricas explícitos.

## TLS

Exigir validação de certificado e hostname. Preferir TLS 1.3 no servidor e permitir TLS 1.2 somente quando a matriz de clientes exigir. Não desabilitar verificação para “corrigir” desenvolvimento.
