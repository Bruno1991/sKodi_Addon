# ADR-0001 — EPG como módulo local independente

- Status: aceito
- Data: 2026-08-18

## Contexto

O EPG anterior vivia dentro do `plugin.video.stv` e consultava uma fonte externa durante a renderização de cada canal. Isso acoplava UI, rede, parsing e persistência, além de tornar o tempo de abertura proporcional ao número de canais.

## Decisão

Criar `script.module.saile.epg` como add-on Python independente. O módulo recebe XMLTV autorizado, normaliza horários para Unix timestamp UTC, resolve canais por ID exato ou nome normalizado e mantém `epg.db` em seu próprio perfil. Quando o XMLTV não puder ser processado, a sincronização manual pode usar `get_short_epg` da API Xtream como provider de fallback.

O sTv conserva apenas `epg_id` junto ao canal, aciona a sincronização manual e consome `get_now_next`. Nenhuma rota de navegação inicia download de EPG.

## Consequências

- EPG pode receber novos providers sem alterar a UI do sTv.
- Falha de download ou XMLTV vazio preserva o snapshot anterior.
- Credenciais presentes na URL XMLTV não são persistidas nem expostas em erros.
- O cache EPG é reconstruível e separado de favoritos, progresso e catálogo.
- Uma instalação ou atualização passa a distribuir cinco add-ons ativos.
