# Handoff 094 — Revisão do PR #11 (`v2.1.1`: CA1, CA2, CB17, CB18)

**Data/Hora:** 2026-10-02T05:00:00Z
**Instância:** Revisor independente (Claude)
**PR revisado:** [#11](https://github.com/nandinhos/antigravity-clearer-engineering-harness/pull/11), `feature/v2.1.1` → `dev`, cabeça `49ab3d0`, base `4a637fe` (`dev` com o PR #9)
**Antecessor:** [Handoff 093](./handoff-093-pr9-homologado.md)
**Estado:** **AJUSTES NECESSÁRIOS.** CC1 (alta) e CC2–CC4 (médias) bloqueiam o merge.

---

## 1. Verificação independente (`OBSERVED`)

| Item | Resultado |
|---|---|
| CI | [run 36962469087](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36962469087): os 4 `Validate`, a paridade Claude e o `ci-ok` = success |
| CB17 e CB18 | aplicados no `ceh-doctor.sh`, com teste em `test_doctor_verify.py` |

**Cobertura do CA1** (gate do PR, repositório temporário em `dev`):
- **dão deny:**
  - as formas `>`, `>>`, `>|`, `&>`, `&>>`, `1>`, `2>` e `<>`, coladas ou com espaço, para `.ceh/a` e `.ceh/config.json`;
  - `.CEH` e `.Ceh`, `./.ceh`, `sub/../.ceh`, `"$PWD"/.ceh`, `${PWD}/.ceh`, `~/.ceh`, alvo entre aspas, `\.ceh`, `$FOO/a` com `FOO=.ceh` e `exec 3>.ceh/a`.
- **dão allow:** os controles `echo ok 2>&1`, `> out.txt 2>&1`, `ls >/tmp/out.txt`, `echo x > .cehx/a` e `echo x > my.ceh.bak`.

Na intenção, a correção está boa. Os problemas estão nos pontos abaixo.

## 2. Achados

### CC1 — Toda escrita em qualquer `*config.json` passou a ser negada, inclusive pelas ferramentas de escrita da IDE — ALTA

Commit 1 (`8f635e4`): `is_ceh_target` (`rules.py`) e `is_protected_target` (`engine.py`) passaram a negar qualquer alvo cujo caminho **contenha** `config.json`, em qualquer diretório.

Gate da `dev` × gate do PR (`OBSERVED`):

| Caso | `dev` | PR #11 |
|---|---|---|
| `echo {} > tsconfig.json` | allow | **deny** |
| `npx tsc --showConfig > tsconfig.json` | allow | **deny** |
| `jq . a.json > config.json` | allow | **deny** |
| `echo x > src/app/config.json` | allow | **deny** |
| `cat base.json > jsconfig.json` | allow | **deny** |
| payload do Antigravity `write_to_file` com `TargetFile` = `<repo>/tsconfig.json` | allow | **deny** (G9) |
| payload do Antigravity `write_to_file` com `TargetFile` = `<repo>/src/config.json` | allow | **deny** (G9) |

Na IDE, o agente deixa de conseguir editar `tsconfig.json`, `jsconfig.json` ou qualquer `config.json` de projeto. Isso é uma regressão no fluxo principal do host principal. O fuzz não pega, porque só procura afrouxamentos, e o corpus não tem nenhum `config.json` fora do `.ceh/`.

**Correção** (testada nesta revisão em cópia temporária): tirar `"config.json"` da lista de substrings nas duas funções. O `.ceh/config.json` continua coberto pela checagem do componente `.ceh`. Com a mudança:
- `tsconfig.json` e `src/config.json` → allow, também via `write_to_file`;
- `>.ceh/config.json`, `printf x >.CEH/config.json`, `> .ceh/config.json` e `cp a .ceh/config.json` → deny;
- `write_to_file .ceh/config.json` → deny.

Acrescente ao corpus os controles `echo {} > tsconfig.json` e `echo x > src/config.json`, e um teste de `write_to_file` em `tsconfig.json`.

### CC2 — `rules.py` não importa `Path`: a resolução de symlink é código morto — MÉDIA

`is_ceh_target` usa `Path(...)` dentro de um `try/except Exception: pass`, mas o `rules.py` não importa `pathlib.Path`. O `NameError` é engolido, e a função devolve False antes de resolver o caminho.

Repositório temporário com `link -> .ceh` (`OBSERVED`):

| Caso | Resultado |
|---|---|
| `echo x > link/a` | **allow** |
| com `Path` injetado no módulo | deny |

A D5 (Handoff 090) pedia a resolução de symlink, e a descrição do PR afirma que ela existe. Criar o symlink (`ln -s .ceh link`) continua barrado, o que limita o risco a symlinks que já existam.

**Correção:**
- `from pathlib import Path` no `rules.py`;
- trocar `except Exception` por `except (OSError, ValueError, RuntimeError)` nas duas funções, para que um erro de programação não vire allow em silêncio;
- teste com symlink real num repositório temporário: `echo x > link/a` → deny.

### CC3 — A correção do CA1 não está pinada — MÉDIA

Medido contra o gate da `dev`:
- a bateria `TestCA1WriteRedirectionControls`: **0 de 64 casos** mudam de decisão. Todos os alvos são `last-ci-run.json`, que a v2.1.0 já negava (F01);
- os 38 comandos novos do corpus: só **4** mudam, e todos são o afrouxamento do CA5 (CC4).

Ou seja, nada na suíte prende o que o CA1 de fato corrigiu: arquivos genéricos no `.ceh/` e o `config.json` com redirecionamento colado ou com descritor.

**Correção:** incluir no corpus e na bateria:
- `echo x >.ceh/a`, `printf x >.ceh/config.json`, `echo x 1>.ceh/a`, `echo x &>.ceh/a`, `echo x >.CEH/a`, `echo x >>.ceh/a` e `exec 3>.ceh/a`;
- o symlink do CC2, só na bateria, porque o corpus não cria arquivos;
- os controles `echo x > .cehx/a`, `echo x > my.ceh.bak` e os dois do CC1.

Critério: revertendo o commit 1, pelo menos esses casos têm que reprovar.

### CC4 — O `gate_baseline` foi movido para um commit intermediário do próprio PR e escondeu 6 afrouxamentos — MÉDIA (processo, PR-QA-A)

O commit 3 trocou `e608ea7` por `048ed06`, que é o commit 2 do próprio PR. Ele não foi homologado e já contém o CA1. Além disso, nele o `gate_corpus.txt` foi alterado sem o `.expected.jsonl`, então o snapshot daquele commit está inconsistente.

O cabeçalho do teste diz: "linha de base … avançada exclusivamente pela revisão". As listas de relaxamentos continuam citando `e608ea7`.

`test_gate_differential_fuzz.py` com o gate final do PR (`OBSERVED`):

| Linha de base | Resultado |
|---|---|
| `4a637fe` (último homologado: `dev` com o PR #9) | **REPROVADO: 6 relaxamentos não autorizados** |
| `e608ea7` (o valor anterior) | **REPROVADO: os mesmos 6** |
| `048ed06` (o valor do PR) | OK |

Os 6 afrouxamentos são `cat .ceh/last-ci-run.json > /tmp/output.json` e `cat .ceh/last-ci-run.json > output.json`, nos 3 ambientes, de deny para allow. É o CA5: um falso positivo que, por si, é bom eliminar. Mas o mecanismo exige declarar o afrouxamento, não mover a linha de base para cima dele. O Handoff 090 também previa o CA5 no PR de documentação, como limite conhecido.

**Correção:**
1. `gate_baseline.txt` = `4a637fe`, o último gate homologado.
2. Declarar as 6 linhas em `relaxamentos_justificados.txt` com o ID `CA5`.
3. Registrar o CA5 como corrigido na descrição do PR.

Depois do merge, a revisão avança a linha de base para o commit de merge e zera as listas, como no Handoff 086.

### Ressalvas baixas

**CC5 — Ordem dos commits.**

- O commit 3 ("baseline") também muda código: `normalize_path` em `engine.py` e `rules.py`.
- O commit 2 deixa o snapshot inconsistente.

Não reescreva o histórico. Os commits de correção desta rodada vêm antes de qualquer avanço de corpus ou de baseline, cada um com a suíte verde.

**CC6 — Limites que faltam na documentação.**

- O ADR 007 não registra o TOCTOU do CA1 (D5).
- O `gate-normalization.md` §4.2 ainda trata os redirecionamentos colados como "planejado para v2.1.1"; passam a ser vigentes.
- A escrita no `.ceh/` por interpretador (`python3 -c "open('.ceh/a','w')…"`) dá allow na `dev` e no PR. Registre isso como limite do gate estático.

## 3. Próximos passos

1. O agente corrige CC1–CC4 no próprio PR #11 e, de preferência, também o CC6. A correção do CC1 e do CC2 está descrita acima e foi testada nesta revisão em cópia temporária, sem push: a suíte passa 77/77 com ela. Isso também mostra que nada na suíte cobre hoje o CC1 nem o CC2, daí os casos novos pedidos no CC3.
2. Nova revisão, que inclui o fuzz contra `4a637fe`.
3. Merge.
4. A revisão avança a linha de base para o commit de merge.
