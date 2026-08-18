# STATE.md — Estado Atual do Projeto sRepo / sTv

**Data de Atualização:** 18 de Agosto de 2026
**Status do Projeto:** Implementado e validado no host; reteste em Kodi pendente (sTv v0.6.0)
**Repositório GitHub:** [https://github.com/Bruno1991/sKodi_Addon](https://github.com/Bruno1991/sKodi_Addon)
**Repositório Kodi (GitHub Pages):** `https://bruno1991.github.io/sKodi_Addon/`

---

## 1. Inventário de Add-ons Ativos

| Add-on ID | Versão Atual | Descrição / Responsabilidade |
| :--- | :--- | :--- |
| **`plugin.video.stv`** | `0.6.0` | Add-on IPTV/Xtream com canais EPG promovidos, variantes automáticas, favoritos, TMDB, controle parental e InfoWall 54. |
| **`repository.srepo`** | `1.1.1` | Repositório oficial para instalação e atualizações automáticas via Kodi. |
| **`resource.images.saile`** | `1.0.3` | 9 ícones fixos compartilhados originais em alta definição. |
| **`script.module.saile.core`** | `1.0.0` | Módulo base Python (artwork, notificações, erros, capabilities). |
| **`script.module.saile.epg`** | `1.1.0` | XMLTV autorizado, fallback de EPG curto Xtream, matching público, UTC e cache independente. |

---

## 2. Status de Validação e Funcionalidades

### ✅ Itens Concluídos e Aprovados pelo Usuário
- **1º Nível (Home / Menu Principal)**: Apresentação em InfoWall (54) com os 4 itens fixos (`TV ao Vivo`, `VOD`, `Séries`, `Sincronizar Dados`) e artes oficiais em alta definição.
- **2º Nível (Seções e Submenus)**: Itens fixos (`Buscar`, `Favoritos`) e pastas de categorias dinâmicas com enquadramento perfeito.
- **Canais de TV ao Vivo**: Logos dos canais de TV ao vivo com proporção natural, centralizadas, nítidas e **100% livres de cortes ou zoom lateral**, com carregamento instantâneo.
- **VOD e Séries**: Cartazes 2:3 de cinema com metadados TMDB e fanarts.
- **Roteamento Estrutural**: Correção no roteamento de séries e temporadas (`series_info` e `series_episodes`).
- **Controle Parental**: Proteção com PIN de até 6 dígitos e teclado mascarado para conteúdos adultos e configurações.
- **EPG modular**: XMLTV primário e fallback manual `get_short_epg`; reteste com o provedor real ainda pendente.
- **TV ao vivo projetada pelo EPG**: uma entrada por canal sincronizado, variantes internas e categorias remanescentes apenas para itens sem EPG.
- **Episódios**: frame do próprio episódio priorizado nos slots de capa, thumb e landscape.

---

## 3. Comandos de Build e Validação

```powershell
python tools/bootstrap_artwork.py
python tools/validate_addons.py
python tools/secret_scan.py
python -m unittest discover -s tests -p "test_*.py" -v
python tools/build_repo.py
python tools/generate_structure_manifest.py
```

- **Testes Unitários:** 60/60 testes aprovados no host.
- **Scanner de Segredos:** Nenhum segredo ou chave privada exposta.
- **Repositório Kodi (`docs/`):** gerado com os 5 add-ons; smoke test em Kodi real fica para instalação pelo usuário.


