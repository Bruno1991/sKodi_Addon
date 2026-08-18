## Mudança

## Add-on afetado

- [ ] repository.srepo
- [ ] plugin.video.stv
- [ ] resource.images.saile
- [ ] script.module.saile.core
- [ ] script.module.saile.epg
- [ ] documentação/ferramentas

## Verificação

- [ ] `python tools/validate_addons.py`
- [ ] `python tools/secret_scan.py`
- [ ] `python -m unittest discover -s tests -p "test_*.py" -v`
- [ ] `python tools/build_repo.py`
- [ ] Nenhum segredo, banco, log ou URL temporária incluído
