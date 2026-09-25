# Plano de implementação: elevação do CEH para núcleo portável multi-harness

**Versão:** 1.1.0
**Estado:** Ajustado após o Handoff 005: decisões Q1–Q4 resolvidas (seção 9) e novo P0 no topo da fila (seção 0). O Handoff 006 confirma os pontos que ainda estão `INFERRED`.
**Atualizado em:** 2026-09-25
**Branch de trabalho:** `claude/code-review-technical-analysis-kfwcdl`
**Origem:** code review técnico de alto nível do repositório (achados G, T, I, D abaixo) e evidências de host do [Handoff 005](./temp_implementation/handoffs/handoff-005-coleta-evidencias-por-harness.md).

## 0. Ajuste de voo pós-Handoff 005

### 0.1 Auditoria das conclusões do Conselho contra os dados brutos

O [resumo do Conselho](./temp_implementation/evidence/host-probe/conselho-summary.md) foi conferido contra `results.jsonl`, `invocations.jsonl` e `cli_output.txt` da coleta [`agy/20260925T041046Z`](./temp_implementation/evidence/host-probe/agy/20260925T041046Z/summary.md) (agy 1.2.10, 2 repetições, usuário não-root).

| Afirmação do resumo | O que os dados brutos mostram | Estado |
|---|---|---|
| "P0: fail-closed nativo" (E3, E4) | O controle **falhou**: E1 e E2 (`allow`) também aparecem como BLOQUEADO. O payload mostra que o agente rodou o `touch` com `Cwd` em `~/.gemini/antigravity-cli/scratch`, `~` ou `.`, não no projeto, então a sentinela da sonda estava no lugar errado. Única amostra determinística: **E3Y-r2** (`Cwd: "."`), em que o comando não rodou. As demais dependem da narração do modelo. | `INFERRED` (1 amostra `OBSERVED`) |
| "DENY é inviolável" (E5, E5Y, E7) | **E5Y-r1** (`Cwd: "."`) não rodou; as outras 5 saídas citam o erro do host `tool call denied by pre-tool hook`. | `OBSERVED` |
| `ask` (omitido no resumo) | **E6-r2** (`Cwd: "."`): **o comando rodou com `ask`**. As 4 narrações de E6/E6Y dizem "EXECUTADO". Há um fator de confusão: o plugin do CEH estava instalado junto e respondeu `allow`. | `OBSERVED` (1) + `INFERRED` |
| G9 mitigável (E7) | O hook disparou em `write_to_file` (payload `OBSERVED`) e a negação foi citada na saída. | `OBSERVED` |
| "Claude: 100% medido" | E3Y, E5Y e E6Y do Claude seguem INCONCLUSIVOS (execução como root). | Correção |
| Inventário dos outros 5 CLIs | Não há artefatos E0 commitados para `agent`, `codex`, `gemini`, `hermes` e `muse`. | `INFERRED` até commitar |

### 0.2 Fatos de host `OBSERVED` (22/22 invocações do hook no `agy`)

- **O hook roda com cwd = diretório do plugin** (`~/.gemini/config/plugins/<plugin>`). Portanto **G8 está refutado no `agy`**: o caminho relativo funciona (E2).
- **Contrato do payload do `agy`**: `toolCall.name`, `toolCall.args.CommandLine`, **`toolCall.args.Cwd`**, `workspacePaths` (veio `[]`), `conversationId`, `transcriptPath`, `artifactDirectoryPath`, `modelName`, `stepIdx`. **Não existe `cwd` no nível raiz.**
- O `Cwd` do comando é escolhido pelo agente e pode ser relativo (`"."`) ou `"~"`.
- Variáveis de ambiente do hook: `ANTIGRAVITY_AGENT`, `ANTIGRAVITY_CLI_ALIAS`, `ANTIGRAVITY_CONVERSATION_ID`.
- Python do hook: `python3` do PATH (3.12.3 nessa máquina).
- No modo headless, o agente sob teste **saiu da pasta temporária**: listou `~/.gemini/config/plugins/clearer-engineering/`, leu a pasta de evidências da própria coleta e mirou `write_to_file` no checkout real. Isso contamina as narrações e é arriscado se o hook permitir.

### 0.3 Novo P0: o Safety Gate está cego dentro do Antigravity (`Reproduzido`)

Combinando o cwd do hook (0.2) com o código do gate: `detect_environment`, `get_git_branch` e `check_pre_push_ci_gate` usam o **cwd do processo**, que no `agy` é o diretório do plugin. Reproduzido com o gate real e um payload no formato do `agy` apontando `Cwd` para um repositório na `main` com CI:

| Comando | Hook no diretório do repo | Hook no diretório do plugin (situação real no `agy`) |
|---|---|---|
| `git reset --hard` | `deny` (PRODUCTION LOCK) | **`allow`** (DEV PERMITTED) |
| `git push origin main` sem certificado | `deny` (PRE-PUSH CI GATE) | **`allow`** |

