# Handoff 033 — Revisão do PR-07c e despacho do PR-07d (equivalência de contexto)

**Data/Hora:** 2026-09-27T09:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `37f2079` (PR-07c)
**Antecessor:** [Handoff 032](./handoff-032-revisao-pr07b.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVAS**

Reproduzido de forma independente (`OBSERVED`):

| Item | Prova |
|---|---|
| B1 (baseline isolada) | A baseline e o gate atual rodam em **subprocessos separados** (`Popen` com o `sys.path` da baseline). |
| B2 (prova real) | O teste tautológico foi removido. Num clone com `ENV_KEY_SEGMENTS = set()`, a matriz reprova com **28** relaxamentos e nomeia `[dev] terraform destroy -var env=production: deny->allow`, o mesmo número que está no `pr07c-evidence.md`. |
| B3 | `relaxamentos_deteccao.txt` no formato `branch\|comando\|de->para\|ID`, vazio. |
| AG1 (subshell) | `(cd <main> && git reset --hard)` e `( (cd <main> && …) )` = deny/production. O contexto **não vaza** para fora dos parênteses: `(cd <main>) && git reset --hard` e `(cd <main> && ls); git reset --hard` = allow, **igual ao shell real**. |
| AG2 (`cd` incerto) | `cd "$PROD_DIR" && git reset --hard` e `cd - && …` = deny/production. `cd "$DIR" && npm test` = allow. |
| Pathspec com parênteses | `':(top)'` e `':(exclude)x'` seguem tratados como pathspec, não como subshell. Corpus e bateria sem alteração. |

**Linha de base avançada** para `37f2079`. Os dois arquivos de justificativa seguem vazios.

**Nota de processo:** o relatório de entrega declarou "Onda 1 formalmente concluída". O encerramento de onda é da revisão, pelo critério do Handoff 028 §4.

## 2. Ressalvas

### AH1 — MÉDIO (G6): outras formas de mudar o contexto (`OBSERVED`, repo em `dev`)

| Comando | Hoje | Correto |
|---|---|---|
| `{ cd <main>; git checkout -- .; }` (bloco: o `cd` **vale** dentro dele) | allow/development | deny/production |
| `env -C <main> git reset --hard`, `env --chdir=<main> …` | allow/development | deny/production |
| `sudo -D <main> git reset --hard` (`--chdir`) | allow/development | deny/production |
| `GIT_DIR=<main>/.git GIT_WORK_TREE=<main> git reset --hard` | allow/development | deny/production |
| `export GIT_DIR=<main>/.git && git reset --hard` | allow/development | deny/production |

Já funcionam: `cd`, `pushd`, `cd … \|\| exit;`, subshell, `bash -c "cd … && …"` e `git -C`. O `git --git-dir` é negado (fail-closed).

### AH2 — BAIXO: `cd` sem argumento

`cd && git reset --hard` vai para o `$HOME` e sai allow/development. Já `cd ~ && …` é tratado como incerto. Os dois são o mesmo destino, então devem ter a mesma regra.

### AH3 — BAIXO (custo): a rede de detecção leva ~42 s

Somada ao fuzz (~22 s), ela dobra o tempo da suíte. A causa provável é a detecção de branch, que faz uma chamada `git` **por comando avaliado**. Solução sugerida: cache por `target_dir` em `get_git_branch` e `find_repo_root`, dentro do processo. Isso acelera também o hook real. Meta: rede de detecção < 15 s.

## 3. Despacho — PR-07d `fix(gate): equivalência de contexto (bloco, env -C, sudo -D, GIT_DIR) e cache de branch`

1. **Um único ponto que define o contexto do alvo.** As formas abaixo produzem o mesmo `target_dir` que `cd X &&` produziria:
   - bloco `{ …; }`, que **propaga** o contexto, ao contrário do subshell;
   - `env -C X` / `env --chdir=X` / `--chdir X`;
   - `sudo -D X` / `sudo --chdir=X`;
   - `GIT_DIR=X/.git` ou `GIT_WORK_TREE=X`, como atribuição no comando ou via `export` anterior. Nesse caso, o repositório alvo é o de `X`.
   - O `cd` sem argumento é tratado como `cd ~` (AH2).
2. **Invariante de equivalência de contexto** no `test_environment_tokens.py` ou na rede de detecção:
   - para cada comando destrutivo `C` da bateria e cada forma `F` da lista acima, a decisão de `F(<main>, C)` tem de ser ≥ a de `cd <main> && C`;
   - **falsificabilidade:** remova o tratamento de `env -C` num clone e mostre a invariante reprovando.
3. **AH3:** cache por diretório em `get_git_branch`/`find_repo_root`. Registre na evidência o tempo antes e depois.

### Critérios de aceite do PR-07d

- [ ] Todas as linhas da tabela AH1 e o AH2 estão no `test_environment_tokens.py`, verdes. Os controles do subshell (sem vazamento) seguem allow.
- [ ] A invariante de equivalência está no teste, com a prova de falsificabilidade por mutação real e a saída colada.
- [ ] As duas redes diferenciais contra `37f2079` registram 0 relaxamentos. A rede de detecção leva < 15 s.
- [ ] Protocolo 7.1. O plano não é editado pelo agente, e o encerramento da Onda 1 não é declarado pelo agente.

## 4. Onda 1

Com o PR-07d homologado, a Onda 1 fecha. A invariante de equivalência cobre a classe "mudança de contexto" por construção, e não por lista.
