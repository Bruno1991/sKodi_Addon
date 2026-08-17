# STATE.md — Estado Atual do Projeto sRepo / sTv

**Data de Atualização:** 17 de Agosto de 2026  
**Status do Projeto:** Estável / Operacional (v0.3.5)  
**Repositório GitHub:** [https://github.com/Bruno1991/sKodi_Addon](https://github.com/Bruno1991/sKodi_Addon)  
**Repositório Kodi (GitHub Pages):** `https://bruno1991.github.io/sKodi_Addon/`

---

## 1. Inventário de Add-ons Ativos

| Add-on ID | Versão Atual | Descrição / Responsabilidade |
| :--- | :--- | :--- |
| **`plugin.video.stv`** | `0.3.5` | Add-on principal de IPTV/Xtream (TV ao Vivo, VOD, Séries, Favoritos, TMDB, Controle Parental). |
| **`repository.srepo`** | `1.0.0` | Repositório oficial para instalação e atualizações automáticas via Kodi. |
| **`resource.images.saile`** | `1.0.0` | 9 ícones fixos compartilhados em alta definição. |
| **`script.module.saile.core`** | `1.0.0` | Módulo base Python (artwork, notificações, erros, capabilities). |

---

## 2. Funcionalidades Desenvolvidas e Validadas

### 🛡️ 1. Controle Parental Completo
- **Detecção Híbrida**: Reconhece termos restritos/adultos (`XXX`, `Adulto`, `+18`, `18+`, `Porn`, `Playboy`, `Sexy`, `Venus`, etc.) com normalização de acentos + classificação `adult` nativa do TMDB.
- **PIN Numérico até 6 Dígitos**: Utiliza o diálogo numérico nativo com máscara oculta (`***`), ideal para controle remoto de TV.
- **Proteção Sob Demanda**: Bloqueia abertura de categorias e reprodução de canais/vídeos adultos até que a senha seja digitada.
- **Proteção do Menu de Configurações**: Tranca automaticamente as configurações do sTv com o mesmo PIN cadastrado.
- **Cadastro Inicial Amigável**: Na primeira tentativa de acesso sem senha, solicita cadastro e confirmação do PIN.

### 🎬 2. TMDB 100% Automático
- Chave pública oficial padrão incorporada internamente no cliente TMDB.
- Eliminada a necessidade de digitação manual de token longo nas configurações.

### ▶️ 3. Reprodução Instantânea e Player
- Resolução direta de streaming via `xbmcplugin.setResolvedUrl(handle, succeeded=True, listitem)`.
- Eliminação do spinner/círculo de carregamento preso na tela.

### 🖼️ 4. Padronização Visual InfoWall (ViewMode 54)
- **Home**: Cards do InfoWall verticais elegantes com ícones centralizados (`live.png`, `vod.png`, `series.png`, `sync.png`).
- **VOD & Séries**: Posters oficiais 2:3 de cinema em alta resolução com backdrop (`fanart`) e sinopses completas.
- **TV ao Vivo**: Mapeamento uniforme em InfoWall com logos e miniaturas de canais centralizados e nítidos.

### 📚 5. Séries Organizadas por Temporadas
- Navegação em dois níveis: **Série → Lista de Pastas de Temporadas (`Temporada 1`, `Temporada 2`, etc.) → Lista de Episódios da Temporada Selecionada**.
- Fim da sobrecarga de episódios misturados em uma lista única.

### ⚡ 6. Banco de Dados SQLite & Busca FTS5
- Tabela virtual `media_items_fts` com triggers de sincronização e busca textual ultra-rápida.
- Suporte a cache com TTL configurável (6h, 12h, 24h, 48h).

---

## 3. Comandos de Build e Validação Executados

```powershell
python tools/bootstrap_artwork.py
python tools/validate_addons.py
python tools/secret_scan.py
python -m unittest discover -s tests -p "test_*.py" -v
python tools/build_repo.py
python tools/generate_structure_manifest.py
python tools/print_tree.py
```

- **Testes Unitários:** 23/23 testes aprovados.
- **Scanner de Segredos:** Nenhum segredo ou chave privada exposta.
- **Manifesto e Árvore:** Sincronizados com `STRUCTURE_MANIFEST.json` e `TREE_FINAL.txt`.

---

## 4. Onde Paramos e Próximos Passos para Amanhã

1. **Ponto de Parada**:
   - Todo o código está comitê e publicado na versão **`0.3.5`**.
   - A interface, controle parental, player e organização de temporadas estão funcionando com estabilidade.

2. **Planejamento para a Próxima Sessão**:
   - Validação da experiência de uso real no Kodi após a navegação por temporadas.
   - Sincronização LAN manual (exportação/importação de estado de favoritos e progresso de reprodução entre dispositivos).
   - Melhorias de EPG / Guia de Programação para TV ao Vivo caso requisitado.
