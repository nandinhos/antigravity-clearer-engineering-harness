# Relatório de Evidências — PR-22b

**Data/Hora:** 2026-09-28T01:42:00Z  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Escopo:** `fix(gate): fechar a escrita do certificado por --output e restringir strip de exclusão (AV1/AV2)`  
**Antecessor:** [Handoff 048](../handoffs/handoff-048-revisao-pr22-regressao-g9-despacho-pr22b.md)  
**Linha de Base:** `d6bf922` (inalterada)

---

## 1. Resumo Executivo e Critérios de Aceite

| Requisito do Handoff 048 | Status | Evidência |
|---|---|---|
| **AV1 (Alto):** Bloqueio de `git diff\|log\|show --output/ -o` em `.ceh` | **ATENDIDO** | `is_git_read_subcommand` intercepta flags de escrita (`-o`, `-O`, `--output`, `--output-directory`), negando com `deny/CERTIFICATE_INTEGRITY`. Leituras puras seguem `allow`. |
| **Forja E2E:** Sequência forja-então-push barrada | **ATENDIDO** | Teste `test_e2e_cert_forge_via_git_output_blocked` em `test_cert_protection.py` comprova bloqueio da forja e negação do push subsequente pelo Pre-Push CI Gate. |
| **AV2 (Médio):** Restrição de `strip_ceh_exclusions` a comandos válidos | **ATENDIDO** | `strip_ceh_exclusions` restrito a `{"tar", "rsync", "r8sync", "grep", "rg", "find"}`. `python3 -c "..." --exclude .ceh` volta a ser `deny/CERTIFICATE_INTEGRITY`. |
| **Bateria H048-AV1:** Linhas na bateria como `deny` e verdes | **ATENDIDO** | 3 linhas AV1 e controles em `review_batteries.txt`. `test_review_batteries.py` 100% OK. |
| **AV3 (Corpus):** Cobertura das formas `--output` e diff linha a linha | **ATENDIDO** | 4 comandos adicionados em `gate_corpus.txt`; snapshot 1024 avaliações 100% conforme; diff auditado em `pr22b-corpus-diff.md`. |
| **Falsificabilidade:** Prova em clone isolado sob mutação | **ATENDIDO** | Sob restauração da versão permissiva, `test_review_batteries.py` e `test_cert_protection.py` falham categoricamente (exit code 1). |
| **Rede Diferencial:** Apenas os 5 AM2 legítimos detectados | **ATENDIDO** | `test_gate_differential_fuzz.py` (12.105 casos) e `test_environment_differential.py` passam com 0 relaxamentos não autorizados. |
| **Orçamento de Linhas:** Respeito aos limites do `doc-audit.sh` | **ATENDIDO** | `rules.py` com 220 linhas (teto 300). Auditoria documental 7/7 aprovada. |
| **Governança:** Plano e homologação | **ATENDIDO** | Plano não editado pelo agente; homologação reservada ao Revisor Independente. |

---

## 2. Diagnóstico e Solução Técnica

### 2.1 Causa Raiz de AV1 e Correção
- **Causa:** `is_git_read_subcommand` em `ceh_core/rules.py` tratava `status|log|diff|show` como leitura pura sem inspecionar flags posteriores, ignorando opções que gravam em disco como `--output=<path>`, `-o <path>`, `--output-directory=<path>`.
- **Correção:** Varredura estrita e fail-closed em `args`. Se qualquer argumento contiver flag de escrita (`-o`, `-O`, `--output`, prefixos `--output=`, `--output-`, ou `-o`/`-O` com comprimento > 2), a invocação **não** é considerada leitura pura. Ao mencionar `.ceh/` ou certificados, é interceptada por `is_cert_tampering` e categorizada como `deny` com `use_case: "CERTIFICATE_INTEGRITY"`.

### 2.2 Causa Raiz de AV2 e Correção
- **Causa:** `strip_ceh_exclusions` aplicava regex global indiscriminada em qualquer comando, removendo `--exclude .ceh` inclusive de interpretadores genéricos (`python3 -c "..." --exclude .ceh`), desarmando a detecção opaca que antes gerava `deny`.
- **Correção:** Extração do comando executável base desconsiderando wrappers transparentes (`sudo`, `env`, `rtk`, `rtk proxy`). A remoção de `--exclude` foi limitada estritamente a comandos que aceitam exclusão sintática (`tar`, `rsync`, `r8sync`, `grep`, `rg`, `find`), e `-path ... -prune` exclusivamente a `find`. Comandos genéricos/interpretadores mantêm `--exclude .ceh` intacto e caem no bloqueio de integridade.

