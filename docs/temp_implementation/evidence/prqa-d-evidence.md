# Relatório de Evidências — PR-QA-D: Normalização Única

**Data:** 2026-09-28  
**Ambiente:** DEVELOPMENT (`OBSERVED`)  
**Autor:** Antigravity (Pair programming com Nando Dev)  
**Objetivo:** Consolidar todas as funções dispersas de normalização de comando, caminho, token e opções em uma única API canônica (`ceh_core/normalize.py`), eliminando divergências estruturais (W1/W2) com zero mudança de decisão e validação por teste estrutural falsificável.

---

## 1. Inventário de Funções de Normalização Consolidadas

Conforme exigido pelo item 1 do PR-QA-D (Handoff 050), todas as funções de normalização identificadas nos analisadores foram catalogadas e unificadas:

| Componente Original | Função / Operação Original | Ação no PR-QA-D | API Canônica em `ceh_core/normalize.py` |
|---|---|---|---|
| `ceh_core/lexer.py:182` | `normalize_command_for_evaluation(subcmd)` | Migrado para API canônica; reexportado para compatibilidade | `normalize_command_for_evaluation(subcmd: str) -> str` |
| `ceh_core/environment.py:18` | `normalize_env(val)` | Migrado para API canônica; importado diretamente | `normalize_env(val: str) -> str` |
| `ceh_core/environment.py:25` | `classify_branch_name(b)` | Migrado para API canônica; importado diretamente | `classify_branch_name(b: str) -> str | None` |
| `ceh_core/environment.py:33` | `target.strip().strip('"').strip("'")` | Substituído por `strip_all_quotes` | `strip_all_quotes(s: str) -> str` |
| `ceh_core/environment.py:48` | `shlex.split(cmd_line, comments=True)` | Substituído por `tokenize_command` | `tokenize_command(cmd_line: str, ...) -> list[str]` |
| `ceh_core/git.py:40` | `strip_quotes(s)` | Migrado para API canônica; importado diretamente | `strip_quotes(s: str) -> str` |
| `ceh_core/git.py:55` | `posixpath.normpath(sub)` | Substituído por `normalize_posix_path` | `normalize_posix_path(path: str) -> str` |
| `ceh_core/git.py:139,205,256` | `[o for o in OPTS if o.startswith(opt_name)]` | Substituído por `resolve_long_options` (W2) | `resolve_long_options(token: str, known_options) -> list[str]` |
| `ceh_core/push.py:30` | `shlex.split(cmd_line, posix=True)` | Substituído por `tokenize_command` | `tokenize_command(cmd_line: str, ...) -> list[str]` |
| `ceh_core/push.py:81` | `[o for o in PUSH_LONG_OPTS if o.startswith(opt_name)]` | Substituído por `resolve_long_options` (W2) | `resolve_long_options(token: str, known_options) -> list[str]` |
| `ceh_core/rm.py:70` | `target.replace('"', "").replace("'", "")` | Substituído por `strip_all_quotes` | `strip_all_quotes(s: str) -> str` |
| `ceh_core/rm.py:72` | Expansão manual de `~`, `~/`, `~root` | Substituído por `expand_home_prefix` | `expand_home_prefix(target: str, home_dir) -> str` |
| `ceh_core/rm.py:91,100,129` | `os.path.normpath(join(cwd, base))` | Substituído por `normalize_path` | `normalize_path(path, cwd, resolve_home) -> str` |
| `ceh_core/rm.py:168` | `shlex.split(cmd_line, posix=True)` | Substituído por `tokenize_command` | `tokenize_command(cmd_line: str, ...) -> list[str]` |
| `ceh_core/find.py:23` | `target.replace('"', "").replace("'", "")` | Substituído por `strip_all_quotes` | `strip_all_quotes(s: str) -> str` |
| `ceh_core/find.py:30` | `os.path.normpath(os.path.join(cwd_str, t))` | Substituído por `normalize_path` | `normalize_path(path, cwd, resolve_home) -> str` |
| `ceh_core/find.py:133` | `shlex.split(cmd_line, posix=True)` | Substituído por `tokenize_command` | `tokenize_command(cmd_line: str, ...) -> list[str]` |
| `ceh_core/rules.py:89` | `shlex.split(cmd)` | Substituído por `tokenize_command` | `tokenize_command(cmd_line: str, ...) -> list[str]` |
| `ceh_core/rules.py:157` | `clean_target.replace("\"", "").replace("\x27", "")` | Substituído por `strip_all_quotes` | `strip_all_quotes(s: str) -> str` |
| `ceh_core/interpreters.py:175` | `shlex.split(cmd_line, posix=True)` | Substituído por `tokenize_command` | `tokenize_command(cmd_line: str, ...) -> list[str]` |
| `safety-gate.py:190,265,481` | Chamadas dispersas a `shlex.split` | Substituído por `tokenize_command` | `tokenize_command(cmd_line: str, ...) -> list[str]` |

