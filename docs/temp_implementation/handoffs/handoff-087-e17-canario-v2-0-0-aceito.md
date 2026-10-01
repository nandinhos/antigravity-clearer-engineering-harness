# Handoff 087 — E17 (canário da v2.0.0 na IDE) **aceita**; ciclo da v2.0.0 fechado

**Data/Hora:** 2026-10-01T10:00:00Z
**Instância:** Revisor independente (Claude)
**Commit revisado:** `c413d85` (`main`) — `docs/temp_implementation/evidence/e17-canario-bloqueio-v2-0-0.md`
**Antecessor:** [Handoff 086](./handoff-086-onda4-encerrada-v2-0-0.md)

---

## 1. Verificação (`OBSERVED`)

| Item | Resultado |
|---|---|
| `sha256` do `safety-gate.py` na tag `v2.0.0` (calculado nesta revisão) | `f02f5ae51a30…` |
| `sha256` do gate instalado registrado na E17 | `f02f5ae51a30…` — **igual** |
| Sequência temporal | hash às 22:23:00Z → chamada da ferramenta às 22:23:13Z → `ls -la .ceh/` às 22:23:20Z |
| Resposta da IDE | "tool call denied with reason: [CEH CERTIFICATE INTEGRITY - G9/AL1] …", no mesmo formato bruto da E13 (braço deny/0) e da E14 |
| `.ceh/` antes e depois | sem `canario-hook` |
| Commit | só a evidência nova (1 arquivo) |

**E17: ACEITA.** A v2.0.0 oficial (motor agnóstico + `AntigravityAdapter`) bloqueia na IDE do Antigravity de ponta a ponta.

## 2. Ressalvas baixas

- **BK1:** a E14 citava os passos da transcrição da IDE (3328/3329); a E17 não cita. Acrescente o índice do passo da chamada e o da resposta, para que o registro possa ser cruzado com a transcrição.
- **BK2:** o commit foi direto para a `main`, sem PR. Era só documentação, mas reforça a sugestão AY2 (Handoff 063, ainda aberta): ligar a proteção da `main`, com PR obrigatório e os 4 jobs `Validate`.

## 3. Estado

A v2.0.0 está publicada, homologada e verificada na IDE. A linha de base continua em `9385bf7` (o `c413d85` não muda código).

Próximos passos sugeridos (Handoff 086, §4): proteção da `main`, Codex CLI como 4º host pelo guia, e troca do `clearer-muse` vendorizado pelo pacote gerado.
