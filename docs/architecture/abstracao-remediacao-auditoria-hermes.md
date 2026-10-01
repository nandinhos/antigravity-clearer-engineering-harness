# Abstração Completa e Modelagem Arquitetural de Remediação (Auditoria Hermes b9a72b6)
## Pós-Deliberação do Conselho de Seniores (Claude, Muse, AGY, Codex)

**Data:** 2026-10-01  
**Snapshot de Auditoria:** `b9a72b6b6dbd898dd737609bada8036866e56646`  
**Branch de Trabalho:** `dev-onda5-remediacao-hermes` (derivada de `dev` atualizada com `main`)  
**Status:** **HOMOLOGADO COM RESSALVAS** pelo Conselho de Seniores — Refinado para Validação Soberana do Desenvolvedor  

---

## 1. Princípios Invariantes Refinados pelo Conselho de Seniores

A deliberação plenária refinou os 6 invariantes com foco estrito em **Ponytail Mode (Senior Minimalista)**, eliminando sobre-engenharia e blindando contra regressões:

1. **Invariante 1 — Detecção Cirúrgica de Redirecionamento sem Risco Global (F01)**:
   *Refinamento Claude/Muse:* Não alterar o lexer global de toda a aplicação (evitando blast radius desnecessário e quebra de operadores POSIX como `2>&1`, `&>`, etc.). A proteção é aplicada cirurgicamente em `is_cert_tampering` (`ceh_core/rules.py`): se uma linha de comando mencionar `.ceh/` ou arquivos de certificado, qualquer caractere `>` fora de aspas e não escapado é classificado sumariamente como tentativa de adulteração de integridade (G9), fechando tanto o caso adjacente (`f>.ceh/...`) quanto wrappers com cauda de redirecionamento (`bash -c '...' > .ceh/...`).

2. **Invariante 2 — Piso Monotônico de Severidade de Ambiente (F02)**:
   *Refinamento Claude/AGY:* O desembrulho de wrappers (`bash -c`, `sh -c`) não pode desligar a detecção dinâmica de repositório no `depth + 1`. O ambiente resolvido no comando exterior atua como um **piso mínimo** (`env_floor`), de modo que o comando interno calcule seu próprio ambiente e o resultado efetivo seja:
   $$\text{env}_{\text{efetivo}} = \max_{\text{ENV\_SEVERITY}}(\text{env}_{\text{piso}}, \text{env}_{\text{interno}})$$
   Isso garante que `APP_ENV=production bash -c '...'` nunca seja rebaixado para desenvolvimento, e ao mesmo tempo um `bash -c 'git -C /repo-prod push'` detecte o repositório produtivo e suba para produção.

3. **Invariante 3 — Canonicalização de Binário Git por Basename Exato (F03)**:
   *Refinamento Claude/Muse:* A normalização do executável Git usa `os.path.basename(token)` sem conversão para minúsculas arbitrárias (preservando o case-sensitivity POSIX no Linux), verificando se o basename é estritamente `git` ou `git.exe` e suportando caminhos absolutos (`/usr/bin/git`, `/usr/local/bin/git`, `/mingw64/bin/git`) e relativos (`./bin/git`).

4. **Invariante 4 — Consumo de Flags Estruturadas & Regra Sintática para `rm` (F04, F10)**:
   *Refinamento Claude/AGY/Muse:*
   - Para `git reset`: se `--hard` estiver presente em qualquer posição de argumento do subcomando, classificar como destrutivo (`GIT_HISTORY`), eliminando a fragilidade de regex sensível à ordem dos argumentos (`git reset HEAD --hard`).
   - Para `git push`: consultar a chave `"force"` já estruturada por `parse_push_args` (cobrindo `-f`, `--force` e agrupamentos como `-vf`).
   - Para `rm -rf` (F10): **Regra puramente sintática sem `os.path.isdir`**. A presença das flags recursivas `-r` ou `-R` desabilita incondicionalmente o atalho de arquivo único seguro. Se há recursão, a classificação de blast radius é destrutiva, eliminando riscos de TOCTOU e dependência de filesystem.

