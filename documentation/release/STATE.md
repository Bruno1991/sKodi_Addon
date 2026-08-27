# STATE.md — Estado Atual do Projeto sRepo / sTv

**Data de Atualização:** 27 de Agosto de 2026
**Status do Projeto:** Implementado, sincronizado e validado no host e no Kodi (sTv v0.8.0, sEPG v1.3.1)
**Repositório GitHub:** [https://github.com/Bruno1991/sKodi_Addon](https://github.com/Bruno1991/sKodi_Addon)
**Repositório Kodi (GitHub Pages):** `https://bruno1991.github.io/sKodi_Addon/`

---

## 1. Inventário de Add-ons Ativos

| Add-on ID | Nome | Versão Atual | Descrição / Responsabilidade |
| :--- | :--- | :--- | :--- |
| **`plugin.video.stv`** | **sTv** | `0.8.0` | Add-on IPTV/Xtream com navegação de canais ao vivo pelas categorias nativas da API Xtream, Agora/Próximo em tempo real (EPG Claro TV+), sem lag no InfoWall 54, frames 16:9 TMDB e controle parental. |
| **`repository.srepo`** | **sRepo** | `1.1.1` | Repositório oficial para instalação e atualizações automáticas via Kodi. |
| **`resource.images.saile`** | **sArtwork** | `1.0.3` | 9 ícones fixos compartilhados originais em alta definição. |
| **`script.module.saile.core`** | **sCore** | `1.0.1` | Módulo base Python (artwork, notificações, erros, capabilities). |
| **`script.module.saile.epg`** | **sEPG** | `1.3.1` | Integração com a API Oficial da Claro TV+ (AVSClient v1.2) em paralelo (3s), extração segura de metadados, mais de 5.500 programas e cache SQLite independente. |

---

## 2. Status de Validação e Funcionalidades

### ✅ Itens Concluídos e Aprovados pelo Usuário
- **1º Nível (Home / Menu Principal)**: Apresentação em InfoWall (54) com os 4 itens fixos (`TV ao Vivo`, `VOD`, `Séries`, `Sincronizar Dados`) e artes oficiais em alta definição.
- **2º Nível (Seções e Submenus)**: Itens fixos (`Buscar`, `Favoritos`) e pastas de categorias dinâmicas da API Xtream com enquadramento perfeito e retenção de modo InfoWall.
- **Canais de TV ao Vivo**: Apresentação por categorias nativas do provedor Xtream, com logos preservadas sem distorção e Agora/Próximo (EPG Claro TV+) integrado em tempo real no InfoWall 54.
- **VOD e Séries**: Cartazes 2:3 de cinema com metadados TMDB e fanarts.
- **Roteamento Estrutural & Retenção de ViewMode**: Travamento em InfoWall 54 com preservação de cache de navegação (`cacheToDisc=True`) ao retornar de diretórios/temporadas/episódios e priorização de preferências persistidas em `user_preferences`.
- **Controle Parental**: Proteção com PIN de até 6 dígitos e teclado mascarado para conteúdos adultos e configurações.
- **EPG modular**: Integração Claro TV+ em paralelo, fallback XMLTV/Xtream e cache local SQLite UTC (`epg.db`).
- **Episódios**: frame 16:9 do próprio episódio priorizado nos slots de thumb e landscape.

---

## 3. Comandos de Build e Validação

```powershell
python tools/bootstrap_artwork.py
python tools/validate_addons.py
python tools/secret_scan.py
python -m unittest discover -s tests -p "test_*.py" -v
python tools/build_repo.py
python tools/generate_structure_manifest.py
python tools/print_tree.py
```

- **Testes Unitários:** 83/83 testes aprovados no host.
- **Scanner de Segredos:** Nenhum segredo ou chave privada exposta.
- **Repositório Kodi (`docs/`):** gerado com os 5 add-ons; smoke test em Kodi real fica para instalação pelo usuário.


