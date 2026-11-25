# Notas de Release do Ecossistema sKodi

## Versões Ativas dos Componentes

| Add-on ID | Nome | Versão | Destaques da Versão |
| :--- | :--- | :--- | :--- |
| **`plugin.video.stv`** | **sTv** | **`0.8.8`** | Resolução de EPG em lote sem N+1, bloqueio de esquemas não-HTTP e limite de memória, controle parental por categoria em Busca/Favoritos, sincronização LAN de favoritos de canais e sanitização de erros na UI. |
| **`plugin.audio.sradio`** | **sRadio** | **`1.0.6`** | Proteção HTTP contra esquemas inválidos e respostas gigantes, correção de handle em falha de stream e cancelamento limpo do teclado de busca. |
| **`script.module.saile.epg`** | **sEPG** | **`1.4.5`** | Resolução de canais EPG em lote (`resolve_channels_many` em 1 conexão SQLite), preservação de cache em falha de rede e guards defensivos na API Claro TV+. |
| **`resource.images.saile`** | **sArtwork** | **`1.0.4`** | 20 ícones fixos compartilhados originais em alta definição (`common/` e `stv/`). |
| **`script.module.saile.core`** | **sCore** | **`1.0.3`** | Infraestrutura base Python compartilhada com sanitização centralizada de mensagens de erro sem exposição de URLs ou credenciais. |
| **`repository.srepo`** | **sRepo** | **`1.1.1`** | Repositório estático Kodi para distribuição contínua e auto-updates via GitHub Pages. |

---

## Principais Recursos e Melhorias Implementadas

### 1. 🗄️ Persistência de Dados e Performance (Schema v8)
- **Migração Transacional:** Schema SQLite v8 com migração retroativa e não-destrutiva de versões anteriores.
- **Covering Indexes:** Criação de índices especializados (`idx_favorites_order`, `idx_categories_order`, `idx_media_items_normalized`, `idx_media_items_category`) que eliminam `TEMP B-TREE` em ordenações no Kodi.
- **Manutenção Automática:** Execução de `PRAGMA optimize` ao término de sincronizações de catálogo e EPG.
- **Isolamento de Bancos:** `stv.db` para catálogo e estado do usuário; `epg.db` para guia de programação e cache transitório.

### 2. 🔄 Sincronização Inteligente em Background (Catálogo, EPG e LAN)
- **Motor de Aliases & Correspondência EPG:** Reconhecimento automático de canais de qualquer operadora IPTV (Globo RJ/SP/MG/DF/RS/BA, TC Pipoca/Action/Premium, PFC/Premiere 1..8, SporTV 1..3, Warner, Sony, etc.).
- **Sincronização Dinâmica Claro TV+:** Puxa 160+ canais e ~8.400 programas diretamente da API com 36h de grade em alta velocidade.
- **Catálogo com TTL:** Verificação não-bloqueante na Home e seções com atualização em background thread (Live, VOD e Séries).
- **EPG com TTL:** Guia de programação atualizado silenciosamente em background thread com janela de 36 horas.
- **Sincronização em LAN Zero-Config:** Descoberta UDP peer-to-peer (porta 54242) com troca e mesclagem de favoritos entre dispositivos Kodi na mesma rede local.
- **Menu 'Sincronizar Dados' Completo:** Opções manuais para Sincronizar Tudo, Catálogo, EPG, LAN, Exportar Backup, Importar Backup e Limpar Cache.

### 3. 🖼️ Interface Visual InfoWall (View 54) e Proporções Naturais
- Enquadramento profissional em modo InfoWall 54 em 100% das telas (`Home`, `Seções`, `Categorias`, `Séries`, `Temporadas`, `Episódios`, `Busca` e `Favoritos`).
- Dicionário de artes preciso: ícones e logos de canais preservam proporções nativas sem corte/zoom, e pôsteres reais são aplicados a Filmes, Séries e Temporadas.
- Preservação da pilha de navegação (`cacheToDisc=True`), impedindo que o Kodi reverta a visualização para Lista ao retornar (`Back`).

### 4. 🏷️ Identidade de Marca Padronizada
- Padronização de nomes sob o prefixo `s`: `sTv`, `sEPG`, `sArtwork`, `sCore` e `sRepo`.
- Documentação, manifestos XML, HTML do portal e logs totalmente alinhados.

---

## Validação e Qualidade

- **Testes Unitários:** Suíte completa automatizada aprovada com 100% de sucesso (`pytest` e `ruff`).
- **Auditoria de Segurança:** 0 credenciais ou segredos em arquivos versionáveis.
- **Deploy:** Repositório estático atualizado com checksums SHA256/MD5 e XMLs gzip em `docs/`.
