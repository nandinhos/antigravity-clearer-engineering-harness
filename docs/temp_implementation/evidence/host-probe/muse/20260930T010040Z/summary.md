# Relatório de Evidência: Experimento E1b do Muse (Contrato de Resposta & Isolamento)

**Timestamp:** 20260930T010040Z  
**Host:** Muse Code 1.4.1 (Linux x86_64)  
**Objetivo:** Validar contrato de resposta do Muse em modo headless com isolamento estrito (`clearer-muse` desabilitado) e teste exaustivo das 6 variantes de resposta (`None`, `{}`, `allow`, `decision: block`, `hookSpecificOutput: deny` e `decision: ask`).

---

## 1. Tabela Resumo dos Braços

| Braço | Configuração de Resposta | Sentinela Criado? | Bloqueado? | Veredito |
|---|---|---|---|---|
| `B1-control` | `N/A (sem hook)` | True | **False** | ✔ PASS |
| `B2-allow-empty` | `{}` | True | **False** | ✔ PASS |
| `B3-allow-explicit` | `{"decision": "allow"}` | True | **False** | ✔ PASS |
| `B4-deny-decision` | `{"decision": "block", "reason": "CEH bloqueio de teste (B4)"}` | False | **True** | ✔ PASS |
| `B5-deny-claude-style` | `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "CEH bloqueio Claude-style (B5)"}}` | False | **True** | ✔ PASS |
| `B6-ask` | `{"decision": "ask", "reason": "Confirma\u00e7\u00e3o necess\u00e1ria (B6)"}` | True | **False** | ✔ PASS |

---

## 2. Descobertas do Contrato de Resposta do Muse (`OBSERVED`)

1. **Isolamento Estrito Comprovado:** `clearer-muse` foi explicitamente desabilitado durante toda a bateria, auditado em `plugins_list_before.json` em cada braço individual.
2. **Semântica do Modo Headless:** No Muse headless (`muse exec`), a execução automatizada sem TTY interativo requer a desativação de prompts de aprovação humana no console para evitar travamento por stdin bloqueante, enquanto os hooks de plugin `PreToolUse` mantêm interceptação física 100% ativa.
3. **Comportamento de Permitir (Neutro):**
   - Tanto `{}` quanto `{"decision": "allow"}` resultam em `should_block: false` e não alteram as permissões internas do host. O hook do Muse atua como um portão de guarda estritamente neutro na permissão.
4. **Comportamento de Bloquear (Interceptação Efetiva):**
   - `{"decision": "block", "reason": "..."}`: Bloqueia imediatamente a execução da ferramenta no workspace (sentinela não criado).
   - Formato Claude `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", ...}}`: Reconhecido nativamente pelo validador do Muse, bloqueia imediatamente a ferramenta.
5. **Comportamento de Confirmação (`ask`):**
   - O Muse não possui contrato de confirmação interativa disparado programaticamente por hook (`decision: "ask"` não bloqueia nativamente).
   - **Regra Canônica do Adaptador Muse:** O adaptador do Muse deve mapear `ask → block` (fail-closed), exatamente igual ao Antigravity (`agy`, PR-00c).
