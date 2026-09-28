# PR-QA-C — Evidência de Implementação e Verificação (`OBSERVED`)

**Data/Hora:** 2026-09-27T23:25:00-03:00  
**PR:** PR-QA-C (`test(gate): contrato de opções de escrita a partir do --help`)  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Linha de Base Homologada:** `d4bb909` (Handoff 049)  
**Status da Suíte Canônica Local:** **60/60 testes aprovados (100% PASS)**  
**Certificado de CI:** Emitido em `.ceh/last-ci-run.json`  
**CI do Servidor (GitHub Actions):** [Aguardando push para URL de run]

---

## 1. Escopo e Objetivos do PR-QA-C

Conforme despachado no [Handoff 049](../handoffs/handoff-049-revisao-pr22b-despacho-prqa-c.md), o PR-QA-C ataca a causa raiz das regressões de segurança ao admitir comandos em listas de leitura:
1. **Inventário de `--help` Real:** Captura e versionamento em `docs/temp_implementation/evidence/help-contracts/<cmd>.txt` do `--help` real de cada comando e subcomando em listas de leitura/permissão do gate, incluindo metadados com versão do binário e timestamp UTC.
2. **Contrato Formal de Opções (`write_options.json`):** Mapeamento exaustivo em `clearer-engineering/config/write_options.json` de cada comando, identificando se possui opções de gravação ou execução de helpers, citando número de linha exato e snippet textual do help.
3. **Proteção Granular no Gate (`rules.py`):**
   - Interceptação de todas as opções de escrita/execução mapeadas quando o alvo for `.ceh/...` em todos os ambientes (`dev`, `staging`, `prod`) sob `deny/CERTIFICATE_INTEGRITY`.
   - Adicionadas proteções contra flags de escrita e execução de helpers para:
     - `git diff`: `--output`, `--output-directory`, `--ext-diff`, `--textconv`.
     - `git log`: `--output`, `-o`, `--ext-diff`, `--textconv`.
     - `git show`: `--output`, `--ext-diff`, `--textconv`.
     - `less`: `-o`, `-O`, `--log-file`, `--LOG-FILE`.
     - `python3 -m json.tool`: argumento posicional de saída (`[outfile]`).
4. **Resolução de Carona AW1 (Handoff 049):**
   - Removidos `r8sync` (erro de digitação inofensivo copiado do Handoff 048) e `find` (que não aceita `--exclude`) de `EXCLUDE_SUPPORTED_CMDS` em `ceh_core/rules.py`, restando o conjunto estrito: `{"tar", "rsync", "grep", "rg"}`.
5. **Automação Test 60 (`test_help_contract.py`):**
   - Teste automatizado integrado em `run-all-tests.sh` que falha se qualquer comando for adicionado a `ALLOWED_READ_CMDS` ou `ALLOWED_GIT_READ_SUBCMDS` sem entrada correspondente e auditada em `write_options.json`, ou se suas opções de escrita não forem categoricamente negadas diante de `.ceh/`.

---

## 2. Inventário de Comandos e Contrato de Opções (`OBSERVED`)

