# Handoff 034 — PR-07d homologado e despacho do PR-07e (troca de branch e arquivo de ambiente)

**Data/Hora:** 2026-09-27T10:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `8da15d7` (PR-07d)
**Antecessor:** [Handoff 033](./handoff-033-revisao-pr07c.md)

---

## 1. Veredito: **HOMOLOGADO**

Reproduzido de forma independente (`OBSERVED`, repo em `dev` e alvo na `main`):

| Item | Prova |
|---|---|
| AH1 | `{ cd <main>; git checkout -- .; }`, `env -C`, `env --chdir=`, `sudo -D`, `GIT_DIR=… GIT_WORK_TREE=…` e `export GIT_DIR=… &&` = **deny/production**. |
| AH2 | `cd && git reset --hard` = deny/production (tratado como `cd ~`). |
| Controles | O subshell não vaza (`(cd <main>) && git reset --hard` = allow); `env -C <main> npm test`, `sudo -D <main> ls` e `cd "$DIR" && npm test` = allow. |
| Invariante de equivalência | Num clone, tirei o `-C` das linhas 192/197 do `environment.py`. A invariante reprova com a mesma mensagem da evidência (`env_C: … (allow) < 'cd … && git reset --hard HEAD~1' (deny)`). |
| AH3 | A rede de detecção caiu de ~42 s para **7,8 s** (meta < 15 s). |
| Processo | O agente não declarou o encerramento da onda e não editou o plano. |

**Linha de base avançada** para `8da15d7`. As justificativas seguem vazias.

## 2. Varredura final da classe G6 (mudança de contexto dentro do comando)

Fechadas: `cd`, `pushd`, `cd …||exit;`, subshell (sem vazamento), bloco, `env -C`, `sudo -D`, `GIT_DIR`/`GIT_WORK_TREE`, `git -C`, `bash -c "cd …"`, `cd` incerto e `cd` sem argumento. Restam duas formas (`OBSERVED`, repo em `dev`):

| ID | Comando | Hoje | Correto |
|---|---|---|---|
| **AI1** | `git switch main && git reset --hard` | allow/development | deny/production (o reset roda na `main`) |
| **AI1** | `git checkout main && git reset --hard` (sincronizar a `main` é um padrão **comum**) | allow/development | deny/production |
| **AI2** | `source .env.production && php artisan migrate:fresh` | allow/development | deny/production |
| **AI2** | `. ./prod.env && php artisan migrate:fresh` | allow/development | deny/production |
| **AI2** | `cp .env.production .env && php artisan migrate:fresh` | allow/development | deny/production |
| controle | `echo APP_ENV=production > .env && php artisan db:wipe` | deny/production | já funciona (atribuição) |
| controle | `git checkout -b hotfix && git reset --hard` | allow | segue allow (`hotfix` não é branch de produção) |
| controle | `git checkout app/Model.php && git reset --hard` | allow | segue allow (pathspec, não troca de branch) |

**Fora do escopo** (alvo opaco, backlog): `npm --prefix <dir> run …` e `make -C <dir> …`. O gate não enxerga o que o script ou o alvo executam.

## 3. Despacho — PR-07e `fix(gate): troca de branch e arquivo de ambiente como mudança de contexto`

1. **AI1:** `git switch <b>`, `git switch -c/-C <b>`, `git checkout <b>` e `git checkout -b/-B <b>` passam a definir a **branch de contexto** dos subcomandos seguintes. Ela é classificada pela mesma regra de branch que já existe (`main`/`master`/`production`/`prod` → production; segmentos de staging → staging).
   - O modelo é **estático**: usa o nome da branch do comando, não o estado do git. O gate roda **antes** da execução, e o cache do PR-07d não pode ser usado para "reler" a branch.
   - Um `git checkout <x>` em que `<x>` também existe como caminho no diretório é ambíguo. Nesse caso, trate como troca de branch **só se** o nome classificar como produção ou staging (só escala).
2. **AI2:** `source F`, `. F` e `cp|mv|ln -s F .env` (destino terminando em `.env`) definem o **ambiente de contexto** dos subcomandos seguintes pelos segmentos do nome de `F` (`.env.production` → production). Isso só escala.
3. **Invariante de equivalência estendida:** acrescente à lista de formas `F` do PR-07d:
   - `git switch main &&` e `git checkout main &&` (comparados a `cd <main> && C`);
   - `source .env.production &&` e `cp .env.production .env &&` (comparados a `APP_ENV=production C`).
   - **Falsificabilidade:** num clone, desligue o tratamento de `git checkout <b>` e mostre a invariante reprovando.

### Critérios de aceite do PR-07e

- [ ] Todas as linhas da tabela da seção 2 estão no `test_environment_tokens.py`, verdes, inclusive os 3 controles.
- [ ] A invariante estendida está no teste, com a prova por mutação real e a saída colada.
- [ ] As duas redes diferenciais contra `8da15d7` registram 0 relaxamentos. Protocolo 7.1. O plano não é editado pelo agente.

## 4. Onda 1

Com o PR-07e homologado, a classe G6 fica coberta por invariante para as formas que o gate consegue modelar sem executar nada. As que dependem de execução (alvos de `make`/`npm`, `ssh`, `docker exec`) ficam como **limite documentado**, no backlog. **Com o PR-07e homologado, a Onda 1 fecha.**