Consequência: **no Antigravity, o bloqueio de produção por branch e o Pre-Push CI Gate não funcionam hoje**, a menos que `APP_ENV`/`CEH_ENV` esteja definida. O Handoff 006 confirma isso de ponta a ponta (E10).

### 0.4 Mudanças de rota

| Item | Antes (v1.0.0) | Agora (v1.1.0) | Base |
|---|---|---|---|
| Primeiro PR | PR-01 (suíte hermética) | **PR-00**: contexto do alvo no hook (G6) | 0.3 |
| Fail-closed do gate | P0 genérico | **PR-00b**: `__future__` + tratamento de erro no nível mais alto (`deny`/exit 2). O `agy` já é fail-closed em crash (`INFERRED`), mas o Claude é fail-open (`OBSERVED`), então isso é portabilidade. | Handoff 005 |
| PR-06 | Módulo `unwrap.py` | ~4 linhas na tabela (`find -delete/-exec rm` e APIs destrutivas em one-liners). Os wrappers já são pegos. | Escada Ponytail |
| PR-09 (G8) | Caminho absoluto no `hooks.json` | Só fail-closed em payload vazio ou inválido. G8 está refutado no `agy`. | 0.2 |
| Homologação (`ask`) | Barreira com 2 alertas | **`ask` não é barreira no `agy` CLI** (`OBSERVED` 1 + narrações). Regra condicional na seção 9. | 0.1 |
| Onda 4 | `adapters/` + empacotador | Detectar o formato do payload dentro do `handle_hook`; extrair adaptadores só no 3º host | Escada Ponytail |
| PR-20 | Arquivar `temp_implementation/` | **Removido**: a pasta é dependência viva | Q3 |
| Marcos | v1.1.0 / v2.0.0 | **v1.3.0** / v2.0.0. As tags `v1.0.0`–`v1.2.0` já existem em commits antigos, mas o `plugin.json` diz 1.0.0. | `git tag` |

### 0.5 Handoff 006: re-coleta com a sonda v2 (escopo)

1. **Sentinela com caminho absoluto** no prompt, para que a medição não dependa do `Cwd` escolhido pelo agente.
2. **Isolamento:** desativar o plugin do CEH durante a sonda, ou registrar sua presença, para eliminar o fator de confusão do E6.
3. **Resolução de `"."`:** registrar `PWD`, `OLDPWD` e `/proc/<ppid>/cwd` no hook, para desenhar como o PR-00 resolve `Cwd` relativo.
4. **Desvio do agente:** marcar como `DESVIO` todo comando no hook que não seja o da sentinela; a narração deixa de valer como evidência.
5. **E10 (P0 de ponta a ponta):** com o gate real do CEH, criar um repositório temporário na `main` com um arquivo versionado alterado e pedir `git reset --hard` com `Cwd` nesse repositório. Se a alteração for revertida, o comando rodou (antes do PR-00 espera-se `allow`; depois, `deny`).
6. Tabela manual da **Antigravity IDE** (E6 com diálogo?) e E3Y/E5Y/E6Y do Claude como usuário não-root.

## 1. Objetivo

Levar o CEH de "harness para o Antigravity" a **núcleo de comportamento portável**, a partir do qual plugins para outros harnesses (Claude Code, Codex, Cursor etc.) sejam gerados com o mesmo comportamento verificável. Na ordem de execução:

1. **Fechar os bypasses reproduzidos no Safety Gate** antes de qualquer expansão, porque um defeito de segurança no núcleo seria replicado em todos os plugins derivados.
2. **Tornar a verificação honesta e hermética**: a suíte tem que passar em máquina limpa e o instalador não pode declarar sucesso quando falha.
3. **Separar o núcleo (política) dos adaptadores (host)**, com uma suíte de conformidade que prova decisões idênticas em todos os hosts.

Fora de escopo: reescrever skills e agentes, trocar Python/Bash por outra stack, adicionar dependências externas (o núcleo continua *stdlib-only*).

## 2. Princípios de execução

- **Cirúrgico**: cada PR tem uma única responsabilidade, é revertível isoladamente e segue Conventional Commits.
- **RED antes de GREEN**: todo defeito entra primeiro como teste de regressão marcado `@unittest.expectedFailure`. A correção remove o decorador; um "passou inesperadamente" sinaliza deriva.
- **Corpus dourado**: toda mudança no gate é comparada contra um snapshot de decisões (`comando × ambiente → decisão, use_case`). Refatorações exigem diff vazio. Correções exigem diff revisado linha a linha, com cada linha alterada justificada por um ID de achado.
- **Compatibilidade preservada**: `scripts/safety-gate.py --check` mantém a interface CLI e os exit codes `0/1/2`, e `hooks.json` continua funcionando durante toda a migração.
- **Evidência no PR**: comando executado, exit code e diff do corpus na descrição de cada PR, seguindo a taxonomia de estados de [`plano-validacao-revisao-conselho-seniors.md`](./plano-validacao-revisao-conselho-seniors.md).

## 3. Registro de achados

