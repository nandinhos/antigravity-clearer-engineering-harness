# Evidência Técnica — PR-14/15: Contrato de Adaptadores de Host (Onda 4, Fase 2)

**Data/Hora:** 2026-09-30T14:18:00Z  
**Branch:** `feature/onda-4`  
**Linha de Base:** `v1.4.1` (`e608ea7`)  
**Autor:** Agente Antigravity  
**Revisão de Referência:** Handoff 073 / Handoff 074 (Claude / Revisor Independente)

---

## 1. Sumário Executivo & Resultados (`OBSERVED`)

O PR-14/15 implementa a arquitetura formal de adaptadores de host para o CLEARER Engineering Harness (CEH), eliminando qualquer acoplamento de hosts dentro de `hook_context.py` e encapsulando todo o conhecimento de payloads, ferramentas, diretórios e convenções de resposta na nova pasta `clearer-engineering/scripts/adapters/`.

| Verificação | Critério Handoff 073 (§4) | Resultado Observado | Status |
|---|---|---|---|
| **Contrato `HostAdapter`** | Base abstrata com detect, parse, resolve_target, render, render_error | Criado em `adapters/base.py` | ✔ **PASS** |
| **Adaptadores Isolados** | Antigravity e Claude Code isolados em `adapters/` | Implementados em `adapters/antigravity.py` e `adapters/claude_code.py` | ✔ **PASS** |
| **Despachante Agnóstico** | `hook_context.py` sem termos de host (`toolCall`, `tool_name`, `tool_input`, `hookSpecificOutput`, `CommandLine`) | **0 referências** a termos de host em `hook_context.py` | ✔ **PASS** |
| **A1 (Decisões do Gate)** | 1.024 decisões idênticas | 1.024 avaliações idênticas, hash `3878d3cc285f7ab6...` | ✔ **PASS** |
| **A2a (Ativos Não-Código)** | Ativos byte-idênticos | 41 arquivos byte-a-byte idênticos, aliases idênticos | ✔ **PASS** |
| **A2b (Manifesto de Arquivos)** | Somente arquivos declarados | 117 caminhos instalados (14 novos declarados da Onda 4) | ✔ **PASS** |
| **A3 (Respostas do Hook)** | 107 respostas idênticas | 107 respostas idênticas em exit_code e stdout | ✔ **PASS** |
| **A3-muse (Marcador Antes)** | 41 payloads inalterados | 41 payloads do Muse confirmados com deny/exit 2 | ✔ **PASS** |
| **A4 (Acoplamento de Host)** | 0 fora de `adapters/`, medindo `adapters/` separadamente | `safety_gate=0 refs`, `ceh_core=0 refs`, `hook_context=0 refs`, `adapters=48 refs` | ✔ **PASS** |
| **Fixtures por Host** | Fixtures JSONL por host em `tests/fixtures/adapters/` | Criadas em `tests/fixtures/adapters/antigravity/` e `claude_code/` | ✔ **PASS** |
| **Bateria Dedicada de Testes** | Suíte de adaptadores unitária | `test_adapters.py` com 9 casos em matriz | ✔ **PASS** |
| **Orçamento de Linhas** | <= 100 safety-gate, <= 300 módulos core | `safety-gate.py=100`, `hook_context.py=217`, `adapters/*.py <= 165` | ✔ **PASS** |
| **Falsificabilidade (Mutações)** | 2 mutações reprovam em clone temporário (Regra AT5) | M1 e M2 rejeitadas em `test_mutation_p14.py` | ✔ **PASS** |
| **Suíte Canônica de Testes** | 70/70 testes verdes | 70/70 PASS (100% de sucesso) | ✔ **PASS** |
| **Auditoria Documental** | 7/7 checagens aprovadas | `doc-audit.py` exit 0 (7/7 PASS) | ✔ **PASS** |

---

## 2. Métricas de Acoplamento A4: Antes × Depois (`OBSERVED`)

