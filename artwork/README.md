# Artwork do Ecossistema

Esta pasta é a fonte canônica para bootstrap e gerenciamento de artwork dos add-ons.

- Os cinco add-ons ativos, incluindo `script.module.saile.epg`, possuem `icon.png` e `fanart.jpg` nas respectivas pastas de estilo.
- Os 9 ícones fixos compartilhados têm origem em `artwork/common/png/` e destino definido em `artwork/artwork-manifest.json`.
- `python tools/bootstrap_artwork.py` copia cada arquivo para o destino correto dentro de `addons/`.
- `python tools/select_artwork.py` permite selecionar estilos visuais dinâmicos para ícones e fanarts.
