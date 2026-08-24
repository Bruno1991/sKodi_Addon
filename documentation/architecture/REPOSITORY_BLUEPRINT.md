# Blueprint do repositório

```text
s_kodi_addon/
├── .agents/                             # instruções e base corporativa
├── .github/workflows/
├── Biblioteca_Universal_Corporativa/
│   └── web-scripting/python-kodi/docs/   # documentação técnica canônica
├── addons/
│   ├── repository.srepo/
│   ├── resource.images.saile/
│   │   └── resources/media/
│   │       ├── common/
│   │       └── stv/
│   ├── script.module.saile.core/
│   │   └── lib/saile_core/
│   ├── script.module.saile.epg/
│   │   └── lib/saile_epg/
│   └── plugin.video.stv/
│       └── resources/lib/stv/
├── artwork/                             # fontes e assets visuais canônicos
├── tests/                               # suíte de testes unitários
├── tools/                               # automação, build e validação
├── docs/                                # repositório estático publicado no GitHub Pages
├── .env.example
├── .gitignore
├── AGENTS.md
└── README.md
```

## Grafo de dependências

```mermaid
flowchart TD
  REPO[repository.srepo]
  ART[resource.images.saile]
  CORE[script.module.saile.core]
  EPG[script.module.saile.epg]
  STV[plugin.video.stv]

  CORE --> ART
  STV --> CORE
  EPG --> CORE
  STV --> EPG
  STV --> ART
  REPO -. distribui .-> ART
  REPO -. distribui .-> CORE
  REPO -. distribui .-> STV
```

## Conteúdo permitido no core (`script.module.saile.core`)

- caminhos portáveis Kodi (`special://`);
- artwork compartilhado (`resource.images.saile`);
- notificações nativas do Kodi;
- erros padronizados (`SaileError`);
- logging sanitizado;
- detecção de capacidades do dispositivo e SQLite.

## Conteúdo proibido no core

- endpoints Xtream;
- matching TMDB;
- categorias e persistência de TV, filmes ou séries;
- rotas específicas do plugin de vídeo.

## Conteúdo do módulo EPG (`script.module.saile.epg`)

- contrato público de canais, programas e snapshots;
- parsing XMLTV com limites de segurança;
- fallback manual de EPG curto pela API Xtream;
- normalização e matching determinístico de canais;
- timestamps UTC e cache SQLite próprio;
- providers sem dependência do `plugin.video.stv` ou da UI Kodi.

## Projeção de TV ao vivo do sTv

- o catálogo bruto Xtream continua preservado no SQLite do sTv;
- o módulo EPG fornece todas as identidades declaradas, mesmo sem programa atual;
- um XMLTV parcial é completado com IDs EPG do catálogo Xtream sem sobrescrever nomes oficiais já presentes;
- o sTv agrupa variantes por `epg_id` exato ou nome normalizado único;
- canais agrupados aparecem uma vez na raiz de TV ao Vivo;
- canais não reconhecidos permanecem nas categorias originais;
- categorias sem itens remanescentes são ocultadas;
- Agora/Próximo é consultado em lote para evitar consultas por card;
- a seleção de variante ocorre somente no clique e usa as preferências globais de reprodução, sem backend ou serviço contínuo.

## Add-ons futuros condicionais

```text
service.saile.monitor       após necessidade funcional comprovada
repository.srepo.beta       após existir processo de release estável
```