O desacoplamento de hosts foi completado com 100% de sucesso: todo e qualquer formato ou termo de host foi erradicado de `safety-gate.py`, `ceh_core/` e `hook_context.py`.

| Métrica | Retrato v1.4.1 (Antes PR-13) | PR-13 | PR-14/15 (Atual) | Redução Líquida Fora de `adapters/` |
|---|---|---|---|---|
| **`safety-gate.py`** | 4 referências | 0 referências | **0 referências** | **-100%** |
| **`ceh_core/`** | N/A (não isolado) | 0 referências | **0 referências** | **0 absoluto** |
| **`hook_context.py`** | 53 referências | 56 referências | **0 referências** | **-100% (56 -> 0)** |
| **`adapters/` (isolamento)** | N/A | N/A | **48 referências** | **Isolamento 100%** |

### Detalhamento dos 5 Termos Monitorados em `A4`:
- `toolCall`: 0 no `safety-gate.py`, 0 no `ceh_core/`, 0 no `hook_context.py` (isolado em `adapters/antigravity.py`)
- `tool_name`: 0 no `safety-gate.py`, 0 no `ceh_core/`, 0 no `hook_context.py` (isolado em `adapters/`)
- `tool_input`: 0 no `safety-gate.py`, 0 no `ceh_core/`, 0 no `hook_context.py` (isolado em `adapters/claude_code.py`)
- `hookSpecificOutput`: 0 no `safety-gate.py`, 0 no `ceh_core/`, 0 no `hook_context.py` (isolado em `adapters/claude_code.py`)
- `CommandLine`: 0 no `safety-gate.py`, 0 no `ceh_core/`, 0 no `hook_context.py` (isolado em `adapters/antigravity.py` e `adapters/claude_code.py`)

---

## 3. Saída da Rede de Não-Regressão (`onda4_baseline.py --check`)

Comando executado:
```bash
python3 clearer-engineering/tests/tools/onda4_baseline.py --check
```

Saída observada (`exit 0`):
```text
=== [Onda 4 Baseline: Verificando contra retrato da v1.4.0] ===
[1/5] Verificando A1 (Decisões do gate)...
  ✔ A1 OK (1024 decisões idênticas, hash 3878d3cc285f7ab6...)
[2/5] Verificando A2a (Ativos não-código byte-a-byte)...
  ✔ A2a OK (41 ativos não-código byte-idênticos, aliases idênticos)
[3/5] Verificando A2b (Estrutura/manifesto de arquivos instalados)...
  ✔ A2b OK (117 caminhos instalados, 14 novos declarados da Onda 4)
[4/5] Verificando A3 (Respostas do hook: agy + claude)...
  ✔ A3 OK (107 respostas do hook idênticas em exit_code e stdout)
[5/5] Verificando A3-muse (Marcador do antes para Muse)...
  ✔ A3-muse OK (41 payloads do Muse confirmados com deny/2 no marcador do antes)
Verificando A4 (Acoplamento)...
  • A4 Atual (PR-14/15): hook_context=0 refs, safety_gate=0 refs, ceh_core=0 refs, safety_gate=100 linhas, adapters=48 refs
  • A4 Retrato v1.4.1 (antes PR-13): hook_context=53 refs, safety_gate=4 refs, 636 linhas
  ✔ A4 OK (Meta do PR-14/15 atingida: 0 referências de host fora de adapters/; adapters/ isola 48 termos)

✔ SUCESSO: Todas as 5 medições (A1-A4 + A3-muse) conferem rigorosamente com o retrato v1.4.0!
```

---

## 4. Provas por Mutação e Falsificabilidade (`test_mutation_p14.py`)

Conforme a regra **AT5** (Handoff 046 / Handoff 072), todas as mutações são testadas estritamente em clones descartáveis (`tempfile.TemporaryDirectory()`).

Comando executado:
```bash
python3 clearer-engineering/tests/tools/test_mutation_p14.py
```

