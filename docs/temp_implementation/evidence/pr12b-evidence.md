# Evidência Técnica de Implementação — PR-12b

**Data:** 2026-09-27  
**PR:** PR-12b — `fix(install): one-liner funcional, versão fixada honesta e remoção de órfãos sem heurística`  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commit Base:** `a1dc3ba` (Handoff 041 — Revisão PR-11b/PR-12 e Despacho PR-12b)  
**Status:** IMPLEMENTADO E SUBMETIDO PARA REVISÃO  

---

## 1. Resumo Executivo das Correções

O PR-12b resolve em definitivo todos os apontamentos levantados no [Handoff 041](../handoffs/handoff-041-revisao-pr11b-pr12-despacho-pr12b.md):

1. **AO2 (One-Liner Funcional via Pipe / Stdin)**:
   - Em `install.sh`, a guarda de execução foi corrigida de `if [[ "${BASH_SOURCE[0]}" == "${0}" ]]` para `if [[ ${#BASH_SOURCE[@]} -eq 0 || "${BASH_SOURCE[0]}" == "${0}" ]]`.
   - Sob `set -u`, execuções via pipe (`curl ... | bash` ou `cat install.sh | bash`) não mais abortam com `BASH_SOURCE[0]: unbound variable`.
   - Garante que a execução via pipe invoca `main "$@"` e propaga exit codes de erro em caso de falha, sem nunca sair com código 0 silencioso.
2. **AO3 (Resolução Estrita de Árvore Local vs. Versão Fixada)**:
   - A árvore local em `setup_source_directory` agora só é ativada quando o script roda comprovadamente a partir de um arquivo físico (`[[ ${#BASH_SOURCE[@]} -gt 0 && -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]`), com caminho resolvido por `dirname "${BASH_SOURCE[0]}"`.
   - Execuções via pipe nunca assumem árvore local, mesmo se o diretório de trabalho atual contiver um clone do CEH.
   - Quando `CEH_VERSION` é informado em execução de arquivo local, o instalador emite aviso explícito no log (`log_warn`) alertando sobre o uso da árvore local.
   - `README.md` e `README_PT.md` atualizados para publicar a URL fixada na tag (`https://raw.githubusercontent.com/.../v1.3.0/install.sh | CEH_VERSION=1.3.0 bash`), com aviso de ativação pós-publicação da tag `v1.3.0`.
3. **AO1 (Fonte Única de Limpeza de Aliases sem Heurística `\.sh`)**:
   - Criado [`clearer-engineering/scripts/rc_aliases.py`](../../../clearer-engineering/scripts/rc_aliases.py), consolidando toda a lógica de instalação, atualização e desinstalação de aliases em um único módulo canônico compartilhado por `install.sh` e `uninstall.sh`.
   - Eliminada completamente a heurística de regex `(detect|setup-branches|preflight|...)\.sh`.
   - Um alias órfão só é removido se casado no início de linha (`^alias <nome>=`), pertencer ao conjunto de nomes conhecidos do CEH, e seu valor for idêntico a `aliases.sh` ou contiver as assinaturas canônicas `--agent clearer-harness` ou `plugins/clearer-engineering/`.
   - Aliases customizados do usuário terminando em `.sh` (ex: `alias ceh-help='bash ~/bin/help.sh'`) permanecem 100% intactos byte a byte.
   - Fixture de `cluster3_acceptance.py` atualizada para caminhos reais históricos com `plugins/clearer-engineering/`.
4. **AO4 (Honestidade Documental e Alinhamento ao ADR 007)**:
   - [`CHANGELOG.md`](../../../CHANGELOG.md) revisado para eliminar alegações hiperbólicas ("inviolable", "non-tamperable", "zero-tolerance").
   - Descrição sóbria e técnica da proteção em profundidade do diretório `.ceh/`, com explicitação de que a garantia primária reside na branch protection e nos status checks obrigatórios do servidor de CI (ADR 007).
5. **AO5 (Validação Byte a Byte com `cmp` no Teste AN1)**:
   - Asserção do sub-teste AN1 em `run-install-verification.sh` refatorada para utilizar `cmp -s`, garantindo preservação de quebras de linha exatas sem truncamento de substituição de comando `$(cat ...)`.
6. **Aviso Normativo de Versão**:
   - A tag `v1.3.0` **NÃO** foi criada pelo agente (decisão e prerrogativa exclusiva do mantenedor após o merge).

---

## 2. Matriz de Testes Normativos (`OBSERVED`)

