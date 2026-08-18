# Arquitetura universal

## Camadas e bounded contexts

Cada serviço ou componente organiza dependências nesta direção:

`interfaces/adapters de entrada → application/use cases → domain ← ports → adapters de infraestrutura`

O domínio não importa frameworks, banco, HTTP, UI ou telemetria. Application coordena transação, autorização e idempotência. Adapters convertem protocolos em tipos do domínio. A composição e configuração ficam na borda executável.

SOLID, DRY, KISS e YAGNI são critérios de decisão, não metas mecânicas. Não crie uma interface para cada classe; crie um port quando houver uma fronteira real, política variável ou necessidade de isolamento.

## Fronteiras de linguagem

- HTTP/JSON sobre TLS é o default entre processos. Schemas em `contracts/` são versionados e validados na borda.
- Eventos precisam de `event_id`, `event_type`, `occurred_at`, `correlation_id`, `schema_version` e payload versionado. Consumidores devem ser idempotentes.
- Banco de dados nunca é API entre bounded contexts. Cada serviço é dono de suas tabelas.
- FFI é permitido somente para chamadas no mesmo processo. Exportar uma C ABI pequena, tipos de largura fixa, ownership documentado e códigos de erro estáveis.
- Dados binários usam comprimento explícito; strings atravessam fronteiras como UTF-8 validado.

## Fluxo de dados da API de referência

1. Middleware recebe ou cria `X-Correlation-ID` e limita o tamanho do request.
2. Pydantic valida Base64, AAD e forma do comando.
3. Application solicita a chave ao provider e chama o serviço AES-GCM.
4. O serviço retorna apenas o envelope; a chave e o plaintext não entram em logs.
5. Erros são convertidos no envelope corporativo, com mensagem pública e correlação.
6. Métricas e logs registram operação, resultado e duração sem cardinalidade descontrolada.

## Infraestrutura

O pacote não exige mensageria ou banco para a API de referência. Em produção, use secret manager, ingress TLS 1.3 quando suportado, observabilidade central, rate limiting no gateway e orquestrador com probes. Os schemas SQL são módulos independentes para serviços que precisem de usuários, sessões e auditoria.
