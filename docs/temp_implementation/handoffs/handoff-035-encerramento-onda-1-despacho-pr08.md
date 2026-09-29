# Handoff 035 — PR-07e homologado, encerramento da Onda 1 e despacho do PR-08 (G7)

**Data/Hora:** 2026-09-27T11:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `9dfc85a` (PR-07e)
**Antecessor:** [Handoff 034](./handoff-034-revisao-pr07d.md)

---

## 1. PR-07e: **HOMOLOGADO**

Reproduzido de forma independente (`OBSERVED`, repo em `dev`):

- **AI1:** `git switch main && git reset --hard`, `git checkout main && …`, `git switch -c main-fix && …` e `git checkout -B production && git clean -fdx` = deny/production.
- **AI2:**
  - `source .env.production &&`, `. ./prod.env &&` e `cp .env.production .env &&` = deny/production;
  - `mv .env.staging .env && php artisan db:wipe` = ask/staging.
- **Controles:** `git checkout -b hotfix && git reset --hard`, `git checkout app/Model.php && git reset --hard`, `git checkout main` sozinho, `git switch main && npm test` e `cp .env.example .env && php artisan key:generate` = allow.
- **Falsificabilidade:** num clone, restringi a linha 172 do `environment.py` a `("switch",)`. A invariante reprova com `git_checkout_main: … (allow) < 'cd … && git reset --hard HEAD~1' (deny)`, a mesma saída da evidência.
- **Coerência:** um repositório que **está** na branch `main-fix` também é production (a mesma regra de segmento), então a troca estática e a detecção real concordam.

**Linha de base avançada** para `9dfc85a`. As duas redes diferenciais seguem verdes, com as justificativas vazias.

## 2. **ONDA 1 ENCERRADA** (G1–G6)

Pelo critério do Handoff 028 §4: nenhuma rodada de revisão encontra mais contorno nas classes cobertas.

| Classe | O que o gate faz hoje | Rede que protege |
|---|---|---|
| G1/G4 `rm` | Alvos normalizados; catastrófico = raiz, `HOME`, `/home/x` ou pasta acima; atalho seguro só dentro do cwd | Fuzz de invariantes (2500), corpus, bateria |
| G2/G3 `git` | Analisador por tokens (pathspec canônico, magia, abreviações, opções globais) | Fuzz diferencial, bateria |
| G5 indireto | `find`, interpretadores (python/node/deno/bun/perl/ruby/php/awk), shells, embrulhos e prefixos (varredura sem lista, em um nível) | Invariantes de embrulho, de prefixo e de benignidade |
| G6 contexto | Alvo do host, `cd`/`pushd`/subshell/bloco/`env -C`/`sudo -D`/`GIT_DIR`, troca de branch, `.env` carregado, sinais por forma (só escalam) | Rede diferencial da detecção + invariantes de não rebaixamento e de equivalência de contexto |

**Limites documentados (backlog, não reabrem a Onda 1):**
- `curl … | bash`;
- `ssh host "…"` e `docker exec`;
- código vindo de arquivo ou do stdin;
- comandos montados em tempo de execução;
- alvos opacos (`make -C`, `npm --prefix`);
- banco e infraestrutura não detectados: `prisma migrate reset --force`, `docker compose down -v`, `php artisan migrate --force`.

**Falsos positivos anotados (baixos, fail-closed):**
- `git checkout main -- app/Model.php && git reset --hard` = deny. Com `--`, não há troca de branch.
- `echo find / -delete` = deny. É o custo aceito da varredura sem lista.

## 3. Despacho — PR-08 `fix(gate): validar os refspecs do push contra o certificado` (G7, Onda 2)

**Estado atual (`OBSERVED`):** o `check_pre_push_ci_gate` compara o certificado **só com o HEAD**. `cluster4_acceptance.py` mantém o G7 em RED: `git push origin outro:main`, com `outro` apontando para um commit **não certificado**, sai allow.

1. **Módulo novo `ceh_core/push.py`** (≤ 300 linhas). O `safety-gate.py` está em 635/650 e não comporta a lógica.
2. **Análise por tokens do `git push`**, reaproveitando a resolução de contexto (`git -C`, `cd`…):
   - remoto, refspecs (`src:dst`, `+src:dst`, `src`, `HEAD`, `HEAD:refs/heads/main`) e opções: `-f`/`--force`, `--force-with-lease[=…]`, `-d`/`--delete`, `--all`, `--mirror`, `--tags`, `--follow-tags`, `-u`, `--set-upstream`, `--no-verify`, `-o`/`--push-option <v>`;
   - resolução das opções longas por prefixo único, como no `git.py`: abreviação só aperta.
3. **Regra do certificado** (repositório com CI):
   - cada `src` é resolvido com `git rev-parse --verify <src>^{commit}` no repositório alvo, e **todos** têm de ser iguais ao `commit_hash` do certificado;
   - sem refspec (`git push`, `git push origin`), vale o comportamento atual (HEAD);
   - `src` que não resolve → **deny** (fail-closed), com motivo nomeando o refspec;
   - `--all`, `--mirror` e `--tags` → **deny**: não dá para certificar um conjunto;
   - deleção (`:dst`, `--delete dst`) não envia commit, então fica fora do certificado; a regra que já existe decide.
4. **Testes:**
   - o RED do G7 fica **verde** (sem `@expectedFailure`), e o controle `git push origin dev:main` com `dev` certificado segue allow;
   - `tests/test_pre_push_refspecs.py`, com um repositório-fixture que tem CI, certificado do HEAD e branch `outro` não certificada. Casos:
     - `outro:main`, `+outro:main` e `outro` = deny;
     - `HEAD:main` = allow;
     - `--all`, `--mirror` e `--tags` = deny;
     - `origin :feature` segue a regra que já existe;
     - `--forc` = mesma decisão de `--force`;
     - `git -C <fixture> push origin outro:main` = deny;
     - `cd <fixture> && git push origin outro:main` = deny;
   - **falsificabilidade:** num clone, faça o gate ignorar o `src` (comparar só o HEAD) e mostre o teste reprovando e nomeando `outro:main`.
5. **Redes:** os dois diferenciais contra `9dfc85a` registram 0 relaxamentos. Os pushes do corpus e da bateria rodam em fixture **sem** CI, então não são afetados. O teste novo é a rede do PR-08.

### Critérios de aceite do PR-08

- [ ] O RED do G7 está verde; `cluster4_acceptance.py` não tem mais nenhum `@expectedFailure`.
- [ ] `test_pre_push_refspecs.py` cobre a lista do item 4, com a prova por mutação real e a saída colada na evidência.
- [ ] Lógica em `ceh_core/push.py`; `safety-gate.py` ≤ 650 linhas.
- [ ] Protocolo 7.1. O plano não é editado pelo agente.

## 4. Sequência da Onda 2 em diante

PR-08 (G7) → PR-09 (payload vazio → deny) → PR-10 (proteção do certificado e escrita de arquivo) → Onda 3: PR-11 (instalador honesto) e PR-12 (SemVer/CHANGELOG) → **tag v1.3.0**.

A trilha PR-QA (B: integridade do motivo; C: contrato com `--help`; D: canonicalização única) vai para a Onda 5. Os itens A, A2 e as invariantes das Ondas 1 e 2 já cobrem o risco principal.
