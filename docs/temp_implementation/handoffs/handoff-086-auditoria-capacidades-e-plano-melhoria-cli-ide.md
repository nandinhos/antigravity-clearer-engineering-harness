# Handoff 086 — Consolidação: Diagnóstico de Latência (5 Gates), Higiene de Frontmatter/Hooks e Evolução Dual-Host (CLI & IDE)

> **Data/Hora:** 2026-10-20T15:08:00-03:00
> **Instância Origem:** Sessão Antigravity (`clearer-harness` / Gemini 4 Argon)
> **Repositório Alvo:** `clearer-engineering-harness` (branch `dev`, commit base `89b0ef5`, versão atual `v2.1.2`)
> **Antecessor na Série:** [Handoff 085](./handoff-085-revisao-final-pr6-v2-0-0.md)
> **Status:** `PLANO CONSOLIDADO (Unificação Handoff 086 + Handoff de Diagnóstico de Latência e Higiene)`

---

## 1. Contexto & Objetivo da Consolidação

Este documento unifica dois levantamentos técnicos independentes realizados em 2026-10-20:
1. **Relatório de Debugging Sistemático (5 Gates — `F01` a `F06`)**: Investigação de lentidão severa (3–4 min por turno em `"Working / Generating / Loading"`) na Antigravity IDE/CLI e mapeamento de erros silenciosos nos parsers internos em Go (`rules.go`, `skills.go`, `permission_grant_store.go`).
2. **Auditoria Arquitetural de Capacidades e Performance Dual-Host (`G1` a `G5`)**: Mapeamento das 5 camadas do ecossistema, conflitos de hooks no `PreToolUse`, contradições de `RTK` entre perfis, falsos positivos no `test-runner.sh` e ergonomia CLI/IDE.

---

## 2. Análise de Conflitos e Interdependências entre os Dois Handoffs (`OBSERVED`)

Antes de unificar as fases de implementação, os dois documentos foram confrontados contra as invariantes de código do CEH (`doc-audit.py`, `ceh-doctor.sh` e `tools/package.py`). Foram identificados e resolvidos **4 conflitos técnicos críticos**:

| # | Conflito Detectado entre os Planos e o Repositório | Causa Raiz (`OBSERVED`) | Resolução Arquitetural no Plano Unificado |
|---|---|---|---|
| **C1** | **Incompatibilidade de `F04` (`hooks.json` interpolado no `install.sh`) com `ceh-doctor.sh --verify` e `test_doctor_verify.py`** | `F04` sugeria alterar `~/.gemini/config/plugins/clearer-engineering/hooks.json` durante o `install.sh` injetando o path absoluto do usuário. Porém, `ceh-doctor.sh --verify` (linhas 152–210) e `test_doctor_verify.py` (linha 92) comparam o SHA-256 byte-a-byte de `hooks.json` instalado contra o pacote gerado por `tools/package.py --host antigravity`. Qualquer mutação pós-empacotamento quebra o `--verify`! | Usar `"$HOME/.gemini/config/plugins/clearer-engineering/scripts/safety-gate.py"` diretamente na fonte canônica `clearer-engineering/hooks.json` (que é copiada deterministicamente por `package.py`), mantendo o SHA-256 100% idêntico entre fonte, pacote e instalação, além de manter o path absoluto em `~/.gemini/config/hooks.json`. |
| **C2** | **Sobreposição entre `G1` (`~/.gemini/config/hooks.json`) e `F04` (`clearer-engineering/hooks.json`)** | Ambos tratam da execução do `safety-gate.py` no evento `PreToolUse`, mas em arquivos distintos (configuração global do usuário vs manifesto do plugin empacotado). | Unificados na **Fase 2**: saneamento simultâneo de `clearer-engineering/hooks.json` (path via `$HOME`) e de `~/.gemini/config/hooks.json` (desativação de `guard_destructive.py` que conflitava com `ALLOW` em `DEV` e triplicava o spawn Python). |
| **C3** | **Teto Rígido de 200 Linhas em `test-runner.sh` (`doc-audit.py` Check [7/7]) vs `G4` (Anti-Stub + `docker_service`)** | `clearer-engineering/scripts/test-runner.sh` possui atualmente **187 linhas** (`OBSERVED`), restando apenas **13 linhas** de orçamento antes de reprovar no `doc-audit.py` (linha 267: `runner_lines > 200`). Além disso, `test-runner.sh` usa `python3 -c` multi-linha nas linhas 172–178 (violando o espírito de `F03`). | Na **Fase 5**, compactar o bloco Python das linhas 172–178 em one-liner e implementar a detecção anti-stub de `package.json` + suporte a `docker_service` mantendo `test-runner.sh` estritamente $\le 195$ linhas. |
| **C4** | **Bloqueio de Caminhos Absolutos Locais em `docs/` (`doc-audit.py` Check [4/7])** | `doc-audit.py` (linhas 188–201) rejeita qualquer arquivo `.md` em `docs/` que contenha caminhos `/home/<usuario>/` (exceto `/home/user/`). Os dois handoffs originais continham o username real da máquina. | Todos os caminhos em `docs/` usam exclusivamente `~/` ou `/home/user/`, garantindo aprovação imediata no `doc-audit.sh`. |