Saída observada (`exit 0`):
```text
=== [CEH PR-14/15: Provas de Falsificabilidade por Mutação (Regra AT5)] ===
✔ Prova por mutação M1 aprovada: test_adapters.py rejeitou AntigravityAdapter com exit 2 (em clone temporário).
✔ Prova por mutação M2 aprovada: rejeitou ClaudeCodeAdapter com cwd ignorado (em clone temporário).

[SUCESSO] Todas as 2 mutações do PR-14/15 foram falsificadas e detectadas pelas baterias de teste!
```

---

## 5. Auditoria Estrutural Documental (`doc-audit.py`)

Comando executado:
```bash
python3 clearer-engineering/scripts/doc-audit.py
```

Saída observada (`exit 0`):
```text
=== [CEH Bounded Document Structure Audit] ===
Repositório: /caminho/para/repositorio
Alvo principal: docs/plano-validacao-revisao-conselho-seniors.md
--------------------------------------------------
[1/7] Verificando taxonomia de estados permitidos...
  • Estados permitidos normativos identificados: ['Inconclusivo', 'Inspeção estática', 'Pendente', 'Refutado', 'Reproduzido', 'Reproduzido e corrigido']
[2/7] Verificando consistência da tabela de achados (R1 a R10)...
  • Todos os 10 achados (R1 a R10) possuem estados normativos válidos e consistentes com o claim global.
[3/7] Verificando existência física de arquivos de evidência citados...
  • Todos os 20 links de evidências apontam para arquivos físicos existentes.
[4/7] Verificando portabilidade de links e ausência de session IDs na documentação...
  • Zero caminhos absolutos locais ou session IDs recentes detectados em docs/.
[5/7] Verificando existência de commits citados no Git local...
  • Todos os commits citados (bb61fe7, b7df47d, 8fbb318, 1c9a0d2) foram confirmados no Git local.
[6/7] Verificando consistência em handoffs...
  • Handoffs devidamente sincronizados com as autorizações e commits consolidados.
[7/7] Verificando orçamento de linhas dos componentes core...
  • safety-gate.py: 100 linhas (Teto: 650)
  • test-runner.sh: 188 linhas (Teto: 200)
  • ceh_core/engine.py: 275 linhas (Teto: 300)
  • ceh_core/environment.py: 291 linhas (Teto: 300)
  • ceh_core/find.py: 201 linhas (Teto: 300)
  • ceh_core/git.py: 287 linhas (Teto: 300)
  • ceh_core/git_invocation.py: 83 linhas (Teto: 300)
  • ceh_core/interpreters.py: 253 linhas (Teto: 300)
  • ceh_core/interpreters_extra.py: 263 linhas (Teto: 300)
  • ceh_core/lexer.py: 286 linhas (Teto: 300)
  • ceh_core/normalize.py: 176 linhas (Teto: 300)
  • ceh_core/push.py: 271 linhas (Teto: 300)
  • ceh_core/redact.py: 82 linhas (Teto: 300)
  • ceh_core/rm.py: 269 linhas (Teto: 300)
  • ceh_core/rules.py: 230 linhas (Teto: 300)
  • ceh_core/subcommand.py: 280 linhas (Teto: 300)
--------------------------------------------------
SUCESSO: 7/7 checagens estruturais documentais passaram.
Auditoria estrutural documental APROVADA; coerência semântica integral não avaliada.
```

---

## 6. Resultado da Suíte Canônica (`test-runner.sh`)

Comando executado:
```bash
bash clearer-engineering/scripts/test-runner.sh
```

Saída observada (`exit 0`):
```text
============================================================
TEST RESULTS SUMMARY:
Total Tests:   70
Passed Tests:  70
Failed Tests:  0
============================================================
ALL CEH HARNESS TESTS PASSED SUCCESSFULLY (100%)

==========================================
EXIT CODE: 0
STATUS:    PASS
==========================================
```
