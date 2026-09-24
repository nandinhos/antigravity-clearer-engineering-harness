# Plano de implementação: elevação do CEH para núcleo portável multi-harness

**Versão:** 1.0.0
**Estado:** Proposto — aguardando aprovação das decisões pendentes (seção 9).
**Atualizado em:** 2026-09-24
**Branch de trabalho:** `claude/code-review-technical-analysis-kfwcdl`
**Origem:** code review técnico de alto nível do repositório (achados G, T, I, D abaixo).

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
| G6 | O ambiente é detectado por substring em qualquer parte do comando (qualquer menção a "production"), e o branch é lido do cwd do processo em vez do alvo `-C` ou do cwd do payload. | `Inspeção estática` | `safety-gate.py:238-243,279` |
| G7 | O pre-push valida só o `HEAD`, mas um refspec pode enviar outro commit (`git push origin outro:main`). | `Inspeção estática` | `safety-gate.py:212-216` |
| G8 | `hooks.json` usa o caminho relativo `python3 scripts/safety-gate.py`, então o resultado depende do cwd que o host usa para rodar o hook. Payload vazio resulta em `allow`. | `Inspeção estática` | `hooks.json`; `safety-gate.py:591-593` |
| G9 | O certificado pode ser forjado: é um JSON em disco, e as ferramentas de escrita de arquivo não passam pelo hook. O próprio teste 16 da suíte forja o certificado e o gate responde `allow`. | `Reproduzido` | `run-all-tests.sh:100` |
| C1 | `safety-gate.py` tem 645 linhas para um teto de 650 no `doc-audit`, o que não deixa espaço para nenhuma correção sem extrair módulos antes. | `Reproduzido` | `doc-audit.py` check 7/7 |
| T1 | A suíte não é hermética: depende dos aliases no `~/.bashrc`, de `agy` e de `~/.gemini`. Em container limpo o resultado foi 42/44. | `Reproduzido` | `run-all-tests.sh:178-182` |
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

**PR-06 `feat(gate): desembrulhar wrappers e deleções indiretas`** (M), resolve G5
- `unwrap.py`: tirar o prefixo `sudo`, `env VAR=...`, `nohup`, `timeout N`, `nice`, `time` e `command`, e reavaliar o comando interno. Para `bash -c` e `sh -c`, reavaliar a string interna recursivamente com profundidade ≤ 3. Profundidade maior ou string que não pode ser analisada resulta em `deny` (fail-closed).
- Novas regras: `find ... -delete`, `find ... -exec rm`, `xargs rm`, `shred`, `truncate -s 0`, `chmod -R`/`chown -R` sobre alvo catastrófico.
- One-liners de interpretador (`python -c`, `node -e`, `perl -e`, `ruby -e`): `ask` em homologação e produção. A regra fica explicitamente fora do escopo em DEV e documentada.
- Aceite: G5 passa e os casos benignos do corpus (`timeout 60 npm test`, `env CI=1 pytest`) continuam `allow`.

**PR-07 `fix(gate): detecção de ambiente por token e pelo alvo real`** (P), resolve G6
- A detecção pelo comando passa a considerar só flags e atribuições explícitas (`--env=`, `APP_ENV=`, `--context`, `-e`), não substrings em caminhos. Regra invariante: sinais do comando **só escalam** o ambiente, nunca rebaixam.
- O branch e o `.env` são lidos do diretório alvo (`-C` ou o `cwd` do payload), não do cwd do processo.
- Aceite: G6 passa, e `rm -rf build/production-assets` volta a ser tratado como DEV quando o ambiente real é DEV.

### Onda 2: integridade do pre-push e do hook

**PR-08 `fix(gate): validar os refspecs do push contra o certificado`** (P), resolve G7
- Resolver o lado de origem de cada refspec com `git rev-parse` e exigir que todos coincidam com `commit_hash`. Em repositório com CI, `--all`, `--mirror` e `--tags` resultam em `deny`.

**PR-09 `fix(hook): caminho absoluto e fail-closed no contrato do host`** (P), resolve G8
- O instalador grava em `hooks.json` o caminho absoluto do plugin instalado (template com um placeholder, ex. `{{PLUGIN_ROOT}}`), ou usa a variável de raiz do plugin se o host oferecer uma.
- Payload vazio ou malformado resulta em `ask`, com motivo explícito.
- Novo teste de contrato: rodar o hook com um cwd **estranho** ao plugin e com payload gravado de uma sessão real.

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
- `plugin.json` passa a ser a fonte única de versão. Criar `CHANGELOG.md` (Keep a Changelog) e a tag `v1.1.0` ao fim da Onda 2.
- O one-liner aceita `CEH_VERSION` e clona `--branch v<versão>`; a documentação publica a URL fixada.
- O perfil do agente sai do heredoc para `clearer-engineering/profiles/clearer-harness.agent.md`, e um teste garante que o instalado é idêntico à fonte.

