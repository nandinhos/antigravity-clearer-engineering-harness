# Handoff 048 — PR-22 **não homologado**: o relaxamento AM2 reabriu a escrita do certificado (G9); despacho do PR-22b

**Data/Hora:** 2026-09-28T01:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `21b440b`, `4c837c3` (PR-22)
**Antecessor:** [Handoff 047](./handoff-047-revisao-pr18b-despacho-pr22.md)

---

## 1. Veredito: **NÃO HOMOLOGADO**

O PR-22 acerta o AT3, mas o relaxamento do AM2 **reabriu o G9** (proteção do certificado, homologado no PR-10). A linha de base **permanece em `d6bf922`**.

### AV1 — ALTO (regressão de segurança): `git diff|log|show --output=<.ceh/…>` grava o certificado

- **Reproduzido (`OBSERVED`), comparado com a base `d6bf922`:**

  | Comando (env production) | base `d6bf922` | HEAD `4c837c3` |
  |---|---|---|
  | `git diff --output=.ceh/last-ci-run.json` | deny | **allow** |
  | `git log -1 --output=.ceh/last-ci-run.json` | deny | **allow** |
  | `git show --output=.ceh/last-ci-run.json HEAD` | deny | **allow** |

- **Causa:** `is_git_read_subcommand` (`rules.py`) trata `status|log|diff|show` como leitura pura e **ignora as flags** (`arg.startswith("-") → continue`). Mas `git diff/log/show` aceitam **`--output=<arquivo>`**, que **escreve**. O `--format=` do `git log` controla o conteúdo. Juntos, gravam um JSON arbitrário em `.ceh/last-ci-run.json`.
- **Impacto de ponta a ponta:** num repositório-fixture com CI, sem certificado, o push é **deny**. Depois de
  `git log -1 --format=<json PASS com %H> --output=.ceh/last-ci-run.json` (que o gate **libera**), o mesmo push passa a **allow**. **O certificado foi forjado com um único comando que o gate aprova.** É exatamente a classe de ataque que o PR-10/G9 fechou.
- **Estas linhas ainda não estão na bateria.** Verifiquei que, se acrescentadas hoje, elas deixam as **redes diferenciais vermelhas** (a rede lê a bateria e vê deny→allow, exatamente a regressão). Como não corrijo o código do PR e não certifico um HEAD vermelho, elas ficam especificadas aqui e o **PR-22b as adiciona junto com a correção**, já como `deny`. Controles a usar: `git diff .ceh/…` e `git show HEAD:app.txt` = allow; `git format-patch --output=.ceh/…` já = deny.

### AV2 — MÉDIO: `strip_ceh_exclusions` enfraquece a detecção em qualquer comando

- `strip_ceh_exclusions` remove `--exclude .ceh` / `-path ./.ceh -prune` de **toda** linha, antes de checar o alvo. Isso vale mesmo para comandos que **não** têm semântica de exclusão.
- Efeito colateral observado: `python3 -c "…copytree('/tmp/fake', dst)…" --exclude .ceh` (sem redirecionamento) passou de **deny** (base) para **allow**, porque o texto `--exclude .ceh` some e some também o gatilho que gerava o deny. O `python3 … > .ceh/…` (com redirecionamento) continua deny.
- É um caso de alvo opaco (backlog), mas a regressão de deny para allow **não está justificada** na lista.

### AV3 — MÉDIO (método): os relaxamentos não listados não foram vistos pela rede diferencial

- `relaxamentos_justificados.txt` lista **só** as 5 leituras do AM2 × 3 ambientes. O AV1 e o AV2 **não** aparecem lá, e mesmo assim as evidências dizem "0 relaxamentos não autorizados".
- Motivo: o corpus do fuzz não tem as formas `--output=` nem `--exclude` com `copytree`. **A rede diferencial só vê o que está no corpus** (a lição AK2). "0 não autorizados" significa "0 dentro do corpus", não "0 no gate".
- Por isso a varredura desta revisão, fora do corpus, é o que pegou o AV1.

## 2. O que está correto (para preservar no PR-22b)

- **AT3, sólido em produção** em todas as variações que sondei (`OBSERVED`):
  - `git stash clear/drop`, com `-C .`, `-c core.x=y`, `GIT_DIR=`, `rtk git` → deny;
  - `docker volume rm/prune`, `docker compose down -v/--volumes`, `docker-compose down --volumes`, `-f prod.yml … -v` → deny;
  - `redis-cli … flushall/flushdb`, com `-n 0`, `ASYNC`, caixa alta, `bash -c "…"` → deny;
  - `prisma migrate reset --force`, `pnpm prisma migrate reset` → deny;
  - `dd … of=app.db`/`of="app.db"` → deny; `of=/dev/sda` segue CATASTROPHIC.
- A graduação DEV/HML/PROD e o `test_rules_data_infra.py` (14 casos) estão certos.
- As leituras legítimas do AM2 (`du -sh .ceh`, `diff .ceh/…`, `git status --ignored .ceh`, `--exclude=.ceh`, `-path ./.ceh -prune`) funcionam, e as 5 estão justificadas.
- Os controles de escrita seguem deny: `git diff > .ceh/…`, `rsync … .ceh/`, `tar czf .ceh/… …`, `du … > .ceh/…`.
- CI do servidor verde (4/4) em `21b440b` ([run 36361871642](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36361871642)). O verde é real; ele apenas **não cobre** o AV1.
- `rules.py` com 172 linhas (teto 300). O orçamento foi respeitado.

