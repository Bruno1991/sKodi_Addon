# Notas do pacote V2 (IPTV Focus)

## Incluído

- Foco exclusivo no ecossistema IPTV (sTv), módulos compartilhados e repositório.
- `resource.images.saile` com nove artes fixas (5 comuns + 4 sTv).
- `script.module.saile.core` com artwork, notificações, caminhos, erros e capacidades.
- Navegação contratual oficial do sTv (Home e seções).
- Cliente Xtream para autenticação, listagem de categorias/mídias e geração de stream URLs.
- Cliente TMDB integrado para enriquecimento de metadados sob demanda.
- Persistência e repositório SQLite robusto para sTv (`stv.db`).
- Suíte expandida com 20 testes unitários cobrindo persistência, clientes, contratos, roteamento e core.
- Pipeline de build determinístico gerando `docs/` e ZIPs compatíveis com Kodi.
- Verificação de segredos e políticas de segurança 100% conformes.
- `script.module.saile.epg` independente, com XMLTV autorizado, UTC e cache próprio.
- InfoWall 54 aplicado de forma central a todos os diretórios do sTv.
- Frames de episódios priorizados em todos os slots de artwork do episódio.
