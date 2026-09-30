# Evidência Técnica — PR-13: Motor Agnóstico de Host (Onda 4, Fase 1)

**Data/Hora:** 2026-09-30T02:44:00Z  
**Branch:** `feature/onda-4`  
**Linha de Base:** `v1.4.1` (`e608ea7`)  
**Autor:** Agente Antigravity  
**Revisão:** Handoff 071 (Claude / Revisor Independente)

---

## 1. Sumário Executivo & Resultados (`OBSERVED`)

O PR-13 realiza o desacoplamento formal do motor de decisão de segurança do CLEARER Engineering Harness (CEH), eliminando qualquer conhecimento ou dependência de formatos de host (`toolCall`, `tool_name`, `tool_input`, `hookSpecificOutput`, `CommandLine`) dentro do núcleo de avaliação (`ceh_core/`) e no script principal (`safety-gate.py`).

| Verificação | Critério Handoff 071 | Resultado Observado | Status |
|---|---|---|---|
| **A1 (Decisões do Gate)** | 1.024 decisões idênticas | 1.024 avaliações, sha256 `3878d3cc285f7ab6...` | ✔ **PASS** |
| **A2a (Ativos Não-Código)** | 39 ativos byte-idênticos | 39 arquivos byte-a-byte idênticos, aliases idênticos | ✔ **PASS** |
| **A2b (Manifesto de Arquivos)** | Somente arquivos declarados | 108 caminhos instalados (5 novos declarados da Onda 4) | ✔ **PASS** |
| **A3 (Respostas do Hook)** | 107 respostas idênticas | 107 respostas idênticas em exit_code e stdout | ✔ **PASS** |
| **A3-muse (Marcador Antes)** | 41 payloads inalterados | 41 payloads do Muse confirmados com deny/exit 2 | ✔ **PASS** |
| **A4 (Acoplamento de Host)** | 0 no gate, 0 no ceh_core | `safety_gate=0 refs`, `ceh_core=0 refs`, `hook_context=56 refs` | ✔ **PASS** |
| **Orçamento de Linhas** | <= 650 gate, <= 300 ceh_core | `safety-gate.py=61`, `engine.py=275`, `subcommand.py=280` | ✔ **PASS** |
| **Suíte Canônica de Testes** | 67/67 testes verdes | 67/67 PASS (100% de sucesso) | ✔ **PASS** |
| **Auditoria Documental** | 7/7 checagens aprovadas | `doc-audit.py` exit 0 (7/7 PASS) | ✔ **PASS** |
| **Falsificabilidade (Mutações)** | 2 mutações reprovam | M1 e M2 rejeitadas com exit 1 em `test_mutation_p13.py` | ✔ **PASS** |

---

## 2. Métricas de Acoplamento A4: Antes × Depois (`OBSERVED`)

Conforme exigido pelo Handoff 071, o núcleo agora é 100% agnóstico em relação a qualquer formato de host:

| Métrica | Retrato v1.4.1 (Antes PR-13) | PR-13 (Depois) | Variação |
|---|---|---|---|
| **`safety-gate.py` (termos de host)** | 4 referências | **0 referências** | **-4 (-100%)** |
| **`ceh_core/` (termos de host)** | N/A (não isolado) | **0 referências** | **0 absoluto** |
| **`safety-gate.py` (linhas de código)** | 636 linhas | **61 linhas** | **-575 (-90.4%)** |
| **`hook_context.py` (concentração)** | 53 referências | **56 referências** | **+3** (centralizado) |

### Detalhamento dos 5 Termos Monitorados em `A4`:
- `toolCall`: 0 no `safety-gate.py`, 0 no `ceh_core/` (18 concentrados no `hook_context.py`)
- `tool_name`: 0 no `safety-gate.py`, 0 no `ceh_core/` (24 concentrados no `hook_context.py`)
- `tool_input`: 0 no `safety-gate.py`, 0 no `ceh_core/` (8 concentrados no `hook_context.py`)
- `hookSpecificOutput`: 0 no `safety-gate.py`, 0 no `ceh_core/` (4 concentrados no `hook_context.py`)
- `CommandLine`: 0 no `safety-gate.py`, 0 no `ceh_core/` (2 concentrados no `hook_context.py`)

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
  ✔ A2a OK (39 ativos não-código byte-idênticos, aliases idênticos)
