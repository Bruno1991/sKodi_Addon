# Auditoria de Código Legado
Data: 2026-11-24 | Escopo: repositório inteiro (`addons/`, `tools/`, `tests/`) | Linha de base dos testes: 121/121 OK
(`python -m unittest discover -s tests -p "test_*.py"`), `validate_addons` OK, `secret_scan` OK, `compileall` OK.
Ponto de retorno: commit `cc62e62`. Lotes 1–3 executados em 2026-11-24 (122/122 testes OK ao final).

Local do arquivo: `documentation/governance/` e não `docs/`, porque `docs/` é gerado por `tools/build_repo.py`
(apagado e recriado a cada build) e publicado no GitHub Pages.

Ferramentas: `ruff` (F401, F811, F841, T201, ERA001) e `vulture` (confiança ≥ 60%), e depois `grep` em código, XML,
Makefile, CI e documentação para cada candidato.

Fora do relatório (mantidos de propósito):
- 67 `print` em `tools/`: são a saída das ferramentas de linha de comando, não logs de depuração.
- Campos do dataclass `Capabilities` (`saile_core/capabilities.py`) e `row_factory` do sqlite: falsos positivos do vulture.
- `EpgProvider` (`saile_epg/providers/base.py`): `Protocol` que documenta o contrato dos providers.
- Parâmetros `offscreen`/`isFolder` em `tests/test_stv_view_preferences.py`: assinatura dos dublês do Kodi.
- `_icon`/`_set_video_metadata` duplicados entre sRadio e sTv: cruzam a fronteira entre add-ons instaláveis
  independentes (regra 5). Ficam como estão.
- Sem código comentado (ERA001 limpo).

## Lote 1 (Risco Baixo): imports e variáveis sem uso
- [x] `addons/plugin.audio.sradio/resources/lib/sradio/bootstrap.py:3,4,7`: `sys`, `urllib.parse`, `TuneInAPI` sem uso. Remover.
- [x] `addons/plugin.audio.sradio/resources/lib/sradio/bootstrap.py:360`: variável `folder_icon` atribuída e não usada. Remover.
- [x] `addons/plugin.audio.sradio/resources/lib/sradio/favorites.py:4`: `os` sem uso. Remover.
- [x] `addons/plugin.video.stv/resources/lib/stv/bootstrap.py:3,4,13`: `sys`, `unicodedata`, `ensure_all_live_streams_loaded` sem uso. Remover.
- [x] `addons/plugin.video.stv/resources/lib/stv/domain/catalog.py:5`: `MediaItem` sem uso. Remover.
- [x] `addons/script.module.saile.core/lib/saile_core/capabilities.py:5`: `sys` sem uso. Remover.
- [x] `addons/script.module.saile.epg/lib/saile_epg/providers/claro.py:9`: `Sequence` sem uso. Remover.
- [x] `tests/*`: 10 imports sem uso e 1 redefinição (`Category` em `test_stv_ui_standardization.py`), mais a variável `png_dir` em `test_sradio.py:263`. Remover.
- [x] `tools/*`: 9 imports sem uso (`colorize_common_svgs`, `deploy_kodi_emulator`, `generate_sradio_icons`, `print_tree`, `test_sradio_full_battery`) e `except ... as e` sem uso em `deploy_kodi_emulator.py:44`. Remover.

Evidência: ruff F401/F811/F841, e nenhum `patch("modulo.nome")` ou acesso por atributo a esses nomes em testes e ferramentas.

## Lote 2 (Risco Baixo/Médio): funções sem referência
- [x] `addons/plugin.audio.sradio/resources/lib/sradio/catalog.py:361`: `RadioCatalog.get_international_groups`. Remover. Evidência: nenhuma referência em código, XML, testes ou docs.
- [x] `addons/plugin.video.stv/resources/lib/stv/app/services.py:262`: `AppContainer.get_live_schedule`. Remover. Evidência: nenhuma referência (o Agora/Próximo usa a consulta em lote).
- [x] `addons/plugin.video.stv/resources/lib/stv/app/sync.py:166`: `ensure_all_live_streams_loaded`. Remover. Evidência: só era importada (sem uso) em `bootstrap.py`; o auto-sync substituiu a função.
- [x] `addons/plugin.video.stv/resources/lib/stv/bootstrap.py:90`: `_add_unmatched_live_item`. Remover. Evidência: nenhuma referência.
- [x] `addons/plugin.video.stv/resources/lib/stv/domain/catalog.py:8`: `filter_categories_by_parent`. Remover. Evidência: nenhuma referência.
- [x] `addons/script.module.saile.core/lib/saile_core/artwork.py:9`: `_resource_root` (privada). Remover. Evidência: nenhuma referência; o caminho é resolvido por `artwork_absolute_path`.

Fronteiras Kodi conferidas: nenhum desses nomes aparece em `addon.xml`, `resources/settings.xml` nem nas rotas
`action=` dos plugins.

## Lote 3 (Risco Médio): duplicação dentro da mesma fronteira
- [x] `addons/plugin.video.stv/resources/lib/stv/bootstrap.py` (listagem de temporadas e de episódios): extração de
  `cover`/`backdrop_path`/`series_fanart` copiada nas duas funções. Consolidar em `_series_artwork(info, fanart)`
  dentro do próprio sTv, com comportamento idêntico.

## Lote 4 (Revisão Manual): aguardam decisão
- [ ] `addons/plugin.video.stv/resources/lib/stv/ui/player.py:13`: `SailePlayer` nunca é instanciado, então
  `update_playback_progress` nunca roda e o "continuar de onde parou" (`StartOffset` em `play_video`) nunca encontra
  progresso salvo. **Decidir:** ligar o `SailePlayer` (exige um loop de monitoramento após `setResolvedUrl`) ou remover
  o recurso de retomada.
- [ ] `tools/select_artwork.py`, `tools/colorize_common_svgs.py`, `tools/generate_sradio_icons.py`: geradores de
  artwork usados uma vez, citados só em docs gerados e em `artwork/README.md`. **Decidir:** manter como ferramenta
  de manutenção ou remover.
- [ ] `tools/deploy_kodi_emulator.py`, `tools/test_lock_screen_playback.py`, `tools/test_sradio_full_battery.py`:
  testes manuais via adb/JSON-RPC fora da suíte automática. Recomendação: manter.
- [ ] `addons/plugin.video.stv/resources/lib/stv/providers/tmdb/client.py:17`: `DEFAULT_API_KEY` do TMDB embutida
  (chave pública do app, distribuída no ZIP). Tirar dali muda o contrato: o usuário passaria a ter de informar
  a própria chave. **Decidir.**
- [ ] `addons/plugin.video.stv/resources/lib/stv/providers/xtream/client.py:20`: atributo `raw_host` sem leitura.
  Ganho mínimo; pode ser lido por código de diagnóstico futuro. Recomendação: manter.
