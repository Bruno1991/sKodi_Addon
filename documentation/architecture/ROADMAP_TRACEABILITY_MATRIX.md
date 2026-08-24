# Matriz de rastreabilidade (IPTV / sTv)

| Capacidade | Componente | Persistência | Fase | Evidência mínima |
|---|---|---|---|---|
| Distribuição/updates | `repository.srepo` | artefatos estáticos | V1 | ZIPs, addons.xml, SHA256SUMS |
| Nove artes fixas | `resource.images.saile` | arquivos locais | V1 | manifesto + teste de existência |
| Infraestrutura comum | `script.module.saile.core` | nenhuma de domínio | V1 | teste de dependências/import/capabilities |
| EPG modular | `script.module.saile.epg` | `epg.db`, cache UTC | V1 | parser XMLTV, matching, migração, Agora/Próximo e ZIP |
| Home sTv | `plugin.video.stv` | nenhuma | V1 | ordem contratual coberta por teste |
| Buscar/Favoritos por seção | `plugin.video.stv` | favorites/SQLite | V1 | ordem fixa + testes de persistência |
| Provedor Xtream | `plugin.video.stv` | catálogo/cache | V1 | parsing, client, stream URLs e sync |
| Metadados TMDB | `plugin.video.stv` | SQLite/enrichment | V1 | client TMDB, matching e fanart HD |
| Progresso de reprodução | `plugin.video.stv` | playback_progress | V1 | teste de atualização de posição/duração |
| Sincronização LAN manual | `plugin.video.stv` | journal/export | V2 | ação explícita + dados sanitizados |
| Diagnóstico seguro | core/plugins | logs sanitizados | V2 | auditoria secret_scan sem vazamentos |
| Serviço de monitoramento | futuro | a definir | futuro | necessidade comprovada |
| PVR avançado | futuro | M3U e integração PVR | futuro | ADR e teste multiplataforma |
