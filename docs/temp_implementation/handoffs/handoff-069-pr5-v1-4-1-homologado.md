# Handoff 069 — PR #5 (v1.4.1) **HOMOLOGADO**: deny bloqueante na IDE do Antigravity

**Data/Hora:** 2026-09-30T23:00:00Z
**Instância:** Revisor independente (Claude)
**PR revisado:** [#5](https://github.com/nandinhos/antigravity-clearer-engineering-harness/pull/5) — head `5a020ba`
**CI:** [run 36668178956](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36668178956) = success (4/4)
**Antecessor:** [Handoff 068](./handoff-068-revisao-pr5-v1-4-1-ajustes-antes-do-merge.md)

---

## 1. Verificação independente (`OBSERVED`)

| Item | Verificação | Resultado |
|---|---|---|
| **B1** o payload decide o host | `_is_claude_host`: com `toolCall` → Antigravity; com `hook_event_name`/`tool_name` → Claude; o ambiente só vale quando o payload não identifica o host | ✅ |
| B1, hermeticidade | `test_hook_context.py` e `test_cert_protection.py` verdes **com** as variáveis do Claude no ambiente (esta revisão roda dentro do Claude Code) **e sem** elas | ✅ |
| B1, mutação | num clone, sem o retorno antecipado para `toolCall`, o `test_case_21` reprova | ✅ |
| **B2** `ask` com exit 0 | `handle_hook`: `ask` → `sys.exit(0)` | ✅ |
| B2, mutação | num clone, com `ask` voltando a exit 1, reprovam `test_case_22` e `test_case_23` | ✅ |
| Deny do agy com exit 0, mutação (Handoff 068) | 7 + 1 testes reprovam | ✅ |
| **BA1** README fixado em `v1.4.1` | `README.md:45-46` | ✅ |
| **BA2** teste renomeado | `test_case_20_agy_deny_exit_0` | ✅ |
| **BA3** `conversationId` mascarado | 0 ocorrências do identificador real em `docs/` (`conv-1`) | ✅ |
| CI no head | 4/4 | ✅ |

### Ressalva baixa (não bloqueia)

- **BB1:** o `test_case_23_ask_decision_mutation_proof` repete o erro do BA2: é uma asserção igual à do `test_case_22`, não uma prova por mutação. A prova real está nesta revisão (tabela acima). Renomeie ou remova o teste no próximo PR que tocar o `test_hook_context.py`.

## 2. Veredito: **HOMOLOGADO**

A v1.4.1 corrige o fail-open da IDE do Antigravity sem mudar nenhuma decisão do gate: só mudam os códigos de saída, que agora seguem o contrato observado de cada host.

| Host | Deny | Ask | Erro tratável | Evidência |
|---|---|---|---|---|
| IDE do Antigravity | JSON + exit 0 | convertido em deny | JSON + exit 0 | E13 |
| agy CLI | JSON + exit 0 | convertido em deny | JSON + exit 0 | E5 (Handoffs 005/007) |
| Claude Code | `hookSpecificOutput` + exit 2 | `hookSpecificOutput` + exit 0 | exit 2 | E5, E6, E9 |

**Limites que continuam** (ADR 007, seção 4): na IDE, timeout, Python ausente ou erro de sintaxe no próprio gate deixam a ferramenta rodar. A mitigação é o CI do servidor.

## 3. Passos do desenvolvedor

1. Tirar o PR #5 do rascunho e fazer o merge na `main`.
2. Criar a tag **`v1.4.1`** no commit do merge.
3. Na máquina da IDE, reinstalar pelo `install.sh` da `main` (ou da tag). A reinstalação substitui a edição local do gate.
4. Apagar o `.ceh/canario-hook`, se ainda existir.

## 4. Depois — Passo 3 do Handoff 067 (agente)

Num commit da `feature/onda-4`:

1. **Canário oficial:** com a v1.4.1 instalada, `diff` zero entre o gate instalado e o da tag; `touch .ceh/canario-hook` **bloqueado** na IDE, com a mensagem de bloqueio gravada.
2. Merge da `main` na `feature/onda-4`.
3. Retrato regenerado **uma única vez** a partir da `v1.4.1`:
   - A1, A2a, A2b e A4 iguais aos da v1.4.0;
   - no A3, listar cada linha que mudou. O esperado é que só mudem os códigos de saída das **7** respostas deny do agy (de 2 para 0);
   - o A3-muse continua com deny em todas as ferramentas (o Muse é classificado como Claude, exit 2, até o PR-15b).
4. CI verde (4/4). Depois, revisão curta e liberação do **PR-13**.

**Linha de base:** avança para o commit da tag `v1.4.1` quando ela existir.
