# Constituição de engenharia do ecossistema sKodi

## Artigo 1 — Local-first

sTv executa no dispositivo do usuário dentro do Kodi. Serviços externos são provedores de dados ou mídia; não existe backend próprio obrigatório, banco remoto central, fila remota ou autenticação externa.

## Artigo 2 — Responsabilidades dos add-ons ativos

- `repository.srepo` (**sRepo**): descoberta, instalação e atualização pelo GitHub Pages.
- `resource.images.saile` (**sArtwork**): artes fixas compartilhadas e somente elas (9 ícones).
- `script.module.saile.core` (**sCore**): infraestrutura comum estável, sem regras de domínio.
- `script.module.saile.epg` (**sEPG**): ingestão XMLTV, matching de canais, cache UTC e consultas de programação.
- `plugin.video.stv` (**sTv**): Xtream, TV ao vivo, VOD, séries, favoritos, busca, TMDB e reprodução de vídeo.

Dependências comuns são explícitas e versionadas.

## Artigo 3 — Navegação contratual

A ordem dos atalhos da home (`TV ao Vivo` → `VOD` → `Séries` → `Sincronizar Dados`) e das seções (`Buscar` → `Favoritos` → Conteúdo dinâmico) é requisito funcional coberto por testes. Provedores, ordenação alfabética e configurações não podem reorganizar os atalhos fixos.

## Artigo 4 — Persistência

O sTv usa SQLite próprio em `special://profile/addon_data/plugin.video.stv/stv.db`. Catálogo, cache e estado do usuário são separados. Migrações são versionadas, transacionais e testadas. Atualizações do add-on não apagam dados.

O módulo EPG usa banco independente em `special://profile/addon_data/script.module.saile.epg/epg.db`. EPG é cache reconstruível e nunca é misturado ao estado do usuário do sTv.

## Artigo 5 — Sincronização LAN

A sincronização é manual, opcional e acionada pelo usuário. Cada dispositivo mantém banco independente. O protocolo troca registros sanitizados, nunca arquivos SQLite ou segredos.

## Artigo 6 — Segurança

`.env` é ferramenta local. GitHub PAT pertence apenas ao fluxo administrativo. Credenciais Xtream vêm das configurações do Kodi. Qualquer chave distribuída em software cliente deve ser considerada recuperável e possuir escopo mínimo.

## Artigo 7 — Experiência Kodi

A UI usa APIs públicas do Kodi, navegação por controle remoto e artwork real. Falhas de rede, metadados ou imagens degradam com mensagens seguras, sem derrubar a navegação.

## Artigo 8 — Dependências condicionais

Serviços em segundo plano e integrações PVR são adiados até necessidade funcional comprovada.

## Artigo 9 — Evidência

Nenhuma tarefa é concluída por plausibilidade. A conclusão exige evidência proporcional: testes, parse XML, inspeção do ZIP, checksum, migração, instalação limpa ou reprodução em Kodi real.

## Artigo 10 — EPG modular

O sTv consome uma API interna estável de EPG e não conhece parsing XMLTV nem schema do cache. Sincronização da grade é manual; XMLTV é a fonte primária e a API curta autorizada do Xtream é fallback quando necessário. A identidade declarada do canal é independente da existência de programação na janela atual. Listagens consultam somente o banco local. Horários são normalizados para UTC.
