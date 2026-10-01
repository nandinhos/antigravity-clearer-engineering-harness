muse: workspace root: /home/<user>/projects/clearer-engineering-harness (cwd default)
muse: Skills: 70 loaded · 1 warning · 1 detail hidden
muse:   `skills_catalog` was trimmed to fit its size limit (32 KB): 22 descriptions compacted, 0 skill ids omitted
muse:   Run `muse skills list --source all` for full diagnostics.
muse: Agent delegation: auto unavailable: workspace is untrusted.
VEREDITO: RESSALVAS
CERTEZA: 0.80
ANALISE_ESPECIALIZADA:
Invariantes 1,2,4,5,6 corretos em direção; falhas de portabilidade e runtime POSIX nos detalhes. F03 com `.lower()` viola case-sensitivity POSIX (Linux: `GIT`!=`git`) e `endswith("/git")` não cobre `/opt/homebrew/bin/git` (macOS ARM), `~/bin/git`, `command git`, `env git`, symlink; precisa basename exato + realpath/PATH, sem lower. F01: "inserir espaçamento em `>`" ingênuo destrói `2>&1`, `&>`, `>|`, `<>`, `<<-`, `<<<`; exige FSM POSIX com estados quote/escape/FD-digit e tabela completa de operadores, senão regressão léxica. F06: `docker compose exec` não é portável (Compose v1 `docker-compose` vs v2 `docker compose`, nome de serviço, `-T`, BSD sh sem `pipefail`); "corresponder semanticamente" é inverificável — exigir igualdade de argv/transporte ou `CANONICAL_VERIFIED=false`. F07: lookup deve ser `command -v` (não `which`), cobrir `python -m pytest`/`uv run`; exit infra reservado (ex: 127). F10: `os.path.isdir` segue symlink; semântica `rm -r link/` diverge GNU/BSD/macOS; há TOCTOU stat-vs-exec. F11/F13: marker sem `realpath`+`islink`+deny-list (`/`, `$HOME`, mountpoint) permite escape via symlink; `mv` só é atômico intra-filesystem e sem lock concorrente; `mktemp -d` tem flags distintas BSD/GNU. F05: `git config --get` por push = fork+exec por avaliação (latência), precisa escopo `--local`, timeout, cache e FAIL_CLOSED definido quando git ausente. F08: `git status --porcelain` pós-teste O(n) em monorepo, precisa snapshot antes/depois + allowlist de caches (`.ceh/`, `__pycache__/`, `.pytest_cache/`). Documento cita fases A,B,C,D mas só define Blocos A/B: sequência em 4 fases inverificável.
RISCOS_IDENTIFICADOS:
- F03: bypass via `GIT`, `./bin/git`, `command git`, Homebrew path; falso-negativo no push gate.
- F01: corrupção de `2>&1`/`<<EOF` gerando deny/allow incorreto e quebra dos 75 testes.
- F06/F07/F08: `test-runner.sh` quebra em sh sem bashisms; certificado falso por transporte trocado ou fallback parcial.
- F10: deleção recursiva de `customer.db/` ou symlink seguida incorretamente no macOS/BSD.
- F11: `rmtree(--out)` em symlink/mountpoint apaga fora do destino apesar do marker.
- F13: instalação concorrente ou cross-filesystem deixa perfil meio-migrado (mv não-atômico).
- F05/F08: latência e flakiness (subprocess git, status em repo grande) degradam UX do gate.
RECOMENDACAO_FINAL:
Condicionar homologação a: (1) F03 sem `lower()`, basename em `{"git","git.exe"}` + `realpath` e unwrap de `command/env/sudo -n`; (2) F01 com FSM POSIX testada contra matriz `> >> < 1> 2> &> >& >| <> << <<- <<< 2>&1`; (3) `test-runner.sh` pinado a `#!/usr/bin/env bash` + `set -euo pipefail`, detecção `command -v docker`, suporte `docker compose`/`docker-compose`, comparação estrita de comando canônico; (4) F10/F11 com `os.path.realpath`+`islink`+deny-list e write-atômico temp+rename; (5) F13 com staging no mesmo diretório destino + lockfile + rollback; (6) publicar definição ausente das fases C/D e ordem Bloco A→B→C→D antes do RED.
------------------------------------
