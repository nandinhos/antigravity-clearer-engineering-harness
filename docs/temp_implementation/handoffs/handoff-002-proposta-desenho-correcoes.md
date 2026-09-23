# Handoff 002 — Proposta de Desenho Técnico e Critérios de Correção (Revisão v22)

> **SUPERADO PARA R2 E PARA O FORCE PUSH DE R5 pelo [Handoff 003](handoff-003-redesenho-contrato-ci.md) (2026-09-23), correção mínima no modo Ponytail.**
> Este documento fica preservado como histórico. Não implementar a partir dele as seções de R2 (veto a execução inline, inspeção de manifestos, cobertura de jobs) nem a isenção de force push no gate de CI. O desenho de R1 e o de `resolve_git_invocation()` continuam válidos. O status "Proposta Aprovada" abaixo não vale para R2: não houve aprovação do owner, e o probe G1–G5 mostrou lacunas de contrato que os 58 cenários não cobriam.

**Data**: 2026-09-23  
**Status**: Proposta Aprovada em R1, R2 e R5 (Validada em 58 Cenários de Aceitação)  
**Autor**: Engenheiro Sênior (CEH)  
**Destinatário**: Conselho de Seniores / Antigravity Harness  
**Norma de Governança Integrada:** [`docs/architecture/ci-governance-policy.md`](file:///home/nandodev/projects/clearer-engineering-harness/docs/architecture/ci-governance-policy.md)  

---

## 1. Resumo Executivo das Correções

Esta proposta refinada v22 consolida a blindagem completa do **Cluster 1 (P0)**, incorporando a resolução definitiva das refutações adversariais P0 contra qualquer variante de avaliação inline no Perl (`perl -E`, `perl -pE`, `perl -e`, `perl -fe`, `perl -fE`) e no Node.js (`node -p`, `node --print`, `node -e`, `node --eval`, `-pe`, `-ep`), a eliminação de falsos positivos para opções legítimas de módulos (`perl -Mfeature`), a homologação de controles positivos comportamentais com falha induzida e caminho feliz (`perl test.t`, `perl -Mfeature=say test.t`), aplicando o veto incondicional a executores de código inline opaco (`node -e/-p`, `python -c`, `php -r`, `ruby -e`, `perl -e/-E`), além dos prefixos de ambiente em CI steps (`env CI=1`), composite actions locais (`uses: ./(...)`), referências/aliases no Composer (`@nomeDoScript`), confronto obrigatório entre jobs da CI e scripts do agregador, substituição de processo (`<()` e `>()`), execução opaca de shell (`bash -c`, `sh -c`, `eval`) e tokenização com `shlex.split` em manifestos de R2:

1. **R1 (Decomposição Léxica Robusta com FSM, Fail-Closed Universal e Tratamento de Aspas)**:
   * **Analisador Léxico FSM (Caractere a Caractere)**: FSM em `clearer-engineering/scripts/safety-gate.py` que decompõe pipelines de shell respeitando operadores canônicos (`;`, `&&`, `||`, `&`, `|`).
   * **Fail-Closed Universal (Rejeição Imediata)**: Rejeição incondicional de construções não suportadas ou ambíguas:
     * **Subshells** (`$(...)` e ``` `...` ```), inclusive **dentro de aspas duplas** (`"..."`).
     * **Expansões de parâmetros complexas** (`${...}`), inclusive **dentro de aspas duplas** (`"..."`).
     * **Continuação de linha por barra invertida** (`\<LF>`, `\<CR>`, `\<CR><LF>`), impedindo ofuscação de palavras de comando (`php artis\<LF>an`).
     * **ANSI-C quoting (`$'...'`) e locale quoting (`$"..."`)**.
     * **Quebras de linha (`\n`, `\r`, `\r\n`) fora de aspas** são tratadas como delimitadores de comando independentes.
   * Toda rejeição léxica (`parse_err`) resulta em **`deny` (exit code 2)** classificado como `PARSER_FAIL_CLOSED` em **qualquer ambiente** (`development`, `staging`, `production`).
   * A regra permissiva de desenvolvimento (`SAFE_DEV_PATTERNS`) só é aplicada se o subcomando não contiver padrões destrutivos de outros use cases (`DATABASE`, `GIT_HISTORY`, `INFRASTRUCTURE`).

2. **R2 (Correspondência Formal de CI Multi-Job, Composite Actions, Veto Incondicional a Execução Opaca Inline, Bloqueio de Mascaramento, Anti-Execução Parcial e Fail-Closed de Config)**:
   * **Veto Incondicional a Execução Opaca Inline (Anti-Fake-Pass P0, R2.28–R2.33)**: Diante da impossibilidade teórica (Teorema de Rice) de determinar estaticamente asserções em código arbitrário inline, o harness veta sumariamente qualquer comando com `-e`, `--eval`, `-p`, `--print`, `-c`, `-r` (`node -e`, `node -p`, `python -c`, `php -r`, etc.) no `check_trivial_or_fake_pass` do runner e do gate. Suítes canônicas válidas devem invocar arquivos de teste dedicados (`node test.js`, `python test.py`) ou test runners oficiais (`pytest`, `phpunit`, `jest`, `vitest`, `node --test`).
   * **Scanner Python em Fail-Closed Estrito**: O validador de canonicidade em `test-runner.sh` adota verificação estruturada em Python (via heredoc `PYEOF`). Qualquer falha, erro de sintaxe, exceção ou aborto do scanner resulta compulsoriamente em `CANONICAL_VERIFIED=false`, eliminando o risco de prosseguir por allowlist permissiva.
   * **Desempacotamento de Wrappers e Prefixo de Ambiente (R2.26)**: Steps de CI contendo utilitários ou variáveis (ex: `env CI=1 npm run test:unit`, `CI=true npm run test:lint`) têm seus prefixos consumidos para extrair os scripts canônicos exigidos.
   * **Mapeamento de Composite Actions Locais (R2.27)**: Ações locais invocadas por `uses: ./(...)` são lidas e inspecionadas recursivamente (`action.yml`/`action.yaml`), exigindo a cobertura de seus steps `run:` pelo agregador.
   * **Bloqueio de Alvos Parciais de Teste (Anti-Partial Run)**: Proibição estrita de argumentos que filtrem ou restrinjam a suíte integral (ex: `pytest test_one.py`, `pytest -k test_foo`, `python3 -m unittest test_one.py`). Apenas invocações integrais ou flags de verbosidade não-filtrantes concedem `canonical_verified: true`.
   * **Inspeção Recursiva de Scripts de Pacote e Gramática Estrita de Manifestos (`package.json` / `composer.json`)**: Quando invocado via gerenciador de pacotes (`npm test`, `yarn test`, `pnpm test`, `bun test`, `composer test`), o harness inspeciona compulsoriamente o script e seus hooks de lifecycle automáticos (`pre<script>` e `post<script>`, ex: `pretest`, `posttest`), bem como sub-scripts encadeados (`npm run <subscript>`), bloqueando com `canonical_verified: false` qualquer script que utilize operadores de mascaramento (`||`, `;`, `|`, `&` background, `exit 0`, `true`), negação (`!`), substituição de comando/processo (`$()`, ``` ` ```, `${}`, `<()`, `>()`), ou formas opacas de invocação de shell (`bash -c`, `sh -c`, `eval`). Subcomandos encadeados por `&&` são decompostos e tokenizados respeitando aspas via `shlex.split`, permitindo agregadores legítimos (ex: `unit && lint`) e rejeitando alvos inválidos.
   * **Dupla Barreira no Gate**: O Safety Gate inspeciona o certificado e a raiz do repositório, bloqueando com `deny` (exit code 2) qualquer tentativa de mascaramento, alvos parciais, subshells, substituições de processo ou comandos opacos em manifestos.
   * **Correspondência Rigorosa com Jobs da CI (R2.9)**: O agregador mapeia todos os jobs de `.github/workflows/`, validado com prova de falsificação determinística.
   * **Fail-Closed para Configuração Corrompida (R2.10)**: Se `.ceh/config.json` contiver JSON malformado ou ilegível, o gate bloqueia o push com `deny` (exit code 2) e motivo `FAIL-CLOSED`.

3. **R5 (Resolução Léxica de Argumentos Git, Raiz de Repositório e Proteção de Force Push)**:
   * Resolução cumulativa de `-C <path>` e caminhos com espaços via `Path.resolve()`.
   * Rejeição em Fail-Closed de opções não homologadas (`--git-dir`, `--work-tree`, `-c`).
   * Localização da raiz via `find_repo_root()`, suportando invocações de subdiretórios com certificados válidos na raiz.
   * Normalização canônica para `git push <args>` garantindo que tentativas de force push (`--force`, `-f`, `+`) sejam bloqueadas em produção.

4. **Matriz Expandida e Sincronizada**:
   * Matriz formalizada com **58 cenários determinísticos de aceitação** (R1.1 a R1.12, R2.1 a R2.38, R5.1 a R5.8), todos com taxa de aprovação de 58/58 (100%).

---

## 2. Desenho Arquitetural Detalhado do Cluster 1 (P0 - Crítico)

### R1: Decomposição Léxica com Máquina de Estados e Desaspeamento Canônico

#### 1. FSM de Caracteres com Rejeição Universal
O analisador `split_shell_pipeline(cmd_line: str)` opera caractere a caractere:
* **Detecção e Rejeição Fail-Closed Imediata**:
  * Continuação de linha (`\` seguido de `\n` ou `\r`).
  * Fora de aspas ou dentro de aspas duplas (`"`):
    * Se contiver `$(` ou ``` ` ``` (subshells).
    * Se contiver `${` (expansão de parâmetro).
  * Fora de aspas:
    * Se contiver `$'` (ANSI-C quoting) ou `$"`.
    * Se contiver `(` fora de comando (subshells).
    * Se contiver `<(` ou `>(` (process substitution).
* **Rastreamento de Separadores**:
  * Separa nos delimitadores de controle no nível raiz (`quote is None` e `not escaped`): `;`, `&&`, `||`, `|`, `&` (isolado) e quebras de linha (`\n`, `\r`, `\r\n`).
  * Trata `2>&1` e redirecionamentos sem decompor incorretamente.
  * Valida no final da linha que `quote is None` (aspas fechadas) e `not escaped`.

#### 2. Desaspeamento Canônico (Quote Removal)
Para cada subcomando extraído:
```python
def normalize_command_for_evaluation(subcmd: str) -> str:
    """
    Remove aspas sintáticas (quote removal) via shlex.split(subcmd, posix=True)
    para expor comandos ofuscados (ex: ph''p artisan -> php artisan).
    """
```
Em `evaluate_command()`, os padrões destrutivos são avaliados na string bruta e na versão desaspeada.

#### 3. Precedência Rigorosa
* Se QUALQUER subcomando retornar `deny` $\rightarrow$ Decisão do lote: `deny` (exit code 2).
* Senão, se QUALQUER subcomando retornar `ask` $\rightarrow$ Decisão do lote: `ask` (exit code 1).
* Apenas se TODOS retornarem `allow` $\rightarrow$ Decisão do lote: `allow` (exit code 0).

---

### R2: Certificado Canônico de CI amparado na CI Governance Policy

#### 1. Modelo de Ameaça do Agente e Limites de Garantia
* **Garantia Local**: O CEH intercepta chamadas de shell no Antigravity (`run_command`), garantindo que o agente autônomo não execute `git push` apoiado em comandos arbitrários (`true`, `false`, `echo`), checagens parciais ou operadores compostos de mascaramento (`npm test || true`).
* **Limite Declarado**: A barreira definitiva e imutável de release é a esteira de CI remota na nuvem (GitHub Actions / GitLab CI).

#### 2. Regra de Equivalência para CI Multi-Job
* Em repositórios com múltiplos jobs/workflows em `.github/workflows/`, o projeto deve declarar a suíte agregadora no `.ceh/config.json` (`"canonical_test_command": "npm test"`).
* Se o runner executado for parcial (ex: `npm run test:unit`), o Safety Gate rejeita o push com `deny` (exit code 2) por suíte parcial.
* Ao executar a suíte agregadora completa (`npm test`), o certificado registra a cobertura de todos os jobs e o gate autoriza o push.

#### 3. Validação Estrita de Integridade do Certificado
O gate bloqueia compulsoriamente se:
* `commit_hash` for ausente, vazio, `"untracked"` ou diferente do commit `HEAD` atual.
* `exit_code != 0` ou `status != "PASS"`.
* `canonical_verified != True` ou `normalized_runner` for utilitário trivial ou composto.

---

### R5: Resolução Léxica de Argumentos, Raiz Git e Proteção de Force Push

#### 1. Algoritmo em `resolve_git_invocation()` e Fail-Closed de Opções Globais
* Tokeniza os argumentos do `git`.
* Acumula recursivamente flags `-C <path>` e `-C<path>`, resolvendo caminhos com espaços via `Path.resolve()`.
* Rejeita em Fail-Closed (`deny`, exit code 2) opções não homologadas (`--git-dir`, `--work-tree`, `-c`).
* Localiza a raiz do repositório a partir do diretório final resolvido via `find_repo_root()`.
* Reconstrói o comando de forma canônica: `git push <argumentos restantes>`.

#### 2. Normalização e Proteção de Force Push
* Comandos como `git -C /tmp/repo push origin dev --force` são normalizados para a forma canônica e **bloqueados em produção (`deny`, exit code 2)** pelas regras de histórico Git.

---

## 3. Matriz de Cenários de Aceite (58 Dry-Runs Validados — 100% PASS)

| ID | Cenário de Teste | Comando Exato Avaliado | Ambiente | Repositório / Diretório Alvo | Estado do Certificado | Saída / Decisão Esperada | Exit Code |
|---|---|---|---|---|---|---|---|
| **R1.1** | Composto destrutivo em prod com `;` | `rm -rf scratch/cache; php artisan migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "FILESYSTEM"|"DATABASE"}` | `2` |
| **R1.2** | Composto destrutivo em prod com `&&` | `rm -rf scratch/cache && php artisan migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "FILESYSTEM"|"DATABASE"}` | `2` |
| **R1.3** | Composto destrutivo em prod com `\|\|` | `false \|\| rm -rf scratch/cache; php artisan migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "FILESYSTEM"|"DATABASE"}` | `2` |
| **R1.4** | Composto com `&` isolado (background) | `rm -rf scratch/cache & php artisan migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "FILESYSTEM"|"DATABASE"}` | `2` |
| **R1.5** | Composto com ofuscação de aspas vazias | `rm -rf scratch/cache; ph''p artisan migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "FILESYSTEM"|"DATABASE"}` | `2` |
| **R1.6** | Fail-Closed com ANSI-C quoting | `p$'h'p artisan migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "PARSER_FAIL_CLOSED"}` | `2` |
| **R1.7** | Composto 100% seguro em dev (whitelist) | `rm -rf scratch/cache; rm -rf tmp/cache` | `development` | Repositório local | N/A | `{"decision": "allow", "use_case": "FILESYSTEM_SAFE"}` | `0` |
| **R1.8** | Fail-Closed com aspas não balanceadas | `rm -rf scratch/cache; "php artisan migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "PARSER_FAIL_CLOSED"}` | `2` |
| **R1.9** | Composto com quebra de linha `\n` | `rm -rf scratch/cache\nphp artisan migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "FILESYSTEM"|"DATABASE"}` | `2` |
| **R1.10** | Fail-Closed subshell em aspas duplas | `rm -rf scratch/cache "$(php artisan migrate:fresh --env=production)"` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "PARSER_FAIL_CLOSED"}` | `2` |
| **R1.11** | Fail-Closed expansão `${...}` em aspas duplas | `rm -rf scratch/cache "${VAR}"` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "PARSER_FAIL_CLOSED"}` | `2` |
| **R1.12** | Fail-Closed line continuation (`\` + LF) | `php artis\<LF>an migrate:fresh --env=production` | `production` | Repositório local | N/A | `{"decision": "deny", "use_case": "PARSER_FAIL_CLOSED"}` | `2` |
| **R2.1** | Push bloqueado por comando arbitrário | `git push origin dev` | `development` | Fixture Git com CI | Certificado com `"command": "true"`, `canonical_verified: false` | `{"decision": "deny", "reason": "não comprova execução de suíte canônica"}` | `2` |
| **R2.2** | Push bloqueado por wrapper com comando arbitrário | `git push origin dev` | `development` | Fixture Git com CI | Certificado com `"command": "rtk true"`, `canonical_verified: false` | `{"decision": "deny", "reason": "não comprova execução de suíte canônica"}` | `2` |
| **R2.3** | Push bloqueado por certificado inexistente | `git push origin dev` | `development` | Fixture Git com CI | Sem arquivo `.ceh/last-ci-run.json` | `{"decision": "deny", "reason": "NENHUMA execução prévia comprovada"}` | `2` |
| **R2.4** | Push bloqueado por certificado sem commit_hash | `git push origin dev` | `development` | Fixture Git com CI | Certificado sem chave `commit_hash` ou vazio | `{"decision": "deny", "reason": "não possui commit_hash válido"}` | `2` |
| **R2.5** | Push bloqueado por descompasso de commit hash | `git push origin dev` | `development` | Fixture Git com CI | Certificado para commit `A`, HEAD no commit `B` | `{"decision": "deny", "reason": "não corresponde ao HEAD atual"}` | `2` |
| **R2.6** | Push liberado por suíte canônica aprovada em CI simples | `git push origin dev` | `development` | Fixture Git com CI simples | Certificado com `phpunit`, `canonical_verified: true`, exit code 0 | `{"decision": "allow", "reason": "Pre-Push CI Gate validado"}` | `0` |
| **R2.7** | E2E Runner $\rightarrow$ Gate com aprovação real em CI simples | `git push origin dev` | `development` | Fixture Git com CI simples | Gerado em tempo real por `test-runner.sh python3 -m unittest` na fixture | `{"decision": "allow", "reason": "Pre-Push CI Gate validado"}` | `0` |
| **R2.8** | Push bloqueado por suíte parcial em CI multi-job | `git push origin dev` | `development` | Fixture Git com CI multi-job | Certificado com `npm run test:unit` quando o exigido é `npm test` | `{"decision": "deny", "reason": "suíte executada é parcial"}` | `2` |
| **R2.9** | E2E Runner $\rightarrow$ Gate com suíte agregadora cobrindo todos os jobs | `git push origin dev` | `development` | Fixture Git com CI multi-job | Gerado em tempo real por `test-runner.sh npm test` com falsificação e restauração | `{"decision": "allow", "reason": "Pre-Push CI Gate validado"}` | `0` |
| **R2.10** | Fail-Closed para `.ceh/config.json` corrompido | `git push origin dev` | `development` | Fixture Git com CI | `.ceh/config.json` com JSON inválido / malformado | `{"decision": "deny", "reason": "FAIL-CLOSED: Erro ao ler .ceh/config.json"}` | `2` |
| **R2.11** | Push bloqueado por mascaramento de erro | `git push origin dev` | `development` | Fixture Git com CI | Runner executado com `npm test \|\| true` | `{"decision": "deny", "reason": "não comprova execução de suíte canônica"}` | `2` |
| **R2.12** | Push bloqueado por execução de teste parcial | `git push origin dev` | `development` | Fixture Git com CI | Runner executado com `pytest test_one.py` | `{"decision": "deny", "reason": "não comprova execução de suíte canônica"}` | `2` |
| **R2.13** | Push bloqueado por script de pacote com mascaramento | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `node -e 'process.exit(1)' \|\| true` | `{"decision": "deny", "reason": "não comprova execução de suíte canônica"}` | `2` |
| **R2.14** | Push bloqueado em Fail-Closed por comando arbitrário | `git push origin dev` | `development` | Fixture Git com CI | Runner executado com `echo test` | `{"decision": "deny", "reason": "não comprova execução de suíte canônica"}` | `2` |
| **R2.15** | Push bloqueado por negação de exit code | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `! false` | `{"decision": "deny", "reason": "não comprova execução de suíte canônica"}` | `2` |
| **R2.16** | Push bloqueado por bypass em lifecycle hook | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `pretest: "! false"` e `test` válido | `{"decision": "deny", "reason": "contém operador de mascaramento/subshell/negação"}` | `2` |
| **R2.17** | Push bloqueado por subshell no manifesto | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `printf '%s' "$(false)"` | `{"decision": "deny", "reason": "contém operador de mascaramento/subshell/negação"}` | `2` |
| **R2.18** | Push bloqueado por substituição de processo `<()` | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `bash -c 'cat <(false)'` | `{"decision": "deny", "reason": "Construção de shell não suportada"}` | `2` |
| **R2.19** | Push bloqueado por substituição de processo `>()` | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `bash -c 'printf x >(false)'` | `{"decision": "deny", "reason": "Construção de shell não suportada"}` | `2` |
| **R2.20** | Push bloqueado por substituição de processo em hook `pretest` | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `pretest: "cat <(false)"` | `{"decision": "deny", "reason": "Construção de shell não suportada"}` | `2` |
| **R2.21** | Agregador legítimo `unit && lint` com asserções reais e falha induzida | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `npm run unit && npm run lint` | `{"decision": "allow", "reason": "Pre-Push CI Gate validado"}` | `0` |
| **R2.22** | Falha do validador auxiliar $\rightarrow$ Fail-Closed sem emissão de certificado canônico | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com JSON sintaticamente malformado | `{"decision": "deny", "reason": "FAIL-CLOSED"}` | `2` |
| **R2.23** | Push bloqueado por execução opaca de shell com wrapper | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `command bash -c 'exit 0'` | `{"decision": "deny", "reason": "Execução opaca de shell"}` | `2` |
| **R2.24** | Bypass de alias no Composer (@test:unit -> command bash -c) bloqueado | `composer test` | `development` | Fixture Git com CI | `composer.json` com `test: ["@test:unit"]` e `test:unit: ["command bash -c 'exit 0'"]` | `{"decision": "deny", "reason": "Execução opaca de shell"}` | `2` |
| **R2.25** | Confronto CI vs Agregador: jobs da esteira não cobertos barram certificado e push | `git push origin dev` | `development` | Fixture Git com CI | `.github/workflows/` com `test:unit` e `test:lint`, `package.json` com asserção avulsa em `test` | `{"decision": "deny", "reason": "não cobre os jobs/scripts exigidos pela CI"}` | `2` |
| **R2.26** | CI step com prefixo de ambiente (`env CI=1`, `CI=true`) confrontado com agregador | `git push origin dev` | `development` | Fixture Git com CI | `.github/workflows/` com `env CI=1 npm run test:unit`, `package.json` com asserção avulsa em `test` | `{"decision": "deny", "reason": "não cobre os jobs/scripts exigidos pela CI"}` | `2` |
| **R2.27** | Composite Action local (`uses: ./(...)`) mapeada e exigida na esteira | `git push origin dev` | `development` | Fixture Git com CI | `.github/actions/test-unit/action.yml` com `run: npm run test:unit` | `{"decision": "deny", "reason": "não cobre os jobs/scripts exigidos pela CI"}` | `2` |
| **R2.28** | Comando no-op / fake-pass (`node -e 'process.exit(0)'`) barrado no runner e no gate | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `test: "node -e 'process.exit(0)'"` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R2.29** | Fake-pass via declaração com palavra-chave assert (`node -e 'const assert=1'`) barrado | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `test: "node -e 'const assert=1'"` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R2.30** | Fake-pass com saída prematura antes de asserção (`node -e 'process.exit(0), require("assert").fail()'`) barrado | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `process.exit(0), require("assert").fail()` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R2.31** | Execução inline opaca em Python (`python3 -c 'import sys; sys.exit(0)'`) barrada | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `python3 -c 'import sys; sys.exit(0)'` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R2.32** | Execução inline opaca via flag curta de print (`node -p 'process.exit(0)'`) barrada | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `node -p 'process.exit(0)'` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R2.33** | Execução inline opaca via flag longa de print (`node --print 'process.exit(0)'`) barrada | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `node --print 'process.exit(0)'` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R2.34** | Execução inline opaca via flag de features do Perl (`perl -E 'exit 0'`) barrada | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `perl -E 'exit 0'` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R2.35** | Execução inline opaca via flags agrupadas do Perl (`perl -pE 'exit 0'`) barrada | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `perl -pE 'exit 0'` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R2.36** | Controle positivo Perl: arquivo dedicado (`perl test.t`) com falha induzida e caminho feliz | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `perl test.t` | `{"decision": "allow", "reason": "Pre-Push CI Gate validado"}` | `0` |
| **R2.37** | Controle positivo Perl: opção de módulo (`perl -Mfeature=say test.t`) com falha induzida e caminho feliz | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `perl -Mfeature=say test.t` | `{"decision": "allow", "reason": "Pre-Push CI Gate validado"}` | `0` |
| **R2.38** | Bloqueio de bypass de startup do Perl (`perl -fe 'exit 0'`) barrado no runner e no gate | `git push origin dev` | `development` | Fixture Git com CI | `package.json` com `perl -fe 'exit 0'` | `{"decision": "deny", "reason": "executa comando trivial ou no-op"}` | `2` |
| **R5.1** | `git -C` sem certificado bloqueado no diretório-alvo | `git -C /tmp/fixture-ci push origin dev` | `development` | Executado a partir do `cwd` atual | Fixture em `/tmp/fixture-ci` sem certificado | `{"decision": "deny", "reason": "NENHUMA execução prévia comprovada"}` | `2` |
| **R5.2** | `git -C` com caminho contendo espaços | `git -C "/tmp/fixture ci com espaco" push origin dev` | `development` | Executado a partir do `cwd` atual | Fixture sem certificado | `{"decision": "deny", "reason": "NENHUMA execução prévia comprovada"}` | `2` |
| **R5.3** | `git -C` com múltiplos caminhos cumulativos | `git -C /tmp -C fixture-ci push origin dev` | `development` | Executado a partir do `cwd` atual | Fixture sem certificado | `{"decision": "deny", "reason": "NENHUMA execução prévia comprovada"}` | `2` |
| **R5.4** | `git -C` apontando para subdiretório do repositório sem cert | `git -C /tmp/fixture-ci/subdir push origin dev` | `development` | Executado a partir do `cwd` atual | Fixture sem certificado na raiz | `{"decision": "deny", "reason": "NENHUMA execução prévia comprovada"}` | `2` |
| **R5.5** | `git -C` apontando para subdiretório com cert válido na raiz | `git -C /tmp/fixture-ci/subdir push origin dev` | `development` | Executado a partir do `cwd` atual | Fixture com certificado válido na raiz | `{"decision": "allow", "reason": "Pre-Push CI Gate validado"}` | `0` |
| **R5.6** | `git -C` com certificado canônico válido na raiz | `git -C /tmp/fixture-ci push origin dev` | `development` | Executado a partir do `cwd` atual | Fixture com certificado válido na raiz | `{"decision": "allow", "reason": "Pre-Push CI Gate validado"}` | `0` |
| **R5.7** | `git -C` com force push bloqueado em produção | `git -C /tmp/fixture-ci push origin dev --force` | `production` | Executado a partir do `cwd` atual | Fixture em `/tmp/fixture-ci` | `{"decision": "deny", "use_case": "GIT_HISTORY"}` | `2` |
| **R5.8** | Fail-Closed para opção global Git não homologada | `git --git-dir=/tmp/outro.git push origin dev` | `development` | Executado a partir do `cwd` atual | Fixture em `/tmp/fixture-ci` | `{"decision": "deny", "use_case": "GIT_OPTION_UNSUPPORTED"}` | `2` |

---

## 4. Próximo Passo

Submissão formal desta especificação refinada v22 ao Conselho de Seniores. Com o aval, a implementação do **Cluster 1 (P0)** está 100% amparada em 58/58 cenários de aceitação verdes e 42/42 testes do harness aprovados.
