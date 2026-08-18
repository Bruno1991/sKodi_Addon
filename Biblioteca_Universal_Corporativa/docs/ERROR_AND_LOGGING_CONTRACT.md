# Contrato de erros e logs

## Taxonomia

- `validation_error`: entrada inválida; não repetir.
- `authentication_error`: identidade ausente ou inválida.
- `authorization_error`: identidade válida sem permissão.
- `not_found`: recurso não existe ou não pode ser revelado.
- `conflict`: versão, idempotência ou estado incompatível.
- `rate_limited`: capacidade temporariamente negada; pode incluir retry.
- `dependency_unavailable`: dependência falhou temporariamente.
- `internal_error`: defeito ou estado inesperado; mensagem pública genérica.

Try/catch existe apenas onde há recuperação, adição de contexto ou tradução de fronteira. Rust usa `Result`; Kotlin pode usar sealed results na application; Python e Java preservam `cause`; JavaScript rejeita com `Error` tipado. Cancelamento não é falha e nunca deve ser convertido em retry automático.

## Envelope de erro

O schema canônico está em `contracts/error-envelope.schema.json`. `code` é estável para máquinas. `message` é segura para o cliente. `correlation_id` liga a resposta ao diagnóstico. `details` só contém campos permitidos e nunca stack trace.

## Logs JSON

O schema está em `contracts/log-event.schema.json`. Campos mínimos: timestamp UTC, level, event, message, service, correlation_id e outcome. Campos recomendados: duration_ms, dependency, attempt e error_code.

Não registrar chaves, plaintext, senhas, tokens, cookies, session hashes ou envelopes criptográficos. Uma falha é registrada uma vez na camada que possui contexto operacional; camadas inferiores retornam erro com causa.
