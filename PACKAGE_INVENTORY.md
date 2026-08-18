# Inventário do pacote V2 (IPTV Focus)

## Resumo

- Add-ons ativos: **5**
- Artes fixas compartilhadas: **9** (5 comuns + 4 sTv)
- Testes unitários: **42**
- ZIPs Kodi gerados em `docs/zips/`: **5**
- Manifesto estrutural de referência: `STRUCTURE_MANIFEST.json`

## Add-ons Ativos

- `plugin.video.stv`: Add-on principal de IPTV/Xtream (TV ao Vivo, VOD, Séries, Favoritos, TMDB).
- `repository.srepo`: Repositório oficial para Kodi (distribuição via GitHub Pages).
- `resource.images.saile`: Recurso com 9 ícones de interface compartilhados.
- `script.module.saile.core`: Infraestrutura Python comum estável.
- `script.module.saile.epg`: Provider XMLTV, matching e cache SQLite UTC independente.

## Decisões Incorporadas

- `resource.images.saile` centraliza exatamente 9 artes fixas em PNG.
- `script.module.saile.core` provê apenas caminhos portáveis, artwork, notificações, erros e capabilities.
- `script.module.saile.epg` concentra toda a regra e persistência de EPG fora do sTv e do core.
- Contrato imutável de navegação do sTv:
  - Home: `TV ao Vivo` → `VOD` → `Séries` → `Sincronizar Dados`.
  - Seções: `Buscar` → `Favoritos` → conteúdo dinâmico.
- Sincronização LAN é manual sob demanda e não compartilha SQLite bruto.

## Validações Executadas

```text
5 add-ons válidos
9 artes compartilhadas válidas
42 testes unitários aprovados
0 segredos conhecidos encontrados
5 ZIPs Kodi gerados
```

## Ferramentas Operacionais

- `tools/bootstrap_artwork.py`: Copia e sincroniza ícones e fanarts do manifest.
- `tools/select_artwork.py`: Seleção e geração dinâmica de estilos de artwork.
- `tools/validate_addons.py`: Validação estática de `addon.xml`, `settings.xml` e artwork.
- `tools/secret_scan.py`: Auditoria de credenciais e tokens em arquivos versionáveis.
- `tools/build_repo.py`: Empacotamento de ZIPs, geração de `addons.xml`, MD5, SHA256 e HTML.
- `tools/generate_structure_manifest.py`: Geração do `STRUCTURE_MANIFEST.json`.
- `tools/print_tree.py`: Geração da árvore do projeto (`TREE_FINAL.txt`).