---

## 3. Diagnóstico Consolidado: Relatório de 5 Gates (`/systematic-debugging`) + Matriz de Gaps (`F01–F06` & `G1–G5`)

### 3.1. Resumo dos 5 Gates de Latência e Parser
- **Gate 0 (Triage)**: Lentidão severa (3–4 min em `"Working / Generating"`) e descarte silencioso de rules/skills no Antigravity IDE/CLI.
- **Gate 1 (Reproduce — `OBSERVED`)**:
  - Logs de CLI (`~/.gemini/antigravity-cli/log/cli-20261020_*.log`) e IDE (`~/.antigravity-ide-server/data/logs/.../Antigravity IDE.log`):
    - `UNAVAILABLE (code 503): No capacity available for model gemini-3.8-flash-medium on the server`
    - `UNAVAILABLE (code 503): No capacity available for model gemini-3.8-flash-high on the server`
    - `Print mode: print timeout after 2m20s with turn in progress after 5487 polls`
  - Logs de Parser (`rules.go`, `skills.go`, `permission_grant_store.go`):
    - `skills.go:236] Failed to parse skill file ~/.gemini/skills/security-hardening/SKILL.md: failed to decode frontmatter: yaml: unmarshal errors`
    - `rules.go:158] Failed to parse global rule file ~/.gemini/config/rules/macos-symlink-resolution.md: invalid frontmatter format`
    - `rules.go:169] Failed to parse rule file .agents/rules/*.md: invalid frontmatter format`
    - `permission_grant_store.go:373] ignoring invalid allow entry "command(python3 -c \"\nimport json...": invalid grant string`
- **Gate 2 & 3 (Isolate & Root Cause)**:
  1. **Primária (Externa — P0)**: Saturação HTTP 503 nos pools `gemini-3.8-flash-high/medium` somada ao encadeamento silencioso de múltiplos tool calls sem emissão de texto intermediário. A migração para **`Gemini 4 Argon (Medium)`** reduziu o round-trip de 180–270s para **8–15s** com zero falhas.
  2. **Secundária (Interna — P1/P2)**:
     - Arquivos `.md` em `rules/` sem frontmatter YAML `---\ntrigger: always_on\n---` (mas com `---` no corpo do texto) quebram o `rules.go`.
     - Comandos `python3 -c` multi-linha aprovados pelo usuário corrompem o `permission_grant_store.go`.
     - Tripla execução de hooks Python no `PreToolUse` em `~/.gemini/config/hooks.json` (`safety-gate.py` + `guard_destructive.py` + `sail_container_guard.py`), onde `guard_destructive.py` bloqueava comandos permitidos em `DEV` pelo CEH.

### 3.2. Matriz Unificada de Itens de Ação (11 Achados Consolidados)

