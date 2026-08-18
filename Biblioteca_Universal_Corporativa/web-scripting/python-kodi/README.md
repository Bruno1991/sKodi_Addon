# Empacotamento Kodi

Kodi não fornece AES-GCM seguro na biblioteca padrão do Python. O build gera um ZIP por plataforma e inclui um wheel binário de `cryptography`; não há fallback criptográfico artesanal. Execute `build_addon.py` para cada plataforma suportada e teste dentro da versão mínima do Kodi. A chave deve vir de integração segura do dispositivo; variável de ambiente serve apenas a instalações corporativas controladas.

## Documentação do sRepo / sTv

A documentação Python/Kodi do monorepo está organizada em [`docs/`](docs/README.md):

- `architecture/`: constituição, blueprint, arquitetura e rastreabilidade;
- `governance/`: segurança, ambiente e índice operacional de skills;
- `reference/`: compatibilidade e referências técnicas oficiais;
- `release/`: inventário, notas de versão e estado atual;
- `generated/`: manifesto estrutural e árvore gerados pelas ferramentas do monorepo.
