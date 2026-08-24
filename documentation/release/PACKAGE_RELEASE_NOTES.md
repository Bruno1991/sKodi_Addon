# Notas de Release do Ecossistema sKodi (V2 - IPTV Focus)

## Versões Ativas dos Componentes

| Add-on ID | Nome | Versão | Destaques da Versão |
| :--- | :--- | :--- | :--- |
| **`plugin.video.stv`** | **sTv** | **`0.7.8`** | Promoção exclusiva no 1º nível dos canais presentes na grade oficial EPG com logos HD transparentes, preservação dos canais fora da grade em suas pastas de categorias originais, e Agora/Próximo em tempo real. |
| **`script.module.saile.epg`** | **sEPG** | **`1.3.0`** | Integração completa com a API Oficial da Claro TV+ (AVSClient v1.2) como fonte da verdade, logos em alta resolução, limpeza automática do banco de dados legado e matching avançado de aliases de canais. |
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

### 3. 🖼️ Interface Visual InfoWall (View 54) e Proporções Naturais
- Enquadramento profissional em modo InfoWall 54 em 100% das telas (`Home`, `Seções`, `Categorias`, `Séries`, `Temporadas`, `Episódios`, `Busca` e `Favoritos`).
- Dicionário de artes preciso: ícones e logos de canais preservam proporções nativas sem corte/zoom, e pôsteres reais são aplicados a Filmes, Séries e Temporadas.
- Preservação da pilha de navegação (`cacheToDisc=True`), impedindo que o Kodi reverta a visualização para Lista ao retornar (`Back`).

### 4. 🏷️ Identidade de Marca Padronizada
- Padronização de nomes sob o prefixo `s`: `sTv`, `sEPG`, `sArtwork`, `sCore` e `sRepo`.
- Documentação, manifestos XML, HTML do portal e logs totalmente alinhados.

---

## Validação e Qualidade

- **Testes Unitários:** 80/80 testes automatizados aprovados (100% de sucesso).
- **Auditoria de Segurança:** 0 credenciais ou segredos em arquivos versionáveis.
- **Deploy:** Repositório estático atualizado com checksums SHA256/MD5 e XMLs gzip em `docs/`.