| ID Unificado | Origem | Severidade | Descrição Objetiva |
|---|---|---|---|
| **U01** | `F01` | **HIGH** | `clearer-engineering/rules/AGENTS.md` não possui frontmatter YAML (`trigger: always_on`) no topo e contém `---` na linha 6, gerando falha/ambiguidade no `rules.go`. |
| **U02** | `F02` | **HIGH** | Ausência de regra anti-"Silent Working Loop": encadeamento de $>2$ tool calls sem texto intermediário deixa a UI muda em `"Working / Generating"`. |
| **U03** | `F03` | **MEDIUM** | Uso de `python3 -c` / `php -r` com quebras de linha literais (`\n`) corrompe `permission_grant_store.go` da Antigravity IDE quando aprovado. |
| **U04** | `F04` + `G1` | **HIGH** | `clearer-engineering/hooks.json` usa caminho relativo (`scripts/safety-gate.py`), enquanto `~/.gemini/config/hooks.json` dispara 3 processos Python por comando e `guard_destructive.py` bloqueia `migrate:fresh`/`TRUNCATE` em `DEV`. |
| **U05** | `F05` | **HIGH** | Falta validação automática de frontmatter YAML para `rules/*.md` em `test_content_schema.py` / `doc-audit.py`, além de arquivos locais órfãos sem frontmatter (`~/.gemini/skills/security-hardening/SKILL.md` e `~/.gemini/config/rules/macos-symlink-resolution.md`). |
| **U06** | `F06` + `G5` | **MEDIUM** | Falta documentação de diagnóstico/fallback para `HTTP 503` (`gemini-3.8-flash-*` ➔ `Gemini 4 Argon`) e atualização do catálogo de modelos no `gemini-orchestrator`. |
| **U07** | `G2` | **HIGH** | Contradição direta sobre `RTK`: `AGENTS.md` (§6.4) exige `rtk`, mas `~/.gemini/config/agents/gemini-orchestrator/agent.md` (linha 67) proíbe `RTK`. |
| **U08** | `G5` | **MEDIUM** | Comando `ceh-doctor` é anunciado em `ceh-help.sh`, mas não existe em `clearer-engineering/config/aliases.sh` nem em `rc_aliases.py` (`DEFAULT_KNOWN_NAMES`). |
| **U09** | `G4` | **MEDIUM** | `test-runner.sh` executa `npm test` mesmo quando `package.json` contém apenas o stub padrão (`no test specified`) e só reconhece containers `laravel.test` ou `app`. |
| **U10** | `G3` | **MEDIUM** | Degradação `ask -> deny` em `HOMOLOGACAO` (`adapters/antigravity.py`) não orienta o uso do modal `ask_question` com os 2 Alertas Obrigatórios nem artefatos `RequestFeedback` na IDE. |
| **U11** | `Fase 2 (086)` | **LOW** | `statusline.sh` do Antigravity CLI não exibe o ambiente ativo do CEH (`🛡️ DEV/STG/PRD`) nem o status do certificado CI (`✅ CI`). |

---

## 4. Plano Único de Implementação (6 Fases Sequenciais)

> **Regra de Ouro de Integridade (`ceh-doctor --verify`)**: Todas as edições em arquivos do plugin CEH devem ser feitas em `clearer-engineering/` no repositório, validadas pelos testes e instaladas via `bash install.sh` para manter 100% de paridade SHA-256 com `~/.gemini/config/plugins/clearer-engineering/`.

---

### Fase 1: Regras Core do Harness (`AGENTS.md` e `coding-policy.md`) — Resolve `U01`, `U02`, `U03`

1. **`clearer-engineering/rules/AGENTS.md`**:
   - **Frontmatter YAML no Topo (`U01`)**: Inserir na linha 1:
     ```yaml
     ---
     trigger: always_on
     description: CLEARER Engineering Harness (CEH) Core Rules and Protocol
     ---
     ```
   - **Heurística 12 — Visibilidade em Cadeias de Investigação / Anti-Silent Loop (`U02`)**: Adicionar na seção `§6.10 Protocolo de Comunicação Executiva & Ponytail UX`:
     - *"Heurística 12 (Visibilidade em Cadeias de Investigação / Anti-Silent Working Loop): Em sequências de investigação com mais de 2 chamadas de ferramentas consecutivas (ou durante diagnósticos e `/systematic-debugging`), o agente DEVE emitir 1 frase curta e objetiva informando o que está inspecionando e o achado parcial antes de disparar a próxima ferramenta, evitando períodos mudos prolongados em 'Working / Generating'."*
   - **Regra de One-Liner em Comandos Inline (`U03`)**: Adicionar proibição explícita de `python3 -c` ou `php -r` com quebras de linha literais (`\n`) em `run_command` para não corromper o `permission_grant_store.go` da Antigravity IDE.
