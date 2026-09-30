# Handoff 081 — PR-16 **HOMOLOGADO** (empacotador e reserva por host); despacho do **PR-17** (conformidade entre hosts)

**Data/Hora:** 2026-10-02T08:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — `34f053d`; relatório do agente "Handoff 080"
**CI:** [run 36756246016](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36756246016) = success (4/4)
**Antecessor:** [Handoff 079](./handoff-079-pr16-reserva-do-shim-por-host-e16-refazer.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. Verificação independente (`OBSERVED`, worktree limpo do head)

### BI1 — reserva por host

`adapters/fallback.py` usa só a biblioteca padrão e segue a ordem do Handoff 079. O `adapters/__init__.py` não importa nada. Matriz desta revisão, em cópia temporária, com o **primeiro payload real** de cada `recorded.jsonl`, sem variáveis do Claude:

| Módulo quebrado | Muse | Antigravity | Claude Code |
|---|---|---|---|
| `adapters/muse.py` | `{"decision":"block"}`, exit 0 | `{"decision":"deny"}`, exit 0 | `hookSpecificOutput` deny, exit 2 |
| `ceh_core/engine.py` | `block`, exit 0 | `deny`, exit 0 | `hookSpecificOutput` deny, exit 2 |
| `engine.py` **e** `fallback.py` | `deny`, exit 0 (limite documentado no ADR 007, seção 5) | `deny`, exit 0 | — |

O *shim* tem 94 linhas, nenhuma referência a formato de host e lê o stdin uma única vez. O `test_package.py` exige `block` no Muse sem adaptador. A mutação da reserva do Muse para `deny` é pega (`test_mutation_p16.py`).

### BI2 — E16 isolado

| Arquivo | Plugins |
|---|---|
| `plugins_list_before_scenario_1/2/3.json` | `ceh-e16-gate` ativo; `clearer-muse` e `muse-probe` **desligados** |
| `plugins_list_after.json` | `clearer-muse` religado; plugin de teste removido |

- Pacote instalado como gerado (`--plugin-id`), hash `8eb93301d01e…`.
- Cenários: permitir (executa), `git push` (bloqueado pelo portão de push), e **reserva**: `muse.py` corrompido no cache do plugin → "`[CEH SAFETY GATE ERROR] Falha crítica de importação … (invalid syntax (muse.py, line 1))`" e bloqueio. Isso prova a BI1 de ponta a ponta no Muse real.

### Rede e demais itens

- `onda4_baseline.py --check`: A1–A4 e A3-muse (antes, depois e controle cruzado) conferem.
- `test_package`, `test_hook_failclosed` e `test_adapters`: verdes com e sem as variáveis do Claude.
- BI3: 0 identificadores de sessão reais no E1c; a nota sobre o `clearer-muse` ativo durante o E1c foi registrada.
- BI4: `--plugin-id` no `package.py`.

**PR-16: HOMOLOGADO.**

## 2. Despacho — PR-17 `test(conformance): mesma decisão em todos os hosts`

É o **diferencial central da Onda 4** (Handoff 064, item 1): provar por teste que os três hosts tomam a mesma decisão para o mesmo comando, e que só a forma da resposta muda.

1. **`tests/test_cross_host_conformance.py`**, em processo (sem subprocesso por caso, para caber no tempo do CI):
   - para **cada** entrada de comando do `gate_corpus` (1.024), no mesmo ambiente de branch que o corpus usa, monte o payload de cada host e passe pelo despachante (`hook_context`);
   - **Decisão:** `decision` e `use_case` iguais nos três hosts **e** iguais a `evaluate(Request)` chamado direto no motor;
   - **Resposta:** confira a tabela de `render` observada:

     | Decisão | Antigravity | Claude Code | Muse |
     |---|---|---|---|
     | allow | `{"decision":"allow"}`/0 | `{}`/0 | `{}`/0 |
     | deny | `{"decision":"deny"}`/0 | `hookSpecificOutput` deny/2 | `{"decision":"block"}`/0 |
     | ask | vira deny/0 | `hookSpecificOutput` ask/0 | vira block/0 |

2. **Payloads sintéticos fiéis aos reais.** O gerador monta cada payload com **o mesmo conjunto de chaves** dos payloads gravados daquele host (`recorded.jsonl`). Um teste confere isso, para que a conformidade não rode sobre payloads imaginários.
3. **Ferramentas de escrita:** para os alvos de escrita que o corpus ou a bateria já cobrem (proteção do `.ceh/`), faça o mesmo com `write_to_file` (agy), `Write` (Claude) e `write_file` (Muse).
4. **Divergência zero.** Se aparecer alguma, **não** ajuste o teste: reporte a divergência com o comando, os hosts e as decisões, e pare. Decisão que muda é outro PR, fora da Onda 4.
5. **A4:** o contador `cross_host_conformance_tests_count` passa de 0 para ≥ 1.
6. **Falsificabilidade** (em cópia temporária):
   - o `parse` do Muse ignorando o `workdir`/`cwd` → a conformidade reprova (a decisão de algum comando dependente de branch diverge);
   - o `render` do Claude mapeando `ask` para allow → reprova.
7. **Guia `docs/adapters/novo-host.md`**, curto e baseado no que a Onda 4 aprendeu:
   - E0/E1: sonda e payload real;
   - contrato de resposta com braços allow/deny/ask/exit 2/crash/timeout, **no contexto em que o agente de fato roda** (a lição da IDE × CLI, E13);
   - formato de reserva observado (a lição do E1c);
   - isolamento de plugins pré-existentes (a lição do E15/E16);
   - comandos de bloqueio confinados ao diretório temporário (a lição do BH1);
   - adaptador `detect`/`parse`/`render`, linha na reserva, fixtures gravadas, conformidade e manifesto no `package.py`.
8. **Evidência** `onda4-pr17-evidence.md`: número de casos × hosts, 0 divergências, mutações e CI (4/4) com o link.

### Critérios de aceite

- [ ] Conformidade nos 1.024 comandos × 3 hosts, com decisão igual à do motor e `render` conforme a tabela.
- [ ] Payloads sintéticos com as mesmas chaves dos gravados, conferido por teste.
- [ ] 0 divergências (ou relato e parada).
- [ ] Duas mutações em cópia temporária; A4 com o teste de conformidade contado.
- [ ] Guia `novo-host.md`.
- [ ] A1–A3 inalterados. CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 3. Depois do PR-17

`onda4-relatorio-final.md` com a tabela **antes × depois** do Handoff 064 (§4), revisão final, PR `feature/onda-4 → main` com os 4 jobs verdes e, com a homologação, **tag `v2.0.0` pelo desenvolvedor**.
