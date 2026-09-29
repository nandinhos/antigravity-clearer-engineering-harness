# Relatório de Evidências — PR-07e

- **Data/Hora:** 2026-09-27T01:35:00Z
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **Baseline de Comparação:** `8da15d7`
- **Handoff de Origem:** [Handoff 034](../handoffs/handoff-034-revisao-pr07d.md)

---

## 1. Escopo Entregue (`OBSERVED`)

1. **AI1 — Troca Estática de Branch no Próprio Comando**:
   - `git switch <b>`, `git switch -c/-C <b>`, `git checkout <b>` e `git checkout -b/-B <b>` passam a definir a **branch de contexto** dos subcomandos seguintes via `resolve_target_context` (`ceh_core/environment.py`).
   - O modelo é puramente **estático**: utiliza o nome do argumento de branch do comando, classificado via `classify_branch_name` (`main`/`master`/`production`/`prod` → production; segmentos de staging → staging), sem consultar o estado do Git em runtime.
   - Ambiguidade entre branch e caminho de arquivo (`git checkout <x>`): tratada como troca de branch somente se o nome classificar como produção ou staging (princípio de escalada unilateral).
   - O comando de troca em si é avaliado no ambiente atual (`git checkout --force main` em development permanece `allow` e em conformidade com o Golden Corpus snapshot), afetando o contexto apenas dos subcomandos subsequentes.
   - Controles verificados:
     - `git checkout main` sozinho → `allow`;
     - `git checkout -b hotfix && git reset --hard` → `allow`;
     - `git checkout app/Model.php && git reset --hard` → `allow`.

2. **AI2 — Arquivo de Ambiente Carregado ou Copiado**:
   - `source F`, `. F` e `cp|mv|ln -s F .env` (destino terminando em `.env`) definem o **ambiente de contexto** dos subcomandos seguintes com base nos segmentos do nome de `F` (`.env.production` → production, `.env.staging` → staging).
   - Aplica estritamente a regra de escalada: a severidade só aumenta (`development` → `staging` ou `production`), nunca rebaixa.

3. **Invariante de Equivalência Estendida**:
   - Acrescentadas as 4 novas formas em `test_context_equivalence_invariant` em `clearer-engineering/tests/test_environment_tokens.py`:
     - `git switch main &&` (comparado a `cd <main> && C`);
     - `git checkout main &&` (comparado a `cd <main> && C`);
     - `source .env.production &&` (comparado a `APP_ENV=production C`);
     - `cp .env.production .env &&` (comparado a `APP_ENV=production C`).

---

## 2. Prova Física de Falsificabilidade (`OBSERVED`)

Para demonstrar a falsificabilidade da invariante de equivalência de contexto estendida, foi aplicada uma mutação real temporária em `ceh_core/environment.py`, desativando o reconhecimento de `checkout` em `resolve_target_context`.

### Comando Executado:
```bash
python3 -m unittest clearer-engineering/tests/test_environment_tokens.py
```

### Saída da Reprovação com a Mutação Ativa:
```text
F........F..
======================================================================
FAIL: test_context_equivalence_invariant (clearer-engineering.tests.test_environment_tokens.TestEnvironmentTokens.test_context_equivalence_invariant)
Handoff 033 / 034 Invariante de equivalência de contexto estendida:
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_environment_tokens.py", line 343, in test_context_equivalence_invariant
    self.assertGreaterEqual(
AssertionError: 0 not greater than or equal to 2 : Invariante de equivalência violada por git_checkout_main: 'git checkout main && git reset --hard HEAD~1' (allow) < 'cd .../repo_eq_main && git reset --hard HEAD~1' (deny)

======================================================================
FAIL: test_handoff_034_ai1_and_ai2_context_modification (clearer-engineering.tests.test_environment_tokens.TestEnvironmentTokens.TestEnvironmentTokens.test_handoff_034_ai1_and_ai2_context_modification)
Handoff 034 AI1 e AI2: troca de branch e arquivo de ambiente como mudança de contexto.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_environment_tokens.py", line 289, in test_handoff_034_ai1_and_ai2_context_modification
    self.assertEqual(dec, exp_dec, f"AI1/AI2 falhou: {cmd} deveria ser {exp_dec}, mas foi {dec} ({reason})")
AssertionError: 'allow' != 'deny'
- allow
+ deny
 : AI1/AI2 falhou: git checkout main && git reset --hard deveria ser deny, mas foi allow (Safe Git operation permitted (Git branch 'dev' (canonical dev branch)).)

----------------------------------------------------------------------
Ran 12 tests in 0.330s

FAILED (failures=2)
```

Com o suporte restaurado, a suíte passou integralmente:
```text
............
----------------------------------------------------------------------
Ran 12 tests in 0.378s

OK
```

---

## 3. Verificação de Regressão e Redes Diferenciais (`OBSERVED`)

1. **Rede Diferencial de Ambientes (`test_environment_differential.py`)**:
   - Baseline de referência: `8da15d7`.
   - Execução concorrente: **0.782s**.
   - Resultado: **0 relaxamentos**, 100% PASS.

2. **Rede Diferencial com Fuzzing (`test_gate_differential_fuzz.py`)**:
   - 11.997 combinações testadas contra a baseline `8da15d7`.
   - Resultado: **0 relaxamentos**, 100% PASS.

3. **Golden Corpus Snapshot (`snapshot_gate.py --check`)**:
   - 1012 avaliações idênticas; diff rigorosamente **vazio**.

4. **Auditoria Documental (`doc-audit.sh`)**:
   - 7/7 checagens aprovadas.
   - `safety-gate.py`: 635 linhas (teto: 650).
   - `ceh_core/environment.py`: 281 linhas (teto: 300).