2. **`clearer-engineering/rules/coding-policy.md`**:
   - Reforçar na seção de execução de comandos/scripts que scripts inline em `run_command` devem ser estritamente single-line (separados por `;`) ou gravados em `<artifactDir>/scratch/`.

---

### Fase 2: Saneamento de Hooks (`clearer-engineering/hooks.json` e `~/.gemini/config/hooks.json`) — Resolve `U04`, `C1`, `C2`

1. **`clearer-engineering/hooks.json` (Fonte Canônica do Plugin)**:
   - Atualizar `"command": "python3 scripts/safety-gate.py"` nos 4 matchers (`run_command`, `write_to_file`, `replace_file_content`, `multi_replace_file_content`) para:
     ```json
     "command": "python3 \"$HOME/.gemini/config/plugins/clearer-engineering/scripts/safety-gate.py\""
     ```
   - **Por que esse formato?** Funciona em qualquer diretório de trabalho (`CWD`) quando invocado pelo Antigravity, é 100% determinístico (independe do nome de usuário da máquina) e preserva o hash SHA-256 idêntico entre `tools/package.py`, `install.sh` e `ceh-doctor.sh --verify`.
2. **`~/.gemini/config/hooks.json` (Configuração Global da Estação)**:
   - Definir `"enabled": false` em `"destructive-command-guardrail"` (`guard_destructive.py`), eliminando o conflito onde `guard_destructive.py` bloqueava comandos `ALLOW` em `DEV` (`migrate:fresh`, `db:wipe`, `TRUNCATE`) e reduzindo o overhead de processos Python por comando.
   - Manter `"ceh-safety-gate"` ativo com o caminho do `safety-gate.py`.

---

### Fase 3: Validação Estrutural de Frontmatter YAML e Higiene de Rules/Skills Locais — Resolve `U05`

1. **`clearer-engineering/tests/test_content_schema.py`**:
   - Adicionar o método `test_rules_frontmatter(self)` na classe `TestFrontmatterSchema`:
     - Verifica todos os arquivos `clearer-engineering/rules/*.md`.
     - Exige frontmatter YAML iniciando na linha 1 com `---`, fechado com `---`, contendo a chave `trigger` não-vazia (ex: `always_on`).
   - Estender `test_stdlib_yaml_fallback_parses_all_frontmatters` para também validar `rules/*.md`.
2. **`clearer-engineering/scripts/doc-audit.py`**:
   - Adicionar verificação determinística de frontmatter YAML em `clearer-engineering/rules/*.md` e `clearer-engineering/skills/*/SKILL.md` para garantir que nenhum arquivo sem frontmatter seja commitado no harness.
3. **Higienização Imediata dos Arquivos Globais do Ambiente Local (`~/.gemini/`)**:
   - `~/.gemini/skills/security-hardening/SKILL.md`: adicionar frontmatter válido (`name: security-hardening`, `description: ...`).
   - `~/.gemini/config/rules/macos-symlink-resolution.md`: adicionar frontmatter válido (`trigger: always_on`, `description: ...`).

---

### Fase 4: Alinhamento de Aliases (`ceh-doctor` / `ceh-report`), `RTK`, Gemini 4 e `statusline.sh` — Resolve `U06`, `U07`, `U08`, `U11`

1. **`clearer-engineering/config/aliases.sh` e `clearer-engineering/scripts/rc_aliases.py`**:
   - Adicionar em `config/aliases.sh`:
     ```sh
     alias ceh-doctor='sh ~/.gemini/config/plugins/clearer-engineering/scripts/ceh-doctor.sh'
     alias ceh-report='bash ~/.gemini/config/plugins/clearer-engineering/scripts/evidence-report.sh'
     ```
   - Adicionar `'ceh-doctor'` e `'ceh-report'` em `DEFAULT_KNOWN_NAMES` dentro de `scripts/rc_aliases.py`.
   - Atualizar `clearer-engineering/tests/test_help_contract.py` para exigir que todo alias listado em `ceh-help.sh` exista em `config/aliases.sh`.