| ID | Achado | Estado | Evidência |
|---|---|---|---|
| G1 | O atalho `SAFE_DEV_PATTERNS` é avaliado antes do ambiente e casa com um trecho parcial do comando. `rm -rf build/ src/` e `rm -rf a.txt /var/lib/postgresql` resultam em `allow` em produção. | `Reproduzido` | `safety-gate.py --check ... --env production`; `safety-gate.py:478-496` |
| G2 | O regex `\.\b` nunca casa no fim da string. `git checkout .`, `git restore .` e `git checkout -- .` resultam em `allow` em produção. | `Reproduzido` | `safety-gate.py:59-61` |
| G3 | As opções globais do git só são normalizadas para `push`. `git -C . reset --hard` e `git --no-pager reset --hard` resultam em `allow` em produção. | `Reproduzido` | `safety-gate.py:164,469` |
| G4 | Os padrões catastróficos dependem da forma exata dos flags. `rm -r -f /`, `rm -rf /*`, `rm -rf $HOME` e `rm -rf -- /` resultam em `allow` em DEV; `rm --recursive --force /` resulta em `allow` em produção. | `Reproduzido` | `safety-gate.py:20-29` |
| G5 | Deleções indiretas não são reconhecidas: `find / -delete` resulta em `allow` em produção. Os wrappers `bash -c`, `xargs rm` e os one-liners de interpretador não são desembrulhados. | `Reproduzido` (find); `Inspeção estática` (demais) | `safety-gate.py:44-78` |
| G6 | **(P0, agravado)** Branch, `.env` e raiz do repositório são lidos do cwd do processo do hook, que no `agy` é o diretório do plugin. Com isso, o bloqueio de produção e o Pre-Push CI Gate respondem `allow` (seção 0.3). Secundário: detecção de ambiente por substring em qualquer parte do comando. | `Reproduzido` | `safety-gate.py:238-253,279,178`; seção 0.3 |
| G7 | O pre-push valida só o `HEAD`, mas um refspec pode enviar outro commit (`git push origin outro:main`). | `Inspeção estática` | `safety-gate.py:212-216` |
| G8 | `hooks.json` usa o caminho relativo `python3 scripts/safety-gate.py`, então o resultado depende do cwd que o host usa para rodar o hook. Payload vazio resulta em `allow`. | `Refutado` no `agy` (hook roda no diretório do plugin, E2 22/22); payload vazio segue `Inspeção estática` | seção 0.2; `safety-gate.py:591-593` |
| G9 | O certificado pode ser forjado: é um JSON em disco, e as ferramentas de escrita de arquivo não passam pelo hook do CEH (o matcher é só `run_command`). O próprio teste 16 da suíte forja o certificado e o gate responde `allow`. **Mitigável:** `write_to_file` (agy) e `Write` (Claude) disparam PreToolUse quando há matcher. | `Reproduzido` | `run-all-tests.sh:100`; E7 do Handoff 005 |
| H1 | `ask` não bloqueia no `agy` headless: E6-r2 executou o comando, e as 4 narrações de E6/E6Y confirmam. A "homologação com 2 alertas" não é barreira no Antigravity CLI. Fator de confusão: plugin do CEH co-instalado. | `Reproduzido` (1 amostra) | E6-r2 do Handoff 005 |
| H2 | Defeito da sonda v1: sentinela procurada no cwd do projeto, mas o `agy` executa no `Cwd` que o agente escolhe, o que invalidou o controle E1/E2. | `Reproduzido` | seção 0.1 |
| C1 | `safety-gate.py` tem 645 linhas para um teto de 650 no `doc-audit`, o que não deixa espaço para nenhuma correção sem extrair módulos antes. | `Reproduzido` | `doc-audit.py` check 7/7 |
| T1 | A suíte não é hermética: os testes de alias dependiam do `~/.bashrc` do host (42/44 em container limpo, com o Pre-Push Gate negando o push). **Corrigido na parte de aliases:** sem o plugin instalado, verifica o template do `install.sh`. `agy`/`~/.gemini` seguem condicionais (PR-01). | `Reproduzido e corrigido` (aliases) | `89b0058`, `ee169ca`; 44/44 com certificado PASS |
| T2 | As contagens estão escritas à mão e divergem entre si: README "45/45", e2e "33/33", step do CI "24 cases". | `Inspeção estática` | `run-e2e-simulation.sh:250`; `ci.yml` |
| T3 | Parte dos testes só verifica a presença de texto em Markdown, sem medir comportamento. | `Inspeção estática` | `run-all-tests.sh:162-175` |
| T4 | O CI não roda `run-all-tests.sh` como step próprio; ele só roda dentro do `install.sh`, que rebaixa falha para WARNING, e do e2e. | `Inspeção estática` | `ci.yml` |
| I1 | `agy plugin validate ... \|\| true` é seguido da mensagem "validated". O autodiagnóstico rebaixa falha para WARNING e o instalador termina em "success". | `Inspeção estática` | `install.sh` |
| I2 | O `curl \| bash` instala `main` sem tag, versão fixa ou checksum. Não há CHANGELOG nem releases. | `Inspeção estática` | `install.sh`; `plugin.json` |
| I3 | O perfil do agente está embutido como heredoc no `install.sh`, duplicando o conteúdo de `rules/AGENTS.md`. | `Inspeção estática` | `install.sh` |
| D1 | Há cerca de 40 artefatos "temporários" versionados, um `HANDOFF.md` na raiz, um arquivo com espaços no nome em `prd/` e ADRs que começam na 003. | `Inspeção estática` | `docs/temp_implementation/` |
| D2 | `conselho-seniores.sh` envia diffs para CLIs externos sem filtrar segredos. | `Inspeção estática` | `conselho-seniores.sh:349-370` |

