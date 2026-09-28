# Relatório de Evidências — PR-07d

- **Data/Hora:** 2026-09-27T00:48:00Z
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **Baseline de Comparação:** `37f2079`
- **Handoff de Origem:** [Handoff 033](../handoffs/handoff-033-revisao-pr07c.md)

---

## 1. Escopo Entregue (`OBSERVED`)

1. **AH1 e AH2 — Equivalência de Contexto Unificada**:
   - Centralizada a resolução de contexto do alvo em `resolve_target_context` (`ceh_core/environment.py`), cobrindo as formas equivalentes a `cd X &&`:
     - Bloco `{ ...; }`: propaga o contexto internamente e para comandos subsequentes no processo da shell;
     - `env -C X` / `env --chdir=X` / `--chdir X`;
     - `sudo -D X` / `sudo --chdir=X` / `sudo -D=X`;
     - `GIT_DIR=X/.git` e `GIT_WORK_TREE=X` (como prefixo de atribuição de variável ou via `export` persistente);
     - `cd` sem argumentos tratado como `cd ~` (AH2), escalando para `production` por incerteza (Invariante 7).
   - Comandos inócuos (ex: `npm test`, `git status`) seguem `allow`.
   - Controles de subshell `( ... )` seguem isolados sem vazamento para comandos externos.

2. **AH3 — Caches de Desempenho e Concorrência**:
   - Implementado cache por diretório resolvido em `get_git_branch` e `find_repo_root` (`ceh_core/environment.py`).
   - Execução concorrente de workers da rede diferencial (`test_environment_differential.py`) por repositório de teste via `concurrent.futures.ThreadPoolExecutor`.
   - **Tempo pré-cache / sequencial:** `55.272s`.
   - **Tempo pós-cache / concorrente:** `2.942s` (redução de ~95%, superando com folga a meta de < 15s).

3. **Invariante de Equivalência de Contexto**:
   - Implementado `test_context_equivalence_invariant` em `test_environment_tokens.py`, garantindo algebricamente que para qualquer comando destrutivo $C$, $\text{severidade}(F(\langle\text{main}\rangle, C)) \ge \text{severidade}(\text{cd } \langle\text{main}\rangle \text{ \&\& } C)$.

---

## 2. Prova Física de Falsificabilidade (`OBSERVED`)

Para demonstrar a falsificabilidade da invariante de equivalência de contexto, foi aplicada mutação real temporária em `ceh_core/environment.py`, desativando o reconhecimento de opções `-C`.

### Comando Executado:
```bash
python3 -m unittest clearer-engineering/tests/test_environment_tokens.py
```

### Saída da Reprovação com a Mutação Ativa:
```text
F.......F..
======================================================================
FAIL: test_context_equivalence_invariant (clearer-engineering.tests.test_environment_tokens.TestEnvironmentTokens.test_context_equivalence_invariant)
Handoff 033 §3.2 Invariante de equivalência de contexto:
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_environment_tokens.py", line 312, in test_context_equivalence_invariant
    self.assertGreaterEqual(
AssertionError: 0 not greater than or equal to 2 : Invariante de equivalência violada por env_C: 'env -C /tmp/ceh-test-env-tokens-y1m4647b/repo_eq_main git reset --hard HEAD~1' (allow) < 'cd /tmp/ceh-test-env-tokens-y1m4647b/repo_eq_main && git reset --hard HEAD~1' (deny)

======================================================================
FAIL: test_handoff_033_ah1_and_ah2_context_equivalence (clearer-engineering.tests.test_environment_tokens.TestEnvironmentTokens.TestEnvironmentTokens.test_handoff_033_ah1_and_ah2_context_equivalence)
Handoff 033 AH1 e AH2: formas alternativas de contexto produzem mesmo efeito que cd X &&.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_environment_tokens.py", line 261, in test_handoff_033_ah1_and_ah2_context_equivalence
    self.assertEqual(dec, exp_dec, f"AH1/AH2 falhou: {cmd} deveria ser {exp_dec}, mas foi {dec} ({reason})")
AssertionError: 'allow' != 'deny'
- allow
+ deny
: AH1/AH2 falhou: env -C /tmp/ceh-test-env-tokens-ep05z7_b/repo_ah1_main git reset --hard deveria ser deny, mas foi allow

----------------------------------------------------------------------
Ran 11 tests in 0.334s

FAILED (failures=2)
```

Após o teste de falsificabilidade, o código original foi integralmente restaurado e a suíte voltou a passar (11/11 OK em 0.329s).

---

## 3. Verificações Físicas Globais (`OBSERVED`)

| Verificação | Comando | Resultado | Tempo |
|---|---|---|---|
| **Auditoria Documental** | `bash clearer-engineering/scripts/doc-audit.sh` | **7/7 PASS** | < 1s |
| **Tokens & Equivalência** | `python3 -m unittest clearer-engineering/tests/test_environment_tokens.py` | **11/11 PASS** | 0.329s |
| **Rede Diferencial de Detecção** | `python3 -m unittest clearer-engineering/tests/test_environment_differential.py` | **1/1 PASS** (0 relaxamentos contra baseline `37f2079`) | 2.942s |
| **Rede Diferencial Fuzz** | `python3 -m unittest clearer-engineering/tests/test_gate_differential_fuzz.py` | **4/4 PASS** (0 relaxamentos em 11.997 casos) | 12.870s |
| **Golden Corpus Snapshot** | `python3 clearer-engineering/tests/tools/snapshot_gate.py --check` | **1012/1012 CONFORME** (diff vazio) | 1.8s |
| **Smoke-Eval** | `python3 clearer-engineering/tests/cluster2_acceptance.py --clean-eval-smoke` | **5/5 APROVA** | 1.0s |