2. **`~/.gemini/config/agents/gemini-orchestrator/agent.md`**:
   - Remover a instrução conflitante *"não use proxies de compressão (Headroom/RTK)"* na seção 5, alinhando com a Tríade de Economia (`Graphify + RTK + context-mode`).
   - Atualizar a tabela de roteamento de modelos na seção 2 para priorizar `inherit` / **Gemini 4 Argon** e documentar o alerta de saturação HTTP 503 nos pools legados `gemini-3.8-flash-*`.
3. **`~/.gemini/antigravity-cli/statusline.sh`**:
   - Adicionar badge leve em bash/jq ($<5\text{ms}$, sem spawn Python) exibindo o ambiente CEH (`🛡️ DEV` / `🛡️ STG` / `🛡️ PRD`) e o status do certificado CI (`.ceh/last-ci-run.json` ➔ `✅ CI` / `⚠️ CI:STALE`).

---

### Fase 5: Inteligência Anti-Stub e Runtime Adapter no `test-runner.sh` e `detect-project.sh` (Respeitando Teto $\le 200$ Linhas) — Resolve `U09`, `C3`

1. **`clearer-engineering/scripts/test-runner.sh` (atualmente 187 linhas — manter $\le 195$ linhas)**:
   - **Ignorar Stub Padrão do `npm init`**: Ao inspecionar `package.json`, verificar se o script `"test"` não contém `"no test specified"`. Se contiver apenas o stub padrão, não definir `DETECTED_CMD="npm test"` (permitindo fallback limpo para `STATUS: NOT RUN` com razão explícita).
   - **Suporte a `docker_service` em `.ceh/config.json` + Containers Comuns (`web`, `php`, `backend`)**: Ler opcionalmente `docker_service` junto com `canonical_test_command` de `HEAD:.ceh/config.json` e ampliar a lista de containers Compose reconhecidos (`laravel.test`, `app`, `web`, `php`, `backend`).
   - **Compactação One-Liner Python (`F03` + `C3`)**: Converter o bloco `python3 -c` de 7 linhas (linhas 172–178) em chamada compacta, economizando 5 linhas para manter o arquivo bem abaixo do limite de 200 linhas do `doc-audit.py`.
2. **`clearer-engineering/scripts/detect-project.sh`**:
   - Sincronizar a mesma detecção anti-stub de `package.json` e a lista ampliada de containers Compose.

---

### Fase 6: Ergonomia Dual-Host (`HOMOLOGACAO` + Artefatos IDE) & Atualização de Documentação + Certificação — Resolve `U06`, `U10`

1. **`clearer-engineering/scripts/adapters/antigravity.py` e `clearer-engineering/skills/clearer/SKILL.md`**:
   - Em `adapters/antigravity.py`: enriquecer a orientação de `[CEH CONTEXT LOCK]` quando `decision == "ask"` é convertido para `"deny"` em `HOMOLOGACAO`, instruindo o agente a acionar a tool `ask_question` com os **2 Alertas Explícitos** (Impacto + Backup/Rollback) e apresentar o comando verificado para execução segura pelo desenvolvedor.
   - Em `skills/clearer/SKILL.md` e `skills/clearer-feature/SKILL.md`: orientar o uso de `ArtifactMetadata.RequestFeedback = true` ao gerar planos de implementação na Antigravity IDE.
2. **Atualização Completa da Documentação**:
   - `README.md`, `README_PT.md`, `docs/skills_and_commands.md`, `docs/installation.md` (incluindo seção de Troubleshooting de Latência HTTP 503 com comando `grep` de diagnóstico de logs e recomendação do pool `Gemini 4 Argon`).
   - `CHANGELOG.md` e `clearer-engineering/plugin.json` (bump para `v2.1.3`).
3. **Bateria de Certificação Obrigatória (`OBSERVED`)**:
   ```bash
   bash clearer-engineering/tests/run-all-tests.sh
   bash evals/run.sh
   bash clearer-engineering/scripts/doc-audit.sh
   bash install.sh
   sh clearer-engineering/scripts/ceh-doctor.sh --self-check
   sh clearer-engineering/scripts/ceh-doctor.sh --verify .
   bash clearer-engineering/scripts/test-runner.sh
   bash clearer-engineering/scripts/evidence-report.sh --strict
   ```
