# Relatório de Evidências — PR-08

- **Data/Hora:** 2026-09-27T01:55:00Z
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **Baseline de Comparação:** `9dfc85a`
- **Handoff de Origem:** [Handoff 035](../handoffs/handoff-035-encerramento-onda-1-despacho-pr08.md)

---

## 1. Escopo Entregue (`OBSERVED`)

1. **Módulo Novo `ceh_core/push.py`**:
   - Criação de `ceh_core/push.py` (256 linhas, dentro do limite normativo de $\le 300$ linhas).
   - Extração da lógica de validação do pre-push CI de `safety-gate.py`, reduzindo `safety-gate.py` de 636 para 584 linhas (folga de 66 linhas em relação ao teto de 650).

2. **Análise por Tokens do `git push` e Resolução de Refspecs**:
   - Reconhecimento de remoto, refspecs (`src:dst`, `+src:dst`, `src`, `HEAD`, `HEAD:refs/heads/main`) e opções canônicas por prefixo único:
     - `-f`, `--force`, `--force-with-lease[=...]`, `-d`, `--delete`, `--all`, `--mirror`, `--tags`, `--follow-tags`, `-u`, `--set-upstream`, `--no-verify`, `-o`/`--push-option <v>`;
     - Opções agregadoras (`--all`, `--mirror`, `--tags` e abreviações como `--al`) bloqueadas com `deny` sob CI por impossibilidade de certificar commits individuais;
     - Opção abreviada `--forc` tratada com o mesmo comportamento de `--force`;
     - Deleções remotas (`:dst`, `--delete dst`, `-d dst`) não enviam commits novos e são permitidas sob a regra existente de desenvolvimento.

3. **Validação Estrita de Refspecs contra o Certificado da CI (G7)**:
   - Em repositórios com CI (`.github/workflows/*.yml`, `*.yaml` ou `.gitlab-ci.yml`), cada `src` é resolvido via `git rev-parse --verify <src>^{commit}` e validado contra o `commit_hash` aprovado em `.ceh/last-ci-run.json`.
   - Se `src` não resolver $\to$ `deny` (fail-closed) nomeando o refspec.
   - Se `src_commit != cert_commit` $\to$ `deny` nomeando o refspec e os hashes divergentes.
   - Sem refspecs fornecidos (`git push`, `git push origin`) $\to$ valida o `HEAD` do repositório.

4. **Resolução de Contexto**:
   - Suporte transparente para `git -C <fixture> push origin outro:main` e `cd <fixture> && git push origin outro:main`, ambos bloqueando o envio de commit não certificado fora ou dentro da fixture.

5. **Atualização da Suíte de Aceitação**:
   - Removido o `@unittest.expectedFailure` de `test_g7_pre_push_ci_refspec_untested_commit_red` em `clearer-engineering/tests/cluster4_acceptance.py`.
   - O teste do G7 agora é 100% **verde**.

---

## 2. Prova Física de Falsificabilidade (`OBSERVED`)

Para comprovar a falsificabilidade da validação de refspecs do PR-08, foi aplicada mutação real temporária em `ceh_core/push.py`, desativando a verificação de `src` nos refspecs e avaliando apenas o `HEAD`.

### Comando Executado:
```bash
python3 -m unittest clearer-engineering/tests/test_pre_push_refspecs.py
```

### Saída da Reprovação com a Mutação Ativa:
```text
F..F.F
======================================================================
FAIL: test_abbreviated_force_flag_matches_force (clearer-engineering.tests.test_pre_push_refspecs.TestPrePushRefspecs.test_abbreviated_force_flag_matches_force)
--forc tem o mesmo comportamento de --force (allow se commit certificado, deny se não).
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_pre_push_refspecs.py", line 133, in test_abbreviated_force_flag_matches_force
    self.assertEqual(dec_uncert, "deny")
AssertionError: 'allow' != 'deny'
- allow
+ deny

======================================================================
FAIL: test_context_git_dash_c_and_cd_block_uncertified_push (clearer-engineering.tests.test_pre_push_refspecs.TestPrePushRefspecs.test_context_git_dash_c_and_cd_block_uncertified_push)
Verifica se git -C <fixture> e cd <fixture> && git push são bloqueados fora do cwd da fixture.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_pre_push_refspecs.py", line 142, in test_context_git_dash_c_and_cd_block_uncertified_push
    self.assertEqual(dec, "deny", f"git -C falhou: esperado deny, obtido '{dec}' ({reason})")
AssertionError: 'allow' != 'deny'
- allow
+ deny
 : git -C falhou: esperado deny, obtido 'allow' (Pre-Push CI Gate validado: suíte canônica aprovada para o commit atual.)

======================================================================
FAIL: test_uncertified_refspecs_denied (clearer-engineering.tests.test_pre_push_refspecs.TestPrePushRefspecs.test_uncertified_refspecs_denied)
Casos outro:main, +outro:main e outro devem ser bloqueados (deny).
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_pre_push_refspecs.py", line 89, in test_uncertified_refspecs_denied
    self.assertEqual(dec, "deny", f"Comando '{cmd}' deveria ser deny, obtido '{dec}' ({reason})")
AssertionError: 'allow' != 'deny'
- allow
+ deny
 : Comando 'git push origin outro:main' deveria ser deny, obtido 'allow' (Pre-Push CI Gate validado: suíte canônica aprovada para o commit atual.)

----------------------------------------------------------------------
Ran 6 tests in 0.209s

FAILED (failures=3)
```

E no `cluster4_acceptance.py`:
```text
FAIL: test_g7_pre_push_ci_refspec_untested_commit_red (__main__.Cluster4Acceptance.test_g7_pre_push_ci_refspec_untested_commit_red)
AssertionError: 'allow' != 'deny'
 : Esperado 'deny' ao enviar commit não certificado via refspec, obtido 'allow'
```

Com o suporte restaurado, a suíte passou integralmente:
```text
......
----------------------------------------------------------------------
Ran 6 tests in 0.154s

OK
```

---

## 3. Verificação de Regressão e Redes Diferenciais (`OBSERVED`)

1. **Rede Diferencial de Ambientes (`test_environment_differential.py`)**:
   - Baseline de referência: `9dfc85a`.
   - Execução: **0.801s**.
   - Resultado: **0 relaxamentos**, 100% PASS.

2. **Rede Diferencial com Fuzzing (`test_gate_differential_fuzz.py`)**:
   - 11.997 combinações avaliadas contra a baseline `9dfc85a`.
   - Resultado: **0 relaxamentos**, 100% PASS.

3. **Golden Corpus Snapshot (`snapshot_gate.py --check`)**:
   - `INT-G7_RED` (`git push origin outro:main`) promovido de `allow` para `deny` (comportamento correto do G7).
   - 1012 avaliações idênticas; diff rigorosamente **vazio**.

4. **Auditoria Documental (`doc-audit.sh`)**:
   - 7/7 checagens aprovadas.
   - `safety-gate.py`: 584 linhas (teto: 650).
   - `ceh_core/push.py`: 256 linhas (teto: 300).
