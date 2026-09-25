# Handoff 009 — Revisão de PR-00b, PR-00d e D4b, e despacho do PR-00e

**Data/Hora:** 2026-09-25T20:00:00Z
**Instância:** Revisor sênior (auditoria independente em outro ambiente)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `b077ea9..3435c19`
**Antecessor:** [Handoff 008](./handoff-008-revisao-pr00-pr00c-d4.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.8
**Decisão soberana:** do desenvolvedor (`nandodev`).

---

## 1. Veredito (espaço fechado)

| Entrega | Veredito | Base |
|---|---|---|
| **PR-00b** (`7afb340`) | **HOMOLOGADO** | Payload que não é objeto e exceções → `deny` + exit 2 (`SystemExit` não é capturado pelo `except Exception`); `__future__` presente; `install.sh` exige 3.9+; `test_hook_context` 13/13 **também em Python 3.9** |
| **PR-00d** (`8b7d757`) | **HOMOLOGADO COM RESSALVA CRÍTICA** (F6) e **aceite inválido** (F5) | O formato `hookSpecificOutput` está correto para `deny`; `allow` no Claude aumenta privilégios |
| **D4b** (`3435c19`) | **HOMOLOGADO** | Só `HOMOLOGADO/RESSALVAS/REJEITADO` são aceitos; qualquer outro valor vira `INDEFINIDO`; certeza ausente vira `N/D`; 3/3 fixtures (também em 3.9) |
| Protocolo de saída | **OK** | Reproduzido aqui: suíte 46/46 (sem `agy`; 47 com ele), evals 5/5, gate com 641/650 linhas |

## 2. Achados (Claude Code real, com grupo de controle)

- **F5 — o aceite de ponta a ponta do PR-00d não prova o gate.** O script inline que o agente usou considerou "arquivo continua v2" como bloqueio. No controle **sem hook**, o arquivo **também** continuou v2: o próprio modelo pediu confirmação ("Há uma alteração não commitada... Você confirma?"). Com o gate, a saída menciona o hook, então a atribuição é `INFERRED` pela narração. O script também não foi commitado como evidência.
- **F6 — HIGH (desenho) — `allow` no formato do Claude é aprovação automática.** Com o controle, `OBSERVED`:

  | Cenário (headless, sem `--allowedTools`) | `touch permitido.txt` |
  |---|---|
  | Sem hook | **NÃO rodou**: o Claude pediu aprovação |
  | Com o hook do CEH (`permissionDecision: "allow"`) | **RODOU**: aprovado automaticamente |

  Instalado no Claude, o gate aprovaria sozinho **todo comando que não está na sua lista de destrutivos** (`curl … | sh`, leitura de `.env`, rede), comandos que o usuário teria de aprovar. No `agy` isso não acontece: no E10 do Handoff 006, o hook respondeu `allow` e mesmo assim o `agy` negou por permissão headless (`OBSERVED`).
  **Exposição atual: baixa.** O instalador ainda não registra o CEH no Claude; o risco existe para quem ligar o hook manualmente, como no teste do agente.

## 3. Despacho

**PR-00e `fix(hook): no Claude, o gate nunca aprova — só nega`** — resolve F6.
- Em `format_host_response`, para payload do Claude com decisão `allow`: **não emitir `permissionDecision`**. Saída vazia com exit 0 devolve o fluxo normal de permissões ao Claude. Para `deny` e `ask`, manter `hookSpecificOutput`.
- O formato do `agy` segue inalterado: lá o `allow` do hook não passa por cima da permissão do host (`OBSERVED`).
- Testes: allow no Claude → saída sem `permissionDecision`; deny/ask no Claude → `hookSpecificOutput`; allow no `agy` → `{"decision": "allow"}`.
- **Aceite com controle** (o que invalida o F5), em 3 execuções no Claude headless sem pré-aprovação:
  1. Sem hook: `touch` **não roda** (pede aprovação).
  2. Com o hook do CEH: `touch` **continua não rodando** (o CEH não aprova mais).
  3. Com o hook do CEH e `--allowedTools Bash`, pedindo `git reset --hard` na `main` **com consentimento explícito no prompt** ("confirmo o descarte"): **não roda**. Na variante sem hook e com o mesmo prompt, **roda**; esse é o controle que prova que foi o gate.
  Gravar as saídas em `docs/temp_implementation/evidence/host-probe/claude/pr00e-<ts>/`.

Depois do PR-00e, a fila P0 do plano está fechada: segue a **Onda 0** (PR-01 suíte hermética, PR-02 corpus dourado com G1–G7 em RED).

## 4. Critérios de aceite

- [ ] PR-00e: 3 testes unitários e 3 execuções de aceite com controle, commitadas.
- [ ] Relatório de fechamento com as afirmações do PR-00e apontando para os arquivos de evidência do aceite.
- [ ] Protocolo 7.1 completo, com `evidence-report.sh --strict` = VERIFICADO.
