# Relatório de Evidências — PR-09

- **Data/Hora:** 2026-09-27T02:40:00Z
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **Baseline de Comparação:** `4b03c0b` (e commit intermediário PR-08b `af9c357`)
- **Handoff de Origem:** [Handoff 036](../handoffs/handoff-036-revisao-pr08-despacho-pr08b-pr09.md)

---

## 1. Escopo Entregue (`OBSERVED`)

1. **Fail-Closed em Payload Vazio, Não-Objeto ou Sem Comando**:
   - `safety-gate.py:handle_hook()` e `hook_context.py:evaluate_hook_payload()` agora rejeitam chamadas anômalas no hook com código de saída 2 e motivo explícito:
     - Payload vazio (`""`) ou somente espaços: bloqueado (`deny`, exit code 2).
     - Objeto JSON vazio (`{}`): bloqueado (`deny`, exit code 2).
     - Chamada sem ferramenta identificável (`{"toolCall":{}}`): bloqueado (`deny`, exit code 2).
     - Chamada de terminal sem comando (`{"toolCall":{"name":"run_command","args":{}}}`): bloqueado (`deny`, exit code 2).
     - Claude sem comando (`{"tool_name":"Bash","tool_input":{}}` ou `{"command":""}`): bloqueado (`hookSpecificOutput` com `permissionDecision: "deny"`, exit code 2).
     - Não-JSON: bloqueado (`deny`, exit code 2).
   - Formato sem host identificável: `{"decision": "deny", "reason": ...}` com exit code 2.

2. **Despacho Extensível por Nome de Ferramenta (Preparação PR-10)**:
   - Implementado mapa `TOOL_DISPATCH` em `hook_context.py` registrando os despachantes por ferramenta.
   - Ferramenta desconhecida / não registrada ativa compulsoriamente fail-closed (`deny`, exit code 2).

3. **Bateria de Testes Normativa (7 Linhas do Handoff 036)**:
   - Adicionado `test_case_17_pr09_seven_table_rows_fail_closed_exit_2` em `clearer-engineering/tests/test_hook_context.py`, validando individualmente as 7 linhas via subprocesso com stdin real.
   - Adicionado `test_case_18_pr09_unknown_tools_fail_closed_exit_2` cobrindo ferramentas desconhecidas em ambos os hosts.
   - Total de testes em `test_hook_context.py` elevado para 18 (18/18 PASS).

---

## 2. Prova Física de Falsificabilidade (`OBSERVED`)

Para demonstrar a falsificabilidade da proteção em payload vazio, a checagem foi temporariamente relaxada em `clearer-engineering/scripts/safety-gate.py` restaurando o antigo comportamento fail-open (`if not raw_input.strip(): print(json.dumps({"decision": "allow"})); return`).

### Comando Executado:
```bash
python3 -m unittest clearer-engineering/tests/test_hook_context.py
```

### Saída da Reprovação com a Mutação Ativa:
```text
.......F..........
======================================================================
FAIL: test_case_17_pr09_seven_table_rows_fail_closed_exit_2 (clearer-engineering.tests.test_hook_context.TestHookContext.test_case_17_pr09_seven_table_rows_fail_closed_exit_2)
PR-09: Verifies all 7 rows from Handoff 036 table fail-closed with exit code 2 and explicit deny reason.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_hook_context.py", line 360, in test_case_17_pr09_seven_table_rows_fail_closed_exit_2
    self.assertEqual(code, 2, "Row 1 ('') must exit 2")
AssertionError: 0 != 2 : Row 1 ('') must exit 2

----------------------------------------------------------------------
Ran 18 tests in 0.443s

FAILED (failures=1)
```

Com o código restaurado, a suíte passou integralmente: `Ran 18 tests in 0.667s. OK`.

---

## 3. Verificação de Regressão e Redes Diferenciais (`OBSERVED`)

1. **Rede Diferencial de Ambientes (`test_environment_differential.py`)**:
   - Baseline de referência: `4b03c0b`.
   - Resultado: **0 relaxamentos**, 100% PASS.

2. **Rede Diferencial Fuzz (`test_gate_differential_fuzz.py`)**:
   - 11.997 combinações testadas contra a baseline `4b03c0b`.
   - Resultado: **0 relaxamentos**, 100% PASS.

3. **Golden Corpus Snapshot (`snapshot_gate.py --check`)**:
   - 1012 avaliações idênticas; diff rigorosamente **vazio** (100% CONFORME).

4. **Auditoria Documental (`doc-audit.sh`)**:
   - 7/7 checagens aprovadas.
   - `safety-gate.py`: 619 linhas (teto: 650).
   - `ceh_core/push.py`: 273 linhas (teto: 300).
   - `hook_context.py`: 222 linhas.
