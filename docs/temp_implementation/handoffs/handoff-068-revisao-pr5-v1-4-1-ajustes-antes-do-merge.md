# Handoff 068 — Revisão do PR #5 (v1.4.1): E13 aceita; correção **quase pronta**, com dois ajustes bloqueantes antes do merge

**Data/Hora:** 2026-09-30T21:00:00Z
**Instância:** Revisor independente (Claude)
**PR revisado:** [#5](https://github.com/nandinhos/antigravity-clearer-engineering-harness/pull/5) — `claude/fix-hook-ide-v1.4.1` → `main`, commits `fe3687b`, `ae46de7`, `8c958cc`, `b823a2c`
**CI:** [run 36665666325](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36665666325) = success (4/4)
**Antecessor:** [Handoff 067](./handoff-067-fase0c-hook-fail-open-na-ide-antigravity.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. Veredito

| Item | Veredito |
|---|---|
| **E13** (IDE do Antigravity 2.5.5) | ✅ **aceita**: 6 braços + braço oficial, com diff do gate instalado e payload real. Defeito `OBSERVED` de ponta a ponta |
| Desenho da correção (deny do agy com exit 0, Claude com exit 2) | ✅ correto |
| Prova por mutação (independente, num clone) | ✅ voltar `_exit_deny_or_error` para `sys.exit(2)` reprova **7** testes do `test_hook_context.py` e **1** do `test_cert_protection.py` |
| ADR 007 (limites da IDE: timeout, Python ausente, erro de sintaxe) | ✅ |
| AZ1–AZ3 | ✅ |
| **Merge** | ⛔ **ainda não**: B1 e B2 abaixo, mais três ajustes baixos |

## 2. Bloqueantes

### B1 — O ambiente se sobrepõe ao payload (fail-open reaberto) — **HIGH**

`_is_claude_host` devolve verdadeiro se **qualquer** das variáveis `CLAUDECODE`, `CLAUDE_PROJECT_DIR` ou `CLAUDE_PID` existir, **mesmo com `toolCall` no payload**. Reprodução (`OBSERVED`):

| Payload | Ambiente | Exit |
|---|---|---|
| agy (`toolCall`, deny) | sem variáveis do Claude | 0 ✅ |
| agy (`toolCall`, deny) | `CLAUDECODE=1` | **2** → na IDE, executa |

Uma IDE aberta a partir de um terminal que herdou essas variáveis volta ao fail-open. O mesmo defeito deixa a **suíte não hermética**: rodando o `test_hook_context.py` num ambiente do Claude Code, **7 testes reprovam**.

**Correção:**

1. **O payload decide.** Com `toolCall` → Antigravity (exit 0). Com `tool_name`/`hook_event_name` e sem `toolCall` → Claude (exit 2).
2. As variáveis de ambiente só valem quando o payload **não identifica** o host (vazio, não JSON, não objeto).
3. Nos testes, `_run_gate_hook` **remove** as variáveis `CLAUDE*` por padrão, e um teste novo roda o payload do agy com `CLAUDECODE=1` e exige exit 0.

A E13 confirma que o payload da IDE **sempre** traz `toolCall` (22 invocações), então a regra 1 basta para a IDE.

### B2 — `ask` sai com exit 1 — **HIGH** (anterior à v1.4.1, mesma classe de defeito)

`handle_hook` termina `ask` com `sys.exit(1)`. No agy isso não importa: o `ask` é convertido em deny antes (PR-00c). No **Claude Code**, porém, código de saída diferente de 0 e de 2 é "erro não bloqueante": o JSON do stdout **não é lido** e a ferramenta segue o fluxo normal. A decisão `ask` do CEH (homologação/staging) é ignorada.

- **Status:** `INFERRED`, pelo contrato documentado do Claude Code. No projeto, o E6 do Handoff 005 mostrou que o **mesmo JSON de `ask` com exit 0 bloqueia** sem humano presente (`OBSERVED`).
- **Correção:** `ask` sai com **exit 0** (o JSON já está no formato do host). Teste por subprocesso: payload do Claude num cenário de `ask` → exit 0 com `permissionDecision: "ask"`. Prova por mutação: voltar o exit 1 reprova.

## 3. Ajustes baixos (no mesmo PR)

- **BA1:** o README ainda fixa a instalação em `v1.4.0` (`README.md:45-46`). Troque para `v1.4.1`; senão, a instalação fixada entrega a versão vulnerável.
- **BA2:** o `test_case_20_mutation_proof_agy_exit2_fails` não é prova por mutação, é uma asserção comum. Renomeie o teste (por exemplo, `test_case_20_agy_deny_exit_0`) e registre a prova real (a mutação da §1) na evidência.
- **BA3:** a E13 versiona o `conversationId` real da IDE (no campo e dentro de `transcriptPath` e `artifactDirectoryPath`). Mascare-o com um marcador estável (`conv-1`), como no C5.

## 4. Registro para a Onda 4 (sem ação agora)

O payload do **Muse** traz `hook_event_name`, então a regra do Claude o classifica como Claude (exit 2). Hoje isso não muda nada: o Muse recebe deny para todas as ferramentas. Mas o E1b só gravou respostas com exit 0, e o comportamento do Muse com exit 2 não foi observado. No **PR-15b**, o adaptador do Muse precisa ser reconhecido **antes** da regra do Claude e responder com o formato e o código de saída observados no E1b (`{"decision":"block"}` com exit 0).

## 5. Sequência

1. O agente aplica B1, B2 e BA1–BA3 no PR #5, com CI verde (4/4).
2. Revisão curta (Claude ou Codex) → homologação.
3. O **desenvolvedor** faz o merge, cria a tag `v1.4.1` e reinstala o CEH na máquina da IDE pelo `install.sh`. A reinstalação sobrescreve a edição local, e o diff fica zero.
4. Canário na IDE com a instalação oficial: `touch .ceh/canario-hook` **bloqueado**.
5. Passo 3 do Handoff 067: merge da `main` na `feature/onda-4`, retrato regenerado uma única vez a partir da v1.4.1 (A1, A2a, A2b e A4 iguais; linhas do A3 com o exit alterado listadas) e, depois, o PR-13.

### Critérios de aceite

- [ ] Payload do agy com `CLAUDECODE=1` → exit 0; suíte verde **com e sem** as variáveis do Claude no ambiente.
- [ ] `ask` com exit 0, com teste e prova por mutação.
- [ ] README fixado em `v1.4.1`; teste renomeado; `conversationId` mascarado.
- [ ] CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.
