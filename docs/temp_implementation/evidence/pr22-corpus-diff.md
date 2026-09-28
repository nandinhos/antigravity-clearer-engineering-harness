# PR-22 — Golden Corpus Diff Audit (AK2)

**Data/Hora:** 2026-09-27T21:17:15-03:00  
**PR:** PR-22 (`feat(gate): cobertura de regras de dados e infraestrutura (AT3) e leituras de .ceh (AM2)`)  
**Linha de Base Homologada:** `d6bf922` (Handoff 047)  
**Total de Comandos Avaliados no Corpus:** 1.012 casos  
**Total de Linhas Alteradas no Gabarito:** 3 linhas (CMD-116)  

---

## 1. Resumo Executivo das Alterações

O Golden Corpus foi reavaliado contra o Safety Gate com as regras do PR-22 (AT3 / AM2).
Houve **zero relaxamentos** no corpus pré-existente.
A única alteração observada consiste no **aperto de segurança estrito** da regra AT3 para o comando `npx prisma migrate reset` (`CMD-116`):

| ID | Comando | Ambiente | Decisão Anterior (`d6bf922`) | Nova Decisão (PR-22) | Direção | Justificativa |
|---|---|---|---|---|---|---|
| `CMD-116-dev` | `npx prisma migrate reset` | `development` | `allow` (`GENERAL`) | `allow` (`DATABASE`) | **Neutro (Classificação)** | Identificação explícita do Caso de Uso `DATABASE` (Banco de Dados). |
| `CMD-116-sta` | `npx prisma migrate reset` | `staging` | `allow` (`GENERAL`) | `ask` (`DATABASE`) | **Aperto de Segurança** | Proteção contra reset acidental de schema em staging (exige 2 alertas). |
| `CMD-116-pro` | `npx prisma migrate reset` | `production` | `allow` (`GENERAL`) | `deny` (`DATABASE`) | **Aperto de Segurança** | Bloqueio incondicional em produção de reset de banco. |

---

## 2. Diff Linha a Linha (`OBSERVED`)

```diff
--- gate_corpus.expected.jsonl (baseline d6bf922)
+++ gate_corpus.expected.jsonl (PR-22)
@@ -346,9 +346,9 @@
 {"command": "npx prisma migrate deploy", "decision": "allow", "env": "development", "has_alerts": false, "id": "CMD-115-dev", "type": "command", "use_case": "GENERAL"}
 {"command": "npx prisma migrate deploy", "decision": "allow", "env": "staging", "has_alerts": false, "id": "CMD-115-sta", "type": "command", "use_case": "GENERAL"}
 {"command": "npx prisma migrate deploy", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-115-pro", "type": "command", "use_case": "GENERAL"}
-{"command": "npx prisma migrate reset", "decision": "allow", "env": "development", "has_alerts": false, "id": "CMD-116-dev", "type": "command", "use_case": "GENERAL"}
-{"command": "npx prisma migrate reset", "decision": "allow", "env": "staging", "has_alerts": false, "id": "CMD-116-sta", "type": "command", "use_case": "GENERAL"}
-{"command": "npx prisma migrate reset", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-116-pro", "type": "command", "use_case": "GENERAL"}
+{"command": "npx prisma migrate reset", "decision": "allow", "env": "development", "has_alerts": false, "id": "CMD-116-dev", "type": "command", "use_case": "DATABASE"}
+{"command": "npx prisma migrate reset", "decision": "ask", "env": "staging", "has_alerts": true, "id": "CMD-116-sta", "type": "command", "use_case": "DATABASE"}
+{"command": "npx prisma migrate reset", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-116-pro", "type": "command", "use_case": "DATABASE"}
 {"command": "alembic upgrade head", "decision": "allow", "env": "development", "has_alerts": false, "id": "CMD-117-dev", "type": "command", "use_case": "GENERAL"}
 {"command": "alembic upgrade head", "decision": "allow", "env": "staging", "has_alerts": false, "id": "CMD-117-sta", "type": "command", "use_case": "GENERAL"}
 {"command": "alembic upgrade head", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-117-pro", "type": "command", "use_case": "GENERAL"}
```

---

## 3. Conformidade

- **Total de Relaxamentos no Corpus:** 0 (zero)
- **Total de Apertos no Corpus:** 2 (`CMD-116-sta`, `CMD-116-pro`)
- **Regeneração e Verificação do Gabarito:** `python3 clearer-engineering/tests/tools/snapshot_gate.py --check` validado com exit code 0 (`1012 avaliações idênticas, diff vazio`).
