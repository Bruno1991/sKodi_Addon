# Matriz de compatibilidade

## Alvos

| Plataforma | Prioridade | Validação necessária |
|---|---:|---|
| Windows + Kodi 19+ (Matrix, Nexus, Omega) | alta | instalação, menus, SQLite e reprodução |
| Linux + Kodi 19+ | alta | instalação, permissões e reprodução |
| Android TV + Kodi 19+ | alta | memória, controle remoto e reprodução |
| Fire TV / Firestick + Kodi 19+ | alta | desempenho e reprodução de streams |
| Versões futuras do Kodi | preventiva | testes contínuos sem quebra de compatibilidade |

## Requisitos comuns

- Python 3 fornecido pelo Kodi (`xbmc.python` >= 3.0.0).
- `resource.images.saile` e `script.module.saile.core` instalados como dependências automáticas.
- Dados locais gravados exclusivamente em `special://profile/addon_data/`.
- Nenhum executável ou binário externo obrigatório na V1.
