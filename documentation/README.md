# Documentação Python/Kodi do sRepo

Este diretório é a fonte canônica da documentação técnica do ecossistema sRepo/sTv. A raiz do monorepo mantém somente o ponto de entrada (`README.md`), o contrato operacional do agente (`AGENTS.md`) e arquivos essenciais do repositório.

## Arquitetura

- [`PROJECT_CONSTITUTION.md`](architecture/PROJECT_CONSTITUTION.md): princípios e fronteiras obrigatórias.
- [`ROADMAP_ARCHITECTURE.md`](architecture/ROADMAP_ARCHITECTURE.md): arquitetura funcional derivada do roadmap.
- [`REPOSITORY_BLUEPRINT.md`](architecture/REPOSITORY_BLUEPRINT.md): estrutura e grafo de dependências.
- [`ROADMAP_TRACEABILITY_MATRIX.md`](architecture/ROADMAP_TRACEABILITY_MATRIX.md): capacidades, componentes e evidências.

## Governança

- [`SECURITY_AND_ENV_POLICY.md`](governance/SECURITY_AND_ENV_POLICY.md): política de segredos, ambiente, logs e build.
- [`SKILLS_INDEX.md`](governance/SKILLS_INDEX.md): catálogo operacional de skills Python/Kodi.

## Referência

- [`COMPATIBILITY_MATRIX.md`](reference/COMPATIBILITY_MATRIX.md): plataformas e versões suportadas.
- [`OFFICIAL_REFERENCE_MAP.md`](reference/OFFICIAL_REFERENCE_MAP.md): fontes técnicas primárias.

## Release e estado

- [`PACKAGE_INVENTORY.md`](release/PACKAGE_INVENTORY.md): inventário funcional e operacional.
- [`PACKAGE_RELEASE_NOTES.md`](release/PACKAGE_RELEASE_NOTES.md): escopo da versão corrente.
- [`STATE.md`](release/STATE.md): estado validado do projeto.

## Artefatos gerados

O diretório [`generated/`](generated/) contém o manifesto estrutural e a árvore produzidos por `tools/generate_structure_manifest.py` e `tools/print_tree.py`.

## Atualização

Execute os geradores a partir da raiz do monorepo:

```powershell
python tools/generate_structure_manifest.py
python tools/print_tree.py
```

Os arquivos em `generated/` não devem ser editados manualmente.
