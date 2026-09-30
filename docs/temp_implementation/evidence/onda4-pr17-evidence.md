# Relatório de Evidências — PR-17: Conformidade de Decisão Cross-Host

**Data/Hora:** 2026-10-02T12:00:00Z  
**Branch:** `feature/onda-4`  
**Antecessor:** [Handoff 081](../handoffs/handoff-081-pr16-homologado-despacho-pr17-conformidade.md)  
**Objetivo:** Provar deterministicamente e por testes em processo que todos os três hosts (Google Antigravity, Claude Code e Muse Code) tomam rigorosamente a mesma decisão que o motor agnóstico do CEH Core (`ceh_core.engine`), e que apenas o formato da resposta de renderização varia conforme a tabela observada.

---

## 1. Métricas e Estatísticas de Avaliação In-Process

| Métrica | Valor Observado | Meta / Requisito | Status |
|---|---|---|---|
| **Total de Entradas do Corpus Avaliadas** | **1.024** | 1.024 | ✔ PASS |
| **Hosts Avaliados por Caso** | **3** (Antigravity, Claude Code, Muse) | 3 | ✔ PASS |
| **Total de Avaliações Cross-Host** | **3.072** avaliações | 3.072 | ✔ PASS |
| **Divergências de Decisão Encontradas** | **0** | 0 (Zero-Tolerance) | ✔ PASS |
| **Divergências de Use Case Encontradas** | **0** | 0 | ✔ PASS |
| **Divergências de Renderização Encontradas** | **0** | 0 | ✔ PASS |
| **Tempo de Execução da Suíte de Conformidade** | **~1.8s** (in-process) | < 10s | ✔ PASS |

---

## 2. Validação da Tabela de Render Observada

A conformidade comprovou em 100% dos 1.024 casos que a resposta renderizada segue estritamente a especificação do Handoff 081:

| Decisão | Antigravity | Claude Code | Muse Code |
|---|---|---|---|
| **`allow`** | `{"decision":"allow"}`, exit 0 | `{}`, exit 0 | `{}`, exit 0 |
| **`deny`** | `{"decision":"deny", ...}`, exit 0 | `hookSpecificOutput` com `permissionDecision: deny`, exit 2 | `{"decision":"block", ...}`, exit 0 |
| **`ask`** | vira `deny` (`{"decision":"deny", ...}`), exit 0 | `hookSpecificOutput` com `permissionDecision: ask`, exit 0 | vira `block` (`{"decision":"block", ...}`), exit 0 |

---

## 3. Fidelidade Estrita de Payloads Sintéticos

Comprovado pelo teste unitário `test_synthetic_payload_fidelity` contra os payloads gravados em `fixtures/adapters/<host>/recorded.jsonl`:
- **Antigravity**:
  - Top-level keys: `artifactDirectoryPath`, `conversationId`, `modelName`, `stepIdx`, `toolCall`, `transcriptPath`, `workspacePaths` (idêntico ao gravado).
  - `toolCall.args` (comando): `CommandLine`, `Cwd`, `WaitMsBeforeAsync`, `toolAction`, `toolSummary`.
  - `toolCall.args` (escrita): `CodeContent`, `Description`, `Overwrite`, `TargetFile`, `toolAction`, `toolSummary`.
- **Claude Code**:
  - Top-level keys: `cwd`, `effort`, `hook_event_name`, `permission_mode`, `prompt_id`, `scratchpad_dir`, `session_id`, `tool_input`, `tool_name`, `tool_use_id`, `transcript_path` (idêntico ao gravado).
  - `tool_input` (comando): `command`, `description`.
  - `tool_input` (escrita): `content`, `file_path`.
- **Muse Code**:
  - Top-level keys: `cwd`, `hook_event_name`, `model`, `model_provider`, `permission_mode`, `session_id`, `tool_input`, `tool_name`, `tool_use_id`, `transcript_path`, `turn_id` (idêntico ao gravado).
  - `tool_input` (comando): `command`, `description`, `workdir`.
  - `tool_input` (escrita): `content`, `path`.

---

## 4. Ferramentas de Escrita e Proteção do `.ceh/`

O teste `test_cross_host_conformance_file_tools` validou nos 3 hosts:
- **Alvos protegidos de certificados** (`.ceh/last-ci-run.json`, `.ceh/last-evals-run.json`, `.ceh/sub/cert.json`):
  - Decisão: `deny` com use_case `CERTIFICATE_INTEGRITY`.
  - Antigravity: `{"decision": "deny"}`, exit 0.
  - Claude Code: `hookSpecificOutput` deny, exit 2.
  - Muse: `{"decision": "block"}`, exit 0.
- **Alvos seguros de escrita** (`src/index.ts`, `README.md`):
  - Decisão: `allow` com use_case `GENERAL`.
  - Antigravity: `{"decision": "allow"}`, exit 0.
  - Claude Code: `{}`, exit 0.
  - Muse: `{}`, exit 0.

---

## 5. Falsificabilidade por Mutações em Clone Temporário (Regra AT5)

Executado deterministicamente via `clearer-engineering/tests/tools/test_mutation_p17.py`:
- **Mutação M1 (Muse ignorando `workdir`/`cwd`)**:
  - O código do adaptador foi mutado para forçar `raw_cwd = None` em `resolve_target`.
  - Resultado: `test_cross_host_conformance.py` reprovou imediatamente (`git reset --hard` em dev virou deny no Muse por falta de target, divergindo do motor e dos outros hosts).
  - Status: ✔ **Falsificabilidade comprovada**.
- **Mutação M2 (Claude mapeando `ask` para allow)**:
  - O código de renderização do Claude foi mutado para retornar `{}, 0` quando `decision == "ask"`.
  - Resultado: `test_cross_host_conformance.py` reprovou imediatamente pela quebra da tabela de render em comandos de staging.
  - Status: ✔ **Falsificabilidade comprovada**.

---

## 6. Verificação do Baseline da Onda 4 (`onda4_baseline.py --check`)

- **A1**: 1.024 decisões idênticas, hash `3878d3cc285f7ab6...` (0 alterações).
- **A2a**: 45 ativos não-código byte-idênticos.
- **A2b**: 128 caminhos instalados, 25 novos declarados da Onda 4 (incluindo `test_cross_host_conformance.py` e `test_mutation_p17.py`).
- **A3**: 107 respostas do hook idênticas em exit_code e stdout.
- **A3-muse**: 41 payloads antes e depois idênticos; controle cruzado 7/7 OK.
- **A4**: 0 referências de host fora de `adapters/`, `safety-gate.py` com 94 linhas, `cross_host_conformance_tests_count = 1` (meta $\ge 1$ atingida).

---

## 7. Guia de Novos Hosts

Criado em [docs/adapters/novo-host.md](../adapters/novo-host.md), sintetizando:
- E0/E1 (sondagem e gravação de payload real).
- Contrato de resposta no contexto real de execução (CLI vs IDE).
- Reserva observada por host (`fallback.py`).
- Isolamento de plugins pré-existentes e restauração de estado.
- Confinamento estrito de comandos destrutivos em sandbox temporário.