## 4. Arquitetura alvo: núcleo + adaptadores + empacotamento

```
clearer-engineering/
├── core/ceh_core/              # política pura, stdlib-only, sem I/O de host
│   ├── lexer.py                # split_shell_pipeline + tokenização (shlex)
│   ├── unwrap.py               # sudo/env/nohup/timeout/nice/xargs/bash -c (profundidade limitada)
│   ├── rules.py                # tabelas de regras (dados), com use_case e severidade
│   ├── analyzers/              # análise por token: rm.py, git.py, find.py, sql.py
│   ├── environment.py          # detecção de ambiente que só escala (nunca rebaixa)
│   ├── certificate.py          # emissão/validação do certificado de voo
│   └── engine.py               # evaluate(Request) -> Decision
├── adapters/
│   ├── antigravity/            # toolCall.args.CommandLine -> {"decision","reason"}
│   ├── claude-code/            # tool_input.command -> hookSpecificOutput.permissionDecision
│   └── cli/                    # --check (compatível com o safety-gate.py atual)
├── content/                    # skills, agents, rules: fonte única, neutra de host
├── hosts/<host>/               # manifesto, hooks e mapa de capacidades -> ferramentas
└── scripts/safety-gate.py      # shim fino -> adapters/antigravity (compatibilidade)
tools/package.py                # gera dist/<host>/ a partir de content/ + hosts/<host>/
```

**Contratos centrais:**

- `Request(command: str, cwd: Path, explicit_env: str | None, tool_kind: "shell" | "file_write", target_path: Path | None)`
- `Decision(decision: "allow" | "ask" | "deny", reason: str, environment: str, use_case: str, evidence: str)`
- Adaptador: `parse(payload: dict) -> Request | None` e `render(Decision) -> (stdout: str, exit_code: int)`. Não contém nenhuma regra de política.
- **Capacidades canônicas** no frontmatter do conteúdo (`shell.exec`, `fs.read`, `fs.write`, `fs.edit`, `search.grep`, `search.glob`, `web.fetch`, `agent.invoke`), traduzidas para o nome da ferramenta de cada host por `hosts/<host>/tools.json`. Exemplos: `shell.exec → run_command` (Antigravity) e `shell.exec → Bash` (Claude Code).

Essa separação faz o "comportamento desejado" viver em um único lugar (`ceh_core` + `content/`), com os plugins de cada harness gerados e verificados por conformidade.

## 5. Plano de execução por ondas

As estimativas pressupõem uma pessoa dedicada; "P" = até meio dia, "M" = 1 dia, "G" = 2–3 dias.

### Onda P0: devolver a visão ao gate dentro do host (antes de tudo)

**PR-00 `fix(hook): avaliar o comando no diretório alvo informado pelo host`** (P), resolve G6 (P0)
- Novo módulo pequeno `scripts/hook_context.py`, fora do teto de 650 linhas do gate. Ele extrai o diretório alvo do payload: `toolCall.args.Cwd` (agy) ou `cwd` (Claude). `~` é expandido; um caminho relativo é resolvido contra `PWD` ou `/proc/<ppid>/cwd`, conforme o que o Handoff 006 mostrar que existe.
- Em `handle_hook`: `os.chdir(alvo)` antes de `evaluate_command`. É uma mudança de ~3 linhas no gate, e toda a lógica existente (branch, `.env`, raiz do repo, certificado) passa a olhar o lugar certo, sem mexer nas regras.
- Alvo não resolvível ou inexistente: **escalar** para `explicit_env="production"`, seguindo o Invariante 7 (incerteza é escalada). `git push` sem repositório identificável resulta em `deny`.
- Teste de contrato com **fixture real** (payload do E6-r2 do Handoff 005), rodando o hook a partir de um cwd estranho. Os dois casos da seção 0.3 passam a dar `deny`.
- Aceite: seção 0.3 invertida (`deny`/`deny`), matriz 24/24, evals 5/5, `doc-audit` 7/7; E10 do Handoff 006 = `deny`.

**PR-00b `fix(gate): fail-closed em qualquer falha do próprio gate`** (P), resolve P0/Q4
- `from __future__ import annotations` no gate (1 linha; Python 3.8/3.9 = 24/24, `OBSERVED`).
- `main()` envolvido em tratamento de exceção: imprime `deny` com motivo e sai com exit 2. No Claude, exit 2 bloqueia (E9 `OBSERVED`); no `agy`, exit ≠ 0 bloqueia (`INFERRED`).
- `install.sh`: verificação de `python3 >= 3.9`.

