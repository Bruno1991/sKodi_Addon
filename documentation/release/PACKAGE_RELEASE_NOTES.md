# Notas de Release do Ecossistema sKodi (V2 - IPTV Focus)

## Versões Ativas dos Componentes

| Add-on ID | Nome | Versão | Destaques da Versão |
| :--- | :--- | :--- | :--- |
| **`plugin.video.stv`** | **sTv** | **`0.7.2`** | Preenchimento 100% de artes (poster, thumb, icon, tvshow.poster, season.poster), fixação do modo InfoWall (54) com preservação de cache de navegação (`cacheToDisc=True`), mediatypes padronizados, busca sem acentos, encerramento limpo de diretórios e integração completa com sEPG 1.2.1/TMDB. |
| **`script.module.saile.epg`** | **sEPG** | **`1.2.1`** | Preservação de todos os canais declarados mesmo sem programação atual, mescla de identidades Xtream ausentes do XMLTV, normalizador de termos de busca e exportações completas para sTv, timestamps UTC e cache SQLite independente. |
| **`resource.images.saile`** | **sArtwork** | **`1.0.3`** | Nove ícones fixos compartilhados originais em alta definição (5 comuns + 4 sTv). |
| **`script.module.saile.core`** | **sCore** | **`1.0.1`** | Infraestrutura base Python compartilhada (artwork, notificações, caminhos portáveis, erros padronizados, detecção de capabilities e metadados atualizados). |
| **`repository.srepo`** | **sRepo** | **`1.1.1`** | Repositório estático Kodi para distribuição contínua e auto-updates via GitHub Pages. |

---

## Principais Recursos e Melhorias Implementadas

### 1. 🗄️ Persistência de Dados e Performance (Schema v8)
- **Migração Transacional:** Schema SQLite v8 com migração retroativa e não-destrutiva de versões anteriores.
- **Covering Indexes:** Criação de índices especializados (`idx_favorites_order`, `idx_categories_order`, `idx_media_items_normalized`, `idx_media_items_category`) que eliminam `TEMP B-TREE` em ordenações no Kodi.
- **Manutenção Automática:** Execução de `PRAGMA optimize` ao término de sincronizações de catálogo e EPG.
- **Isolamento de Bancos:** `stv.db` para catálogo e estado do usuário; `epg.db` para guia de programação e cache transitório.

### 2. 🔍 Mecanismo de Busca Universal sem Acentos
- Busca inteligente com e sem acentos (ex: `pokemon` encontra `Pokémon`, `capitao` encontra `Capitão`, `america` encontra `América`).
- Indexação e normalização de `normalized_name` para todos os tipos de mídia (Live TV, VOD, Séries e Episódios).
- Motor híbrido com **FTS5 Unicode61** (`remove_diacritics 2`) e fallback dinâmico indexado.

### 3. 🖼️ Interface Visual InfoWall (View 54) e Pôsteres
- Enquadramento profissional em modo InfoWall em todas as telas (`Home`, `Seções`, `Categorias`, `Séries`, `Temporadas`, `Episódios`, `Busca` e `Favoritos`).
- Dicionário de artes completo com fallbacks automáticos em cascata para evitar cards vazios.
- Preservação da pilha de navegação (`cacheToDisc=True`), impedindo que o Kodi reverta a visualização para Lista ao retornar (`Back`).

### 4. 🏷️ Identidade de Marca Padronizada
- Padronização de nomes sob o prefixo `s`: `sTv`, `sEPG`, `sArtwork`, `sCore` e `sRepo`.
- Documentação, manifestos XML, HTML do portal e logs totalmente alinhados.

---

## Validação e Qualidade

- **Testes Unitários:** 78/78 testes automatizados aprovados (100% de sucesso).
- **Auditoria de Segurança:** 0 credenciais ou segredos em arquivos versionáveis.
- **Deploy:** Repositório estático atualizado com checksums SHA256/MD5 e XMLs gzip em `docs/`.