### Onda 4: núcleo portável e plugins multi-harness (estratégica)

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
- Rodar em `ubuntu-latest` e `macos-latest`, com Python 3.10 e 3.12. O macOS cobre a portabilidade BSD citada no R9.
- `shellcheck` começa como informativo e passa a bloquear após a limpeza.

**PR-20 `docs: arquivar trilha de revisão, índice de ADRs e consolidação`** (M), resolve D1
- `docs/temp_implementation/` e `HANDOFF.md` vão para `docs/history/2026-09-revisao-r1-r10/`, atualizando os caminhos no `doc-audit.py`. O arquivo em `prd/` é renomeado sem espaços.
- Criar `docs/architecture/README.md` como índice, registrando o motivo da ausência das ADRs 001/002, mais a ADR 006 (núcleo + adaptadores) e a ADR 007 (modelo de ameaças).
- O README da raiz passa a ser o canônico, e os READMEs do plugin viram um resumo com link para ele.
- Revisar promessas que o código não cumpre ("Zero Hallucination", "imune a evasão") para uma redação verificável.

**PR-21 `feat(conselho): redação de segredos antes do envio externo`** (P), resolve D2
- Com `--diff`, excluir caminhos sensíveis (`.env*`, `*.pem`, `*.key`, `*secret*`) e mascarar padrões de token conhecidos. A redação vem ligada por padrão e tem teste com um segredo sintético.

## 6. Dependências e sequência

```
PR-01 ─┬─> PR-02 ─> PR-03 ─┬─> PR-04 ─┐
       │                   ├─> PR-05 ─┼─> PR-07 ─> PR-08 ─> PR-09 ─> PR-10 ─> [tag v1.1.0]
       │                   └─> PR-06 ─┘
       └─> PR-11 ─> PR-12
[v1.1.0] ─> PR-13 ─> PR-14 ─> PR-15 ─> PR-16 ─> PR-17 ─> [tag v2.0.0]
PR-18, PR-19, PR-20, PR-21: paralelos a partir de PR-03
```

**Marcos:**
- **v1.1.0**: gate sem os bypasses conhecidos, suíte hermética e instalador honesto.
- **v2.0.0**: núcleo portável, com Antigravity e Claude Code gerados a partir da mesma fonte e conformidade de 100%.

## 7. Definição de pronto (vale para todo PR)

- [ ] Conventional Commit com escopo, e o ID do achado na mensagem.
- [ ] `run-all-tests.sh` verde em `HOME` temporário, evals 5/5 e `doc-audit` verde.
- [ ] Diff do corpus dourado vazio (refatoração) ou justificado linha a linha (correção).
- [ ] Nenhuma contagem escrita à mão em README, CI ou mensagens.
- [ ] Documentação e ADR atualizadas quando o contrato muda.
- [ ] Evidência (`OBSERVED`) na descrição do PR: comando, exit code e artefato.

## 8. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Falsos positivos em produção bloqueiam trabalho legítimo | Atrito operacional | Casos incertos viram `ask`, não `deny`; o corpus inclui comandos benignos frequentes; motivo claro na resposta. |
| Refatoração altera decisões sem ninguém perceber | Regressão de segurança | Corpus dourado com diff obrigatório vazio em PR-03 e PR-13. |
| Eval Deriva B quebra com a modularização | Perda do meta-eval | PR-03 migra a mutação para uma cópia do pacote na mesma entrega. |
| Contrato de hook do host muda ou está mal documentado | Adaptador silenciosamente inoperante | Fixtures gravadas de sessões reais; payload desconhecido resulta em `ask`. |
| Teto de linhas bloqueia correções | PR travado | PR-03 redefine o orçamento por módulo antes das correções. |
| O empacotador diverge do conteúdo instalado hoje | Regressão para quem usa o Antigravity | Teste dourado byte-idêntico no PR-16. |

## 9. Decisões pendentes (necessárias antes da Onda 1)

1. **Postura para comandos incertos em produção** (one-liners de interpretador, wrappers muito profundos): `ask` (recomendado) ou `deny`?
2. **Ordem dos hosts na Onda 4**: Claude Code primeiro (recomendado, tem contrato de hook documentado), depois Codex e Cursor?
3. **Trilha `temp_implementation/`**: arquivar em `docs/history/` (recomendado) ou remover?
4. **Versão mínima de Python**: 3.10, que o código já exige pelo uso de `str | None`, a ser declarada formalmente?

## 10. Métricas de sucesso

- 0 bypass conhecido no corpus dourado; cada achado G1–G9 tem teste de regressão permanente.
- Suíte 100% verde em container limpo, sem estado do host.
- Instalador com exit ≠ 0 em qualquer falha real.
- Novo host suportado com adaptador ≤ 150 linhas, sem alteração no núcleo e com conformidade de 100%.