5. **Invariante 5 — Fail-Closed em Push Indireto e Certificação Pós-Execução (F05, F06, F07, F08)**:
   *Refinamento Claude/AGY/Muse:*
   - Para `git push` sem refspec (F05): Fail-Closed direto. Se houver `remote.<name>.push` configurado ou se `push.default` não for explicitamente `simple` ou `current`, bloquear e exigir refspec explícito.
   - Para substituição de suíte e pytest ausente (F06, F07): Sem transportes complexos de Docker; se o comando executado diferir da suíte canônica, marcar estritamente `CANONICAL_VERIFIED=false`.
   - Para integridade pós-execução (F08): Capturar `HEAD_BEFORE` antes do runner e exigir que `HEAD_AFTER == HEAD_BEFORE` e worktree limpa antes de emitir o certificado.

6. **Invariante 6 — Transacionalidade Estrita e Destinos Gerenciados (F09 a F16)**:
   - Limpeza de aliases (`rc_aliases.py` / F12): ancorada a linhas completas de comentário.
   - Empacotador (`package.py` / F11): checagem de diretório vazio ou marker nas duas ocorrências de `rmtree` (linhas 262 e 279).
   - Matchers do Claude (`package.py` / F09): cobertura das 5 ferramentas (`Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`).
   - Sincronização de versão (F14): fonte única extraída de `plugin.json`.
   - API de ambiente (F15): `from ceh_core.environment import detect_environment`.

---

## 2. Matriz Refinada de Testes de Falsificabilidade (TDD Estrito)

Cada achado possui um teste unitário/isolado com falha comprovada (`RED`) e teste negativo de controle:

| ID | Teste RED (Vetor Positivo) | Teste Negativo (Controle / Falso Positivo) | Comportamento Pós-Fix (GREEN) |
|---|---|---|---|
| **F01a** | `cat f>.ceh/last-ci-run.json` | `cat .ceh/last-ci-run.json` (leitura pura) | `deny` no positivo / `allow` no negativo |
| **F01b** | `bash -c 'echo' > .ceh/last-ci-run.json` | `echo "a>b"` (redirecionamento em string) | `deny` no positivo / `allow` no negativo |
| **F02** | `env APP_ENV=production bash -c 'php artisan migrate:fresh'` | `bash -c 'ls -la'` em dev | `deny` em prod / `allow` em dev |
| **F03** | `/usr/bin/git push origin dev` | `/usr/bin/git status` (leitura permitida) | `deny PRE_PUSH_CI` no push sem cert |
| **F04** | `git reset HEAD --hard` e `git push -vf origin dev` | `git reset HEAD file.txt` (unstage seguro) | `deny` / `ask` conforme ambiente |
| **F05** | `git push origin` com `remote.origin.push=unchecked:dev` | `git push origin HEAD:dev` com certificado | `deny FAIL_CLOSED` / `allow` certificado |
| **F06** | Troca de `bash canonical.sh` por `./vendor/bin/sail test` | Execução direta da suíte canônica exata | `canonical_verified=false` na troca |
| **F07** | Projeto com `pytest.ini` sem `pytest` no PATH | Execução de unittest quando canônico é unittest | aborto com exit > 0 em pytest ausente |
| **F08** | Suíte que faz `git commit` ou altera worktree | Suíte que mantém worktree e HEAD idênticos | recusa emissão de certificado |
| **F09** | Manifesto Claude sem `MultiEdit`/`NotebookEdit` | Validação de matchers gerados | manifest cobre todas as 5 tools |
| **F10** | `rm -rf customer.db` (com flag `-r`) | `rm -f customer.log` (arquivo sem `-r`) | `deny` no recursivo / `allow` no pontual |
| **F11** | `package.py --out <dir_com_arquivos_usuario>` | `package.py --out <dir_vazio_ou_com_marker>` | recusa apagar sem marker |
| **F12** | Arquivo rc com `# BEGIN` como substring em string | Arquivo com bloco `# BEGIN CEH ALIASES` real | preserva arquivo com substring intacto |
| **F13** | Instalação com falha intermediária simulada | Instalação bem sucedida | restaura versão anterior intacta |
| **F14** | `package.py --host muse` verificando versão gerada | Comparação contra `plugin.json:3` | versão idêntica à canônica |
| **F15** | `evidence_report.py` em repo com commit | Detecção de ambiente em branch main | retorna `PRODUCTION` sem erro |
| **F16** | Execução de testes do pacote Antigravity isolado | Bundle sem repo pai | testes do bundle passam autonomamente |
