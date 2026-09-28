# PR-QA-C / PR-QA-C2 — Evidência de Implementação e Verificação (`OBSERVED`)

**Data/Hora:** 2026-09-28T07:15:00-03:00  
**PR:** PR-QA-C2 (`test(gate): contrato de opções executável v1.1.0 e validação estrita de help (C01)`)  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Linha de Base Homologada:** `d4bb909` (Handoff 049)  
**Status da Suíte Canônica Local:** **60/60 testes aprovados (100% PASS)**  
**Certificado de CI:** Emitido em `.ceh/last-ci-run.json`  
**CI do Servidor (GitHub Actions):** [Run 36369910415](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36369910415) e [Run 36371154717](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36371154717) (4/4 jobs concluídos com sucesso em ambas as runs: Ubuntu/macOS × Python 3.9/3.12)  

---

## 1. Escopo e Objetivos do PR-QA-C2 (Resolução do Handoff 050 / C01)

Conforme apontado no [Handoff 050](../handoffs/handoff-050-revisao-prqa-c.md), o PR-QA-C2 resolve as seguintes lacunas:
1. **Contrato Dirige a Execução dos Testes (Resolução C01):**
   - O arquivo `write_options.json` foi elevado para a versão **1.1.0**, passando a ser a fonte de verdade dinâmica de execução de todos os testes de gate.
   - Foram eliminadas as listas manuais hardcoded em `test_help_contract.py`. O teste itera compulsoriamente sobre cada opção de escrita e cada leitura pura registradas no JSON.
2. **Precisão Estrita da Fonte (`--help` Real):**
   - Removida a entrada `--output-directory` de `git-diff` e `-o` de `git-log`, que não existem no help dos respectivos comandos.
   - Implementada normalização de terminal (`_\b` do `less`) e verificação linha a linha: o teste agora valida que o `help_snippet` existe fisicamente na `help_line` indicada do arquivo versionado em `docs/temp_implementation/evidence/help-contracts/`.
3. **Comandos de Teste Declarados por Opção:**
   - Toda opção de escrita declara explicitamente sua lista `test_commands`, avaliada nos três ambientes (`development`, `staging`, `production`) sob exigência inegociável de `(deny, CERTIFICATE_INTEGRITY)`.
   - Toda leitura pura declara sua lista `pure_read_test_commands`, avaliada nos três ambientes sob `(allow, GENERAL)`.

---

## 2. Inventário de Comandos e Contrato de Opções v1.1.0 (`OBSERVED`)

| Comando / Subcomando | Arquivo de Help | Versão Capturada | Opções de Gravação / Execução | Linhas Citadas no Help | Snippet no Help | Bloqueio no Gate |
|---|---|---|---|---|---|---|
| `cat` | `cat.txt` | cat 9.4 | Nenhuma | — | — | Leitura pura. |
| `less` | `less.txt` | less 633 | `-o`, `-O`, `--log-file`, `--LOG-FILE` | 171, 173 | `-o [file]`, `-O [file]`, `--log-file=[file]`, `--LOG-FILE=[file]` | Bloqueado quando visa `.ceh/`. |
| `more` | `more.txt` | more 2.39.3 | Nenhuma | — | — | Leitura pura. |
| `head` | `head.txt` | head 9.4 | Nenhuma | — | — | Leitura pura. |
| `tail` | `tail.txt` | tail 9.4 | Nenhuma | — | — | Leitura pura. |
| `jq` | `jq.txt` | jq-1.7.1 | Nenhuma (stdout apenas) | — | — | Leitura/transformação em stdout. |
| `grep` | `grep.txt` | grep 3.11 | Nenhuma | — | — | Leitura pura em stdout. |
| `egrep` | `egrep.txt` | grep 3.11 | Nenhuma | — | — | Leitura pura em stdout. |
| `fgrep` | `fgrep.txt` | grep 3.11 | Nenhuma | — | — | Leitura pura em stdout. |
| `ls` | `ls.txt` | ls 9.4 | Nenhuma | — | — | Leitura pura de metadados. |
| `stat` | `stat.txt` | stat 9.4 | Nenhuma | — | — | Leitura pura de metadados. |
| `wc` | `wc.txt` | wc 9.4 | Nenhuma | — | — | Leitura pura de contagem. |
| `du` | `du.txt` | du 9.4 | Nenhuma | — | — | Leitura pura de uso em disco. |
| `diff` | `diff.txt` | diff 3.10 | Nenhuma (stdout apenas) | — | — | Leitura pura em stdout. |
| `git status` | `git-status.txt` | git 2.43.0 | Nenhuma | — | — | Leitura pura de estado. |
| `git log` | `git-log.txt` | git 2.43.0 | `--output`, `--ext-diff`, `--textconv` | 2304, 3126, 3136 | `--output=<file>`, `--ext-diff`, `--textconv, --no-textconv` | Bloqueados quando visam `.ceh/`. |
| `git diff` | `git-diff.txt` | git 2.43.0 | `--output`, `--ext-diff`, `--textconv` | 170, 994, 1004 | `--output=<file>`, `--ext-diff`, `--textconv, --no-textconv` | Bloqueados quando visam `.ceh/`. |
| `git show` | `git-show.txt` | git 2.43.0 | `--output`, `--ext-diff`, `--textconv` | 994, 1816, 1826 | `--output=<file>`, `--ext-diff`, `--textconv, --no-textconv` | Bloqueados quando visam `.ceh/`. |
| `python3 -m json.tool` | `python-json-tool.txt` | Python 3.12.3 | `[outfile]` (posicional opcional) | 16 | `outfile            write the output of infile to outfile` | Bloqueado quando visa `.ceh/`. |

