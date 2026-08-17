# Regras para agentes

1. Preserve os contratos em `contracts/` e versione qualquer quebra.
2. Não implemente criptografia manualmente nem reduza nonce, tag ou tamanho de chave.
3. Nunca registre plaintext, chave, token, sessão ou envelope completo.
4. Respeite a estrutura domain/application/adapters nos serviços; bibliotecas pequenas podem usar ports explícitos sem camadas vazias.
5. Execute o teste focal e o build do ecossistema alterado; declare toolchain ausente.
6. Use retries somente para operações seguras/idempotentes e respeite `Retry-After`.
7. Mantenha SQL específico por engine em seu diretório; o contrato ANSI é o mínimo comum.
8. Não publique, assine ou opere produção sem autorização explícita.
9. Atualize `docs/PROJECT_TREE.md` e o manifesto antes de empacotar.
