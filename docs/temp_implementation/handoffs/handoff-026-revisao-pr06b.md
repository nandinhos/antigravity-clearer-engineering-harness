# Handoff 026 — Revisão do PR-06b e despacho do PR-06c (resolução única da cabeça do comando)

**Data/Hora:** 2026-09-26T10:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `75a763a` (PR-06b)
**Antecessor:** [Handoff 025](./handoff-025-revisao-pr06.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVAS**

Reproduzido de forma independente (`OBSERVED`):

| Item | Prova |
|---|---|
| AA1–AA3 | As 17 linhas `PENDENTE:H025` ficaram verdes. O diff da bateria **só remove prefixos**. |
| Diferencial contra `2820dad` | 0 relaxamentos no fuzz e em 29 sondas novas da revisão (prefixos, embrulhos, `subprocess`/`spawnSync` com lista, `$0`/`$1`). Vários **apertos corretos**: `subprocess.run(['rm','-rf','/'])`, `spawnSync('rm',['-rf','/'])` e `env -i bash -c "find / -delete"` agora saem deny. |
| Falsificabilidade do AA1 | Num clone, desliguei o desembrulho do `-exec` no `find.py` e restaurei o retorno antecipado. Com corpus e bateria vazios, o fuzz reprova com **75** relaxamentos, o mesmo número do agente. |
| Composição | `max_severity_decision` + `finalize` em todos os retornos de `evaluate_subcommand`, inclusive no ramo do `git.py`, que era o ponto 1 do despacho. |

**Observação (sem ação):** só a regra de composição, sozinha, não é falsificável hoje. Com o desembrulho ativo, reintroduzir **só** o retorno antecipado não muda nenhuma decisão, porque o `find.py` já devolve CATASTROPHIC pelo `-exec`. Ela fica como defesa em profundidade.

**Linha de base avançada** para `75a763a`. O `relaxamentos_justificados.txt` segue vazio e o fuzz, verde.

## 2. Achados

### AB1 — ALTO (mesma classe, ainda aberta): prefixos de execução escondem o comando dos analisadores por tokens

`OBSERVED` em produção. O resultado é igual no `2820dad`, então **não é regressão**, mas o aceite do G5 ("`find /` = CATASTROPHIC em qualquer ambiente") e o G2 seguem contornáveis:

| Comando | Decisão |
|---|---|
| `nice find / -delete`, `timeout 10 find / -delete`, `nohup find / -delete`, `sudo -u deploy find / -delete` | **allow** |
| `timeout 5 python3 -c "…shutil.rmtree('/')"` | **allow** |
| `sudo -u root bash -c "…"`, `timeout 5 bash -c "…"`, `exec bash -c "…"`, `xargs -I{} sh -c '…'` | **allow** |
| `eval "find / -delete"`, `su -c "…"`, `watch -n1 "…"` | **allow** |
| `nice git checkout -- .` | **allow** (o `git.py` tem a mesma lacuna desde o PR-05c) |

Por que o `rm` não sofre com isso: a regex antiga casa `rm -rf /` em qualquer lugar do texto, com qualquer prefixo (`timeout 5 rm -rf /` = CATASTROPHIC). Os **analisadores por tokens** (`git.py`, `find.py`, `interpreters.py`, `extract_shell_c_command`) só reconhecem `sudo`, `rtk`, `command` e `env`, e cada um tem **a sua própria cópia** desse laço. É o padrão 1 do Handoff 018 outra vez: quatro enumerações independentes da mesma coisa.

### AB3 — BAIXO: parâmetros posicionais do `sh -c`

Em `bash -c 'rm -rf "$0"' /` e `bash -c 'find "$1" -delete' _ /`, os valores de `$0`, `$1`… estão **na própria linha de comando**. Hoje o gate os trata como variável não resolvida (allow em DEV), quando o alvo real é `/`.

Os dois achados estão na bateria como `PENDENTE:H026-*` (**15 linhas**), com 6 controles: `nice npm run build`, `timeout 5 git status`, `sudo -u deploy ls /var/www`, `watch -n1 "git status"`, `time python3 -c "print(1)"` e `bash -c 'echo "$0"' /`.

## 3. Despacho — PR-06c `fix(gate): resolução única da cabeça do comando` (fecha a Onda 1)

1. **Uma função em `ceh_core`** (`resolve_command_head(tokens) -> (head_idx, string_exec | None)`) usada por **todos** os analisadores por tokens. As 4 cópias do laço de prefixos são removidas.
   - **Prefixos transparentes**, com as opções de cada um consumidas conforme a `--help` da ferramenta (cite no PR): `sudo` (`-u X`, `-g X`, `-E`, `-H`…), `doas`, `env` (opções e `VAR=val`), `command`, `builtin`, `exec`, `nice` (`-n N`), `nohup`, `timeout` (opções + duração), `time`, `stdbuf`, `ionice`, `chrt`, `taskset`, `xargs` (opções; `-I{}` troca `{}` por um nome inócuo), `rtk`.
   - **Executores de string:** `eval <str…>`, `su -c <str>`, `watch [opções] <str>`. A string é avaliada **recursivamente** com o gate inteiro (mesma regra de profundidade do PR-06b).
   - **Prefixo desconhecido seguido de um comando conhecido não é problema desta função.** Ela resolve só a lista acima. O fuzz (item 3) é que mede a cobertura.
2. **AB3:** no desembrulho de `sh|bash|zsh|dash -c SCRIPT [arg0 [arg1…]]`, substitua `$0`, `$1`… e `"$@"` pelos argumentos antes da avaliação recursiva, com as aspas preservadas.
3. **Invariante de prefixo no fuzz:** estenda a invariante de embrulho do PR-06b. Para cada comando gerado `X`, a decisão de `nice X`, `timeout 5 X`, `sudo -u x X`, `nohup X`, `exec X`, `eval "X"` e `watch -n1 "X"` tem de ser **pelo menos tão severa** quanto a de `X`.
   - **Falsificabilidade:** num clone, remova `nice` da lista de prefixos. A invariante tem de reprovar **só pela gramática**, com corpus e bateria vazios.
   - Se o tempo total do fuzz passar de ~20 s, reduza a amostra da invariante (hoje são 400 comandos), mas não os embrulhos.

### Critérios de aceite do PR-06c

- [ ] As 15 linhas `PENDENTE:H026-*` ficam verdes, e todos os controles (H017–H026) seguem verdes.
- [ ] `grep -n '"sudo", "rtk", "command"'` nos 4 módulos → **uma** ocorrência (a função única).
- [ ] O diferencial contra `75a763a` registra 0 relaxamentos e nenhuma linha nova em `relaxamentos_justificados.txt`.
- [ ] A invariante de prefixo está no fuzz, com a prova de falsificabilidade sem bateria.
- [ ] Toda decisão alterada no corpus está justificada em `pr06c-corpus-diff.md`. O plano **não** é editado pelo agente. Protocolo 7.1 e relatório `--strict`.

Com o PR-06c homologado, **a Onda 1 fecha**: G1–G6, sem contorno conhecido na bateria.

## 4. Sequência

PR-06c → PR-QA B–E (o item D, canonicalização única de caminho, é o irmão natural do PR-06c) → Onda 2 (PR-08 G7, PR-09, PR-10). `curl | bash` segue no backlog.
