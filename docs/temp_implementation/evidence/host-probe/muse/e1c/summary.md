# Relatório de Evidência: Experimento E1c (Reserva do Shim no Muse)

**Data/Hora:** 2026-09-30T16:29:46Z  
**Host:** Muse Code 1.4.1 (1.4.1-R4503.1)  
**Referência:** Handoff 077 (Ressalva BH2)  
**Formato Testado:** `{"decision": "deny", "reason": "..."}` com **exit code 0**  

---

## 1. Tabela Comparativa de Bloqueios no Muse (E1b + E1c)

| Experimento | Formato Retornado pelo Hook | Exit Code | Sentinela Criado? | Bloqueado pelo Muse? | Comportamento Observado |
|---|---|---|---|---|---|
| **E1b (B4)** | `{"decision": "block", "reason": "..."}` | 0 | False | **SIM** | Bloqueio nativo do Muse |
| **E1b (B5)** | `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` | 0 | False | **SIM** | Reconhecido pelo parser Claude do Muse |
| **E1c (Novo)** | `{"decision": "deny", "reason": "..."}` | 0 | True | **NÃO** | FALHA: Nao bloqueou; executou a ferramenta |

## 2. Diagnóstico Técnico

- **Sentinela criado:** `True`
- **Bloqueio efetivo:** `FALHOU EM BLOQUEAR (fail-open)`
- **Saída bruta do CLI:** Arquivo [`cli_output.txt`](./cli_output.txt)
- **Payloads registrados:** Arquivo [`e1c_invocations.jsonl`](./e1c_invocations.jsonl)

## 3. Conclusão e Veredito para o Handoff 077 / BH2

O formato `{"decision": "deny"}` NÃO bloqueia no Muse. O shim precisará adotar formato universal compatível nos 3 hosts conforme deliberação da revisão.
