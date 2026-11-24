# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Monorepo **sRepo**: add-ons Kodi (Python 3, `xbmc.python` 3.0.0) distribuídos por um repositório Kodi estático no
GitHub Pages (`docs/`). Repositório remoto: `Bruno1991/sKodi_Addon`. Textos, commits e docs em pt-BR.

@AGENTS.md

O `AGENTS.md` acima é o contrato operacional (navegação imutável, artwork, fronteiras), mas está **defasado em três
pontos**. Na dúvida, vale o código atual:
- Não cita o `plugin.audio.sradio` (sRadio), que é um add-on ativo.
- Diz que a sincronização LAN e a de EPG são só manuais. O código tem auto-sync em thread daemon: catálogo e EPG
  por TTL (`stv/app/services.py`) e LAN por UDP na porta 54242 (`stv/app/lan_sync.py`). O README descreve o
  comportamento atual.
- A `../engineering-library` citada não existe nesta máquina.

## Comandos

```bash
python -m unittest discover -s tests -p "test_*.py"        # suíte completa (é o que a CI roda)
python -m unittest tests.test_saile_epg_normalizer         # um arquivo
python -m unittest tests.test_sradio.SRadioPlaybackTests.test_stream_mimetype_maps_each_tunein_format  # um teste
python tools/validate_addons.py && python tools/secret_scan.py && python -m compileall -q addons tools tests
python -m ruff check addons tools tests                    # config no pyproject.toml (ruff não vem instalado)
python tools/build_repo.py                                 # regenera docs/: zips, addons.xml, hashes, site
```

A CI (`.github/workflows/ci.yml`, Python 3.11) roda: bootstrap_artwork → validate_addons + secret_scan →
compileall → unittest → build_repo. O `Makefile` tem os mesmos alvos.

Cada arquivo de teste coloca o `lib` dos add-ons que usa no `sys.path`. Um teste novo que importa `saile_core` ou
`saile_epg` precisa adicionar o caminho, senão passa na suíte completa e falha quando roda sozinho.

## Arquitetura

### Add-ons (`addons/`)

| ID | Papel | Código |
|---|---|---|
| `plugin.video.stv` (sTv) | IPTV/Xtream, VOD, séries, TMDB | `resources/lib/stv/` |
| `plugin.audio.sradio` (sRadio) | Rádios TuneIn (catálogo em `resources/data/radios.json` + API) | `resources/lib/sradio/` |
| `script.module.saile.epg` (sEPG) | EPG (Claro TV+ / XMLTV), aliases de canais, SQLite próprio, `clean_media_title` | `lib/saile_epg/` |
| `script.module.saile.core` (sCore) | Artwork, notificações, erros, capabilities, caminhos | `lib/saile_core/` |
| `resource.images.saile` (sArtwork) | Ícones compartilhados (`common/`, `stv/`) | só imagens |
| `repository.srepo` | Instalador do repositório Kodi | só `addon.xml` |

Dependências entre add-ons ficam em `<requires><import>` do `addon.xml`. O sTv consome o sEPG, e o sEPG não pode
importar nada do sTv. sTv e sRadio são instaláveis de forma independente: código parecido entre os dois (`_icon`,
`_set_video_metadata`) é duplicação intencional, não candidato a consolidação.

### Fluxo de uma invocação de plugin

`default.py` coloca `resources/lib` no `sys.path` e chama `bootstrap.run(sys.argv)`. Cada clique no Kodi é um
processo Python novo; não há estado em memória entre telas. `Request.from_argv` (`routing.py`) lê
`plugin://…?action=…` e o `run` despacha por `request.action`. Toda tela nova precisa de uma rota ali.
`handle >= 0` é uma listagem ou item resolvível; `-1` vem de `RunPlugin` (menu de contexto), sem `setResolvedUrl`.

No sTv, `AppContainer` (`stv/app/services.py`) monta tudo a partir das settings do Kodi: `XtreamClient`
(`providers/xtream`), `TmdbClient` (`providers/tmdb`), catálogo SQLite `stv.db` no perfil do add-on
(`persistence/`) e o `EpgService` do sEPG no perfil do módulo sEPG. A UI fica em `stv/ui/`
(`directory.py`: `add_folder`/`finish_directory`; `player.py`: `play_video`).

### Contratos que os testes travam

- Ordem fixa dos menus: `stv/navigation_contract.py` (testado em `test_navigation_contract.py`).
- InfoWall (view mode 54) em todas as telas: além do `SetViewMode`, `ensure_infowall_in_kodi_db` reescreve o
  `ViewModes6.db` do próprio Kodi depois de cada listagem. É intencional; não "otimize" removendo.
- `docs/` é **gerado** por `tools/build_repo.py` (apagado e recriado) e é o que o GitHub Pages publica. Nunca edite
  à mão. Documentação de verdade fica em `documentation/` (a auditoria de legado está em
  `documentation/governance/LEGACY_AUDIT.md`).

### Imports do Kodi

Módulos `xbmc*` só existem dentro do Kodi. O código os importa **dentro das funções**, e os testes injetam dublês
com `patch.dict(sys.modules, {"xbmc": ...})`. Import de `xbmc*` no topo de um módulo quebra a suíte, com uma
exceção: `stv/ui/player.py`, que só é importado dentro de handlers.

## Release

Versões são independentes por add-on. Ao mudar o código de um add-on, suba a versão no mesmo PR:
1. Suba `version` na tag raiz do `addon.xml`. Não mexa nos `<import>`, a não ser que o add-on passe a exigir API
   nova da dependência.
2. Atualize o `<news>`.
3. Crie `changelog-<versão>.txt`. O `build_repo.py` empacota só o changelog da versão atual.
4. Alinhe o `__version__` do `__init__.py` do pacote.
5. Atualize as versões em `documentation/release/STATE.md`.

Tags: uma por add-on, no formato `<addon-id>-<versão>` (ex.: `plugin.video.stv-0.8.6`). Push e publicação no Pages
(`build_repo.py` + commit de `docs/`) só com pedido do usuário.

Testes manuais no aparelho e no emulador (adb + JSON-RPC do Kodi) ficam em `tools/deploy_kodi_emulator.py`,
`tools/test_sradio_full_battery.py` e `tools/test_lock_screen_playback.py`; não fazem parte da suíte.
