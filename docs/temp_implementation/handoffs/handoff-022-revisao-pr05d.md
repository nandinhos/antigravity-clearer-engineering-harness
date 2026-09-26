# Handoff 022 — Revisão do PR-05d e despacho do PR-05e e do PR-QA-A

**Data/Hora:** 2026-09-26T06:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `41e665f` (PR-05d)
**Antecessor:** [Handoff 021](./handoff-021-revisao-pr05c.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVAS**

| Critério | Resultado (`OBSERVED`) |
|---|---|
| W1–W4 | Fechados. As 15 linhas `PENDENTE:H021` estão verdes, e os controles (`git checkout main app/x`, `--quiet`, `--detach`, `src/*`, `'src/*.php'`) seguem allow |
| W5 | Um único helper (`build_destructive_decision`); as 901 decisões anteriores do corpus não mudaram |
| W6 | `session id` removido de `20260925_214340/parecer_codex.md` |
| Diferencial contra o PR-05c (`c2b191d`) | **0 relaxamentos** em 465 comandos × 3 ambientes (corpus decodificado de `RAW:`/`B64:`, bateria e 73 sondas adversariais) |
| Diferencial contra o PR-05b (`7c1680f`) | 22 relaxamentos, **todos V3** (`--staged` sozinho, inclusive `--staged --source=HEAD .`) **ou V4** (nomes com hífen), como os Handoffs 019 e 020 autorizaram |
| Variantes inéditas do agente | 6 linhas (4 deny e 2 allow), com critério atendido |

A comparação diferencial que o agente registrou (`pr05d-corpus-diff.md`) confere com a minha reprodução independente.

## 2. Achados

| ID | Severidade | Origem | Descrição |
|---|---|---|---|
| **X1** | **MÉDIO** | preexistente (desde o PR-05c) | **Magia curta combinada.** `git checkout -- ':/!x'` sai allow em produção nas três versões (05b, 05c e 05d). No git 2.43 real, ele **descartou os 3 arquivos modificados** (raiz + exclusão = tudo exceto `x`). O `is_broad_pathspec` só procura `!`/`^` **logo depois do `:`**, então `:/!x`, `:/^x` e `:/!:x` escapam. |
| **X2** | BAIXO | PR-05d | **A checagem de session ID no `doc-audit` é uma lista de permissão disfarçada.** Ela só olha `20260925_214340` e `handoffs` por nome de diretório. Uma ata futura (`conselho/<novo timestamp>/`) passa sem checagem, e a ata `20260925_151613/parecer_codex.md` **ainda versiona** um session ID. |
| **X3** | INFO (repetido) | processo | O W7 continua: o `evidence-report` voltou a citar `test_git_canonicalization.py` como prova de "Suíte canônica 52/52 PASS". O estado da suíte **não é uma afirmação do agente**: a seção TESTS do relatório já o calcula do certificado. Não declare o estado da suíte como `--claim`/`--criterion`. |

O X1 está na bateria como `PENDENTE:H022-X1` (4 linhas), com 2 controles allow (`':/app/x'` e `':/:app/x'`).

## 3. Despacho — PR-05e `fix(gate): magia curta de pathspec e varredura de session ID` (pequeno)

1. **X1: siga a sintaxe do `gitglossary` e não enumere combinações.** Na forma curta, um pathspec é `:` seguido de **zero ou mais** símbolos mnemônicos (`/`, `!`, `^`), com um `:` opcional como terminador, e depois o caminho.
   - Consuma a sequência de mnemônicos.
   - Se houver `!` ou `^` → **amplo**.
   - Se houver `/` → o caminho restante vale a partir da raiz, com as regras atuais (normalização, glob no 1º segmento, `$`/`~`).
   - Cite a seção *pathspec* do `git help gitglossary` no PR.
2. **X2:** a varredura de session ID vale para **todo** o `docs/`, sem exceção por diretório. Remova o ID de `20260925_151613/parecer_codex.md`. Uma exceção só pode existir com justificativa escrita **no próprio arquivo de configuração** do check, e hoje nenhuma se justifica.

**Aceite:**
- as 4 linhas `PENDENTE:H022-X1` perdem o prefixo, e os controles seguem verdes;
- pelo menos 3 variantes novas do agente (uma allow);
- `doc-audit` verde, **sem** filtro por diretório;
- diferencial contra `41e665f` com 0 relaxamentos;
- protocolo 7.1, **sem** declarar o estado da suíte como afirmação (X3).

## 4. Despacho — PR-QA-A `test(gate): fuzz diferencial contra a linha de base` (logo depois do PR-05e)

O que o Handoff 018 (item A) especificou, com os aprendizados das três últimas revisões:

- **Linha de base:** `tests/fixtures/gate_baseline.txt` contém **um sha**, o do último PR homologado. **Só a revisão avança esse sha**, no commit do handoff. Quem implementa não o toca, senão o teste perde o sentido. O sha inicial será o do PR-05e, avançado pelo handoff que o homologar; até lá, use `41e665f`.
- **Extração:** `git archive <sha> clearer-engineering/scripts | tar -x -C <tmp>`, importando o gate antigo pelo caminho temporário. O CI já usa `fetch-depth: 0` (`ci.yml:21`), então o sha está disponível.
- **Entradas:**
  - todos os comandos do corpus, **decodificados** (`RAW:` literal, `B64:` em base64; as linhas `HOOK:`/`INTEGRATION:` ficam fora);
  - todos os comandos da bateria;
  - ≥ 3000 comandos gerados por gramática com semente fixa: `rm`, `git checkout|restore|switch|reset|clean|branch|push` com opções curtas e longas, abreviações, pathspecs (relativos, `..`, glob, magia curta e longa, variáveis), `find` e one-liners.
  - **Armadilha real desta revisão:** passar `RAW:git checkout .` sem decodificar gera 100 "relaxamentos" falsos.
- **Regra:** toda transição que relaxa (`deny→ask|allow`, `ask→allow`, ou saída de `CATASTROPHIC`), em qualquer ambiente, tem de constar em `tests/fixtures/relaxamentos_justificados.txt` no formato `env|comando|de->para|ID-do-achado`. Relaxamento não listado **reprova** e imprime a linha pronta para colar. Quando a revisão avança a linha de base, o arquivo é zerado.
- **Falsificabilidade no PR:** reintroduza numa cópia o W1 (tree-ish ignorado) e mostre a suíte falhando e nomeando `git checkout . app/x`.
- **Custo:** o teste roda em < 20 s na suíte canônica. Se passar disso, reduza a gramática, não a cobertura do corpus e da bateria.

## 5. Sequência

PR-05e → PR-QA-A → PR-06 (G5) → PR-QA B–E → Onda 2.
