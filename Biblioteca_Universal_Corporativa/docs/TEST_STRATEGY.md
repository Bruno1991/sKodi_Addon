# Estratégia de testes

## Pirâmide orientada a risco

- Unidade: round-trip, chave inválida, AAD incorreto, envelope truncado, tag adulterada e transições do circuit breaker.
- Integração: biblioteca criptográfica real, cliente HTTP contra servidor controlado, schemas em cada engine real e API de referência via ASGI.
- Contrato: validar JSON Schemas e compatibilidade do envelope entre duas implementações.
- Sistema/HIL: Arduino em placa suportada, perda/retorno de Wi-Fi e limites de payload; Assembly chamado por harness C com ASan ao redor.

Criptografia não usa snapshots do ciphertext porque nonce é aleatório. Verifique invariantes e adulteração. Testes nunca reutilizam chave real; fixtures geram chaves efêmeras.

## Gates

1. Formatação e análise estática.
2. Testes unitários.
3. Build de release.
4. Testes de integração por superfície alterada.
5. Scan de dependências e imagem.
6. Manifesto/checksum e smoke test do artefato.
