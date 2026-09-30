# Relatório Experimental E1: Caracterização de Hook e Payloads Reais do Muse

- **Timestamp**: `20260930T001955Z`
- **Host**: `muse` (Muse Code 1.4.1)
- **Protocolo**: CLEARER Engineering Harness (CEH) — Onda 4 (Fase 0 / A5)
- **Critério**: E1 payload real de hook gravado com contrato de resposta em 3 braços

## 1. Resultados da Matriz Experimental (3 Braços)

| Braço | Descrição | Comportamento do Hook | Exit Code | Invocations Gravadas | Sentinela Criado | Bloqueado? |
|---|---|---|---|---|---|---|
| **B1-control** | Controle: sem hook ativo; ferramentas devem executar livremente | `none` | `0` | `0` | `True` | **NÃO** |
| **B2-allow** | Hook ativo permitindo ({}); ferramentas devem executar e hook deve gravar payloads | `allow` | `0` | `5` | `True` | **NÃO** |
| **B3-deny** | Hook ativo negando ('decision': 'block'); comando deve ser interceptado e impedido de executar | `deny` | `0` | `5` | `False` | **SIM** |

## 2. Contrato de Interceptação do Hook Observado

1. **Recepção de Payloads (`PreToolUse`)**:
   - O Muse invoca o hook passando o payload via `stdin` em JSON.
   - O payload contém: `tool_name` (ex.: `"bash"`), `tool_input` (ex.: `{"command": "...", "workdir": "..."}`), `cwd`, `hook_event_name`, `session_id`, `tool_use_id`, `turn_id`.
   - Variáveis de ambiente fornecidas ao processo do hook: `MUSE_PLUGIN_DATA_DIR`, `MUSE_PLUGIN_ID`, `MUSE_PLUGIN_ROOT`.

2. **Contrato de Resposta (Veredito)**:
   - **Permitir neutro**: Devolver `{}` via stdout com exit code 0. O Muse prossegue com a execução normalmente.
   - **Bloquear efetivamente**: Devolver `{"decision": "block", "reason": "<motivo>"}` via stdout com exit code 0 (ou formato compatível `hookSpecificOutput` com `permissionDecision: "deny"`).
   - O bloqueio impede fisicamente a execução da ferramenta no workspace, mantendo `sentinel_created = False`.

## 3. Total de Payloads Reais Gravados (A5)

- **Total de invocações capturadas**: `10`
- **Arquivo de registro**: `docs/temp_implementation/evidence/host-probe/muse/20260930T001955Z/invocations.jsonl`
