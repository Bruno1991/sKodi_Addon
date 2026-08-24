# Inventário do pacote V2 (IPTV Focus)

## Resumo

- Add-ons ativos: **5**
- Artes fixas compartilhadas: **9** (5 comuns + 4 sTv)
- Testes unitários: **67**
- ZIPs Kodi gerados em `docs/zips/`: **5**
- Manifesto estrutural de referência: `../generated/STRUCTURE_MANIFEST.json`

## Add-ons Ativos

- `plugin.video.stv` (**sTv**): Add-on principal de IPTV/Xtream (TV ao Vivo, VOD, Séries, Favoritos, TMDB).
- `repository.srepo` (**sRepo**): Repositório oficial para Kodi (distribuição via GitHub Pages).
- `resource.images.saile` (**sArtwork**): Recurso com 9 ícones de interface compartilhados.
- `script.module.saile.core` (**sCore**): Infraestrutura Python comum estável.
- `script.module.saile.epg` (**sEPG**): Provider XMLTV, matching e cache SQLite UTC independente.

## Decisões Incorporadas

- `resource.images.saile` (**sArtwork**) centraliza exatamente 9 artes fixas em PNG.
- `script.module.saile.core` (**sCore**) provê apenas caminhos portáveis, artwork, notificações, erros e capabilities.
- `script.module.saile.epg` (**sEPG**) concentra toda a regra e persistência de EPG fora do sTv e do core.
- Contrato imutável de navegação do sTv:
  - Home: `TV ao Vivo` → `VOD` → `Séries` → `Sincronizar Dados`.
  - Seções: `Buscar` → `Favoritos` → conteúdo dinâmico.
- Sincronização LAN é manual sob demanda e não compartilha SQLite bruto.

## Validações Executadas

```text
5 add-ons válidos
9 artes compartilhadas válidas
67 testes unitários aprovados
0 segredos conhecidos encontrados
5 ZIPs Kodi gerados
```

## Ferramentas Operacionais

- `tools/bootstrap_artwork.py`: Copia e sincroniza ícones e fanarts do manifest.
- `tools/select_artwork.py`: Seleção e geração dinâmica de estilos de artwork.
- `tools/validate_addons.py`: Validação estática de `addon.xml`, `settings.xml` e artwork.
- `tools/secret_scan.py`: Auditoria de credenciais e tokens em arquivos versionáveis.
- `tools/build_repo.py`: Empacotamento de ZIPs, geração de `addons.xml`, MD5, SHA256 e HTML.
- `tools/generate_structure_manifest.py`: geração de `docs/generated/STRUCTURE_MANIFEST.json`.
- `tools/print_tree.py`: geração da árvore do projeto em `docs/generated/TREE_FINAL.txt`.
