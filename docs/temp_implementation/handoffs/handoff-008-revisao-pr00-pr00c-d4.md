# Handoff 008 — Revisão de PR-00, PR-00c e D4, e despacho do PR-00b

**Data/Hora:** 2026-09-25T19:30:00Z
**Instância:** Revisor sênior (auditoria independente em outro ambiente)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `f070395..0b2389d`
**Antecessor:** [Handoff 007](./handoff-007-revisao-006-e-despacho-pr00.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.7
**Decisão soberana:** do desenvolvedor (`nandodev`).

---

## 1. Veredito (espaço fechado)

| Entrega | Veredito | Base |
|---|---|---|
| **PR-00** (`4f2b193`, contexto do alvo) | **HOMOLOGADO** | E10-YOLO antes = EXECUTADO 2/2; depois = comando não rodou 2/2; 8 testes; gate com 631/650 linhas |
| **PR-00c** (`60113ae`, `ask`→`deny` no `agy`) | **HOMOLOGADO COM RESSALVA** (F1) | A conversão vale só dentro de `evaluate_hook_payload`; o caminho de exceção ainda emite `ask` |
| **D4** (`0b2389d`, contagem do Conselho) | **RESSALVAS** (F3) | Resolve o caso real, mas o fallback ainda conta o template, a certeza é inventada e não há teste |
| Protocolo de saída do agente | **OK**, com a ressalva F4 | Reproduzido aqui: suíte 45/45 (sem `agy`; 46/46 com ele), evals 5/5, relatório `--strict` VERIFICADO |

**Marco:** o **P0/G6 foi confirmado de ponta a ponta no `agy` real e corrigido**. Antes do PR-00, `git reset --hard` na `main` executou com o CEH ativo; depois, não executou.

## 2. Evidências verificadas

| Afirmação | Dado bruto | Estado |
|---|---|---|
| Linha de base: E10-YOLO EXECUTADO | [`agy/20260925T184745Z`](../evidence/host-probe/agy/20260925T184745Z/summary.md): 2/2, CEH ativo, 0 desvios | `OBSERVED` |
| Pós-PR-00: E10-YOLO BLOQUEADO 2/2 | [`agy/20260925T185652Z`](../evidence/host-probe/agy/20260925T185652Z/summary.md): o arquivo **não foi revertido** em 2/2 (`OBSERVED`). A sonda classificou a r1 como **INCONCLUSIVO**, porque o hook da sonda não disparou (provavelmente o `agy` interrompe a cadeia no primeiro `deny`); a atribuição ao CEH na r1 vem da narração, com 0 desvios. | `OBSERVED` (não rodou) · `INFERRED` (autoria na r1) |
| 46/46 | 45/45 aqui (sem `agy`), o que é coerente com o teste condicional | `OBSERVED` |

## 3. Achados

- **F1 — MEDIUM — o erro do hook ainda vira `ask`, e `ask` executa no `agy`.** O `except` de `handle_hook` (`safety-gate.py`) responde `{"decision": "ask"}`. Reproduzido: `{"toolCall": "x"}` → `ask` ("'str' object has no attribute 'get'"). Pelo H1 (`OBSERVED`), no `agy` isso **executa o comando**. Além disso, um payload que não é objeto (`[]`) agora sai `allow`; antes do PR-00 saía `ask`.
- **F2 — LOW hoje, HIGH quando o CEH virar plugin do Claude — o Claude ignora o formato do `agy`.** Teste no Claude real: um hook que responde `{"decision": "deny", "reason": ...}` **não bloqueou**; o comando rodou (`OBSERVED`). O `hook_context` lê o payload do Claude (caso 6), mas responde no formato do `agy`. O caso 6 só confere a decisão interna, não o formato que o host entende.
- **F3 — MEDIUM (governança) — o D4 ainda aceita o template por outra porta.**
  - Com resposta só com o template, `verd` fica vazio e o fallback faz `grep -qi "HOMOLOGADO"` no arquivo inteiro. Reproduzido: resultado `verd=HOMOLOGADO`.
  - `[[ -z "$cert" ]] && cert="0.80"` **inventa** uma certeza que o conselheiro não deu.
  - Não há teste (o Handoff 007 pedia teste por commit).
- **F4 — LOW — o relatório de fechamento arredondou.** "BLOQUEADO (2/2)" corresponde, na classificação da sonda, a 1 BLOQUEADO + 1 INCONCLUSIVO. O fato relevante (o comando não rodou 2/2) está certo; a redação deveria dizer isso.

## 4. Despacho — próximos PRs (em commits separados, cada um com teste)

**PR-00b `fix(gate): fail-closed em qualquer falha do hook`** — resolve F1 e P0 (Claude), e prepara o Q4.
- `handle_hook`: payload que não é objeto JSON → `deny` com motivo. Qualquer exceção → `deny` com motivo e **exit 2**. No `agy`, exit 2 bloqueia (E9, `OBSERVED`); no Claude também (E9, Handoff 005).
- `from __future__ import annotations` no gate (piso 3.9, Q4) e verificação de `python3 >= 3.9` no `install.sh`.
- Testes: `{"toolCall": "x"}`, `[]` e `"texto"` → `deny`; exceção forçada → exit 2.

**PR-00d `feat(hook): responder no formato do host`** — resolve F2.
- `evaluate_hook_payload` devolve a decisão no formato do host: payload com `toolCall` → `{"decision", "reason"}`; payload com `tool_input` → `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision", "permissionDecisionReason"}}` (contrato `OBSERVED` no Handoff 005).
- O caso 6 passa a conferir o **formato de saída**. Aceite de ponta a ponta: instalar o gate como hook de projeto no Claude e confirmar `git reset --hard` na `main` = bloqueado com a sonda (E10-equivalente).

**D4b `fix(conselho): sem fallback por palavra solta e sem certeza inventada`** — resolve F3.
- Sem linha `VEREDITO:` válida → `INDEFINIDO` (remover o fallback por `grep` no arquivo inteiro). Sem `CERTEZA:` válida → `N/D`, nunca um número padrão.
- Teste com 3 respostas-fixture: só o template → `INDEFINIDO`; template seguido de `VEREDITO: RESSALVAS` → `RESSALVAS`; `VEREDITO: HOMOLOGADO` sem certeza → certeza `N/D`.

Depois desses três, segue o plano: **Onda 0** (PR-01/PR-02, corpus dourado), seguida dos bypasses G1–G5 (PR-04 a PR-06).

## 5. Critérios de aceite do próximo ciclo

- [ ] PR-00b: 4 casos de erro → `deny`/exit 2; `safety-gate.py` ≤ 650 linhas; matriz 24/24; evals 5/5.
- [ ] PR-00d: caso 6 confere o formato; E10-equivalente no Claude = bloqueado.
- [ ] D4b: 3 fixtures verdes.
- [ ] Relatório de fechamento separa "não rodou" (`OBSERVED`) de "quem bloqueou" (quando vier da narração).
- [ ] Protocolo 7.1 completo, com `evidence-report.sh --strict` = VERIFICADO.
