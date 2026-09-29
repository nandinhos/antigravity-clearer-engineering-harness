# Handoff 061 — Fix P2 (Fork Bomb Bypass) e Ergonomia CLI (`--command` / `--cwd`)

**Data:** 2026-09-28  
**Autor:** Antigravity (Upstream Core CEH)  
**Destinatário:** Fernando dos Santos Souza & Agente do Muse (`clearer-muse`)  
**Contexto:** Retorno da integração do Muse (Onda 4) apontando P2 (bypass de fork bomb por fatiamento léxico) e discrepância de flags na CLI.

---

## 1. Diagnóstico do Problema (`OBSERVED`)

O agente do Muse identificou que o comando:
```bash
python3 clearer-engineering/scripts/safety-gate.py --check ':(){ :|:& };:'
```
retornava `decision: allow`, exit code `0` em todos os ambientes (`dev`, `staging`, `production`).

### Causa Raiz Confirmada:
Em `clearer-engineering/scripts/safety-gate.py`, a função `evaluate_command()` executava `split_shell_pipeline(cmd_normalized)` **antes** da avaliação de `CATASTROPHIC_PATTERNS`.
Como a assinatura da fork bomb utiliza os operadores de controle de fluxo de shell `;`, `|` e `&`, o lexer decompunha o comando em quatro fragmentos atômicos:
1. `:(){ :`
2. `:`
3. `}`
4. `:`

Nenhum desses fragmentos isolados casava a regex global `r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"`, provocando o falso negativo (bypass catastrófico).

---

## 2. Correções Efetivadas no Upstream

### 2.1 Fix P2: Early Catastrophic Check sobre a Linha Bruta
Em `clearer-engineering/scripts/safety-gate.py`:
- Inserida checagem prévia imediata de `CATASTROPHIC_PATTERNS` sobre a linha completa (`cmd_normalized` e `cmd_line`) **antes** de invocar a decomposição em pipeline `split_shell_pipeline()`.
- Se qualquer padrão catastrófico (incluindo fork bombs ou comandos com operadores de controle) for casado na string inteira, o retorno imediato é:
  ```json
  {
    "decision": "deny",
    "use_case": "CATASTROPHIC",
    "reason": "[CEH CATASTROPHIC BLOCK] Hard block: Fork bomb detected."
  }
  ```
  com exit code `2`.

### 2.2 Ergonomia CLI: Suporte a `--command` e `--cwd`
No ponto de entrada `main()` de `clearer-engineering/scripts/safety-gate.py`:
- Adicionada a flag `--command` como alias transparente de `--check`:
  `parser.add_argument("--check", "--command", dest="check", type=str, ...)`
- Adicionada a flag `--cwd`:
  `parser.add_argument("--cwd", type=str, default=None, ...)`
  Permite que harnesses externos (como Codex, Muse, Cursor) informem o diretório de ancoragem do projeto sem depender de `os.chdir()` no processo pai.

### 2.3 Cobertura de Testes Automatizados
Atualizado [`clearer-engineering/tests/test_rules_data_infra.py`](../../tests/test_rules_data_infra.py):
- `test_catastrophic_fork_bomb_blocked_in_all_envs`: valida bloqueio incondicional de fork bomb em `development`, `staging` e `production` (`deny` + `CATASTROPHIC`).
- `test_cli_ergonomics_command_and_cwd`: valida execução de `--command` com comandos benignos (exit 0), catastróficos (exit 2) e combinação com `--cwd`.

---

## 3. Evidências de Validação (`OBSERVED`)

1. **Teste Unitário Específico**:
   ```bash
   python3 clearer-engineering/tests/test_rules_data_infra.py
   # Ran 16 tests in 0.351s - OK
   ```

2. **Auditoria Documental e Orçamento**:
   ```bash
   python3 clearer-engineering/scripts/doc-audit.py
   # safety-gate.py: 627 linhas (Teto: 650) - 7/7 SUCESSO
   ```

---

## 4. Orientações para Aplicação no Harness do Muse (`clearer-muse`)

Com o fix consolidado no upstream:

1. **Atualização do Vendoring / Módulo**:
   - Atualize os arquivos `safety-gate.py` e `ceh_core/` no seu projeto copiando a versão atualizada do upstream.
2. **Desativação do Controle Compensatório CC1**:
   - Como o `safety-gate.py` agora realiza a checagem prévia na linha bruta por padrão, você pode **remover o controle compensatório CC1** do seu adapter.
3. **Uso das Flags de CLI**:
   - Você agora pode utilizar indistintamente `--check "<cmd>"` ou `--command "<cmd>"`, além de poder repassar `--cwd "<path>"` opcionalmente.
