# Inventário do pacote V2 (IPTV Focus)

## Resumo

- Add-ons ativos: **4**
- Artes fixas compartilhadas: **9** (5 comuns + 4 sTv)
- Testes unitários: **23**
- ZIPs Kodi gerados em `docs/zips/`: **4**
- Manifesto estrutural de referência: `STRUCTURE_MANIFEST.json`
- Relatório de estado atual: `STATE.md`

## Add-ons Ativos

- `plugin.video.stv` (v0.3.5): Add-on principal de IPTV/Xtream (TV ao Vivo, VOD, Séries, Favoritos, TMDB, Controle Parental).
- `repository.srepo` (v1.0.0): Repositório oficial para Kodi (distribuição via GitHub Pages).
- `resource.images.saile` (v1.0.0): Recurso com 9 ícones de interface compartilhados.
- `script.module.saile.core` (v1.0.0): Infraestrutura Python comum estável.

## Decisões Incorporadas

- `resource.images.saile` centraliza exatamente 9 artes fixas em PNG.
- `script.module.saile.core` provê apenas caminhos portáveis, artwork, notificações, erros e capabilities.
- Contrato imutável de navegação do sTv:
  - Home: `TV ao Vivo` → `VOD` → `Séries` → `Sincronizar Dados`.
  - Seções: `Buscar` → `Favoritos` → conteúdo dinâmico.
- Sincronização LAN é manual sob demanda e não compartilha SQLite bruto.
- Separação hierárquica das séries por pastas de temporadas (`Temporada 1`, `Temporada 2`, etc.).
- Modo InfoWall (54) padronizado em todas as telas com visual de cinema.
- Controle parental com PIN numérico de até 6 dígitos e bloqueio de configurações.
- Integração nativa de chave do TMDB v3.

## Validações Executadas

```text
4 add-ons válidos
9 artes compartilhadas válidas
23 testes unitários aprovados
0 segredos conhecidos encontrados
4 ZIPs Kodi gerados
```

## Ferramentas Operacionais

- `tools/bootstrap_artwork.py`: Copia e sincroniza ícones e fanarts do manifest.
- `tools/select_artwork.py`: Seleção e geração dinâmica de estilos de artwork.
- `tools/validate_addons.py`: Validação estática de `addon.xml`, `settings.xml` e artwork.
- `tools/secret_scan.py`: Auditoria de credenciais e tokens em arquivos versionáveis.
- `tools/build_repo.py`: Empacotamento de ZIPs, geração de `addons.xml`, MD5, SHA256 e HTML.
- `tools/generate_structure_manifest.py`: Geração do `STRUCTURE_MANIFEST.json`.
- `tools/print_tree.py`: Geração da árvore do projeto (`TREE_FINAL.txt`).