---

## 3. Matriz de Comportamento dos Comandos Críticos

| Comando | Ambiente | Linha de Base (`d6bf922`) | HEAD PR-22 (`4c837c3`) | HEAD PR-22b (Corrigido) | Decisão e Use Case |
|---|---|---|---|---|---|
| `git diff --output=.ceh/last-ci-run.json` | production | deny | allow ❌ | **deny** ✔ | `deny/CERTIFICATE_INTEGRITY` |
| `git log -1 --output=.ceh/last-ci-run.json` | production | deny | allow ❌ | **deny** ✔ | `deny/CERTIFICATE_INTEGRITY` |
| `git show --output=.ceh/last-ci-run.json HEAD` | production | deny | allow ❌ | **deny** ✔ | `deny/CERTIFICATE_INTEGRITY` |
| `git log -1 -o .ceh/last-ci-run.json` | production | deny | allow ❌ | **deny** ✔ | `deny/CERTIFICATE_INTEGRITY` |
| `git log -1 --format=... --output=.ceh/...` | production | deny | allow ❌ | **deny** ✔ | `deny/CERTIFICATE_INTEGRITY` |
| `git diff .ceh/last-ci-run.json` | production | deny | allow ✔ | **allow** ✔ | `allow/GENERAL` (leitura legítima AM2) |
| `git show HEAD:app.txt` | production | allow | allow ✔ | **allow** ✔ | `allow/GENERAL` (leitura pura fora de .ceh) |
| `git format-patch --output=.ceh/patch` | production | deny | deny ✔ | **deny** ✔ | `deny/CERTIFICATE_INTEGRITY` |
| `python3 -c "..." --exclude .ceh` | production | deny | allow ❌ | **deny** ✔ | `deny/CERTIFICATE_INTEGRITY` |
| `tar czf out.tgz --exclude=.ceh .` | production | deny | allow ✔ | **allow** ✔ | `allow/GENERAL` (AM2 legítimo) |
| `find . -path ./.ceh -prune -o -name '*.py' -print` | production | deny | allow ✔ | **allow** ✔ | `allow/GENERAL` (AM2 legítimo) |

---

## 4. Prova de Falsificabilidade (Mutação em Clone Isolado)

Em clone temporário isolado em `/tmp`, reintroduziu-se o defeito do PR-22 em `is_git_read_subcommand` (ignorando flags de escrita e tratando qualquer `diff|log|show` como leitura pura).

### Resultado sob mutação:
1. **`test_review_batteries.py`**:
   - Exit code: 1
   - Falha observada:
     ```
     linha 453 [H048-AV1] production: esperado deny, obtido allow/GENERAL — git diff --output=.ceh/last-ci-run.json
     linha 454 [H048-AV1] production: esperado deny, obtido allow/GENERAL — git log -1 --output=.ceh/last-ci-run.json
     linha 455 [H048-AV1] production: esperado deny, obtido allow/GENERAL — git show --output=.ceh/last-ci-run.json HEAD
     ```
2. **`test_cert_protection.py`**:
   - Exit code: 1
   - Falhas observadas:
     - `test_e2e_cert_forge_via_git_output_blocked`: `AssertionError: 'allow' != 'deny'`
     - `test_git_output_flag_denied_all_envs`: `AssertionError: 'allow' != 'deny'`

Com a correção do PR-22b ativa, ambos os testes passam com exit code 0 e 100% de asserções verdes.

---

## 5. Auditoria Estrutural e Linhas Core (`doc-audit.sh`)

Execução de `bash clearer-engineering/scripts/doc-audit.sh`:
- [1/7] Taxonomia de estados: Aprovado
- [2/7] Tabela de achados (R1 a R10): Aprovado
- [3/7] Existência física de evidências: Aprovado (20 links)
- [4/7] Portabilidade de links e ausência de session IDs: Aprovado
- [5/7] Existência de commits citados: Aprovado
- [6/7] Consistência em handoffs: Aprovado
- [7/7] Orçamento de linhas:
  - `safety-gate.py`: 624 / 650
  - `test-runner.sh`: 188 / 200
  - `ceh_core/rules.py`: 220 / 300
- **Resultado:** 7/7 SUCESSO.