[3/5] Verificando A2b (Estrutura/manifesto de arquivos instalados)...
  ✔ A2b OK (108 caminhos instalados, 5 novos declarados da Onda 4)
[4/5] Verificando A3 (Respostas do hook: agy + claude)...
  ✔ A3 OK (107 respostas do hook idênticas em exit_code e stdout)
[5/5] Verificando A3-muse (Marcador do antes para Muse)...
  ✔ A3-muse OK (41 payloads do Muse confirmados com deny/2 no marcador do antes)
Verificando A4 (Acoplamento)...
  • A4 Atual (PR-13): hook_context=56 refs, safety_gate=0 refs, ceh_core=0 refs, safety_gate=61 linhas
  • A4 Retrato v1.4.1 (antes PR-13): hook_context=53 refs, safety_gate=4 refs, 636 linhas
  ✔ A4 OK (Meta do PR-13 atingida: 0 referências de host no safety-gate e 0 no ceh_core)

✔ SUCESSO: Todas as 5 medições (A1-A4 + A3-muse) conferem rigorosamente com o retrato v1.4.0!
```

---

## 4. Provas por Mutação e Falsificabilidade (`test_mutation_p13.py`)

Comando executado:
```bash
python3 clearer-engineering/tests/tools/test_mutation_p13.py
```

Saída observada (`exit 0`):
```text
=== Executando Provas de Mutação do PR-13 (Falsificabilidade) ===
✔ Prova por mutação M1 aprovada: onda4_baseline.py rejeitou 'toolCall' em ceh_core/ com exit 1.
✔ Prova por mutação M2 aprovada: onda4_baseline.py detectou quebra do hook do Antigravity em A3 com exit 1.
=== Todas as 2 Provas de Mutação do PR-13 passaram com sucesso! ===
```

- **Mutação M1:** Injeção intencional de `# Prova: toolCall` em `ceh_core/engine.py`. O `onda4_baseline.py --check` falha imediatamente reportando `ceh_core possui referências de host! Meta do PR-13 é 0`.
- **Mutação M2:** Alteração do retorno de deny do Antigravity em `hook_context.py` de `exit 0` para `exit 2`. O `onda4_baseline.py --check` rejeita imediatamente com divergências no baseline de respostas A3.

---

## 5. Resolução Formal das Ressalvas da Revisão (Handoff 071)

- **BC1 (Processo, Média):**
  - O status do Handoff 070 foi atualizado de "Homologado" para: `Status: Relatório do agente — aguardando revisão`.
  - A seção temporária 0.65 criada no plano de implementação foi removida e substituída pela seção 0.67 oficial enviada pelo revisor independente no commit `64aab9c`.
- **BC2 (Relatório Impreciso, Baixa):**
  - Registrado explicitamente: as 16 linhas adicionais alteradas no A3 durante a regeneração do retrato diferem exclusivamente no `payload_hash`, decorrente do mascaramento determinístico de caminhos absolutos locais (`/home/<user>`) aplicado na Fase 0c (P2). Os códigos de saída (`exit_code`) e o `stdout` mantiveram-se rigorosamente idênticos.
- **BC3 (Canário sem Registro, Baixa):**
  - Trecho do log oficial da IDE versionando o bloqueio do canário `touch .ceh/canario-hook` com caminhos mascarados devidamente arquivado.
- **BC4 (Nome Enganoso, Baixa):**
  - O campo `source_version: "v1.4.1"` foi incorporado no cálculo e arquivo do A4 (`A4_coupling_metrics.json`), identificando de forma unívoca a versão de origem do retrato.
- **BB1 (Nomenclatura do Teste 23):**
  - O método `test_case_23_ask_decision_mutation_proof` em `clearer-engineering/tests/test_hook_context.py:467` foi renomeado para `test_case_23_ask_decision_exit_0`.

---

## 6. Auditoria de Linhas e Arquitetura (`doc-audit.py`)

Todos os módulos respeitam estritamente os orçamentos arquiteturais definidos:
- `safety-gate.py`: 61 linhas (Teto: 650)
- `ceh_core/engine.py`: 275 linhas (Teto: 300)
- `ceh_core/subcommand.py`: 280 linhas (Teto: 300)
- `ceh_core/git_invocation.py`: 83 linhas (Teto: 300)
- Ponto único de normalização (`ceh_core/normalize.py`): validado e aprovado em `test_normalization_structural.py` (6/6 PASS).
