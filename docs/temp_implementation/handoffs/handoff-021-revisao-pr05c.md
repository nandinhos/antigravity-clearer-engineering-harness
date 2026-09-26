# Handoff 021 — Revisão do PR-05c e despacho do PR-05d

**Data/Hora:** 2026-09-26T05:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `c2b191d` (PR-05c)
**Antecessores:** [Handoff 019](./handoff-019-revisao-pr05b.md), [Handoff 020](./handoff-020-revisao-ata-conselho-pr05c.md)

---

## 1. Veredito: **NÃO HOMOLOGADO: duas regressões em produção**

O que o PR-05c acertou (`OBSERVED`):

- As 25 linhas `PENDENTE` do H019/H020 ficaram verdes, e todos os controles seguem verdes. O diff da bateria só remove prefixos e acrescenta linhas.
- As regex de `checkout`/`restore`/`switch` saíram do `rules.py`, e o `ceh_core/git.py` tem 222 linhas.
- O V4 (falso positivo com hífen) foi extinto, e o V5 (`--pathspec-from-file`) está fechado.
- As 787 decisões anteriores do corpus não mudaram. O teste de canonicalização só ganhou asserções (nenhuma removida).
- A entrega saiu como "pronto para revisão". Obrigado: esse é o fluxo certo.

Mas uma **comparação diferencial** entre o gate do PR-05b (`7c1680f`) e o do PR-05c, com 41 comandos novos nos 3 ambientes, encontrou **relaxamentos não justificados**. Todos foram conferidos no **git 2.43 real**, num repositório temporário.

| Comando (produção) | PR-05b | PR-05c | O que o git faz de verdade (`OBSERVED`) |
|---|---|---|---|
| `git checkout . app/x` | deny | **allow** | "Updated 3 paths": descarta **todo** o worktree |
| `git restore --staged --work .` | deny | **allow** | descarta o worktree (`--work` = `--worktree`) |

O corpus não tinha esses comandos, por isso "0 regressões nas 787" era verdade e ainda assim insuficiente. É exatamente a lacuna que o item A do PR-QA fecha (seção 4).

## 2. Achados

| ID | Severidade | Origem | Descrição |
|---|---|---|---|
| **W1** | **ALTO (regressão)** | PR-05c | Sem `--`, o analisador assume que o 1º posicional é tree-ish e o ignora. O git trata `.` como pathspec quando não é ref: `git checkout . app/x` e `git checkout src/.. app/x` saem allow. |
| **W2** | **ALTO (regressão parcial)** | PR-05c | Opções longas são comparadas por igualdade, mas o git aceita **prefixo único**. `OBSERVED`: `git checkout --forc other` e `git switch --discard other` trocam de branch descartando mudanças; `--work` vale `--worktree`. Hoje saem allow: `--forc`, `--discard`, `--force-c` e `restore --staged --work .`; `--pathspec-from=x` também escapa. |
| **W3** | MÉDIO | preexistente | Glob no primeiro segmento alcança o repositório inteiro. `OBSERVED`: `git checkout -- '*.php'` restaurou `src/y.php` e `z.php`. `./*` (expandido pelo shell) e `'**'` saem allow. |
| **W4** | BAIXO | preexistente | Variável ou `~` no pathspec (`"$PWD"`, `$DIR`, `~`) sai allow. O `rm` já trata isso como incerteza (S2). |
| **W5** | BAIXO (manutenção) | PR-05c | A montagem do motivo por ambiente foi **copiada** (`safety-gate.py:228` e `:285`). É o mesmo risco do R3: dois textos que vão divergir. |
| **W6** | INFO | PR-05c | `parecer_codex.md` versiona o `session id` do CLI do Codex. Remova. A checagem de vazamento passa a incluir IDs de sessão de ferramentas. |
| **W7** | INFO | processo | No `evidence-report`, o critério "Suíte 52/52 PASS" citou como prova o `test_git_canonicalization.py`. O hash de um arquivo de teste não prova que a suíte passou; quem prova é a seção TESTS, que o relatório calcula a partir do certificado. Cite como prova apenas o que sustenta a afirmação. |

