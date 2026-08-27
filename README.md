# sRepo — Ecossistema sKodi (sTv / sEPG / sArtwork / sCore)

Monorepo local-first que desenvolve e distribui o add-on **sTv** (IPTV / Xtream) e seus módulos compartilhados por um repositório Kodi hospedado estaticamente no GitHub Pages.

🌐 **Portal de Add-ons & Repositório (GitHub Pages):**  
👉 [https://bruno1991.github.io/sKodi_Addon/](https://bruno1991.github.io/sKodi_Addon/)

📦 **Download direto do instalador sRepo:**  
👉 [`repository.srepo-1.1.1.zip`](https://bruno1991.github.io/sKodi_Addon/repository.srepo-1.1.1.zip)

A documentação técnica de Python/Kodi está centralizada em
[`documentation/`](documentation/README.md). Diretrizes gerais de engenharia de software e padrões de arquitetura encontram-se na [Mega Biblioteca de Engenharia](../engineering-library/README.md).

## Add-ons Ativos

```text
addons/
├── repository.srepo/          (sRepo - Instalador e atualizações)
├── resource.images.saile/     (sArtwork - Recursos de imagem e ícones)
├── script.module.saile.core/  (sCore - Infraestrutura Python compartilhada)
├── script.module.saile.epg/   (sEPG - Guia de programação e normalização)
└── plugin.video.stv/          (sTv - Cliente IPTV, VOD, Séries e Player)
```

- `repository.srepo` (**sRepo**): instala e atualiza os add-ons do ecossistema no Kodi.
- `resource.images.saile` (**sArtwork**): 9 ícones fixos compartilhados em alta definição.
- `script.module.saile.core` (**sCore**): caminhos portáveis, artwork, notificações, erros padronizados e detecção de capacidades.
- `script.module.saile.epg` (**sEPG**): Integração direta com a API da Claro TV+ (AVSClient v1.2), motor de aliases para 100% dos canais brasileiros e afiliadas regionais, horários UTC e cache SQLite independente.
- `plugin.video.stv` (**sTv**): cliente de TV ao vivo com categorias nativas Xtream, VOD e séries com persistência SQLite, auto-sincronização de catálogo e EPG, sincronização LAN P2P UDP e metadados TMDB.

## Navegação Oficial (Contrato Imutável)

### sTv

```text
Home: TV ao Vivo → VOD → Séries → Sincronizar Dados
Cada seção: Buscar → Favoritos → Categorias e conteúdo dinâmico
```

A sincronização de catálogo e do EPG ocorre automaticamente em background daemon thread (TTL configurável) e também pode ser disparada manualmente sob demanda no menu `Sincronizar Dados`.

A sincronização em LAN opera de forma automática via Zero-Config UDP Peer-to-Peer (porta 54242) entre instâncias Kodi na rede local, com opções manuais completas de exportação, importação e merge sanitizado no menu interativo.

Os canais ao vivo guardam o título original do provedor, um nome limpo para exibição e uma chave canônica produzida pelo motor universal de aliases do EPG. Tags de qualidade e redundância não interferem no matching, garantindo exibição de Agora/Próximo em 100% dos canais suportados.

Em TV ao Vivo, a navegação é organizada pelas categorias nativas da operadora Xtream, com carregamento do Agora/Próximo em lote (1 única query SQL). O enquadramento visual é padronizado em `InfoWall` (`view mode 54`) em todas as telas. Em episódios, o sTv prioriza o frame fornecido pelo Xtream em `icon`, `thumb`, `poster` e `landscape`.

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

# 6. Atualizar manifesto estrutural e árvore na biblioteca Python/Kodi
python tools/generate_structure_manifest.py
python tools/print_tree.py
```
