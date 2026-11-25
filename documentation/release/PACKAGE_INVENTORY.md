# Inventário do pacote V2 (Ecossistema sKodi)

## Resumo

- Add-ons ativos: **6**
- Artes fixas compartilhadas: **20** (16 comuns + 4 sTv)
- ZIPs Kodi gerados em `docs/`: **6**
- Manifesto estrutural de referência: `../generated/STRUCTURE_MANIFEST.json`

## Add-ons Ativos

- `plugin.video.stv` (**sTv**): Add-on principal de IPTV/Xtream (TV ao Vivo com categorias nativas, VOD, Séries, Favoritos, TMDB, auto-sync de catálogo e EPG e sincronização LAN P2P).
- `plugin.audio.sradio` (**sRadio**): Add-on de rádios online ao vivo (TuneIn global/Brasil, busca em tempo real, favoritos e catálogo offline).
- `repository.srepo` (**sRepo**): Repositório oficial para Kodi (distribuição via GitHub Pages).
- `resource.images.saile` (**sArtwork**): Recurso com 20 ícones de interface compartilhados.
- `script.module.saile.core` (**sCore**): Infraestrutura Python comum estável.
- `script.module.saile.epg` (**sEPG**): Provider Claro TV+ oficial dinâmico em tempo real, 100% de correspondência de canais e afiliados regionais, resolução em lote sem N+1 e cache SQLite UTC independente.

## Decisões Incorporadas

- `resource.images.saile` (**sArtwork**) centraliza 20 artes fixas em PNG.
- `script.module.saile.core` (**sCore**) provê apenas caminhos portáveis, artwork, notificações, erros e capabilities.
- `script.module.saile.epg` (**sEPG**) concentra toda a regra e persistência de EPG fora do sTv e do core, com integração direta na API Claro TV+ e tabela universal de aliases.
- Contrato imutável de navegação do sTv:
  - Home: `TV ao Vivo` → `VOD` → `Séries` → `Sincronizar Dados`.
  - Seções: `Buscar` → `Favoritos` → conteúdo dinâmico.
- Sincronização LAN opera tanto via UDP Broadcast peer-to-peer em segundo plano quanto sob demanda interativa no menu `Sincronizar Dados`.
- Auto-sincronização do catálogo e EPG em background daemon thread com TTL configurável.

## Validações Executadas

```text
6 add-ons válidos
20 artes compartilhadas válidas
Suíte completa de testes unitários aprovada (pytest + unittest)
0 segredos conhecidos encontrados
6 ZIPs Kodi gerados
```

## Ferramentas Operacionais

- `tools/bootstrap_artwork.py`: Copia e sincroniza ícones e fanarts do manifest.
- `tools/select_artwork.py`: Seleção e geração dinâmica de estilos de artwork.
- `tools/validate_addons.py`: Validação estática de `addon.xml`, `settings.xml` e artwork.
- `tools/secret_scan.py`: Auditoria de credenciais e tokens em arquivos versionáveis.
- `tools/build_repo.py`: Empacotamento de ZIPs, geração de `addons.xml`, MD5, SHA256 e HTML.
- `tools/generate_structure_manifest.py`: geração de `docs/generated/STRUCTURE_MANIFEST.json`.
- `tools/print_tree.py`: geração da árvore do projeto em `docs/generated/TREE_FINAL.txt`.
