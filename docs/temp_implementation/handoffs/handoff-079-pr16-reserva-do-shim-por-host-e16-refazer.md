# Handoff 079 — PR-16: empacotador aprovado; **reserva do *shim* falha aberta no Muse** (decisão da revisão) e **E15/E16 sem isolamento**; não homologado

**Data/Hora:** 2026-10-02T02:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — `88e5d47` (BH1–BH3, E1c), `3dd0d32` (PR-16), `7cea101`; relatório do agente "Handoff 078"
**CI:** [run 36747893030](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36747893030) = success (4/4)
**Antecessor:** [Handoff 077](./handoff-077-pr15b-homologado-e15-ressalvas-despacho-pr16.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

> O "Handoff 078" é um relatório de entrega do agente, sem declaração de homologação.

---

## 1. O que está certo (`OBSERVED`)

| Item | Resultado |
|---|---|
| `package.py --all` | gera `antigravity`, `muse` e `claude-code` da mesma fonte; dois empacotamentos seguidos dão árvores idênticas (`diff -r` vazio) |
| `install.sh` | instala a partir do pacote `antigravity` gerado na hora; `--check`: A2a (45) e A2b (124; 21 declarados) idênticos |
| Rede | A1, A3, A3-muse (antes e depois, controle cruzado) e A4 idênticos |
| `test_package`, `test_adapters`, `test_hook_failclosed` | verdes com e sem as variáveis do Claude |
| BH1 | primeira execução do E15 registrada como reconstrução rotulada; `summary.md` e runner corrigidos |
| BH2 | **E1c executado e registrado honestamente**: `{"decision":"deny"}` com exit 0 **não bloqueia** no Muse (sentinela criado), e o *shim* não foi alterado por conta própria. Correto |
| BH3 | limite da detecção registrado |

O código do empacotador está aprovado.

## 2. Bloqueantes

### BI1 — A resposta de reserva do *shim* falha aberta no Muse (`OBSERVED` no E1c) — ALTA

Quando um módulo do CEH quebra, o *shim* responde `{"decision":"deny"}` com exit 0 (ou exit 2 se houver variáveis do Claude). O E1c prova que o Muse **ignora** esse formato. Hoje, um erro de sintaxe no `adapters/muse.py` (ou no `ceh_core`) deixa **qualquer** comando passar no Muse.

Pior: o controle negativo do `test_package.py` (linha 200) **exige** `"deny"` para o pacote do Muse sem o adaptador. O teste trata como sucesso justamente o caso que falha aberto.

**Decisão da revisão:** a reserva passa a responder **no formato observado de cada host**, lendo o payload bruto, sem depender do motor nem dos adaptadores.

1. **`adapters/fallback.py`**, só com a biblioteca padrão, com a tabela abaixo (só formatos observados). As linhas são avaliadas **nesta ordem**: o payload do Muse também tem `hook_event_name` e `tool_name`, e por isso os marcadores do Muse vêm antes dos do Claude.

   | Payload bruto (JSON válido) | Resposta | Evidência |
   |---|---|---|
   | tem `toolCall` | `{"decision":"deny","reason":…}`, exit 0 | E5 (CLI), E13 (IDE) |
   | tem `model_provider` ou `turn_id` | `{"decision":"block","reason":…}`, exit 0 | E1b B4 |
   | tem `hook_event_name` ou `tool_name` | `hookSpecificOutput` com `permissionDecision:"deny"`, **exit 2** | E5/E9 (Claude) |
   | vazio, não JSON, não objeto ou sem marcador | regra atual (variáveis do Claude → exit 2; senão `{"decision":"deny"}` com exit 0) | — |

2. **`adapters/__init__.py` sem importar os submódulos.** Hoje ele importa todos os adaptadores. Com isso, um `muse.py` quebrado também quebraria o `import adapters.fallback`. O `hook_context.py` passa a importar cada adaptador explicitamente.
3. **O *shim*** lê o stdin **uma vez**. Na falha de import do `hook_context`/`ceh_core`, e em qualquer exceção, chama `fallback.respond(raw)`. Só se o próprio `fallback.py` falhar ao importar vale a resposta genérica atual; registre isso no ADR 007 como limite ("Muse falha aberto só se o adaptador **e** a reserva estiverem quebrados").
4. **Testes** (em cópia temporária, com e sem as variáveis do Claude), cada um com o payload real do respectivo `recorded.jsonl`:
   - `muse.py` quebrado + payload do Muse → `{"decision":"block"}`/0;
   - `ceh_core` quebrado + payload de cada host → o formato da tabela;
   - `fallback.py` quebrado + `ceh_core` quebrado → resposta genérica (o limite documentado).
5. **Corrija o controle negativo do `test_package.py`:** Muse sem adaptador → `{"decision":"block"}`/0.
6. **Mutação:** a reserva respondendo `"deny"` para o Muse faz o teste reprovar.

A A4 continua valendo: os termos de host da reserva ficam em `adapters/`, e o *shim* continua sem nenhum.

### BI2 — E15 e E16 rodaram com o `clearer-muse` **ativo** — ALTA (atribuição)

O `plugins_list_installed.json` do E16 mostra `clearer-muse enabled=True` ao lado do `ceh-e16-gate`. Nenhum dos runners do E15, do E16 e do E1c desliga o `clearer-muse`, ao contrário do E1b (condição C2.1 do Handoff 065). O `clearer-muse` tem a **sua própria cópia** do gate, com o mesmo portão de push. Com os dois hooks ativos, **não dá para atribuir** o bloqueio do `git push` ao adaptador (E15) nem ao pacote (E16).

**Refazer o E16** (ele cobre também o objetivo do E15):

1. **Isolamento, em ordem de preferência:**
   - um perfil do Muse realmente temporário (`XDG_CONFIG_HOME`/`XDG_DATA_HOME` num diretório temporário). Se isso exigir copiar credenciais do Muse, a cópia fica **só** no diretório temporário, é apagada no `finally` e **nunca** vai para a evidência;
   - ou `clearer-muse` desligado durante o experimento e religado no fim, como no E1b.
2. `muse plugins list --json` **antes de cada cenário**, mostrando só o pacote do CEH ativo com hook.
3. Os dois cenários do E16, com o bloqueio confinado ao diretório temporário.
4. Instale o pacote **como gerado**. Se precisar de outro id de plugin, acrescente `--plugin-id` ao `package.py`, em vez de editar o manifesto depois de empacotar (o hash registrado tem de ser o do que foi instalado).
5. Acrescente um **terceiro cenário**, que prova a BI1 ponta a ponta: um pacote do Muse com o `muse.py` quebrado de propósito (cópia temporária), com um comando que o gate negaria → **bloqueado** pela reserva, com a mensagem de erro do CEH.

### Ressalvas baixas

- **BI3:** os payloads do E1c trazem `session_id` reais. Mascare-os (regra C5). O E1c também rodou com o `clearer-muse` ativo. A conclusão ("`deny` não bloqueia") se mantém, porque o comando rodou mesmo com os dois hooks. Registre isso no resumo.
- **BI4:** o E16 alterou o `name` do manifesto depois de empacotar, então o hash registrado não é o do pacote instalado. Resolvido pelo item 4 da BI2.

## 3. Critérios de aceite

- [ ] Reserva por host em `adapters/fallback.py` (só biblioteca padrão), com `__init__.py` sem imports em cadeia.
- [ ] Testes de módulo quebrado por host e mutação da reserva do Muse; controle negativo do `test_package.py` corrigido.
- [ ] E16 refeito com isolamento comprovado por `plugins list` antes de cada cenário, pacote instalado como gerado, e o terceiro cenário (reserva) bloqueando.
- [ ] BI3 e BI4 resolvidas; ADR 007 com o limite da reserva.
- [ ] A1–A4 inalterados. CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

Com isso, o PR-16 é homologado, e segue o **PR-17** (conformidade entre hosts).
