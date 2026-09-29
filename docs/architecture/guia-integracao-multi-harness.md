# Guia de Integração Multi-Harness — CEH Núcleo Portável (Onda 4)

Este documento é a especificação canônica para plugar o motor de políticas do **CLEARER Engineering Harness (CEH)** em agentes externos (como Muse, Codex, Claude Code, Cursor e terminais interativos).

Para o passo a passo detalhado e contratos de execução, consulte o playbook completo em:
👉 [Handoff 060 — Playbook Agnóstico de Integração Multi-Harness](../temp_implementation/handoffs/handoff-060-integracao-agnostica-multi-harness.md)

---

## Síntese de Integração em 3 Passos

1. **Núcleo Agnóstico (`ceh_core/`):**
   - 100% Python stdlib-only (Python 3.9+).
   - Zero dependências de terceiros.
   - Ponto único de verdade para parsing de shell, classificação de ambiente (`DEV`/`STAGING`/`PROD`) e governança de comandos destrutivos (`rm`, `git`, `push`).

2. **Interceptação no Host (Safety Gate):**
   - Invocação via CLI: `python3 safety-gate.py --check "<comando>"` (ou `--command "<comando>"`) `[--env <ENV>]` `[--cwd <DIR>]`.
   - Códigos de saída universais no modo `--check`/`--command`: `0 = ALLOW`, `1 = ASK` (exige aprovação humana), `2 = DENY` (bloqueio incondicional).
   - Invocação via Hook (stdin): Envia payload JSON via pipe; veredito emitido em linha ou em JSON estruturado com fail-closed.

3. **Instruções de Sistema (Protocolo CLEARER):**
   - Adotar [`clearer-engineering/rules/AGENTS.md`](../../clearer-engineering/rules/AGENTS.md) como prompt de sistema no harness de destino.