**Errata minha:** o Handoff 019 indicava `bash clearer-engineering/evals/run.sh`, um caminho que não existe. O certo é `bash evals/run.sh`, na raiz, como o agente acabou usando. O Handoff 019 foi corrigido neste commit.

Todos os achados estão na bateria como `PENDENTE:H021-*` (15 linhas), com os controles `allow` que a correção não pode quebrar (`git checkout main app/x`, `--quiet`, `--detach`, `src/*`, `'src/*.php'`).

## 3. Despacho — PR-05d `fix(gate): posicionais, prefixo de opção longa, glob e variável no pathspec`

Tudo no `ceh_core/git.py`, sem enumerar literais (padrão 1 do Handoff 018):

1. **W1:** avalie a amplitude de **todos** os posicionais, com ou sem `--`. Um nome de ref nunca normaliza para amplo (refs não podem ser `.`, `..`, absolutas, nem conter glob), então a heurística do tree-ish some. Isso é mais simples e fail-closed.
2. **W2: resolução de opção longa como no `parse-options` do git.** Um token `--abc[=v]` corresponde a **toda** opção longa conhecida do subcomando que começa com `--abc`. Regra de direção: **abreviação só pode apertar, nunca relaxar.**
   - Se algum candidato for destrutivo (`--force`, `--discard-changes`, `--force-create`, `--worktree`, `--pathspec-from-file`, `--pathspec-file-nul`), o token é destrutivo.
   - A opção que relaxa (`--staged`) só conta com o nome **exato**.
   - Cite no PR a lista de opções longas de `git checkout|restore|switch --help` (git 2.43) de onde saem os candidatos.
3. **W3:** pathspec cujo **primeiro segmento**, depois da normalização, contém `*`, `?` ou `[` é amplo. `src/*` e `'src/*.php'` seguem específicos.
4. **W4:** pathspec com `$` ou iniciado por `~` é amplo (fail-closed). Ele cai na mesma graduação por ambiente: allow em DEV, ask em STAGING, deny em PROD.
5. **W5:** um único helper monta a decisão por ambiente (texto e `use_case`), usado pelo caminho de regex e pelo analisador. **Prova:** o corpus antigo fica **byte a byte idêntico**.
6. **W6:** remova o `session id` do parecer do Codex.

### Critérios de aceite do PR-05d

- [ ] As 15 linhas `PENDENTE:H021-*` perdem o prefixo, e todas as linhas de controle (H017–H021) seguem verdes.
- [ ] Pelo menos 5 variantes novas escolhidas pelo agente, uma delas `allow`.
- [ ] **Comparação diferencial registrada:** rode os comandos da bateria e do corpus no gate de `c2b191d` e no novo, nos 3 ambientes, e cole no `pr05d-corpus-diff.md` **toda** transição que relaxa. Nenhum relaxamento é esperado. Isso antecipa, à mão, o item A do PR-QA.
- [ ] Suíte, `bash evals/run.sh`, `doc-audit` e Python 3.9/3.12.
- [ ] Protocolo 7.1 e `evidence-report --strict`, com provas que sustentam cada afirmação (W7). O status é "pronto para revisão".

## 4. Sequência atualizada (mudança de ordem)

1. **PR-05d** (seção 3).
2. **PR-QA-A (antecipado):** só o fuzz diferencial contra a linha de base, com `relaxamentos_justificados.txt` (Handoff 018, item A). Foi a segunda vez seguida que uma regressão só apareceu na comparação manual (S1 e agora W1/W2). O PR-06 vai mexer no gate de novo e precisa dessa rede antes.
3. **PR-06** (G5), sem alteração.
4. **PR-QA B–E.** O item C (contrato com `--help`) herda a lista de opções longas do W2.
5. Onda 2.
