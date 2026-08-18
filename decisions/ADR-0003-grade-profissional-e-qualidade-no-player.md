# ADR-0003 — Grade profissional e qualidade no player

- Status: aceito
- Data: 2026-08-18

## Contexto

Uma plataforma de TV apresenta canal, programa atual, próximo programa e progresso sem obrigar o usuário a escolher entre URLs técnicas. Os streams Xtream do sTv são URLs independentes por resolução, não faixas de um único manifesto adaptativo.

## Decisão

Manter o contrato InfoWall 54 e enriquecer cada canal lógico com uma segunda linha, painel Agora/Próximo, horários, descrição e propriedades de progresso. A programação de todos os cards é lida em lote do SQLite local.

Qualidade máxima e limite de banda ficam em uma categoria própria das configurações do sTv. No clique, o seletor escolhe a melhor variante estável permitida e informa a resolução escolhida ao `ListItem` do player.

Não simular múltiplas resoluções no menu nativo do player. A API Python permite descrever streams do item resolvido, mas não associar várias URLs Xtream independentes a opções de resolução do OSD. Troca contínua será considerada somente com manifesto HLS/DASH adaptativo real ou integração PVR/InputStream tecnicamente comprovada.

## Consequências

- grade rápida e consistente com controle remoto;
- nenhum `get_now_next` por card;
- card sem horário continua visível como `Programação indisponível`;
- alteração de qualidade vale para a próxima reprodução;
- a reprodução atual não troca de URL no meio do stream;
- nenhum serviço em segundo plano é introduzido.

## Referências oficiais

- Kodi Python `ListItem`: https://xbmc.github.io/docs.kodi.tv/master/kodi-dev-kit/group__python__xbmcgui__listitem.html
- Kodi Python `VideoStreamDetail`: https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d4/d2c/group__python__xbmc__videostreamdetail.html
