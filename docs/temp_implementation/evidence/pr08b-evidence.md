# Relatório de Evidências — PR-08b

- **Data/Hora:** 2026-09-27T02:30:00Z
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **Baseline de Comparação:** `4b03c0b`
- **Handoff de Origem:** [Handoff 036](../handoffs/handoff-036-revisao-pr08-despacho-pr08b-pr09.md)

---

## 1. Escopo Entregue (`OBSERVED`)

1. **AJ1 — Registro de Testes de Push na Suíte Canônica**:
   - `test_pre_push_refspecs.py` devidamente registrado como Teste 23 em `clearer-engineering/tests/run-all-tests.sh`.
   - Contagem geral da suíte atualizada para `56/56` em `docs/plano-validacao-revisao-conselho-seniors.md`.
   - Adicionada checagem anti-órfão em `clearer-engineering/scripts/doc-audit.py`: valida automaticamente que todo arquivo `tests/test_*.py` e `tests/cluster*_acceptance.py` está presente no texto de `run-all-tests.sh`.

2. **AJ2 — Graduação de Deleção Remota (`GIT_HISTORY`)**:
   - Invocação de git push com deleção remota (`:dst`, `+:dst`, `--delete dst`, `-d dst`, `--del dst`) agora é classificada como `GIT_HISTORY`.
   - Graduação unificada com `git branch -D`:
     - **DEV (`development`):** `allow`
     - **HML (`staging`):** `ask` (com 2 alertas do Safety Gate)
     - **PROD (`production`):** `deny` (bloqueio incondicional)
   - Casos integrados em `clearer-engineering/tests/test_pre_push_refspecs.py`.

---

## 2. Prova Física de Falsificabilidade (`OBSERVED`)

Para demonstrar a falsificabilidade da nova checagem anti-órfão do `doc-audit`, a chamada de `test_pre_push_refspecs.py` foi temporariamente removida de `run-all-tests.sh`.

### Comando Executado:
```bash
bash clearer-engineering/scripts/doc-audit.sh
```

### Saída da Reprovação com a Mutação Ativa:
```text
=== [CEH Bounded Document Structure Audit] ===
Repositório: .../clearer-engineering-harness
Alvo principal: docs/plano-validacao-revisao-conselho-seniors.md
--------------------------------------------------
[1/7] Verificando taxonomia de estados permitidos...
[2/7] Verificando consistência da tabela de achados (R1 a R10)...
[3/7] Verificando existência física de arquivos de evidência citados...
[4/7] Verificando portabilidade de links e ausência de session IDs na documentação...
[5/7] Verificando existência de commits citados no Git local...
[6/7] Verificando consistência em handoffs...
[7/7] Verificando orçamento de linhas dos componentes core...
--------------------------------------------------
FALHA: 2 inconsistência(s) encontrada(s):
  [1] A contagem atual da suíte geral não está sincronizada no cabeçalho do plano: esperado '55/55 testes aprovados'.
  [2] Testes órfãos detectados: ['test_pre_push_refspecs.py'] não estão citados em run-all-tests.sh.
Auditoria documental REJEITADA.
```

Com o registro restaurado, a auditoria passou com `SUCESSO: 7/7 checagens estruturais documentais passaram`.

---

## 3. Verificação de Regressão e Redes Diferenciais (`OBSERVED`)

1. **Rede Diferencial de Ambientes (`test_environment_differential.py`)**:
   - Baseline de referência: `4b03c0b`.
   - Resultado: **0 relaxamentos**, 100% PASS.

2. **Rede Diferencial Fuzz (`test_gate_differential_fuzz.py`)**:
   - 11.997 combinações testadas contra a baseline `4b03c0b`.
   - Resultado: **0 relaxamentos**, 100% PASS.

3. **Golden Corpus Snapshot (`snapshot_gate.py --check`)**:
   - 1012 avaliações idênticas; diff rigorosamente **vazio**.

4. **Auditoria Documental (`doc-audit.sh`)**:
   - 7/7 checagens aprovadas.
   - `safety-gate.py`: 590 linhas (teto: 650).
   - `ceh_core/push.py`: 273 linhas (teto: 300).