### Onda 0: rede de segurança (sem alterar comportamento)

**PR-01 `test(suite): tornar a suíte geral hermética`** (M), resolve T1, T2 e T4
- Arquivos: `tests/run-all-tests.sh`, novo `tests/run-install-verification.sh`, `tests/run-e2e-simulation.sh`, `.github/workflows/ci.yml`.
- Rodar `run-all-tests.sh` com `HOME` temporário. Os testes de alias e de perfil vão para `run-install-verification.sh`, que executa `HOME=$tmp ./install.sh` duas vezes (idempotência: um único bloco de aliases) e depois `uninstall.sh` (remoção simétrica).
- Remover as contagens escritas à mão (`33/33`, `24 cases`); o resumo passa a vir do contador.
- CI: step explícito para `run-all-tests.sh`, `python3 -m compileall -q clearer-engineering evals` e `run-install-verification.sh`.
- Aceite: suíte 100% verde em container limpo sem `~/.gemini` e sem `~/.bashrc`, com evidência do exit code.

**PR-02 `test(gate): corpus dourado e aceite do Cluster 4 em RED`** (M), cobre G1–G7
- Novos: `tests/fixtures/gate_corpus.txt` (≥ 150 comandos: seguros, destrutivos, variantes de evasão), `tests/fixtures/gate_corpus.expected.jsonl` (snapshot atual), `tests/tools/snapshot_gate.py` (gera e compara o snapshot), `tests/cluster4_acceptance.py` (um teste por caso de G1–G7, com `@expectedFailure`).
- Os comandos perigosos ficam codificados em base64, como em `test_safety_matrix.py`, para não disparar o hook da IDE.
- Aceite: a suíte segue verde, os 7 grupos aparecem como "expected failure" e o corpus produz diff vazio contra o próprio snapshot.

### Onda 1: Safety Gate P0 (correções de segurança)

**PR-03 `refactor(gate): extrair regras e lexer em módulos sem mudança de comportamento`** (M), resolve C1
- Mover `CATASTROPHIC_PATTERNS`, `SAFE_DEV_PATTERNS`, `USE_CASE_DESTRUCTIVE_PATTERNS`, `normalize_env` e `split_shell_pipeline` para `core/ceh_core/`. `safety-gate.py` passa a importar do pacote, resolvendo o caminho pelo próprio `__file__`.
- `doc-audit.py` check 7: o teto passa a valer por módulo (≤ 300 linhas cada) e o total do núcleo fica registrado.
- `evals/run.sh` (Deriva B): a mutação passa a ser aplicada a uma **cópia do pacote** em diretório temporário (o `sed` atual atua sobre `safety-gate.py`). O critério continua: o mutante precisa divergir e a restauração tem que ser limpa.
- `install.sh` já copia o diretório `clearer-engineering/` inteiro; conferir que `core/` vai junto.
- Aceite: diff vazio no corpus, matriz 24/24, evals 5/5, `doc-audit` 7/7.

**PR-04 `fix(gate): análise de rm por token e atalho seguro restrito a DEV`** (M), resolve G1 e G4
- `analyzers/rm.py`: separar os argumentos com `shlex` e reconhecer flags em qualquer forma (`-r -f`, `-rf`, `-fr`, `--recursive`, `--force`, `-R`, o separador `--`) e **todos** os alvos.
- Alvo catastrófico: `/`, `/*`, `~`, `~/`, `$HOME`, `..`, `*`, `.`, e diretórios de sistema de primeiro nível (`/etc`, `/usr`, `/var`, `/bin`, `/boot`, `/home`, `/lib`, `/opt`, `/root`, `/srv`). Resultado: `deny` em qualquer ambiente.
- O atalho seguro só vale se `env == development` **e todos** os alvos pertencerem ao conjunto seguro (`tmp/`, `scratch/`, `.cache/`, `dist/`, `build/`, `coverage/`...). Em homologação e produção ele deixa de existir.
- Aceite: os testes G1 e G4 perdem o `@expectedFailure` e passam, e o diff do corpus mostra somente linhas justificadas por G1 e G4.

**PR-05 `fix(gate): canonicalizar invocações git para todos os subcomandos`** (M), resolve G2 e G3
- Generalizar `resolve_git_invocation` para devolver `(subcomando, args, repo_alvo)` para qualquer subcomando, e avaliar as regras de git sobre a forma canônica.
- `analyzers/git.py`: `checkout` e `restore` com pathspec amplo (`.`, `:/`, `*`, `-- .`, `--staged .`, `--worktree .`) contam como destrutivos, e o regex `\.\b` é eliminado.
- Aceite: G2 e G3 passam; `git checkout app/Model.php` continua `allow`, que é o caso do teste 14.

