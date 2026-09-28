# Handoff 024 — Revisão do PR-QA-A2 e despacho do PR-06 (G5)

**Data/Hora:** 2026-09-26T08:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `2820dad` (PR-QA-A2)
**Antecessor:** [Handoff 023](./handoff-023-revisao-pr05e-prqa-a.md). O despacho do PR-06 do [Handoff 017](./handoff-017-revisao-pr04d-pr05-e-despacho-pr05b-pr06.md) (§3) continua valendo, com os ajustes da seção 3.

---

## 1. Veredito: **HOMOLOGADO**

Reproduzido de forma independente (`OBSERVED`):

| Item | Prova |
|---|---|
| Y1: a gramática sozinha pega o W2 | Num clone, troquei `o.startswith(opt_name)` por igualdade e **esvaziei o corpus e a bateria**. O fuzz reprova com **232** relaxamentos, o mesmo número do log do agente, a partir de `restore --staged --work …`. |
| Y4: relaxamento justificado | Esvaziando `relaxamentos_justificados.txt`, o fuzz reprova e nomeia `git checkout -- ':app/x'` (prod `deny->allow` e staging `ask->allow`). Com a linha, passa. É o primeiro uso real do mecanismo, e funcionou. |
| Y2/Y3 | Sem `TimeoutError`; os dois gates rodam num repositório `git init -b dev` temporário, com `HOME` isolado. |
| Y5 | `evals/run.sh` grava `.ceh/last-evals-run.json`; o relatório mostra os evals como `OBSERVED` e, com `--strict`, recusa afirmações de estado. O relatório de entrega do agente não trouxe nenhuma. |

**Linha de base avançada** para `2820dad`, e o `relaxamentos_justificados.txt` foi zerado (regra do Handoff 022). O fuzz segue verde.

## 2. Achados (baixos, para o primeiro commit da próxima rodada)

| ID | Descrição | Correção |
|---|---|---|
| **Z1** | A regex que recusa afirmações de estado não tem **fronteira de palavra**. `evals?` casa com "evaluate", e `pass` casa com "bypass". `OBSERVED`: "Gate evaluates bypass de find -delete" e "Contrato de evaluate_command cobre 12/12 variantes" são recusadas. É uma recusa falsa: obriga a reescrever afirmações legítimas. | Use `\b(su[íi]tes?\|evals?\|smoke)\b` e `\b(pass(ed\|a)?\|aprovad[oa]s?\|verde\|\d+/\d+)\b`. Acrescente 2 contratos: as duas frases acima são **aceitas**, e "Suíte canônica 53/53 PASS" continua **recusada**. |
| **Z2** | O `evals/run.sh` não invalida o certificado anterior ao começar. Uma execução que aborta no mesmo HEAD (erro inesperado, `set -u`) deixa um `APROVA` antigo valendo como se fosse dela. | `rm -f "$CEH_DIR/last-evals-run.json"` antes da verificação prévia. O certificado só existe se **esta** execução chegou ao fim. |

## 3. Despacho — PR-06 `fix(gate): deleções indiretas (G5)`

Vale o Handoff 017 §3, com estes ajustes (lições dos Handoffs 018–023):

1. **`find`:** analisador por tokens em `ceh_core/find.py` (≤ 300 linhas), no padrão do `git.py`, **sem regex nova em `rules.py`**.
   - Caminhos iniciais: os tokens antes da primeira expressão (`-…`, `(`, `!`).
   - **Catastrófico** se algum caminho inicial passar em `is_target_catastrophic` do `rm.py` (reuse, não copie), **exceto quando o caminho for o próprio cwd** (`.`). Ancestrais do cwd (`..`, `../..`) **são** catastróficos, como no `rm`.
   - Ações destrutivas: `-delete` e `-exec|-execdir|-ok|-okdir` cujo comando seja `rm|unlink|shred|rmdir` ou um shell (`sh|bash|zsh -c`). Sem caminho catastrófico, a decisão é graduada por ambiente (FILESYSTEM): DEV allow, HML ask, PROD deny.
2. **Interpretadores:** analisador por tokens.
   - **Resolver a cabeça do comando:** tirar `env`, `sudo`, `command`, `rtk` e o caminho absoluto; aceitar sufixo de versão (`python3.12`).
   - Interpretadores: `python`, `python3`, `node`, `perl`, `ruby`. Flags de código: `-c`, `-e`, `-E`, `--eval`.
   - Dentro do código, procurar APIs destrutivas (lista do Handoff 017 mais `pathlib…unlink/rmdir` e `os.removedirs`) → decisão graduada por ambiente.
   - Se algum **literal de string** do código passar em `is_target_catastrophic` → **CATASTROPHIC** (`shutil.rmtree('/')` não pode sair allow em DEV).
   - **Âncora obrigatória:** `echo "shutil.rmtree"` e `grep -r …` seguem allow.
3. **Gramática do fuzz:** estenda com produções **combinatórias**, não strings fixas:
   - cabeças `{python3, /usr/bin/python3, env python3, python3.12, node, perl, ruby}` × flags `{-c, -e, --eval}` × APIs × literais `{'/', '~', 'db', '/srv', '..'}`;
   - `find` × caminhos `{/, ~, /etc, .., ., build, ./src}` × filtros `{∅, -name '*.pyc', -type f}` × ações `{-delete, -exec rm {} +, -execdir rm -rf {} \;, -ok rm {} \;, -print}`.
4. **Bateria:** a seção "Handoff 024" traz **8 `PENDENTE:H024-G5`** (formas que o Handoff 017 não listava: `find ..`, `-execdir` na raiz, `-ok`, `/usr/bin/python3`, `env python3`, `python3.12`, literal `'/'` no Ruby) e os controles.
   - Nota de honestidade: marquei 3 linhas como pendentes, e o xfail estrito as **recusou**, porque já são negadas (`-exec sh -c 'rm …'`, `os.system('rm -rf …')`, `execSync('rm -rf …')`). Elas estão registradas como `H024-G5-ja-coberto`.
   - Some-se a isso os 7 `PENDENTE:H017-G5` e os 3 `@expectedFailure` do G5 em `cluster4_acceptance.py`.

### Critérios de aceite do PR-06

- [ ] Os 15 `PENDENTE` do G5 (7 do H017 e 8 do H024) ficam verdes, e todos os controles seguem verdes.
- [ ] Os 3 RED do G5 em `cluster4_acceptance.py` ficam verdes (resta só o G7).
- [ ] `rules.py` sem regex nova para `find` e interpretadores.
- [ ] O fuzz diferencial contra `2820dad` passa **sem** nenhuma linha nova em `relaxamentos_justificados.txt` (o PR-06 só aperta).
- [ ] **Falsificabilidade da gramática nova:** num clone, desligue a resolução de cabeça (`/usr/bin/python3` deixa de ser reconhecido). O fuzz tem de reprovar só pela gramática, com corpus e bateria esvaziados.
- [ ] Z1 e Z2 no **primeiro commit** (`fix(evidence): …`), e o PR-06 no segundo.
- [ ] Protocolo 7.1 em cada commit; o relatório `--strict` usa só afirmações com prova.

Com o PR-06, fecha a **Onda 1** (G1–G6).

## 4. Sequência

Z1/Z2 + PR-06 → PR-QA B–E → Onda 2 (PR-08 G7, PR-09, PR-10).