Execução de `clearer-engineering/tests/run-install-verification.sh`:

| Bloco | Cenário Avaliado | Resultado Observado (`OBSERVED`) | Status |
|---|---|---|---|
| **Teste 1** | Idempotência de Instalação | Instalar 2x consecutivas preserva exatamente 1 bloco delimitado. | **PASS** |
| **Teste 2** | Simetria Byte a Byte | Instalar seguido de uninstall restaura os arquivos rc idênticos aos originais. | **PASS** |
| **Teste 2b (AN1)** | Uninstall Seguro: prefixo editado | `export A=1` sem `\n` preservado byte a byte via `cmp -s` (AO5). | **PASS** |
| **Teste 2b (AO1)** | Uninstall Seguro: aliases customizados com `.sh` | `alias ceh-help='bash ~/bin/help.sh'` preservado byte a byte (AO1). | **PASS** |
| **Teste 2b (AN2)** | Uninstall Seguro: comentários do usuário | `# alias ceh=antigo` e `export B=2` preservados intactos. | **PASS** |
| **Teste 2b (Órfão)** | Uninstall Seguro: alias órfão legítimo | `alias ceh-help='bash .../plugins/clearer-engineering/...'` removido limpo. | **PASS** |
| **Teste 2b (AN3)** | Uninstall Seguro: fail-closed | Mock python3 com falha resulta em código de saída não-zero sem falso sucesso. | **PASS** |
| **Teste 3** | Integridade dos Aliases | Todos os aliases apontam para arquivos existentes na árvore instalada. | **PASS** |
| **Teste 4** | Validação Honesta | Falha do `agy plugin validate` retorna código 42; exit 0 com `--skip-diagnostics`. | **PASS** |
| **Teste 5.1** | One-Liner (Pipe) simples sem rede | `cat install.sh \| bash` instala com exit 0 e clone sem `--branch`. | **PASS** |
| **Teste 5.2** | One-Liner (Pipe) com `CEH_VERSION=1.3.0` | Clone invocado com `--branch v1.3.0`. | **PASS** |
| **Teste 5.3** | One-Liner (Pipe) com `CEH_VERSION=v1.3.0` | Normalização de prefixo `v` sem duplicar (`v1.3.0`). | **PASS** |
| **Teste 5.4** | Pipe dentro de clone com `CEH_VERSION` | Clona versão fixada pedida sem ignorar silenciosamente em favor da pasta local. | **PASS** |
| **Teste 5.5** | Execução de arquivo local com `CEH_VERSION` | Emite aviso explícito (`log_warn`) no log. | **PASS** |

---

## 3. Provas Físicas de Falsificabilidade

### 3.1 Prova AO2 (Mutação em `install.sh`)
- **Linha Mutada:** Substituição de `if [[ ${#BASH_SOURCE[@]} -eq 0 || "${BASH_SOURCE[0]}" == "${0}" ]]` por `if [[ "${BASH_SOURCE[0]}" == "${0}" ]]`.
- **Resultado Observado:**
```text
[5/5] Teste 5: One-Liner (Pipe) e Versão Fixada Sem Rede (AO2 / AO3)...
ERRO AO2: 'cat install.sh | bash' falhou com exit code 1
```
- **Conclusão:** O teste 5.1 captura a regressão e falha com código 1.

### 3.2 Prova AO1 (Mutação em `clearer-engineering/scripts/rc_aliases.py`)
- **Linha Mutada:** Reintrodução da heurística `re.search(r'(detect|setup-branches|...)\.sh', val) is not None`.
- **Resultado Observado:**
```text
[2b/4] Teste 2b: Uninstall Seguro (AN1: prefixo editado; AN2: comentários/aliases customizados; AN3: fail-closed)...
  • [PASS] AN1: Caracteres do usuário preservados após edição do prefixo (validação byte a byte cmp).
ERRO AO1: install/uninstall removeu ou modificou aliases do usuário terminando em .sh!
--- /tmp/ceh-verify-xYFkvq/home_ao1/.bashrc.expected    2026-09-27 10:26:00.012361517 -0300
+++ /tmp/ceh-verify-xYFkvq/home_ao1/.bashrc     2026-09-27 10:26:00.822907916 -0300
@@ -1,4 +1,2 @@
 export FOO=bar
-alias ceh-help='bash ~/bin/help.sh'
-alias ceh-monitor='bash ~/tools/monitor.sh'
 export BAZ=qux
```
- **Conclusão:** O teste 2b captura a regressão e rejeita a mutação com código 1.