---

## 3. Saída das Redes Diferenciais (`OBSERVED`)

### 3.1 `test_gate_differential_fuzz.py` (Fuzz Diferencial contra Baseline `d4bb909`)
- **Total de Comandos Avaliados:** 4.035 comandos avaliados nos 3 ambientes (`development`, `staging`, `production`), totalizando **12.105 casos**.
- **Resultado:** 4/4 testes aprovados (`OK`), 17.01s (meta < 20s).
- **Relaxamentos Detectados:** **0 (zero)**. A baseline `d4bb909` já contém os relaxamentos AM2 e o arquivo `relaxamentos_justificados.txt` encontra-se zerado.
- **Invariante:** Nenhuma nova brecha ou relaxamento espúrio foi introduzido.

### 3.2 `test_environment_differential.py` (Rede Diferencial de Detecção sem `explicit_env`)
- **Total de Casos Avaliados:** 4 branches (`dev`, `release/qa-1`, `main`, `feature/evaluation`).
- **Resultado:** 1/1 teste aprovado (`OK`), 1.02s.
- **Relaxamentos Não Autorizados:** **0 (zero)**.

---

## 4. Provas de Falsificabilidade por Mutação em Clone Isolado (`/tmp`)

Executado exclusivamente em clones temporários descartáveis criados em `/tmp/ceh-falsify-prqa-c2-*`, preservando a árvore de trabalho principal limpa:

### 4.1 Mutação 1 (C01 do Handoff 050): Adição de Opção Fictícia em `cat`
- **Intervenção:** Adicionado `--invented-output` como opção de escrita de `cat` em `write_options.json`, sem alterar o Safety Gate.
- **Resultado:** O teste `test_help_contract.py` **FALHOU** imediatamente com exit code 1:
  ```
  AssertionError: 'allow' != 'deny'
  - allow
  + deny
   : Opção de escrita '--invented-output' (cat) em 'cat --invented-output .ceh/last-ci-run.json' DEVE ser deny no ambiente development. Obtido: allow
  FAILED (failures=1)
  ```
- **Conclusão:** É impossível registrar uma nova opção de escrita no JSON sem que o teste exija e comprove o bloqueio no gate. O achado C01 está 100% resolvido.

### 4.2 Mutação 2: Remoção da Defesa de `--output` do Gate
- **Intervenção:** No arquivo `ceh_core/rules.py` do clone, a checagem `if arg.startswith(("--output=", ...)): return False` em `is_git_read_subcommand` foi substituída por `pass`.
- **Resultado:** O teste `test_help_contract.py` **FALHOU** imediatamente com exit code 1:
  ```
  AssertionError: 'allow' != 'deny'
  - allow
  + deny
   : Opção de escrita '--output' (git-diff) em 'git diff --output=.ceh/last-ci-run.json' DEVE ser deny no ambiente development. Obtido: allow
  FAILED (failures=1)
  ```
- **Conclusão:** A proteção contra adulteração de certificado via `--output` é determinística e falsificável.

### 4.3 Mutação 3: Corrupção de Snippet de Help no Contrato
- **Intervenção:** No arquivo `write_options.json`, o snippet da linha 170 de `git diff` foi alterado para `--corrupted-snippet-invented`.
- **Resultado:** O teste `test_help_contract.py` **FALHOU** imediatamente com exit code 1:
  ```
  AssertionError: False is not true : Divergência na fonte em git-diff (docs/temp_implementation/evidence/help-contracts/git-diff.txt:170) para flag '--output'.
    Snippet esperado: '--corrupted-snippet-invented'
    Linha real:       '       --output=<file>'
  FAILED (failures=1)
  ```
- **Conclusão:** Toda opção no contrato é ancorada com exatidão física na linha real do help versionado.

---

## 5. Orçamento de Linhas e Auditoria Documental

Execução do `bash clearer-engineering/scripts/doc-audit.sh`:
- **safety-gate.py:** 624 linhas (Teto: 650)
- **test-runner.sh:** 188 linhas (Teto: 200)
- **ceh_core/rules.py:** 226 linhas (Teto: 300) — *Folga de 74 linhas*.
- **Todos os componentes core:** Dentro do orçamento estrito.
- **Resultado:** SUCESSO: 7/7 checagens estruturais documentais passaram (60/60 testes aprovados).