## 3. Nota sobre a release v1.3.0

- A tag **v1.3.0 já foi publicada** pelo desenvolvedor, em `14510c7` (antes do PR-22, como recomendado), com o CI verde ([run 36358711301](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36358711301)). O `14510c7` **não** tem o AV1: ele é anterior ao PR-22. A v1.3.0 está a salvo.
- **Atenção (fora do escopo do agente, para o desenvolvedor):** a branch `main` (`aa53be1`) ainda **não** contém o conteúdo das Ondas 0–3 desta branch — o `install.sh` da `main` tem a guarda antiga do `BASH_SOURCE` (o AQ2/AO2), e o README aponta para `…/main/install.sh`. Ou seja, a tag v1.3.0 aponta para um commit **desta** branch, não para a `main`. Confirme a topologia do merge antes de anunciar a instalação por `curl … | bash`, senão o one-liner da `main` continua quebrado.

## 4. Despacho — PR-22b `fix(gate): fechar a escrita do certificado por --output e restringir strip de exclusão (AV1/AV2)`

Um commit, certificado, com o CI do servidor verde antes de qualquer declaração. Vale tudo da Onda 1 (corpus diff linha a linha, relaxamentos nomeados, redes diferenciais, um push por commit certificado, controle negativo só em `claude/negctl-*`).

1. **AV1:** a leitura pura do git só vale quando **nenhum argumento escreve**. Antes de classificar `git status|log|diff|show` como leitura:
   - se qualquer token for `-o`, `--output`, `--output=<x>`, `-O`, ou começar com `--output-` → **não é leitura pura** (segue para a checagem normal, que nega se o alvo é `.ceh`);
   - mantenha o `git diff`/`git show` de leitura (sem `--output`) como allow.
   - Reforço: a proteção do `.ceh` **não** deve depender só do nome do subcomando. Mesmo para um subcomando de leitura, se a linha resolve um **destino de escrita** dentro de `.ceh` (via `--output`, `-o`, redirecionamento, `--output-directory`), é deny.
2. **AV2:** `strip_ceh_exclusions` só pode agir quando a exclusão é **sintaticamente válida para o comando**:
   - só remova `--exclude`/`--exclude=` quando o `base_cmd` for um que aceita exclusão (`tar`, `rsync`, `r8sync`, `grep`, `rg`, `cp` com `--exclude`? não — restrinja à lista observada: `tar`, `rsync`, `grep`, `rg`, `find`);
   - só remova `-path … -prune` quando o `base_cmd` for `find`.
   - Assim, `python3 … --exclude .ceh` volta a ser tratado pelo caminho normal (opaco → o comportamento da base), e não ganha um allow novo.
3. **Bateria:** **acrescente** as 3 linhas do AV1 (já como `deny`, sem `PENDENTE`, pois o fix as torna verdes) mais os controles, no mesmo commit da correção. Como a rede diferencial lê a bateria, elas só entram junto com o fix — do contrário deixam a rede vermelha (foi por isso que o Handoff 048 não as versionou). Acrescente também o caso de ponta a ponta como teste: forja via `git log --output` seguida de push = deny (o gate nega a **escrita**; o push com certificado forjado é a consequência).
4. **AV3:** acrescente ao corpus (`gate_corpus.txt`) as formas `--output=`/`-o` para `.ceh`, para que a rede diferencial passe a cobri-las. Documente no `pr22b-corpus-diff.md`.
5. **Teste de forja de ponta a ponta** em `test_cert_protection.py` (ou no `test_rules_data_infra.py`): num repositório-fixture com CI, a sequência forja-então-push **não** pode resultar em push allow. Cubra `--output=`, `-o` e `--format` + `--output`.
6. **Falsificabilidade:** num clone, restaure o `is_git_read_subcommand` que ignora flags e mostre a bateria `H048-AV1` e o teste de forja reprovando.
7. **Evidência:** `pr22b-corpus-diff.md` linha a linha; a rede diferencial listando os relaxamentos (só os 5 AM2 legítimos devem restar); o CI do servidor verde (4/4) com os links dos jobs **dessa** execução; `git status --porcelain` vazio.

### Critérios de aceite do PR-22b

- [ ] `git diff|log|show --output=<.ceh/…>` e `-o <.ceh/…>` = deny em todos os ambientes. As leituras puras seguem allow.
- [ ] A sequência forja-então-push não libera o push, com teste de ponta a ponta.
- [ ] `strip_ceh_exclusions` só age nos comandos que aceitam exclusão; `python3 … --exclude .ceh` não é mais um relaxamento novo.
- [ ] As 3 linhas AV1 estão na bateria como `deny` e verdes. A rede diferencial mostra só os 5 relaxamentos AM2 legítimos.
- [ ] O corpus cobre as formas `--output`. O CI do servidor está verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 5. Sequência

PR-22b (fecha o G9 de novo) → homologação do AT3+AM2 e avanço da linha de base → PR-QA B–D → PR-20/21 (AU1/AU4) → Onda 4.