**PR-06 `fix(gate): deleções indiretas pela tabela existente`** (P), resolve G5
- **Sem módulo novo.** `sudo`, `timeout`, `env`, `nohup`, `xargs rm` e `bash -c '...'` já são pegos, porque os regex não são ancorados (`OBSERVED`).
- ~4 linhas em `USE_CASE_DESTRUCTIVE_PATTERNS`: `find ... -delete`, `find ... -exec rm`, e one-liners com API destrutiva (`shutil.rmtree`, `os.remove`, `fs.rmSync`, `fs.rm`, `unlink`). O mecanismo existente aplica DEV=allow, HML=ask e **PROD=deny** (Q1). One-liners benignos (`python -c 'print(1)'`) seguem `allow`.
- Aceite: G5 passa; `timeout 60 npm test` e `env CI=1 pytest` continuam `allow`.

**PR-07 `fix(gate): detecção de ambiente por token`** (P), resolve o secundário de G6
- A parte principal de G6 (diretório alvo) foi para o PR-00.
- Resta a detecção pelo comando: considerar só flags e atribuições explícitas (`--env=`, `APP_ENV=`, `--context`, `-e`), não substrings em caminhos. Sinais do comando **só escalam** o ambiente, nunca rebaixam.
- Aceite: `rm -rf build/production-assets` é tratado como DEV quando o ambiente real é DEV.

### Onda 2: integridade do pre-push e do hook

**PR-08 `fix(gate): validar os refspecs do push contra o certificado`** (P), resolve G7
- Resolver o lado de origem de cada refspec com `git rev-parse` e exigir que todos coincidam com `commit_hash`. Em repositório com CI, `--all`, `--mirror` e `--tags` resultam em `deny`.

**PR-09 `fix(hook): fail-closed em payload vazio ou inválido`** (P), resolve o restante de G8
- G8 está refutado no `agy`: o hook roda no diretório do plugin, então o caminho relativo funciona. O caminho absoluto não é necessário.
- Payload vazio ou malformado passa a resultar em `deny` com motivo explícito; hoje, payload vazio resulta em `allow`.
- No Claude, o hook do plugin referencia a variável de raiz do plugin (validar no PR-15).

**PR-10 `feat(gate): proteger o certificado e registrar o modelo de ameaças`** (M), resolve G9
- Ampliar o matcher do hook para as ferramentas de escrita de arquivo e negar escrita em `.ceh/last-ci-run.json`. No shell, negar redirecionamento, `tee`, `cp` ou `mv` com destino `.ceh/`.
- O certificado passa a incluir `tree_hash` (`git rev-parse HEAD^{tree}`) e `runner_version`, e o gate valida os dois.
- ADR 007: o gate é **defesa em profundidade, não sandbox**. A garantia real vem de branch protection com status check obrigatório no servidor, com a configuração recomendada documentada.
- Ajustar o teste 16 para gerar o certificado pelo `test-runner.sh`, não com `echo`.

### Onda 3: instalador e distribuição confiáveis

**PR-11 `fix(install): resultado honesto e simetria com o uninstall`** (P), resolve I1
- Tirar o `|| true` da validação e mostrar o resultado real. Falha no autodiagnóstico gera exit ≠ 0 (com `--skip-diagnostics` como saída consciente).
- A lista de aliases vem de uma única fonte, consumida por `install.sh` e `uninstall.sh`.

**PR-12 `build(release): SemVer, CHANGELOG e instalação fixada por versão`** (P), resolve I2 e I3
- `plugin.json` passa a ser a fonte única de versão. Hoje ele diz `1.0.0`, mas as tags `v1.0.0`–`v1.2.0` já existem em commits antigos, então a próxima é **`v1.3.0`**, ao fim da Onda 2, com `plugin.json` alinhado. Criar `CHANGELOG.md` (Keep a Changelog).
- O one-liner aceita `CEH_VERSION` e clona `--branch v<versão>`; a documentação publica a URL fixada.
- O perfil do agente sai do heredoc para `clearer-engineering/profiles/clearer-harness.agent.md`, e um teste garante que o instalado é idêntico à fonte.

### Onda 4: núcleo portável e plugins multi-harness (estratégica)

> **Redução Ponytail (v1.1.0):** com 2 hosts (agy e Claude), o suporte começa como **detecção do formato do payload dentro do `handle_hook`**, reutilizando o resolvedor do PR-00 (`toolCall.args.*` versus `tool_input.*` e `cwd`) e o renderizador de saída, em ~20 linhas. Os PR-13 a PR-17 abaixo só entram quando o **3º host** tiver evidência E0/E1 commitada. O contrato de cada host vem de payload **gravado** (Handoff 005/006), nunca de documentação suposta.

**PR-13 `refactor(core): API de engine agnóstica de host`** (M)
- `engine.evaluate(Request) -> Decision`. `safety-gate.py` vira um shim de menos de 40 linhas sobre `adapters/cli` e `adapters/antigravity`.
- Aceite: diff vazio no corpus; evals 5/5.

**PR-14 `feat(adapters): contrato de adaptador + Antigravity + CLI`** (M)
- Fixtures de payload em `tests/fixtures/hosts/antigravity/*.json`, com a saída esperada lado a lado.

