# Handoff 072 — Revisão do PR-13: motor agnóstico **correto**, mas com **regressão de fail-closed** no import; não homologado

**Data/Hora:** 2026-10-01T06:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — `e9f5c87`, `3506635` (PR-13), `5581219`
**CI:** [run 36675005901](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36675005901) e [run 36675584535](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36675584535) = success (4/4)
**Antecessor:** [Handoff 071](./handoff-071-fase0-encerrada-despacho-pr13.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. O que está certo (`OBSERVED`, num worktree limpo do head)

| Item | Resultado |
|---|---|
| `onda4_baseline.py --check` (sem variáveis do Claude) | A1 (1.024, `3878d3cc…`), A2a, A2b (5 novos declarados), A3 (107), A3-muse (41): **idênticos**; A4: 0 referências de host no `safety-gate.py` e no `ceh_core/` |
| `snapshot_gate.py --check` | 1.024 avaliações idênticas |
| `test_engine.py`, `test_hook_context.py`, `test_cert_protection.py` | verdes **com e sem** as variáveis do Claude no ambiente |
| Mutações M1 (`toolCall` no núcleo) e M2 (exit do agy) | reprovam a rede |
| Mudanças na rede (`onda4_baseline.py`) | só A2b (arquivos novos declarados) e A4 (metas do PR-13). As comparações do A1 e do A3 ficaram intactas |
| `safety-gate.py` | *shim* de 61 linhas; CLI `--check`/`--command`/`--cwd`/`--env` preservado |
| BC1, BC2, BC4, BB1 | ✅ |

O desenho está certo, e a equivalência de decisão e de resposta está provada.

## 2. Bloqueante

### D1 — Regressão: falha de import no `hook_context` volta a deixar o comando passar na IDE — **HIGH**

O *shim* faz os dois imports **no topo do arquivo, fora de qualquer `try`**:

```python
from ceh_core.engine import Request, Decision, evaluate, evaluate_command
from hook_context import handle_hook_lifecycle, get_exit_code
```

Se um desses imports falha, o Python sai com **exit 1** e um *traceback*. Na IDE do Antigravity, exit ≠ 0 é fail-open (E13). Comparação por mutação, com o mesmo payload do agy (`rm -rf /`), cada uma num clone:

| Mutação | v1.4.1 (`e608ea7`) | PR-13 |
|---|---|---|
| erro de sintaxe no `hook_context.py` | deny, **exit 0** (o import estava dentro do `try`) | **exit 1** → executa na IDE |
| exceção no import do `ceh_core` | exit 1 | exit 1 |
| stdin que não é UTF-8 | deny, exit 0 | deny, exit 0 |

- A primeira linha é **regressão** em relação à v1.4.1.
- A segunda já existia, mas o Handoff 071 (§2, item 3) pediu explicitamente "todos os caminhos de erro com o JSON de deny e o código de saída do host, **inclusive falha de import do `ceh_core`**".
- A rede não pega isso porque o A3 só reproduz payloads com os módulos íntegros.

**Correção:**

1. No `safety-gate.py`, os imports do `ceh_core` e do `hook_context` ficam dentro de `try`.
2. Na falha, o *shim* responde `{"decision": "deny", "reason": "[CEH SAFETY GATE ERROR] …"}` e escolhe o código de saída **sem** usar termos de host, pela mesma regra de fallback já usada para payload não identificável: variáveis do Claude no ambiente → 2; senão → 0.
3. O `handle_hook` do *shim* também fica sob `try` amplo, como na v1.4.1: qualquer exceção vira deny.
4. **Teste novo** (`test_hook_failclosed.py`, registrado na suíte). Ele copia os scripts para um diretório temporário, quebra o `hook_context.py` e depois um módulo do `ceh_core`, e exige, para o payload do agy, deny com exit 0 (e, com `CLAUDECODE=1` e payload não identificável, exit 2).
5. **Prova por mutação num clone:** tirar o `try` dos imports faz o teste novo reprovar.

Limite que continua (ADR 007, seção 4): erro de sintaxe no **próprio** `safety-gate.py`, Python ausente ou timeout. Com o *shim* pequeno, essa superfície ficou menor.

## 3. Ressalvas

- **D2 (média) — BC3 declarado sem entrega:** a evidência diz que o trecho do log com o bloqueio do canário foi "arquivado", mas o PR não versiona nenhum arquivo novo com isso. As únicas menções a `canario-hook` na evidência são da E13, com a **v1.4.0**. Versione o trecho (log da IDE ou `guard_audit.log`, mascarado), ou corrija o texto para "não registrado". Não se declara como feito o que não foi.
- **D3 (média) — mutações na árvore real:** o `test_mutation_p13.py` escreve direto no `engine.py` e no `hook_context.py` do checkout e restaura depois. Se a execução for interrompida, a árvore fica mutada. A regra AT5 (Handoff 046) é mutação **só em clone**: copie o repositório para um diretório temporário e mute a cópia (o `test_mutation_p3.py` tem o mesmo defeito e vai junto).
- **D4 (baixa):** o `hook_context.py` concentra agora 56 referências de host. É o esperado neste passo; o PR-14/15 separa essas referências por adaptador.

## 4. Critérios de aceite do ajuste

- [ ] Falha de import do `hook_context` e do `ceh_core` → deny com exit 0 para o payload do agy (exit 2 no fallback do Claude), com teste e prova por mutação.
- [ ] `onda4_baseline.py --check` continua idêntico; A4 continua com 0 referências de host no *shim* e no núcleo.
- [ ] BC3 versionado ou corrigido no texto; mutações só em cópia temporária.
- [ ] CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

Com D1–D3 fechados, o PR-13 é homologado numa revisão curta, e o **PR-14/15** (contrato de adaptador `parse`/`render`) fica liberado.
