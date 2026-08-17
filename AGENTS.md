# AGENTS.md — contrato operacional do agente

## Identidade do sistema

O agente trabalha no monorepo **sRepo**, que administra quatro add-ons ativos focados em IPTV/Xtream:

- `repository.srepo`: distribuição e atualização pelo GitHub Pages.
- `resource.images.saile`: nove artes fixas compartilhadas.
- `script.module.saile.core`: infraestrutura Python comum e sem regras de negócio.
- `plugin.video.stv`: IPTV/Xtream, vídeo, TMDB e estado local do sTv.

Itens condicionais ou futuros não devem ser criados sem ADR e prova técnica:
- `service.saile.monitor`: somente se houver necessidade comprovada de serviço contínuo.
- `repository.srepo.beta`, PVR avançado e sincronização automática: fora da V1.

## Ordem obrigatória de leitura

1. `PROJECT_CONSTITUTION.md`
2. `ROADMAP_ARCHITECTURE.md`
3. `REPOSITORY_BLUEPRINT.md`
4. `SECURITY_AND_ENV_POLICY.md`
5. ADRs e documentações técnicas
6. Skills aplicáveis em `.agents/`

## Fronteiras

- `.agents/` contém instruções e biblioteca corporativa; nunca código de produção dos plugins.
- `addons/` contém os add-ons instaláveis.
- `tools/` contém build, migração e validação.
- `docs/` é gerado e nunca editado manualmente.
- `.env` é somente desenvolvimento/administração e nunca entra no runtime ou ZIP.
- O core compartilhado não contém Xtream, TMDB ou regras de UI específicas do sTv.

## Contrato de navegação imutável

### sTv — home

1. TV ao Vivo
2. VOD
3. Séries
4. Sincronizar Dados

### sTv — dentro de TV ao Vivo, VOD e Séries

1. Buscar
2. Favoritos
3. Categorias e conteúdo dinâmico da seção

Não ordenar alfabeticamente, não ocultar esses atalhos por falta de dados e não colocar conteúdo dinâmico antes deles.

## Artwork

- Cada add-on mantém `icon.png` e `fanart.jpg` próprios.
- Os nove ícones fixos compartilhados vivem apenas em `resource.images.saile`.
- `common/`: `search.png`, `erro.png`, `check.png`, `sync.png`, `folder.png`.
- `stv/`: `live.png`, `vod.png`, `series.png`, `favoritos.png`.
- Pôsteres, logos, thumbnails e fanarts de conteúdo são dinâmicos e não entram nesse recurso.
- Emojis nunca substituem artwork.

## Sincronização LAN

- Sempre manual e iniciada pelo usuário no item `Sincronizar Dados`.
- Nunca ocorre automaticamente ao abrir, fechar ou navegar.
- Nunca compartilha o arquivo SQLite por SMB/NFS.
- Nunca transmite credenciais, cookies, tokens ou URLs temporárias.
- Sincroniza somente estado do usuário por registros versionados; catálogos e caches são reconstruídos localmente.

## Fluxo obrigatório por tarefa

1. Inspecionar os arquivos reais.
2. Produzir plano por arquivo e identificar riscos.
3. Implementar a menor mudança coerente.
4. Atualizar testes, docs e ADR quando necessário.
5. Executar validações reais.
6. Informar arquivos criados, modificados e removidos.
7. Distinguir claramente implementação concluída de scaffold ou decisão futura.

## Comandos mínimos de validação

```powershell
python tools/bootstrap_artwork.py
python tools/validate_addons.py
python tools/secret_scan.py
python -m unittest discover -s tests -p "test_*.py" -v
python tools/build_repo.py
```

## Proibições

- Não criar produção em `.agents`.
- Não inventar teste executado.
- Não apagar banco para resolver migração.
- Não adicionar backend próprio obrigatório.
- Não embutir `.env`, PAT GitHub, senha Xtream, cookie, token ou URL assinada.
- Não duplicar os nove ícones compartilhados dentro dos plugins.
- Não transformar sincronização LAN em rotina automática.
