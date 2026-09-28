# Relatório de Snapshot do Corpus e Comparação Diferencial — PR-07c

- **Data/Hora**: 2026-09-27T00:20:00Z
- **Baseline SHA**: `0a51eef` (definido em `tests/fixtures/gate_baseline.txt`)
- **Arquivos de Relaxamentos Autorizados**:
  - `tests/fixtures/relaxamentos_justificados.txt`: Vazio (0 relaxamentos autorizados no fuzzing).
  - `tests/fixtures/relaxamentos_deteccao.txt`: Vazio (0 relaxamentos autorizados na rede diferencial).

---

## 1. Verificação do Golden Corpus Snapshot (`snapshot_gate.py --check`)

```text
[outro_branch_tmp 4762437] extra commit
 1 file changed, 1 insertion(+)
 create mode 100644 extra_file.txt
✔ Golden Corpus Snapshot 100% CONFORME (1012 avaliações idênticas, diff vazio)
```

**Resultado**: Diff vazio. Nenhuma regressão de decisões nos 1012 comandos mapeados no Golden Corpus Snapshot.

---

## 2. Rede Diferencial de Ambiente sem `explicit_env` (`test_environment_differential.py`)

- **Branches Avaliadas**: `dev`, `release/qa-1`, `main`, `feature/evaluation`.
- **Comandos Avaliados**: 512 comandos únicos cobrindo corpus decodificado, baterias adversariais, tabela dos Handoffs 030/031/032 e gramática determinística de sinais (`seed=42`).
- **Relaxamentos Não Autorizados Detectados**: **0**.
- **Resultado**: `PASS` (Execução isolada em subprocessos herméticos para baseline e current gate).

---

## 3. Fuzzing Diferencial com Ambiente Explícito (`test_gate_differential_fuzz.py`)

- **Ambientes Avaliados**: `development`, `staging`, `production`.
- **Casos Avaliados**: **11.997 casos**.
- **Relaxamentos Não Autorizados Detectados**: **0**.
- **Tempo de Execução**: 3.96s (meta < 20s).
- **Resultado**: `PASS`.
