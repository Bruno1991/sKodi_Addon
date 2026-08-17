# sRepo — Ecossistema SAILE para Kodi (IPTV / sTv)

Monorepo local-first que desenvolve e distribui o add-on **sTv** (IPTV / Xtream) e seus módulos compartilhados por um repositório Kodi hospedado estaticamente no GitHub Pages.

## Add-ons Ativos

```text
addons/
├── repository.srepo/
├── resource.images.saile/
├── script.module.saile.core/
└── plugin.video.stv/
```

- `repository.srepo`: instala e atualiza os add-ons do ecossistema no Kodi.
- `resource.images.saile`: 9 ícones fixos compartilhados em alta definição.
- `script.module.saile.core`: caminhos portáveis, artwork, notificações, erros padronizados e detecção de capacidades.
- `plugin.video.stv`: cliente de TV ao vivo, VOD e séries com integração Xtream Codes, persistência SQLite e metadados TMDB.

## Navegação Oficial (Contrato Imutável)

### sTv

```text
Home: TV ao Vivo → VOD → Séries → Sincronizar Dados
Cada seção: Buscar → Favoritos → Categorias e conteúdo dinâmico
```

A sincronização LAN é sempre manual sob demanda do usuário.

## Artwork Compartilhado

```text
resource.images.saile/resources/media/
├── common/
│   ├── search.png
│   ├── erro.png
│   ├── check.png
│   ├── sync.png
│   └── folder.png
└── stv/
    ├── live.png
    ├── vod.png
    ├── series.png
    └── favoritos.png
```

Cada add-on ainda mantém `icon.png` e `fanart.jpg` próprios. Capas, pôsteres e thumbnails de conteúdo são dinâmicos (fornecidos pelo servidor Xtream ou TMDB).

## Comandos de Validação e Build

```powershell
# 1. Aplicar artwork
python tools/bootstrap_artwork.py

# 2. Validar integridade dos add-ons
python tools/validate_addons.py

# 3. Auditoria de segurança e segredos
python tools/secret_scan.py

# 4. Executar suíte de testes unitários
python -m unittest discover -s tests -p "test_*.py" -v

# 5. Gerar repositório Kodi e pacotes ZIP
python tools/build_repo.py

# 6. Atualizar manifesto estrutural e árvore
python tools/generate_structure_manifest.py
python tools/print_tree.py
```
