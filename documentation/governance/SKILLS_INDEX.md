# Catálogo de Skills e Procedimentos Operacionais do sKodi

Este documento descreve as skills operacionais e fluxos de trabalho especializados utilizados no desenvolvimento, teste, governança e manutenção do ecossistema **sKodi**.

---

## 1. Skills Nativas do Ecossistema

### `antigravity-guide`
- **Finalidade:** Guia canônico, referência rápida e mapa de comandos do ambiente Antigravity, slash commands (`/goal`, `/schedule`, `/learn`, `/grill-me`), CLI e extensões.
- **Uso no Projeto:** Consulta de boas práticas de execução autônoma, automação de tarefas longas e diretrizes de ciclo de vida.

### `agy-customizations`
- **Finalidade:** Estruturação de regras (`rules/`), sidecars e diretrizes operacionais de agentes.
- **Uso no Projeto:** Mantém a conformidade com as regras de autonomia total (`autonomous-operation.md`), pré-autorização irrestrita e isolamento de segredos no arquivo `C:\dev\.env`.

---

## 2. Ferramentas e Procedimentos Operacionais Locais (`tools/`)

| Script / Ferramenta | Responsabilidade | Como Executar |
| :--- | :--- | :--- |
| **`tools/bootstrap_artwork.py`** | Sincroniza e distribui os 9 ícones HD de `sArtwork` (`resource.images.saile`) e os ícones locais (`icon.png`/`fanart.jpg`) para todos os add-ons do ecossistema. | `python tools/bootstrap_artwork.py` |
| **`tools/validate_addons.py`** | Validação estática de XML (`addon.xml`, `settings.xml`), presença de artwork obrigatório e integridade estrutural de cada add-on. | `python tools/validate_addons.py` |
| **`tools/secret_scan.py`** | Auditoria de segurança em arquivos versionáveis para garantir zero exposição de credenciais, tokens ou chaves de API. | `python tools/secret_scan.py` |
| **`tools/build_repo.py`** | Compacta os add-ons em ZIPs com compressão nível 9, calcula checksums SHA256/MD5, gera `addons.xml`, `addons.xml.gz` e constrói o portal estático no GitHub Pages (`docs/`). | `python tools/build_repo.py` |
| **`tools/generate_structure_manifest.py`** | Gera o manifesto estrutural de rastreabilidade de arquivos (`STRUCTURE_MANIFEST.json`). | `python tools/generate_structure_manifest.py` |
| **`tools/print_tree.py`** | Gera a árvore canônica de arquivos do projeto em `documentation/generated/TREE_FINAL.txt`. | `python tools/print_tree.py` |

---

## 3. Pipeline de Verificação Completo

Antes de qualquer release ou commit final, execute o pipeline sequencial de garantia de qualidade:

```powershell
# 1. Distribuir artwork HD
python tools/bootstrap_artwork.py

# 2. Validar sintaxe e integridade dos add-ons
python tools/validate_addons.py

# 3. Executar auditoria de segredos
python tools/secret_scan.py

# 4. Executar suíte de 78 testes automatizados
python -m unittest discover -s tests -p "test_*.py" -v

# 5. Construir repositório Kodi e portal estático
python tools/build_repo.py

# 6. Atualizar manifestos e árvore de arquivos
python tools/generate_structure_manifest.py
python tools/print_tree.py
```
