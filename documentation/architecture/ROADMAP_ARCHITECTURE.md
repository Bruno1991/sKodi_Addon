# Arquitetura derivada do roadmap

## Visão

```mermaid
flowchart LR
  REPO[repository.srepo] --> ART[resource.images.saile]
  REPO --> CORE[script.module.saile.core]
  REPO --> EPG[script.module.saile.epg]
  REPO --> STV[plugin.video.stv]
  STV --> CORE
  STV --> EPG
  STV --> ART

  STV --> X[Xtream API]
  STV --> T[TMDB API]
  STV --> DB1[(SQLite sTv)]
  EPG --> DB2[(SQLite EPG UTC)]
  EPG --> XTV[XMLTV autorizado]
```

## Navegação sTv

```text
sTv
├── TV ao Vivo
│   ├── Buscar
│   ├── Favoritos
│   └── categorias/canais dinâmicos (conforme entregue pela API Xtream)
├── VOD
│   ├── Buscar
│   ├── Favoritos
│   └── categorias/filmes dinâmicos
├── Séries
│   ├── Buscar
│   ├── Favoritos
│   └── categorias/séries dinâmicas
└── Sincronizar Dados
```

## Fluxo do sTv (IPTV)

1. Usuário configura host, usuário e senha Xtream nas configurações do Kodi.
2. Cliente valida autenticação e normaliza payloads.
3. Sincronização do catálogo executa UPSERT em SQLite local (`stv.db`).
4. Home e categorias navegam prioritariamente pelo cache local com suporte a TTL.
5. `Buscar` e `Favoritos` aparecem sempre antes do conteúdo de cada seção.
6. URL de reprodução direta é construída no último momento pelo player.
7. TMDB enriquece metadados (plot, pôster e fanart HD) sob demanda.
8. O módulo EPG sincroniza guia oficial da Claro TV+ (e XMLTV/Xtream como fallback) e armazena em cache SQLite UTC independente.
9. Os canais de TV ao Vivo são organizados pelas categorias nativas da API Xtream.
10. Cada canal exibe Agora/Próximo (Now/Next) em tempo real, descrição e barra de progresso no padrão InfoWall 54.
11. A reprodução do canal conecta diretamente ao stream fornecido pelo provedor Xtream.

## Artwork

`resource.images.saile` contém exatamente nove artes fixas de menu/pop-up/fallback (5 comuns + 4 sTv). Cada add-on mantém sua identidade (`icon.png` e `fanart.jpg`). Capas e fanarts de conteúdo são dinâmicas, fornecidas por Xtream ou TMDB e cacheadas pelo Kodi.

## Sincronização LAN

A sincronização LAN do sTv opera com protocolo Zero-Configuração via UDP Broadcast (porta 54242) em segundo plano e também sob demanda no menu `Sincronizar Dados`. A implementação troca registros versionados e sanitizados (apenas favoritos) entre dispositivos na mesma rede local conforme `LAN_SYNC_CONTRACT.md`; não compartilha `.db` e nunca transmite credenciais, senhas ou URLs de mídia.

## Fases do Projeto

1. Módulos compartilhados, contratos de navegação e build.
2. MVP sTv: autenticação, catálogo e reprodução.
3. Favoritos, busca local, TMDB e persistência do sTv.
4. EPG modular com Claro TV+, UTC, janela de 36h e cache independente.
5. Sincronização LAN (Zero-Config UDP e export/import manual).
6. Auto-sincronização resiliente em background (Catálogo, EPG e LAN).