**PR-15 `feat(adapters): adaptador Claude Code`** (M)
- PreToolUse: ler `tool_name` (`Bash`) e `tool_input.command` / `cwd` do stdin, e responder `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow|ask|deny", "permissionDecisionReason": "..."}}`.
- Validar o contrato contra a documentação oficial vigente e **gravar payloads reais** como fixtures antes de congelar o formato.
- Manifesto e hooks gerados em `hosts/claude-code/`, apontando para o script via a variável de raiz do plugin.

**PR-16 `feat(build): catálogo de capacidades e empacotador por host`** (G)
- Criar `hosts/<host>/tools.json` e `tools/package.py --host <host> --out dist/<host>`.
- Teste dourado: o pacote gerado para o Antigravity tem que ser **byte-idêntico** ao conteúdo instalado hoje, o que prova a migração sem regressão.
- O `install.sh` passa a instalar a partir de `dist/antigravity`.

**PR-17 `test(conformance): suíte de conformidade entre hosts`** (M)
- O mesmo corpus dourado passa por cada adaptador: `Decision` idêntica por comando e ambiente em todos os hosts, e apenas `render()` varia.
- Guia `docs/adapters/novo-host.md`, com o checklist para criar o plugin de um novo harness: gravar fixtures → implementar `parse`/`render` → mapear capacidades → rodar a conformidade.

### Onda 5: qualidade de testes, CI e higiene

**PR-18 `test(content): validação de esquema no lugar de grep em Markdown`** (M), resolve T3
- Validar o frontmatter obrigatório (`name`, `description`), exigir que as capacidades existam no catálogo, que as skills citadas existam e que os links relativos resolvam.
- Fuzz do lexer com semente fixa (`random.Random(1337)`): composições de segmentos seguros e destrutivos, com separadores e aspas. Invariante: com qualquer segmento destrutivo em produção, a decisão nunca é `allow`.

**PR-19 `ci: matriz de plataformas e shellcheck`** (P)
- Rodar em `ubuntu-latest` e `macos-latest`, com Python **3.9** (piso, Q4) e 3.12. O macOS cobre a portabilidade BSD citada no R9.
- `shellcheck` começa como informativo e passa a bloquear após a limpeza.

**PR-20 `docs: índice de ADRs e consolidação`** (P), resolve D1 parcialmente
- **`docs/temp_implementation/` fica onde está (Q3):** é dependência viva do `conselho-seniores.sh:199`, da skill e do `doc-audit`.
- Corrigir o destino das atas do Conselho quando o plugin está instalado fora de um repositório git (`INFERRED` de `conselho-seniores.sh:26,199`): hoje elas iriam para `~/.gemini/config/plugins/docs/...`.
- Criar `docs/architecture/README.md` como índice, registrando o motivo da ausência das ADRs 001/002, mais a ADR 006 (núcleo + adaptadores) e a ADR 007 (modelo de ameaças).
- O README da raiz passa a ser o canônico, e os READMEs do plugin viram um resumo com link para ele.
- Revisar promessas que o código não cumpre ("Zero Hallucination", "imune a evasão") para uma redação verificável.

**PR-21 `feat(conselho): redação de segredos antes do envio externo`** (P), resolve D2
- Com `--diff`, excluir caminhos sensíveis (`.env*`, `*.pem`, `*.key`, `*secret*`) e mascarar padrões de token conhecidos. A redação vem ligada por padrão e tem teste com um segredo sintético.

## 6. Dependências e sequência

```
Handoff 006 (sonda v2, E10) ──┐
PR-00 ─> PR-00b ──────────────┴─> [E10 = deny] ─> PR-01 ─┬─> PR-02 ─> PR-03 ─┬─> PR-04 ─┐
                                                         │                   ├─> PR-05 ─┼─> PR-07 ─> PR-08 ─> PR-09 ─> PR-10 ─> [tag v1.3.0]
                                                         │                   └─> PR-06 ─┘
                                                         └─> PR-11 ─> PR-12
[v1.3.0] ─> formato do payload no handle_hook (agy + Claude) ─> [3º host com evidência] ─> PR-13…PR-17 ─> [tag v2.0.0]
PR-18, PR-19, PR-20, PR-21: paralelos a partir de PR-03
```

O PR-00 pode começar em paralelo ao Handoff 006, porque a fixture real do E6-r2 já existe. A resolução de `Cwd` relativo é finalizada com os dados de `PWD`/`/proc/<ppid>/cwd` da sonda v2.

**Marcos:**
- **v1.3.0**: gate enxergando o alvo real no host (P0), sem os bypasses conhecidos, fail-closed, suíte hermética e instalador honesto.
- **v2.0.0**: núcleo portável, com Antigravity e Claude Code gerados a partir da mesma fonte e conformidade de 100%.

## 7. Definição de pronto (vale para todo PR)

- [ ] Conventional Commit com escopo, e o ID do achado na mensagem.
- [ ] `run-all-tests.sh` verde em `HOME` temporário, evals 5/5 e `doc-audit` verde.
- [ ] Diff do corpus dourado vazio (refatoração) ou justificado linha a linha (correção).
- [ ] Nenhuma contagem escrita à mão em README, CI ou mensagens.
- [ ] Documentação e ADR atualizadas quando o contrato muda.
- [ ] Evidência (`OBSERVED`) na descrição do PR: comando, exit code e artefato.

