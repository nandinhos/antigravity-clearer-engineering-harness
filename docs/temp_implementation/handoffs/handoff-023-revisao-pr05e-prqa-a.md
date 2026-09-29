# Handoff 023 — Revisão do PR-05e e do PR-QA-A e despacho do PR-QA-A2

**Data/Hora:** 2026-09-26T07:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `f5737a4` (PR-05e), `7f87ce3` (PR-QA-A)
**Antecessor:** [Handoff 022](./handoff-022-revisao-pr05d.md)

---

## 1. Vereditos

### PR-05e: **HOMOLOGADO**

- **X1 fechado.** A magia curta agora segue a sintaxe do `gitglossary` (sequência de mnemônicos + terminador `:`). Conferi no git real: `':^/!x'` e `':(top,exclude)x'` descartam tudo, e o gate os nega.
- **X2 fechado.** A varredura cobre todo o `docs/`, e restam 0 session IDs (`OBSERVED`: `grep` vazio).

### PR-QA-A: **HOMOLOGADO COM RESSALVAS**

- Falsificabilidade **reproduzida de forma independente**. Num clone temporário com o W1 reintroduzido, o teste reprova com 60 relaxamentos não autorizados (3,7 s).
- A extração com `git archive`, a decodificação do corpus (`RAW:`/`B64:`), a regra de relaxamento e o formato da linha pronta para colar seguem o Handoff 022.

### Linha de base avançada

`gate_baseline.txt` passa a `7f87ce3` neste commit, que é o último homologado. O gate desse commit é idêntico ao de `f5737a4`, e o fuzz segue verde. O `relaxamentos_justificados.txt` segue vazio.

## 2. Achados

| ID | Severidade | Onde | Descrição |
|---|---|---|---|
| **Y1** | **MÉDIO** | `test_gate_differential_fuzz.py`, gramática | A gramática **não gera** várias dimensões que o Handoff 022 (§4) pediu. Hoje, uma regressão do tipo W2 só é pega se a bateria tiver o literal, e o PR-06 (`find`/interpretadores) não teria nenhuma cobertura gerada. |
| **Y2** | BAIXO/MÉDIO | idem, `setUpClass` | `raise TimeoutError` quando a preparação passa de 20 s. Isso faz da **velocidade da máquina** um critério de reprovação: um runner lento de CI fica vermelho sem nenhum defeito. Os 20 s eram orçamento, não asserção. |
| **Y3** | BAIXO | idem | O gate é avaliado no **cwd real do repositório** (branch, `.ceh/last-ci-run.json`, `HOME`), ao contrário do snapshot e da bateria, que usam um repositório temporário. Os dois lados veem o mesmo estado, então não há falso alarme, mas a suíte deixa de ser hermética nesse ponto. |
| **Y4** | BAIXO (falso positivo) | `git.py`, última linha do ramo de magia curta | `git checkout -- ':app/x'` sai deny, mas no git real (`OBSERVED`) ele restaurou **só** `app/x`: `:` sem mnemônico é um pathspec comum, igual ao `'::app/x'`, que já sai allow. A expressão `idx == 1 and not (…isalnum()…)` é obscura e é a causa. |
| **Y5** | processo (**3ª repetição**) | `evidence-report` | Mais uma vez, "Suíte 53/53 PASS" teve `run-all-tests.sh` como prova e "Evals 5/5" teve `evals/CRITERIA.md`. Um arquivo não prova execução. Pedir não funcionou três vezes, então pela **Invariante 6 (o código decide)** isso passa a ser imposto pelo código. |

As dimensões que faltam no Y1:

- abreviações de opção longa (`--forc`, `--discard`, `--work`, `--pathspec-from`);
- `checkout -B`, `switch --force-create` e `--pathspec-from-file`/`--pathspec-file-nul`;
- `$VAR`/`${VAR}` sem aspas e `~/x` como pathspec do git;
- `find` com `-delete` e com caminho inicial catastrófico (`/`, `~`, `/etc`, `..`);
- one-liners de interpretador (`python3 -c`, `node -e`, `perl -e`, `ruby -e`) com e sem chamada destrutiva.

O Y4 está na bateria como `PENDENTE:H023-Y4`, junto com 3 controles.

## 3. Despacho — PR-QA-A2 `test(gate): gramática completa, fuzz hermético e evidência calculada` (antes do PR-06)

1. **Y1:** gramática com todas as dimensões da tabela acima.
   - **Falsificabilidade no PR:** num clone, troque a comparação de prefixo das opções longas por igualdade (o W2 original) e **remova da bateria e do corpus as linhas com abreviação**. O fuzz tem de reprovar **só pela gramática**.
2. **Y2:** remova o `TimeoutError`. Imprima o tempo decorrido. O orçamento vale como meta registrada no log de entrega.
3. **Y3:** avalie os dois gates dentro de um `git init -b dev` temporário. Use o mesmo `cwd` e um `HOME` isolado para o worker da linha de base e para o processo atual.
4. **Y4:** substitua a última linha por `return _is_broad_subpath(p[idx:])`. Esse é um **relaxamento** (deny→allow para `':app/x'`). Liste-o em `relaxamentos_justificados.txt` com o ID `H023-Y4`: é o primeiro uso real do mecanismo, e o teste tem de passar **por causa** da linha listada.
5. **Y5: estado de execução calculado, nunca declarado.**
   - `evals/run.sh` grava `.ceh/last-evals-run.json` com `{commit, verdict, passed, total, timestamp}`, no mesmo padrão do certificado da suíte.
   - O `evidence-report` lê esse arquivo e mostra os evals na seção TESTS como `OBSERVED`. Se o `commit` for diferente do HEAD, mostra que está desatualizado.
   - Com `--strict`, o relatório **recusa** todo `--claim`/`--criterion` cujo texto afirme o estado da suíte ou dos evals (`suíte|suite|evals?|smoke` junto com `PASS|aprovad|verde|\d+/\d+`). A mensagem diz que esse estado é calculado.
   - Contratos novos em `test_evidence_report.py`: uma afirmação proibida é recusada, o eval aparece como `OBSERVED` e um eval de outro commit aparece como desatualizado.

**Aceite:**

- [ ] O fuzz reprova no clone com W2 **sem** a bateria.
- [ ] `PENDENTE:H023-Y4` fica verde **e** o relaxamento consta no arquivo de justificativas. Remover essa linha faz o fuzz reprovar (mostre no PR).
- [ ] `test_evidence_report.py` com os 3 contratos novos.
- [ ] Suíte, `bash evals/run.sh`, `doc-audit` e Python 3.9/3.12. Protocolo 7.1, com o relatório `--strict` **sem** afirmações de estado.

## 4. Sequência

PR-QA-A2 → PR-06 (G5, que agora terá cobertura gerada de `find`/interpretadores) → PR-QA B–E → Onda 2.
