# ADR-0002 — Canais do EPG como projeção principal de TV ao vivo

- Status: aceito
- Data: 2026-08-18

## Contexto

Provedores Xtream frequentemente repetem o mesmo canal em categorias e stream IDs diferentes para SD, HD, FHD, 4K e backups. Exibir cada stream como canal obriga o usuário a escolher detalhes técnicos e dificulta o matching com o EPG.

## Decisão

Preservar o catálogo bruto no SQLite do sTv e construir uma projeção local derivada do snapshot EPG. Correspondências por `epg_id` exato ou nome normalizado único formam um canal lógico. O nome e o ícone do EPG são apresentados uma vez na raiz de TV ao Vivo; os streams Xtream tornam-se variantes internas.

Canais sem correspondência permanecem na categoria original. Uma categoria é ocultada somente quando há catálogo local suficiente para provar que todos os seus itens foram promovidos. Matching ambíguo nunca promove automaticamente.

No clique, o sTv aplica qualidade máxima, limite de banda com margem de segurança e uma sondagem curta das variantes candidatas. Não existe varredura durante a navegação nem serviço contínuo. O usuário pode escolher uma qualidade manualmente pelo menu de contexto.

## Consequências

- uma entrada visual por canal reconhecido pelo EPG;
- nomes regionais e IDs do guia permanecem distintos;
- menos diretórios e duplicatas na navegação;
- nenhum backend próprio ou conexão automática em segundo plano;
- a primeira reprodução pode ter pequeno custo de sondagem;
- streams independentes não trocam resolução de forma contínua como um manifesto HLS adaptativo;
- favoritos antigos por stream são absorvidos pelo favorito do canal lógico sem apagar outros estados.

## Evidências

- testes puros de agrupamento, ambiguidade, categorias remanescentes e seleção por banda;
- teste de projeção na raiz de TV ao Vivo;
- migração SQLite v7 preservando dados;
- smoke test em Kodi real ainda necessário.
