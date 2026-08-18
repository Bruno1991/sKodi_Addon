# sRepo — Ecossistema SAILE para Kodi (IPTV / sTv)

Monorepo local-first que desenvolve e distribui o add-on **sTv** (IPTV / Xtream) e seus módulos compartilhados por um repositório Kodi hospedado estaticamente no GitHub Pages.

## Add-ons Ativos

```text
addons/
├── repository.srepo/
├── resource.images.saile/
├── script.module.saile.core/
├── script.module.saile.epg/
└── plugin.video.stv/
```

- `repository.srepo`: instala e atualiza os add-ons do ecossistema no Kodi.
- `resource.images.saile`: 9 ícones fixos compartilhados em alta definição.
- `script.module.saile.core`: caminhos portáveis, artwork, notificações, erros padronizados e detecção de capacidades.
- `script.module.saile.epg`: XMLTV autorizado, matching de canais, horários UTC e cache SQLite independente.
- `plugin.video.stv`: cliente de TV ao vivo, VOD e séries com integração Xtream Codes, persistência SQLite, EPG modular e metadados TMDB.

## Navegação Oficial (Contrato Imutável)

### sTv

```text
Home: TV ao Vivo → VOD → Séries → Sincronizar Dados
Cada seção: Buscar → Favoritos → Categorias e conteúdo dinâmico
```

A sincronização LAN é sempre manual sob demanda do usuário.

O EPG também é sincronizado manualmente dentro de `Sincronizar Dados`. XMLTV é a fonte primária; se o documento não puder ser processado, o módulo tenta o EPG curto autorizado da API Xtream. Abrir listas e canais consulta somente o cache local, sem requisições de guia por item.

Os canais ao vivo guardam o título original do provedor, um nome limpo para exibição e uma chave canônica produzida pelo mesmo normalizador do EPG. Tags de qualidade e redundância não interferem no matching, enquanto regiões e números do canal permanecem distintos.

Em TV ao Vivo, todo stream que declara uma identidade EPG aparece uma única vez no nível principal com o nome oficial do guia quando disponível. A existência do canal não depende de haver programação no horário atual. Suas variantes SD/HD/FHD/4K ficam internas; canais realmente sem EPG permanecem em suas categorias e categorias totalmente absorvidas são ocultadas. A grade InfoWall carrega Agora/Próximo em lote, com horários, descrição e progresso. A escolha automática respeita a qualidade máxima e o limite de banda definidos em `Configurações → Reprodução de TV ao Vivo` e sonda apenas o canal clicado.

O Kodi não oferece a add-ons Python uma API para inserir URLs independentes como resoluções selecionáveis no menu nativo do player. O sTv seleciona a variante antes de reproduzir e informa ao player a resolução escolhida; troca contínua exigiria um manifesto adaptativo real ou integração PVR/InputStream.

Todas as rotas de diretório usam o contrato `InfoWall` (`view mode 54`). Em episódios, o sTv prioriza o frame fornecido pelo Xtream em `icon`, `thumb`, `poster` e `landscape`.

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