| Comando / Subcomando | Arquivo de Help | Versão Capturada | Opções de Gravação / Execução | Linhas Citadas no Help | Rationale / Bloqueio no Gate |
|---|---|---|---|---|---|
| `cat` | `cat.txt` | cat (GNU coreutils) 9.4 | Nenhuma | — | Leitura pura. |
| `less` | `less.txt` | less 633 | `-o`, `-O`, `--log-file`, `--LOG-FILE` | 171, 173 | Grava cópia de entrada em arquivo de log. Bloqueado quando visa `.ceh/`. |
| `more` | `more.txt` | more from util-linux 2.39.3 | Nenhuma | — | Leitura pura. |
| `head` | `head.txt` | head (GNU coreutils) 9.4 | Nenhuma | — | Leitura pura. |
| `tail` | `tail.txt` | tail (GNU coreutils) 9.4 | Nenhuma | — | Leitura pura. |
| `jq` | `jq.txt` | jq-1.7.1 | Nenhuma (stdout apenas) | — | Leitura/transformação em stdout. |
| `grep` | `grep.txt` | grep (GNU grep) 3.11 | Nenhuma | — | Leitura pura em stdout. |
| `egrep` | `egrep.txt` | grep (GNU grep) 3.11 | Nenhuma | — | Leitura pura em stdout. |
| `fgrep` | `fgrep.txt` | grep (GNU grep) 3.11 | Nenhuma | — | Leitura pura em stdout. |
| `ls` | `ls.txt` | ls (GNU coreutils) 9.4 | Nenhuma | — | Leitura pura de metadados. |
| `stat` | `stat.txt` | stat (GNU coreutils) 9.4 | Nenhuma | — | Leitura pura de metadados. |
| `wc` | `wc.txt` | wc (GNU coreutils) 9.4 | Nenhuma | — | Leitura pura de contagem. |
| `du` | `du.txt` | du (GNU coreutils) 9.4 | Nenhuma | — | Leitura pura de uso em disco. |
| `diff` | `diff.txt` | diff (GNU diffutils) 3.10 | Nenhuma (stdout apenas) | — | Leitura pura em stdout. |
| `git status` | `git-status.txt` | git version 2.43.0 | Nenhuma | — | Leitura pura de estado. |
| `git log` | `git-log.txt` | git version 2.43.0 | `--output`, `-o`, `--ext-diff`, `--textconv` | 2304, 3126, 3136 | `--output` grava em arquivo; `--ext-diff`/`--textconv` executam helpers. Bloqueados quando visam `.ceh/`. |
| `git diff` | `git-diff.txt` | git version 2.43.0 | `--output`, `--output-directory`, `--ext-diff`, `--textconv` | 170, 994, 1004 | `--output` grava em arquivo; `--ext-diff`/`--textconv` executam helpers. Bloqueados quando visam `.ceh/`. |
| `git show` | `git-show.txt` | git version 2.43.0 | `--output`, `--ext-diff`, `--textconv` | 994, 1816, 1826 | `--output` grava em arquivo; `--ext-diff`/`--textconv` executam helpers. Bloqueados quando visam `.ceh/`. |
| `python3 -m json.tool` | `python-json-tool.txt` | Python 3.12.3 | `outfile` (posicional opcional) | 16 | Segundo argumento posicional grava JSON formatado no arquivo alvo. Bloqueado quando visa `.ceh/`. |

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

Executado exclusivamente em clones temporários descartáveis criados em `/tmp/ceh-falsify-prqa-c-*`, preservando a árvore de trabalho principal limpa:

### 4.1 Mutação A: Remoção da Checagem de `--output` do Gate
- **Intervenção:** No arquivo `ceh_core/rules.py` do clone, a checagem `if arg.startswith(("--output=", ...)): return False` em `is_git_read_subcommand` foi substituída por `pass`.
- **Comando Avaliado pelo Teste:** `git diff --output=.ceh/last-ci-run.json`
- **Resultado:** O teste `test_help_contract.py` **FALHOU** imediatamente com exit code 1:
  ```
  AssertionError: 'allow' != 'deny'
  - allow
  + deny
   : 'git diff --output=.ceh/last-ci-run.json' deve ser deny no ambiente development
  FAILED (failures=1)
  ```
- **Conclusão:** A proteção contra adulteração de certificado via `--output` é determinística e falsificável.

### 4.2 Mutação B: Adição de Comando em Lista de Leitura sem Contrato
- **Intervenção:** Adicionado o comando `"unregistered_read_cmd"` a `ALLOWED_READ_CMDS` em `ceh_core/rules.py` do clone, sem cadastrá-lo em `write_options.json`.
- **Resultado:** O teste `test_help_contract.py` **FALHOU** imediatamente com exit code 1:
  ```
  AssertionError: ['unregistered_read_cmd'] is not false : Comandos em ALLOWED_READ_CMDS sem contrato formal em write_options.json: ['unregistered_read_cmd']
  FAILED (failures=1)
  ```
- **Conclusão:** Nenhum comando pode entrar em listas de leitura sem auditoria prévia do seu `--help` e formalização do contrato de opções.

---

## 5. Orçamento de Linhas e Auditoria Documental

Execução do `bash clearer-engineering/scripts/doc-audit.sh`:
- **safety-gate.py:** 624 linhas (Teto: 650)
- **test-runner.sh:** 188 linhas (Teto: 200)
- **ceh_core/rules.py:** 226 linhas (Teto: 300) — *Folga de 74 linhas*.
- **Todos os componentes core:** Dentro do orçamento estrito.
- **Resultado:** SUCESSO: 7/7 checagens estruturais documentais passaram (60/60 testes aprovados).
