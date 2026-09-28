# Handoff 028 — Revisão do PR-06d, varredura final das classes G1–G6 e despacho do PR-06e

**Data/Hora:** 2026-09-26T12:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `fe171a7` (PR-06d)
**Antecessor:** [Handoff 027](./handoff-027-revisao-pr06c.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVAS**

Reproduzido de forma independente (`OBSERVED`):

| Item | Prova |
|---|---|
| AC1 | As 6 linhas `PENDENTE:H027` ficaram verdes; o diff da bateria **só remove prefixos**. Os controles (`sudo --user deploy systemctl status nginx`, `taskset -c 0 npm test`, `env -S 'npm run build'`) seguem allow. |
| Falsificabilidade da varredura | Num clone, desliguei o bloco da varredura. Com corpus e bateria vazios, a invariante reprova com **1.066** violações no total. As 527 que o agente registrou são só as do prefixo `sudo --user x`, então os números batem. |
| Diferencial contra `3ac81b0` | 0 relaxamentos. |
| Processo | Suíte, evals, relatório `--strict` e gate conferido em passo separado, antes do push. O plano não foi editado pelo agente. |

**Linha de base avançada** para `fe171a7`.

## 2. Varredura final das classes G1–G6 (critério do Handoff 027 §4)

Fiz uma rodada completa sobre `rm`, `git`, `find`, interpretadores, embrulhos e prefixos. **Seguem fechados:**

- `rm` em qualquer posição (`setsid rm -rf /`, `echo rm -rf /`, `rm --recursive --force /`, `rm -rf /*`);
- `find … -exec shred`, `xargs -0 rm`;
- opções globais do git (`-c`, `--git-dir`, `--work-tree`);
- interpretadores com opções que recebem valor (`python3 -W/-X`, `ruby -E`, `node -r`);
- APIs que abrem shell (`os.popen`, crases).

Achados **dentro** das classes, que reabrem a Onda 1 (`OBSERVED`):

| ID | Sev. | Descrição |
|---|---|---|
| **AD1** | **ALTO** | A varredura de sufixos só roda se a **primeira** palavra estiver em `KNOWN_PREFIXES`, uma **segunda lista** de prefixos, paralela à do `lexer.py`. Qualquer outro embrulho esconde `find`, `git` e os interpretadores. Em produção saem **allow**: `setsid find / -delete`, `flock /tmp/l find /…`, `chroot / find /…`, `busybox find /…`, `strace -f find /…`, `ssh host find /…`, `docker exec app find /…` e `setsid git checkout -- .`. O `rm` não sofre com isso porque o caminho antigo o procura em qualquer posição (`setsid rm -rf /` = CATASTROPHIC). |
| **AD2** | MÉDIO | Shells fora da lista: `ksh -c`, `fish -c` e `ash -c "find / -delete"` saem allow. |
| **AD3** | MÉDIO | Um agrupamento de flags é lido letra por letra, **inclusive dentro do argumento colado**. Em `perl -MFile::Path -e '…'`, o "e" de "File" é lido como `-e`, e o código real nunca é analisado (allow para `rmtree("/")`). |
| **AD4** | MÉDIO | Famílias sem cobertura. **PHP** (`php -r`) é a mais relevante, porque o alvo do CEH é Laravel: `php -r 'array_map("unlink", glob("*"));'` sai allow em produção, e `php -r 'system("rm -rf /");'` sai allow em DEV. Também `awk 'BEGIN{system("find / -delete")}'`, `deno eval` e `bun -e`. |

Os achados estão na bateria como `PENDENTE:H028-*` (**19 linhas**), com 10 controles. Entre eles:
- `git commit -m "find / -delete"`, `grep -rn find src/`, `man find`, `which python3` e `sudo apt install git`;
- `docker exec app php artisan route:list`, `php -r 'echo PHP_VERSION;'` e `awk '{print $1}' access.log`.

## 3. Despacho — PR-06e `fix(gate): varredura sem lista, shells, flags agrupadas e PHP/awk/deno/bun`

1. **AD1: a varredura de sufixos vale para todo comando, sem lista.**
   - Para **toda** posição `j ≥ 1` cujo token, pelo nome base, é uma cabeça analisada, avalie o sufixo e componha pela decisão mais severa. **Remova `KNOWN_PREFIXES`.**
   - Isso reproduz, no nível dos tokens, o que o caminho antigo do `rm` já faz por texto, e é **menos** agressivo que ele: não olha dentro de tokens entre aspas (daí o controle `git commit -m "find / -delete"`).
   - **Custo aceito:** `echo find / -delete` passa a negar. O `echo rm -rf /` **já é negado** hoje, então não há mudança de política.
2. **AD2:** a lista de shells do desembrulho passa a ser `sh|bash|zsh|dash|ksh|mksh|ash|fish|csh|tcsh|busybox sh`.
3. **AD3: agrupamentos por interpretador, conforme o `--help` de cada um.**
   - Numa sequência de flags curtas, uma letra que **recebe argumento** consome o **resto do token** (ou o próximo token) e encerra o agrupamento:
     - Perl: `-M -m -I -x -0 -l -C`;
     - Python: `-W -X -m`;
     - Ruby: `-r -I -E -x`;
     - Node: `-r --require`.
   - Só depois disso se procura a flag de código. Cite as linhas do `--help` no PR.
4. **AD4: novas famílias**, no mesmo padrão (código inline + APIs pelo nome + desembrulho de APIs de shell):
   - **PHP:** `-r`; APIs `unlink|rmdir|array_map('unlink'…)`; shell por `system|exec|shell_exec|passthru|popen|proc_open` e crases.
   - **awk/gawk/mawk:** o programa é o primeiro argumento que não é opção; `system("…")` e `print … | "sh"` são desembrulhados.
   - **deno:** `eval`, com `Deno.remove(Sync)?`.
   - **bun:** `-e/--eval`, com as mesmas APIs do Node.
   - O `php artisan …` segue pela regra de banco de dados que já existe (`migrate:fresh`, `db:wipe` = deny em produção).
5. **Invariante com prefixo arbitrário no fuzz.** Para cada comando gerado `X` com cabeça analisada e uma palavra `W` qualquer (`setsid`, `flock /tmp/l`, `strace -f` e uma palavra aleatória da semente), a decisão de `W X` tem de ser ≥ a de `X`.
   - **Falsificabilidade:** restaure a condição `first_tok in KNOWN_PREFIXES`. A invariante tem de reprovar só pela gramática.

### Critérios de aceite do PR-06e

- [ ] As 19 linhas `PENDENTE:H028-*` ficam verdes, e todos os controles (H017–H028) seguem verdes.
- [ ] `KNOWN_PREFIXES` não existe mais. `grep -n KNOWN_PREFIXES` → vazio.
- [ ] O diferencial contra `fe171a7` registra 0 relaxamentos e nenhuma linha nova em justificativas.
- [ ] A invariante com prefixo arbitrário está no fuzz, com a prova de falsificabilidade.
- [ ] `pr06e-corpus-diff.md` se o corpus mudar. Os limites de linhas seguem valendo: se o `interpreters.py` passar de 300 linhas, divida por família (`interpreters_php.py`…), sem subir o teto. O plano não é editado pelo agente. Protocolo 7.1.

## 4. Encerramento da Onda 1 (compromisso)

Com o PR-06e homologado, **a Onda 1 fecha**. A lista de famílias cobertas fica **fechada e documentada**: python, node/deno/bun, perl, ruby, php, awk e os shells acima.

Vão para o **backlog** (limite documentado), sem reabrir a Onda 1:
- outra linguagem;
- código vindo de arquivo ou do stdin;
- execução remota (`curl | bash`);
- comando montado em tempo de execução.

## 5. Sequência

PR-06e → **fechamento da Onda 1** → PR-QA B–E → Onda 2 (PR-08 G7, PR-09, PR-10).