---

## 2. Invariância de Decisão (Zero Mudança de Decisão)

A refatoração preservou integralmente o comportamento do Safety Gate contra a linha de base:
- **Golden Corpus Snapshot:** `python3 clearer-engineering/tests/tools/snapshot_gate.py --check`
  - Resultado: `✔ Golden Corpus Snapshot 100% CONFORME (1024 avaliações idênticas, diff vazio)`.
- **Differential Fuzzing:** `python3 clearer-engineering/tests/test_gate_differential_fuzz.py`
  - 12.105 casos avaliados em 5.21s: **4/4 testes aprovados** (0 apertos, 0 relaxamentos não autorizados).
- **Environment Differential:** `python3 clearer-engineering/tests/test_environment_differential.py`
  - 100% PASS (0 divergências de severidade).
- **Review Batteries:** `python3 clearer-engineering/tests/test_review_batteries.py`
  - 100% PASS (todos os casos e pendências estritas xfail preservados).

---

## 3. Teste Estrutural Falsificável (`test_normalization_structural.py`)

Criado o teste `clearer-engineering/tests/test_normalization_structural.py` (integrado como Teste 29 do `run-all-tests.sh`, totalizando 62 testes canônicos):
1. **Verificação AST:** Garante que nenhuma função reservada de normalização ou com prefixo `normalize_` seja definida fora de `ceh_core/normalize.py`.
2. **Varredura de Normpath:** Garante que `os.path.normpath` e `posixpath.normpath` sejam invocados exclusivamente em `normalize.py`.
3. **Varredura de Shlex:** Garante que chamadas a `shlex.split` residam exclusivamente em `normalize.py` (com exceção justificada documentada em `rules.py:175` para captura de `ValueError` em `is_cert_tampering`).
4. **Exportação de Símbolos:** Garante a presença e executabilidade de todos os 9 símbolos da API canônica.

### Prova de Falsificabilidade por Mutação (Executada em Clone Isolado)
- **Mutação A:** Adição de `def normalize_custom_branch(b)` em `git.py` → O teste reprovou imediatamente com AssertionError citando expressamente `git.py`.
- **Mutação B:** Invocação direta de `os.path.normpath` em `find.py` → O teste reprovou imediatamente com AssertionError citando expressamente `find.py`.

---

## 4. Correção de Precisão de Citação AX2 (Carona)

- **Contrato:** No arquivo `clearer-engineering/config/write_options.json`, a opção `outfile` de `python-json-tool` foi corrigida de `[outfile]` para `outfile`.
- **Teste:** No arquivo `clearer-engineering/tests/test_help_contract.py`, foi adicionada a asserção `self.assertIn(flag, snippet)` garantindo que 100% das opções citam snippets que contêm o nome da própria flag.
- Execução: `test_help_contract.py` aprovado em 0.031s com 5/5 testes verdes.

---

## 5. Orçamento de Linhas dos Componentes Core (Auditoria Documental 7/7)

Executado `bash clearer-engineering/scripts/doc-audit.sh`:
- `safety-gate.py`: 618 linhas (Teto: 650)
- `test-runner.sh`: 188 linhas (Teto: 200)
- `ceh_core/environment.py`: 275 linhas (Teto: 300)
- `ceh_core/find.py`: 201 linhas (Teto: 300)
- `ceh_core/git.py`: 287 linhas (Teto: 300)
- `ceh_core/interpreters.py`: 253 linhas (Teto: 300)
- `ceh_core/interpreters_extra.py`: 263 linhas (Teto: 300)
- `ceh_core/lexer.py`: 286 linhas (Teto: 300)
- `ceh_core/normalize.py`: 162 linhas (Teto: 300)
- `ceh_core/push.py`: 271 linhas (Teto: 300)
- `ceh_core/rm.py`: 239 linhas (Teto: 300)
- `ceh_core/rules.py`: 225 linhas (Teto: 300)

**Resultado:** 7/7 checagens aprovadas. Todos os 12 componentes rigorosamente dentro do orçamento.

---

## 6. Homologação no CI Remoto (GitHub Actions)

- **Commit**: `0cd93dacddafe68c6ed335e4def0e0bf31f479b5`
- **Run ID**: [36428018017](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36428018017)
- **Status Remoto**: `success` (4/4 jobs concluídos com sucesso)
  - `Validate (ubuntu-latest - Python 3.9)`: Concluído em 2m1s (ID 108946706678) — `success`
  - `Validate (ubuntu-latest - Python 3.12)`: Concluído em 2m46s (ID 108946706735) — `success`
  - `Validate (macos-latest - Python 3.12)`: Concluído em 31m42s (ID 108946706286) — `success`
  - `Validate (macos-latest - Python 3.9)`: Concluído em 32m29s (ID 108946707022) — `success`