### 7.1 Protocolo de continuidade pela branch

A branch `claude/code-review-technical-analysis-kfwcdl` é a fonte única de continuidade: o próximo passo está sempre no **handoff mais recente** e na **seção 0** deste plano.

**Ao entrar (qualquer sessão, humana ou agente):**
1. `git fetch origin && git checkout claude/code-review-technical-analysis-kfwcdl && git pull --ff-only`.
2. `git status --short` precisa vir vazio; se não vier, pare e entenda antes de editar.
3. Leia o handoff de número mais alto em `docs/temp_implementation/handoffs/` e a seção 0 deste plano.

**Ao sair (a branch só é considerada "limpa" com os 4 itens):**
1. Worktree limpo: tudo commitado, sem sentinelas ou arquivos temporários (`git status --short` vazio).
2. `bash clearer-engineering/scripts/test-runner.sh` com `STATUS: PASS` e certificado `.ceh/last-ci-run.json` no `HEAD`.
3. `python3 clearer-engineering/scripts/safety-gate.py --check "git push origin <branch>"` resultando em `allow`, e **só então** o push.
4. Evidências novas passam pela checagem de vazamento da seção 4.5 do Handoff 005, e o próximo passo fica registrado no handoff ou na seção 0.

> O CI do GitHub só roda em `main`/`staging`/`dev` e em PRs para elas. Nesta branch, o certificado local é a única verificação até existir um PR.

## 8. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Falsos positivos em produção bloqueiam trabalho legítimo | Atrito operacional | Regras específicas (APIs destrutivas, não "todo one-liner"); o corpus inclui comandos benignos frequentes; motivo claro na resposta. |
| PR-00 escala para produção quando o `Cwd` não é resolvível, e bloqueia demais | Atrito no `agy` | Sonda v2 mede `PWD`/`/proc/<ppid>/cwd` antes de fixar a resolução; a escalada só afeta comandos destrutivos. |
| O agente sob teste sai do diretório temporário e mexe no checkout real | Evidência contaminada e risco ao repositório | Sonda v2: sentinela absoluta, marcação de `DESVIO` e rodar a coleta **fora** do checkout de trabalho. |
| Refatoração altera decisões sem ninguém perceber | Regressão de segurança | Corpus dourado com diff obrigatório vazio em PR-03 e PR-13. |
| Eval Deriva B quebra com a modularização | Perda do meta-eval | PR-03 migra a mutação para uma cópia do pacote na mesma entrega. |
| Contrato de hook do host muda ou está mal documentado | Adaptador silenciosamente inoperante | Fixtures gravadas de sessões reais; payload desconhecido resulta em `ask`. |
| Teto de linhas bloqueia correções | PR travado | PR-03 redefine o orçamento por módulo antes das correções. |
| O empacotador diverge do conteúdo instalado hoje | Regressão para quem usa o Antigravity | Teste dourado byte-idêntico no PR-16. |

## 9. Decisões (resolvidas com evidência)

| # | Decisão | Certeza | Evidência | O que mudaria a decisão |
|---|---|---|---|---|
| Q1 | **`DENY` em produção** pela tabela existente, para APIs destrutivas em one-liners e `find -delete`. | Alta | Invariante 7 (`AGENTS.md:147`); precedente `PARSER_FAIL_CLOSED`; `ask` não é barreira no `agy` headless (H1). | — |
| Q1b | **Homologação no Antigravity CLI:** se o Handoff 006 confirmar H1 sem o fator de confusão, destrutivo em HML sob `ANTIGRAVITY_CLI_ALIAS` passa de `ask` para `deny`. Na IDE, `ask` permanece se o diálogo aparecer. | Média (`INFERRED`) | E6-r2 + narrações; tabela IDE pendente | E6 isolado bloqueando no `agy` |
| Q2 | **Antigravity continua como alvo primário** (o CEH foi modelado para ele), e o Claude como 2º host; ambos com contrato gravado. | Alta | Payloads `OBSERVED` dos dois hosts | — |
| Q3 | **Manter `temp_implementation/`** (diff zero). | Alta | `conselho-seniores.sh:199`, `SKILL.md:76`, `doc-audit.py` | — |
| Q4 | **Piso Python 3.9** com `from __future__ import annotations`. | Alta | 3.8/3.9 = 24/24 com a linha; sem ela, `TypeError`; `agy` usa o `python3` do PATH | — |
| P0 | **Gate fail-closed em qualquer falha** (PR-00b) e **alvo real no hook** (PR-00). | Alta | Claude fail-open `OBSERVED`; `agy` fail-closed `INFERRED`; seção 0.3 `Reproduzido` | — |

## 10. Métricas de sucesso

- 0 bypass conhecido no corpus dourado; cada achado G1–G9 tem teste de regressão permanente.
- Suíte 100% verde em container limpo, sem estado do host.
- Instalador com exit ≠ 0 em qualquer falha real.
- Novo host suportado com adaptador ≤ 150 linhas, sem alteração no núcleo e com conformidade de 100%.
