# Índice das 94 skills (IPTV & Ecossistema SAILE)

> Catálogo operacional opcional. As skills vivem em `.agents/`, são ignoradas pelo Git e não entram no runtime nem nos ZIPs Kodi. Os links só ficam ativos em uma estação de desenvolvimento que tenha a biblioteca local instalada.

| ID | Categoria | Skill | Missão |
|---|---|---|---|
| 00.01 | governance | [Proteção de escopo](.agents/skills/00-governance/scope-guard/SKILL.md) | Definir o que pertence ao sRepo e sTv antes de qualquer alteração. |
| 00.02 | governance | [Arquitetura antes do código](.agents/skills/00-governance/architecture-first/SKILL.md) | Converter uma solicitação em componentes, fluxos e fronteiras antes da implementação. |
| 00.03 | governance | [Plano de mudança](.agents/skills/00-governance/change-plan/SKILL.md) | Produzir um plano executável por arquivo com riscos e critérios de aceitação. |
| 00.04 | governance | [Fronteiras do monorepo](.agents/skills/00-governance/repository-boundaries/SKILL.md) | Manter documentação, ferramentas, addons e artefatos publicados em áreas distintas. |
| 00.05 | governance | [ADRs e decisões](.agents/skills/00-governance/decision-records/SKILL.md) | Registrar decisões arquiteturais duráveis com contexto e consequências. |
| 00.06 | governance | [Rastreabilidade do roadmap](.agents/skills/00-governance/requirements-traceability/SKILL.md) | Mapear cada bloco do roadmap a módulos, dados, testes e fases. |
| 00.07 | governance | [Definição de pronto](.agents/skills/00-governance/definition-of-done/SKILL.md) | Impedir entregas incompletas definindo evidências mínimas por tipo de trabalho. |
| 00.08 | governance | [Governança de dependências](.agents/skills/00-governance/dependency-governance/SKILL.md) | Controlar bibliotecas, licenças, tamanho e compatibilidade com Kodi. |
| 00.09 | governance | [Contrato de saída do agente](.agents/skills/00-governance/agent-output-contract/SKILL.md) | Padronizar respostas do agente com caminhos, arquivos completos e validações. |
| 00.10 | governance | [Constituição local-first](.agents/skills/00-governance/local-first-constitution/SKILL.md) | Garantir que o sistema rode no dispositivo do usuário sem backend próprio obrigatório. |
| 01.01 | python | [Layout Python modular](.agents/skills/01-python/project-layout/SKILL.md) | Organizar módulos por domínio, infraestrutura, aplicação e apresentação. |
| 01.02 | python | [Tipagem e contratos](.agents/skills/01-python/typing-contracts/SKILL.md) | Usar tipos para tornar payloads externos e respostas internas verificáveis. |
| 01.03 | python | [Modelos de domínio](.agents/skills/01-python/domain-models/SKILL.md) | Representar canal, filme, série, episódio e categoria com modelos estáveis. |
| 01.04 | python | [Taxonomia de exceções](.agents/skills/01-python/exception-taxonomy/SKILL.md) | Distinguir erro de configuração, rede, provider, banco, reprodução e cancelamento. |
| 01.05 | python | [Logging sanitizado](.agents/skills/01-python/logging-sanitization/SKILL.md) | Criar logs úteis sem expor credenciais ou dados temporários. |
| 01.06 | python | [Cliente HTTP resiliente](.agents/skills/01-python/http-client/SKILL.md) | Centralizar timeout, headers, erros, retries limitados e parsing JSON. |
| 01.07 | python | [URLs e query strings seguras](.agents/skills/01-python/url-query-safety/SKILL.md) | Montar endpoints sem corromper encoding e sem vazar parâmetros sensíveis. |
| 01.08 | python | [Normalização de JSON externo](.agents/skills/01-python/json-normalization/SKILL.md) | Converter respostas inconsistentes em contratos internos previsíveis. |
| 01.09 | python | [Concorrência segura no Kodi](.agents/skills/01-python/concurrency-kodi/SKILL.md) | Executar I/O concorrente sem chamar APIs de UI fora da thread apropriada. |
| 01.10 | python | [Progresso e cancelamento](.agents/skills/01-python/progress-cancellation/SKILL.md) | Tornar sincronizações e buscas longas visíveis e canceláveis. |
| 02.01 | sqlite | [Ciclo de vida da conexão](.agents/skills/02-sqlite/connection-lifecycle/SKILL.md) | Abrir, configurar e fechar conexões SQLite de forma previsível no Kodi. |
| 02.02 | sqlite | [Design de schema](.agents/skills/02-sqlite/schema-design/SKILL.md) | Modelar catálogos, favoritos, progresso e cache sem duplicação desnecessária. |
| 02.03 | sqlite | [Versionamento de schema](.agents/skills/02-sqlite/schema-versioning/SKILL.md) | Controlar versão do banco independentemente da versão do addon. |
| 02.04 | sqlite | [Migrações transacionais](.agents/skills/02-sqlite/migrations/SKILL.md) | Alterar bancos existentes sem perda silenciosa de dados. |
| 02.05 | sqlite | [Transações e consistência](.agents/skills/02-sqlite/transactions/SKILL.md) | Agrupar escritas relacionadas e evitar catálogos parcialmente atualizados. |
| 02.06 | sqlite | [PRAGMAs seguros](.agents/skills/02-sqlite/pragmas/SKILL.md) | Escolher foreign_keys, journal mode, synchronous, busy_timeout e cache de forma compatível. |
| 02.07 | sqlite | [Índices e query plan](.agents/skills/02-sqlite/indexes-query-plan/SKILL.md) | Criar índices baseados em consultas reais e verificar seu uso. |
| 02.08 | sqlite | [UPSERT e sincronização em lote](.agents/skills/02-sqlite/upsert-bulk-sync/SKILL.md) | Atualizar catálogos Xtream e metadados sem apagar favoritos ou progresso. |
| 02.09 | sqlite | [Favoritos e progresso](.agents/skills/02-sqlite/favorites-progress/SKILL.md) | Persistir ações do usuário separadas do catálogo atualizável. |
| 02.10 | sqlite | [Busca local e FTS](.agents/skills/02-sqlite/fts-search/SKILL.md) | Oferecer busca rápida com fallback quando FTS5 não estiver disponível. |
| 03.01 | kodi-core | [Manifesto addon.xml](.agents/skills/03-kodi-core/addon-xml/SKILL.md) | Criar manifestos válidos para sTv e sRepo com IDs, versões e extensões corretas. |
| 03.02 | kodi-core | [Configurações do addon](.agents/skills/03-kodi-core/settings-xml/SKILL.md) | Definir settings.xml com labels localizadas, campos secretos e defaults seguros. |
| 03.03 | kodi-core | [Localização](.agents/skills/03-kodi-core/localization/SKILL.md) | Manter strings em resource.language e evitar textos soltos em código. |
| 03.04 | kodi-core | [Roteamento de plugin](.agents/skills/03-kodi-core/router/SKILL.md) | Interpretar ações e parâmetros com whitelist e fallback para home. |
| 03.05 | kodi-core | [Diretórios e ListItems](.agents/skills/03-kodi-core/directory-items/SKILL.md) | Construir pastas e itens com metadados, arte e propriedades corretas. |
| 03.06 | kodi-core | [Conteúdo e ordenação](.agents/skills/03-kodi-core/content-sorting/SKILL.md) | Informar tipo de conteúdo e métodos de ordenação adequados ao Kodi. |
| 03.07 | kodi-core | [Caminhos special://](.agents/skills/03-kodi-core/special-paths/SKILL.md) | Usar caminhos portáveis para perfil, temp, home e addon. |
| 03.08 | kodi-core | [Integração de logs Kodi](.agents/skills/03-kodi-core/kodi-logging/SKILL.md) | Encapsular xbmc.log com prefixo, níveis e sanitização. |
| 03.09 | kodi-core | [Serviço opcional](.agents/skills/03-kodi-core/service-addon/SKILL.md) | Decidir quando tarefas em segundo plano justificam service.py sem manter daemon desnecessário. |
| 03.10 | kodi-core | [Compatibilidade Kodi](.agents/skills/03-kodi-core/compatibility/SKILL.md) | Manter APIs usadas dentro da versão alvo e detectar diferenças sem gambiarras. |
| 03.11 | kodi-core | [Módulo Python compartilhado](.agents/skills/03-kodi-core/shared-python-module/SKILL.md) | Extrair somente infraestrutura estável para script.module.saile.core sem mover regras de negócio. |
| 04.01 | kodi-ui | [UI independente de skin](.agents/skills/04-kodi-ui-playback/skin-independent-ui/SKILL.md) | Criar experiência consistente usando recursos públicos do Kodi. |
| 04.02 | kodi-ui | [Artwork e fallbacks](.agents/skills/04-kodi-ui-playback/artwork/SKILL.md) | Selecionar thumb, icon, poster, fanart e fallback sem imagens quebradas. |
| 04.03 | kodi-ui | [Menus de contexto](.agents/skills/04-kodi-ui-playback/context-menus/SKILL.md) | Adicionar favorito, remover, marcar visto e atualizar sem poluir navegação. |
| 04.04 | kodi-ui | [Diálogos de busca](.agents/skills/04-kodi-ui-playback/search-dialogs/SKILL.md) | Coletar termos, validar cancelamento e renderizar resultados locais/remotos. |
| 04.05 | kodi-ui | [Diálogos de progresso](.agents/skills/04-kodi-ui-playback/progress-dialogs/SKILL.md) | Apresentar sincronização de catálogo e metadata com cancelamento seguro. |
| 04.06 | kodi-ui | [Reprodução resolvida](.agents/skills/04-kodi-ui-playback/resolved-playback/SKILL.md) | Entregar ao Kodi uma URL reproduzível com ListItem e MIME apropriados. |
| 04.07 | kodi-ui | [Reprodução de vídeo](.agents/skills/04-kodi-ui-playback/video-playback/SKILL.md) | Configurar live, filmes e episódios com propriedades adequadas. |
| 04.08 | kodi-ui | [Continuar assistindo](.agents/skills/04-kodi-ui-playback/continue-watching/SKILL.md) | Capturar e restaurar progresso sem sobrescrever estado concluído incorretamente. |
| 04.09 | kodi-ui | [Desempenho de renderização](.agents/skills/04-kodi-ui-playback/performance-rendering/SKILL.md) | Evitar travamentos ao listar catálogos grandes. |
| 04.10 | kodi-ui | [Recurso de imagens compartilhado](.agents/skills/04-kodi-ui-playback/shared-artwork-resource/SKILL.md) | Manter ícones fixos em resource.images.saile e conteúdo remoto fora do pacote. |
| 05.01 | stv | [Configuração Xtream](.agents/skills/05-stv-xtream/xtream-configuration/SKILL.md) | Ler e validar host, login e senha do sTv sem expor credenciais. |
| 05.02 | stv | [Cliente Xtream](.agents/skills/05-stv-xtream/xtream-client/SKILL.md) | Centralizar chamadas player_api.php e respostas do provider. |
| 05.03 | stv | [Sincronização de catálogo](.agents/skills/05-stv-xtream/xtream-catalog-sync/SKILL.md) | Atualizar categorias, live, VOD e séries em etapas transacionais. |
| 05.04 | stv | [TV ao vivo](.agents/skills/05-stv-xtream/live-tv/SKILL.md) | Listar canais por categoria e construir stream live válido. |
| 05.05 | stv | [Filmes VOD](.agents/skills/05-stv-xtream/vod/SKILL.md) | Listar filmes, enriquecer metadados e reproduzir extensão informada pelo provider. |
| 05.06 | stv | [Séries, temporadas e episódios](.agents/skills/05-stv-xtream/series/SKILL.md) | Transformar payloads Xtream em hierarquia navegável e estável. |
| 05.07 | stv | [Busca sTv](.agents/skills/05-stv-xtream/stv-search/SKILL.md) | Pesquisar canais, filmes e séries localmente com filtros por domínio. |
| 05.08 | stv | [Favoritos sTv](.agents/skills/05-stv-xtream/stv-favorites/SKILL.md) | Gerenciar favoritos de canais, filmes e séries sem depender do catálogo atual. |
| 05.09 | stv | [Progresso sTv](.agents/skills/05-stv-xtream/stv-continue-watching/SKILL.md) | Manter continuar assistindo para VOD e episódios, nunca para live simples. |
| 05.10 | stv | [Resiliência do provider](.agents/skills/05-stv-xtream/stv-provider-resilience/SKILL.md) | Distinguir indisponibilidade temporária, credencial inválida e payload quebrado. |
| 05.11 | stv | [Contrato de navegação sTv](.agents/skills/05-stv-xtream/stv-navigation-contract/SKILL.md) | Preservar a home e a ordem fixa Buscar/Favoritos em cada seção do sTv. |
| 07.01 | metadata | [Autenticação TMDB](.agents/skills/07-metadata-search/tmdb-auth/SKILL.md) | Carregar token de desenvolvimento com segurança e definir estratégia de runtime local. |
| 07.02 | metadata | [Cliente TMDB](.agents/skills/07-metadata-search/tmdb-client/SKILL.md) | Centralizar autenticação, idioma, região, timeout, cache e erros. |
| 07.03 | metadata | [Correspondência de filmes](.agents/skills/07-metadata-search/movie-matching/SKILL.md) | Encontrar filme por título e ano com score de confiança. |
| 07.04 | metadata | [Correspondência de séries](.agents/skills/07-metadata-search/tv-matching/SKILL.md) | Encontrar série por nome, ano e tipo preservando temporadas do provider. |
| 07.05 | metadata | [Imagens HD](.agents/skills/07-metadata-search/images-hd/SKILL.md) | Construir URLs de poster/backdrop usando configuração e tamanhos compatíveis. |
| 07.06 | metadata | [Cache de metadados](.agents/skills/07-metadata-search/metadata-cache/SKILL.md) | Reduzir chamadas TMDB com TTL, versão e negative cache. |
| 07.07 | metadata | [Normalização de busca](.agents/skills/07-metadata-search/search-normalization/SKILL.md) | Remover ruído de nomes sem destruir títulos legítimos. |
| 07.08 | metadata | [Busca de metadados sTv](.agents/skills/07-metadata-search/unified-search/SKILL.md) | Orquestrar busca de metadados para filmes e séries do sTv. |
| 07.09 | metadata | [Fallbacks de metadados](.agents/skills/07-metadata-search/metadata-fallbacks/SKILL.md) | Priorizar provider, TMDB e assets locais de forma determinística. |
| 07.10 | metadata | [Privacidade de metadados](.agents/skills/07-metadata-search/metadata-privacy/SKILL.md) | Minimizar dados enviados em buscas externas e impedir vazamento de credenciais. |
| 08.01 | srepo | [Addon de repositório sRepo](.agents/skills/08-srepo-delivery/repository-addon/SKILL.md) | Configurar `repository.srepo` para apontar ao índice publicado no GitHub Pages. |
| 08.02 | srepo | [Layout de distribuição](.agents/skills/08-srepo-delivery/repo-layout/SKILL.md) | Organizar fonte, zips, site e ferramentas sem confundir diretório publicado. |
| 08.03 | srepo | [Empacotamento ZIP](.agents/skills/08-srepo-delivery/zip-packaging/SKILL.md) | Gerar ZIPs reproduzíveis com raiz correta e conteúdo mínimo. |
| 08.04 | srepo | [Geração de addons.xml](.agents/skills/08-srepo-delivery/addons-xml/SKILL.md) | Combinar manifests publicados em um índice XML válido e determinístico. |
| 08.05 | srepo | [Checksums do repositório](.agents/skills/08-srepo-delivery/checksums/SKILL.md) | Gerar checksum do índice e hashes dos artefatos para verificação. |
| 08.06 | srepo | [Versionamento e releases](.agents/skills/08-srepo-delivery/versioning/SKILL.md) | Aplicar SemVer e impedir divergência entre código, manifest, ZIP e changelog. |
| 08.07 | srepo | [Publicação GitHub Pages](.agents/skills/08-srepo-delivery/github-pages/SKILL.md) | Publicar site estático do repositório sem executar Python no servidor. |
| 08.08 | srepo | [CI/CD no GitHub Actions](.agents/skills/08-srepo-delivery/github-actions/SKILL.md) | Validar, empacotar e publicar com permissões mínimas e artefatos auditáveis. |
| 08.09 | srepo | [Rollback de release](.agents/skills/08-srepo-delivery/rollback/SKILL.md) | Reverter release quebrada mantendo clientes em versão funcional. |
| 08.10 | srepo | [Auditoria de release](.agents/skills/08-srepo-delivery/release-audit/SKILL.md) | Comprovar que nenhum segredo, banco ou lixo entrou nos ZIPs e Pages. |
| 09.01 | quality | [.gitignore blindado](.agents/skills/09-quality-security/gitignore-hardening/SKILL.md) | Excluir segredos, bancos, caches, IDEs, builds e arquivos pessoais sem ocultar fonte necessária. |
| 09.02 | quality | [Política de .env e segredos](.agents/skills/09-quality-security/env-secrets/SKILL.md) | Usar `.env` apenas em desenvolvimento e GitHub Secrets em automação. |
| 09.03 | quality | [Testes unitários](.agents/skills/09-quality-security/unit-tests/SKILL.md) | Testar normalizadores, roteamento, matching, SQL e seleção de formatos sem Kodi real. |
| 09.04 | quality | [Testes de contrato](.agents/skills/09-quality-security/contract-tests/SKILL.md) | Validar adaptadores contra fixtures de payload Xtream e TMDB. |
| 09.05 | quality | [Testes SQLite](.agents/skills/09-quality-security/sqlite-tests/SKILL.md) | Verificar migrações, constraints, índices, UPSERT e preservação de favoritos. |
| 09.06 | quality | [Stubs do Kodi](.agents/skills/09-quality-security/kodi-stubs/SKILL.md) | Permitir testes fora do Kodi sem contaminar produção com mocks. |
| 09.07 | quality | [Matriz de teste manual](.agents/skills/09-quality-security/manual-test-matrix/SKILL.md) | Validar sTv e sRepo em instalação limpa e atualização. |
| 09.08 | quality | [Orçamento de desempenho](.agents/skills/09-quality-security/performance-budget/SKILL.md) | Definir limites para home, listagem, busca, sync e abertura do banco. |
| 09.09 | quality | [Revisão de segurança](.agents/skills/09-quality-security/security-review/SKILL.md) | Revisar entrada, URLs, arquivos, logs, dependências e publicação. |
| 09.10 | quality | [Diagnóstico de incidentes](.agents/skills/09-quality-security/incident-diagnostics/SKILL.md) | Coletar evidências úteis sem pedir ou expor credenciais do usuário. |
| 09.11 | quality | [Sincronização LAN manual](.agents/skills/09-quality-security/manual-lan-sync/SKILL.md) | Sincronizar registros entre dispositivos somente por ação explícita, sem compartilhar SQLite ou segredos. |
