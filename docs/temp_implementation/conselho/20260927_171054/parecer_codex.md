OpenAI Codex v0.156.1
--------
workdir: .
model: gpt-6-luna
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: medium
reasoning summaries: none
session id: [REDACTED]
--------
user
Você está deliberando como integrante do CONSELHO DE SENIORES do CLEARER Engineering Harness (CEH).
Sua identidade e delegação nesta sessão:
ARQUITETO DE LÓGICA FORMAL & ALGORITMOS — Especialista em raciocínio formal profundo, tipagem estrita, invariantes matemáticos, estruturas de dados e análise de concorrência/deadlocks.

OBJETO DE AVALIAÇÃO:
=== DOCUMENTO SOB AVALIAÇÃO (pr18_implementation_plan.md) ===\n# Plano de Implementação — PR-18 (Handoff 045 / T3)

**PR:** PR-18  
**Título:** `test(content): validação de esquema no lugar de grep em Markdown`  
**Escopo:** Qualidade de conteúdo, catálogo de ferramentas, integridade de links e robustez do lexer.  
**Linha de Base:** Commit `71de82c` (58/58 testes PASS, CI 4/4 verde no PR-19c).

---

## 1. Objetivos & Critérios de Aceite (Handoff 045 §4)

1. **Substituição de Greps Frágeis:** Substituir os `grep -q '<texto>'` estruturais de [run-all-tests.sh:142–165](clearer-engineering/tests/run-all-tests.sh#L142-L165) por asserções em código Python sobre a estrutura real analisada (frontmatter e cabeçalhos Markdown).
2. **Validação de Esquema de Frontmatter YAML:** Garantir que todo `agents/*/agent.md`, `skills/*/SKILL.md` e `profiles/clearer-harness.agent.md` possua frontmatter válido com `name` e `description` preenchidos e com `name` aderente à convenção do diretório.
3. **Catálogo Versionado de Ferramentas com Evidência:** Criar `clearer-engineering/config/tool_catalog.json`. Toda ferramenta declarada em `tools:` deve constar no catálogo com apontamento para arquivo físico de evidência existente.
4. **Resolução de Skills `/nome`:** Toda menção a `/nome` de skill nos perfis e agentes deve corresponder a um arquivo físico existente em `skills/<nome>/SKILL.md`.
5. **Resolução de Links Relativos em Markdown:** Todo link relativo (`./...` e `../...`) em `clearer-engineering/**/*.md`, `README*.md` e `CHANGELOG.md` deve resolver para um arquivo físico existente.
6. **Fuzzing Determinístico do Lexer (Semente 1337):** Criar `clearer-engineering/tests/test_lexer_fuzz.py` executando 2.000 composições determinísticas de comandos seguros e destrutivos com separadores e aspas, garantindo o invariante: sob `--env production`, nenhuma cadeia com segmento destrutivo pode resultar em `allow`.
7. **Correção de Achados Reais:** Corrigir os 24 links quebrados identificados nos READMEs do plugin (`./docs/...` -> `../docs/...`).
8. **Falsificabilidade Comprovada por Mutação:** Provar que uma mutação no frontmatter/links ou no lexer reprova os testes imediatamente indicando o arquivo, linha ou comando mínimo.

---

## 2. Componentes e Arquitetura da Solução

### 2.1. Catálogo Versionado de Ferramentas (`clearer-engineering/config/tool_catalog.json`)
Catálogo estrito contendo as ferramentas autorizadas e suas fontes de evidência física comprovada:
- **Ferramentas Antigravity CLI/IDE (`agy`):**
  - `run_command`: evidência em `docs/temp_implementation/evidence/host-probe/agy/20260925T040852Z/runs/E1-r1/invocations.jsonl`
  - `write_to_file`: evidência em `docs/temp_implementation/evidence/host-probe/agy/20260927T034219Z/runs/E11-allow-write-padrao/invocations.jsonl`
  - `replace_file_content`: evidência em `docs/temp_implementation/evidence/pr10-evidence.md` e matcher em `hooks.json`
  - `multi_replace_file_content`: evidência em `docs/temp_implementation/evidence/pr10-evidence.md` e matcher em `hooks.json`
  - Ferramentas nativas do host (`view_file`, `list_dir`, `grep_search`, `find_by_name`, `search_web`, `read_url_content`, `manage_task`, `schedule`, `generate_image`, `ask_question`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `send_message`): registradas com declaração canônica comprovada no inventário do host `docs/temp_implementation/evidence/host-probe/agy/tools/inventory.json`.
- **Ferramentas Claude Code (`claude`):**
  - `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`: registradas com evidência em `docs/temp_implementation/evidence/host-probe/claude/20260925T033645Z/e0_help.txt` e `summary.md`.

### 2.2. Teste de Esquema (`clearer-engineering/tests/test_content_schema.py`)
Implementado em Python com `unittest` e registrado na suíte do `run-all-tests.sh`:
- **Classe `TestFrontmatterSchema`**:
  - Valida YAML de todos os agentes em `agents/*/agent.md` (`name == f"ceh-{dir_name}"`, `description` não vazio).
  - Valida YAML de todas as skills em `skills/*/SKILL.md` (`name == dir_name`, `description` não vazio).
  - Valida perfil em `profiles/clearer-harness.agent.md` (`name == "clearer-harness"`, `description` não vazio).
- **Classe `TestToolCatalogIntegrity`**:
  - Para cada ferramenta declarada nos frontmatters, verifica se existe no catálogo.
  - Para cada entrada no catálogo, verifica se o `evidence_path` aponta para um arquivo existente.
- **Classe `TestSkillReferences`**:
  - Localiza citações a `/skill-name` e valida se `skills/<skill-name>/SKILL.md` existe fisicamente.
- **Classe `TestMarkdownRelativeLinks`**:
  - Escaneia todos os links relativos em `clearer-engineering/**/*.md`, `README*.md` e `CHANGELOG.md`.
  - Ignora links externos (`http://`, `https://`, `mailto:`, `file://`) e âncoras puras (`#...`).
  - Valida a existência física do arquivo de destino (removendo âncora `#...` de subseção se houver).
- **Classe `TestContentStructure` (Substituição dos greps antigos)**:
  - Validação de que `clearer-bugfix/SKILL.md` possui as 5 seções dos Gates (`Gate 0 — TRIAGE`, `Gate 1 — REPRODUCE`, `Gate 2 — ISOLATE`, `Gate 3 — ROOT CAUSE`, `Gate 4 — FIX & HARDEN`).
  - Validação de que `learned-lesson/SKILL.md` possui seção `Learned Lesson Engine v2.0` e suporte a `dev-memory`.
  - Validação de que `ceh-investigator` orienta o uso da `Matriz de Hipóteses Falsificáveis`.
  - Validação de que `ceh-reviewer` referencia `clearer-bugfix` e o detector de regressões.
  - Validação de que `clearer-adhd` possui `Lead with Action` e `Break-Rules`.

### 2.3. Teste de Fuzz do Lexer (`clearer-engineering/tests/test_lexer_fuzz.py`)
- Semente fixa obrigatória: `random.Random(1337)`.
- Casos: 2.000 iterações determinísticas.
- Segmentos seguros: comandos de leitura e inspeção (`ls -la`, `git status`, `pwd`, `cat README.md`, `git log -n 5`, etc.).
- Segmentos destrutivos: comandos com risco de mutação (`git reset --hard`, `git clean -fd`, `rm -rf /tmp/teste`, `git push --force`, `drop database`, `truncate table`, `terraform destroy`, `kubectl delete`).
- Conectores e separadores: `;`, `&&`, `||`, `|`, quebra de linha `\n`, parênteses de subshell `( ... )`, além de variações com aspas simples `'...'` e duplas `"..."`.
- **Invariante Testado:** Sob ambiente `production` (`explicit_env="production"` ou `APP_ENV=production`), se houver qualquer segmento destrutivo na composição, o resultado do Safety Gate **DEVE ser `deny`**.
- Diagnóstico: Se falhar em qualquer iteração, o teste imprime no log o comando exato mínimo que causou a violação e o tempo total de execução.

---

## 3. Correções Reais do Repositório (Achados)

- **Links Quebrados no Plugin:**
  - `clearer-engineering/README_PT.md`: Linhas 101–110, 183 e 189 apontavam para `./docs/...`, `./evals/...` e `./LICENSE`. Devem ser corrigidos para `../docs/...`, `../evals/...` e `../LICENSE`.
  - `clearer-engineering/README.md`: Linhas 101–110, 183 e 189 com o mesmo ajuste para referências relativas corretas.

---

## 4. Integração no `run-all-tests.sh`

Substituição das linhas antigas [142–165](clearer-engineering/tests/run-all-tests.sh#L142-L165):
```bash
# 6. Content Schema & Structural Integrity (PR-18 / T3)
run_test "Content Schema: Frontmatter, tool catalog, skill links and relative URLs" \
    "python3 '$PLUGIN_DIR/tests/test_content_schema.py'"

run_test "Lexer Fuzz: Deterministic property testing with seed 1337 (2,000 cases)" \
    "python3 '$PLUGIN_DIR/tests/test_lexer_fuzz.py'"
```
- A suíte passará de 58 para **60 testes determinísticos**.

---

## 5. Falsificabilidade por Mutação (AS2)

Realizada em sandbox/clone isolado:
1. **Mutação 1 (Esquema):** Remover temporariamente o campo `description` de uma skill e incluir um link quebrado `[link](./inexistente.md)`.
   - *Comportamento esperado:* `test_content_schema.py` falha citando o arquivo e linha exatos.
2. **Mutação 2 (Lexer Fuzz):** Desativar temporariamente a divisão pelo operador `||` no lexer.
   - *Comportamento esperado:* `test_lexer_fuzz.py` falha reportando o comando mínimo que resultou em falso `allow`.

---

## 6. Sequência de Execução

1. Criar o inventário de evidências de ferramentas em `docs/temp_implementation/evidence/host-probe/agy/tools/inventory.json`.
2. Criar `clearer-engineering/config/tool_catalog.json`.
3. Corrigir os 24 links relativos nos READMEs do plugin.
4. Implementar `clearer-engineering/tests/test_content_schema.py`.
5. Implementar `clearer-engineering/tests/test_lexer_fuzz.py`.
6. Atualizar `clearer-engineering/tests/run-all-tests.sh` e rodar a suíte (60/60 PASS).
7. Executar a prova de falsificabilidade das duas suítes em sandbox isolado.
8. Atualizar o CHANGELOG.md (`[Unreleased]`).
9. Emitir o Certificado de Voo do Safety Gate via `test-runner.sh`.
10. Submeter o commit do PR-18, aguardar e comprovar 4/4 jobs verdes no GitHub Actions.\n\n=== INSTRUÇÃO ESPECÍFICA DO DEVELOPER ===\nAvaliar criticamente o Plano de Implementação do PR-18 (validação de esquema de Markdown, tool_catalog.json e fuzz do lexer com semente 1337). Identificar riscos, blindagens adicionais, refinamentos arquiteturais e oportunidades para elevar o nível de excelência de engenharia sob a ótica de cada especialista.\n\n

INSTRUÇÕES DO PROTOCOLO SYSTEM ONE:
1. Avalie o material estritamente sob o ponto de vista da sua delegação técnica.
2. Não produza enrolação, preâmbulos protocolares ou elogios.
3. Responda obrigatoriamente preenchendo o contrato de saída abaixo:

--- CONTRATO DE SAÍDA MANDATÓRIO ---
VEREDITO: [HOMOLOGADO | RESSALVAS | REJEITADO]
CERTEZA: [número entre 0.0 e 1.0 fundamentado em evidência física]
ANALISE_ESPECIALIZADA:
<análise técnica cirúrgica detalhando pontos fortes ou vulnerabilidades sob sua ótica>
RISCOS_IDENTIFICADOS:
<lista de riscos reais ou 'Nenhum risco observado'>
RECOMENDACAO_FINAL:
<ação prática direta e verificável recomendada>
------------------------------------
codex
Vou conferir o lexer e os testes existentes para avaliar se o invariante de fuzz proposto é realmente demonstrável e se os casos gerados exercitam suas fronteiras.
hook: PreToolUse
hook: PreToolUse Completed
exec
/usr/bin/zsh -lc 'cat ~/.codex/plugins/cache/mwguerra-codex/scribe/0.1.0/skills/documentation-discipline/SKILL.md && rg -n "lexer|Safety Gate|explicit_env|production|run-all-tests" clearer-engineering' in .
 succeeded in 0ms:
---
name: documentation-discipline
description: >
  Use whenever you make or discover a decision, fix a non-trivial error, change
  architecture or what the system does, or defer something undecided — and before
  acting on any task. The canonical contract for how docs/ works: docs/ is the
  single source of truth (read it first, write it after), its truth is typed and
  verified, and stale docs are always a defect. Adopted by every plugin, command,
  and agent that reads or writes project state.
---

# documentation-discipline — the docs/ single source of truth

`docs/` is the **living single source of truth (SSOT)** for a project. Everything the
suite knows about a project — what it is, how it's built, why it was built that way, what
broke and how it was fixed, and where it's going — lives in `docs/`. This skill is the
contract every plugin, command, and agent adopts: **read `docs/` before you act, write it
after, and treat anything stale as a defect.**

If it's in the docs, it is the absolute truth — but "truth" is **typed** (§3), and the
only way docs stay true is **verification** (§5), never trust in an async writer.

## 1. docs/ is the single source of truth — read-first rule

Before acting on ANY task, read:

1. **`docs/STATUS.md`** — what the system is and does right now, the current focus, health.
2. **the relevant `docs/architecture/`** — the boundaries, data model, and interfaces your
   change touches (owned by the architect plugin).
3. **the open `docs/adr/`** — accepted decisions of record that constrain your change.

You do not start work, plan, design, or decompose from memory or from the prompt alone.
`docs/` is the shared read-only context all plugins read; each plugin still keeps its own
store, but the project's *state of truth* is here. If `docs/` does not exist yet, it is
bootstrapped first (`scribe:init`), never improvised per-task.

## 2. The canonical docs/ layout

The full layout, the "when to write what" table, and the ingestion rules live in
**`references/docs-layout.md`**. In brief:

| Path | Holds | Owner |
|---|---|---|
| `docs/README.md` | Index + "this is the SSOT" statement + how to navigate | scribe |
| `docs/STATUS.md` | Current-state snapshot: components, what it does now, focus, health — concise, links to detail | scribe |
| `docs/architecture/` | System design: boundaries, data model, interfaces, seams + extraction triggers | architect |
| `docs/adr/NNNN-title.md` | One decision per file | scribe (any plugin appends) |
| `docs/incidents/NNNN-title.md` | One postmortem per file | scribe |
| `docs/roadmap.md` | Future/planned work + triggers | scribe |
| `docs/open-questions.md` | Undecided, each with an owner | scribe |

`docs/` is an **umbrella** that INGESTS and LINKS, never duplicates:

- `docs/prd/` — requirements, owned by **prd-builder**.
- `docs/deep-analysis/` — audit findings, owned by **maestro**.
- `docs/superpowers/specs/` — specs.

Reference these by link from STATUS / architecture / ADRs. Never copy their content in.

## 3. The typed truth model (the heart)

"If it's in the docs it's the absolute truth" — but the *kind* of truth differs by content
type, so the right check is applied per type. **Stale is ALWAYS a defect**, whatever the
type.

| Content | Lives in | Truth means | Verified by |
|---|---|---|---|
| **System facts** | `STATUS.md`, `architecture/` | **matches the code** | adversarial doc-vs-code reading; any drift = defect |
| **Decisions** | `adr/` | **decision of record** | currency (superseded ones marked) + consistency with code |
| **Incidents** | `incidents/` | **accurate postmortem** | anchored to the real fix in the code |
| **Intent / future** | `roadmap.md`, `open-questions.md` | **current + owned + non-stale** | shipped item → moved to STATUS; decided question → became an ADR |

Two locked rules carry the most weight:

- **System facts drift = defect.** If `STATUS.md` or `architecture/` says something the code
  no longer does, the doc is wrong and must be fixed. The code is the referent.
- **An accepted ADR the code contradicts is FLAGGED for human resolution — neither
  auto-wins.** The code may have violated the decision (a bug/regression), or the decision
  may be stale (the ADR should be superseded). A human decides which. The verifier surfaces
  the conflict; it does not silently rewrite the ADR or excuse the code.

Staleness is cross-document, not just per-doc: a **shipped roadmap item** must move to
`STATUS.md`; a **decided open-question** must become an ADR; a **superseded decision** must
be marked. Leaving these in place is a defect the verifier flags.

## 4. The obligation contract

Every plugin, command, skill, and agent adopts this. **After doing work**, the matching doc
is updated as part of "done" — not optionally, not later:

| You did this | You owe this doc |
|---|---|
| Made / changed a decision | New or updated **ADR** (`docs/adr/`), including a **trigger to revisit** |
| Fixed a non-trivial error | **Incident** (`docs/incidents/`): symptom, root cause + WHY, where/how fixed, why that fix, prevention |
| Changed the architecture | **`docs/architecture/`** update **and** an ADR for the decision |
| Changed what the system is / does | **`STATUS.md`** |
| Deferred / left something undecided | **`open-questions.md`** (with an owner) — or **`roadmap.md`** if it's planned |

**Keep docs LEAN:**

- `STATUS.md` stays concise — a snapshot with **links** to detail, never a dumping ground.
- ADRs and incidents are **atomic** — one decision / one postmortem per file.
- **Link to** `docs/prd/` and `docs/deep-analysis/`, never copy them.

A doc that is verbose, duplicated, or out of date is a defect just as much as a missing one.

## 5. Capture → curate → verify

Trust comes from VERIFICATION, not from trusting an async writer. Three tiers, so docs never
block work yet never drift:

1. **Capture** (sync, cheap) — **the moment** you make a decision, hit a non-trivial error, or
   fix one while working, append a one-line breadcrumb to `docs/.scribe/capture.log` — do not
   wait for the curate step. A decision or error is *semantic* (only the working agent knows it
   happened), so capture is an **obligation of every agent that adopts this skill**, not
   something a hook can do for you. Append it with:
   ```bash
   mkdir -p docs/.scribe
   echo "$(date -Iseconds) | <decision|error|fix|assumption|review> | <one line: what + why>" >> docs/.scribe/capture.log
   ```
   The **type** is a short tag the curator interprets — what each becomes: `decision` → an ADR
   (and `STATUS.md` if it shipped behavior); `error`/`fix` → an incident; `assumption` → an
   `open-questions.md` entry; `review` → a `STATUS.md` note that an audit/review ran and how many
   findings remain open (its *applied* outcomes return later as `decision` breadcrumbs). This is a
   fast, append-only breadcrumb trail (not polished docs) — the raw material the curate step
   consolidates with full context.
2. **Curate** (async, with full context) — at session end (a `Stop` hook) or on
   `scribe:sync`, the **`doc-curator`** agent — which has the real diff, decisions, and
   errors — consolidates the capture log into accurate ADRs, incident postmortems, and an
   updated `STATUS.md`, following the obligation contract (§4).
3. **Verify** (the "absolute truth" guarantee) — the **`doc-verifier`** agent adversarially
   checks every doc claim against the typed truth model (§3) **plus cross-doc staleness**:
   doc-vs-code drift, superseded-but-unmarked ADRs, shipped roadmap items still in the
   roadmap, answered open-questions, and accepted ADRs the code now contradicts. The
   verifier **references maestro's `adversarial-verify` standard** — refute-first, fresh
   independent eyes, evidence over assertion, atomic checks, multi-vote — and adds the
   typed-truth-model checklist as its domain layer.

**Enforcement is advisory + a verification gate**, matching maestro's advisory-hook
philosophy: drift is flagged **loudly as a defect**, but it does not hard-block work. The
discipline is upheld by making the cost of skipping it visible, not by stopping the line.

## Relationship to other processes

- **maestro** is the canonical home of adversarial verification; `doc-verifier` embodies its
  `adversarial-verify` standard and adds the typed-truth checklist. maestro is untouched.
- **architect** owns `docs/architecture/` and writes ADRs through this contract.
- **prd-builder** owns `docs/prd/`; **maestro** owns `docs/deep-analysis/`; both are ingested
  by link, never copied.
- **scribe:init** bootstraps `docs/` (brownfield: via a maestro `deep-analysis` pass, so the
  baseline is reverse-engineered from real code and therefore verifiable = true).

## The mantra

**docs/ is the single source of truth: read it before you act, write it after, and a stale
doc is a defect — caught not by trusting the writer, but by verifying every claim against
the code.**
clearer-engineering/README.md:20:The **CLEARER Engineering Harness (CEH)** is a production-grade software engineering harness natively engineered for **Google Antigravity** (IDE and `agy` CLI).
clearer-engineering/README.md:23:- **Environment Awareness & Granular Safety Gate**: Proactive safety policies tailored to `DEV` (freedom with local safety), `HOMOLOGACAO` (2-step explicit alerts), and `PRODUCAO` (destructive actions strictly denied).
clearer-engineering/README.md:58:## 🛡️ Environment Safety Tiers (Safety Gate)
clearer-engineering/README.md:64:| **`PRODUCAO`** | Branch `main`/`master`, `APP_ENV=production`. | 🔴 **`DENY`** | **STRICTLY PROHIBITED**: Destructive database commands, force push, or bulk deletions are immediately rejected. |
clearer-engineering/README.md:82:   - **Evasion-Immune Safety Gate**: `safety-gate.py` strips `rtk` prefixes before evaluating rules to enforce strict protection across production and staging.
clearer-engineering/README.md:108:| 🛡️ [**Safety Gate Guide**](./docs/safety_gate.md) | How `PreToolUse` hooks intercept destructive commands with `DENY > ASK > ALLOW`. |
clearer-engineering/README.md:134:| **`HIGH`** | Core auth, permissions, payments, concurrency, destructive migrations, production scripts. | Deep Investigation → Specialized Subagents → Adversarial Review → Formal Audit → Human Checkpoint. |
clearer-engineering/README.md:142:2. **Destructive Risk (Environment-Aware Safety Gate)**:
clearer-engineering/README.md:156:   - `main`: Protected production for stable deploy (`DENY` - off limits).
clearer-engineering/README.md:161:   - `main`: Protected production for direct releases (`DENY`).
clearer-engineering/README.md:174:./clearer-engineering/tests/run-all-tests.sh
clearer-engineering/rules/core-engineering.md:19:O agente opera de ponta a ponta e só transfere o controle ao desenvolvedor (handoff) caso ocorra ambiguidade de requisitos, disparo do Safety Gate, falha de teste após auto-reparo ou escopo classificado como HIGH.
clearer-engineering/rules/AGENTS.md:12:| Ambiente | Definição & Evidência | Rigor de Segurança (Safety Gate) |
clearer-engineering/rules/AGENTS.md:16:| **`PRODUCAO`** | Ambiente produtivo, branch `main`/`master`/`production`, `APP_ENV=production`. | **Fora de Cogitação (`DENY` Absoluto)**: Comandos destrutivos em banco, force push ou deleções em massa são sumariamente rejeitados. |
clearer-engineering/rules/AGENTS.md:22:   - **`git push` em Projetos com CI (Zero-Tolerance Pipeline Red)**: Em projetos que possuam esteira de CI (`.github/workflows/`, `.gitlab-ci.yml`), é expressamente proibido disparar `git push` para qualquer branch remota (`dev`, `staging`, `main`) sem a execução prévia da **suíte canônica integral exigida pela CI com exit code 0 comprovado (`OBSERVED`) no mesmo commit hash local**. Checagens parciais (somente linters ou arquitetura isolada) NUNCA autorizam o push. O Safety Gate bloqueia tentativas sem certificado de teste recente (`DENY - Pre-Push CI Gate`).
clearer-engineering/rules/AGENTS.md:133:- **Segurança de Ambiente**: Comandos destrutivos interceptados em `HOMOLOGACAO` continuam exigindo os **2 ALERTAS EXPLÍCITOS** de Safety Gate. Em `PRODUCAO`, o `DENY` continua incondicional.
clearer-engineering/rules/AGENTS.md:168:2. **Risco Destrutivo (Safety Gate)**:
clearer-engineering/scripts/hook_context.py:8:Enforces Invariant 7 (fail-closed on ambiguity): unresolved context escalates to production.
clearer-engineering/scripts/hook_context.py:25:        (target_path, explicit_env, force_deny_push)
clearer-engineering/scripts/hook_context.py:27:        - explicit_env: 'production' if unresolved or non-existent, otherwise None.
clearer-engineering/scripts/hook_context.py:57:        return None, "production", True
clearer-engineering/scripts/hook_context.py:67:            return None, "production", True
clearer-engineering/scripts/hook_context.py:70:        return None, "production", True
clearer-engineering/scripts/hook_context.py:161:    target_dir, explicit_env, force_deny_push = resolve_hook_target(payload)
clearer-engineering/scripts/hook_context.py:175:        decision, reason, _, _ = evaluate_command_fn(cmd_line, explicit_env)
clearer-engineering/scripts/hook_context.py:238:    target_dir, explicit_env, _ = resolve_hook_target(payload)
clearer-engineering/skills/clearer-feature/SKILL.md:20:> **Diretriz de Autonomia:** Conduza os 8 passos em uma única invocação fluida quando os requisitos estiverem definidos. Apenas pause o fluxo caso ocorra ambiguidade de requisitos sem resposta no repositório ou comando bloqueado pelo Safety Gate.
clearer-engineering/skills/conselho-seniores/SKILL.md:36:| **`agy`** | Google Antigravity | **Harness & Safety Gate** | Integridade das regras do CEH, governança de ambientes (`DEV`/`HML`/`PRD`), blast radius mínimo e bloqueio de comandos destrutivos. |
clearer-engineering/scripts/doc-audit.py:85:        suite_script = repo_root / "clearer-engineering/tests/run-all-tests.sh"
clearer-engineering/scripts/doc-audit.py:106:                f"Testes órfãos detectados: {orphan_tests} não estão citados em run-all-tests.sh."
clearer-engineering/scripts/ceh_core/__init__.py:1:"""ceh_core - Módulos internos reutilizáveis do Safety Gate do CEH."""
clearer-engineering/scripts/ceh_core/__init__.py:2:from .lexer import resolve_command_head, substitute_positional_args
clearer-engineering/README_PT.md:23:- **Identificação Prévia de Ambiente & Rigores Granulares**: Safety Gate ativo com políticas diferenciadas para `DEV` (liberdade com salvaguarda local), `HOMOLOGACAO` (confirmação com 2 alertas) e `PRODUCAO` (comandos destrutivos sumariamente bloqueados - fora de cogitação).
clearer-engineering/README_PT.md:58:## 🛡️ Níveis de Rigor por Ambiente (Safety Gate)
clearer-engineering/README_PT.md:64:| **`PRODUCAO`** | Branch `main`/`master`, `APP_ENV=production`. | 🔴 **`DENY`** | **FORA DE COGITAÇÃO**: Comandos destrutivos em banco, force push ou exclusões em massa são sumariamente rejeitados. |
clearer-engineering/README_PT.md:108:| 🛡️ [**Guia do Safety Gate**](./docs/safety_gate.md) | Como o hook `PreToolUse` intercepta comandos destrutivos com `DENY > ASK > ALLOW`. |
clearer-engineering/README_PT.md:142:2. **Risco Destrutivo (Safety Gate Granular por Ambiente)**:
clearer-engineering/README_PT.md:174:./clearer-engineering/tests/run-all-tests.sh
clearer-engineering/scripts/ceh_core/interpreters.py:16:from .lexer import resolve_command_head
clearer-engineering/scripts/ceh_core/interpreters.py:206:            sub_res = eval_fn(cmd, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
clearer-engineering/scripts/ceh_core/interpreters.py:228:    if env == "production":
clearer-engineering/skills/clearer/SKILL.md:62:   - Comando interceptado pelo Safety Gate (`DENY` ou `ASK`);
clearer-engineering/scripts/detect-project.sh:24:        if [[ "$VAL" =~ (prod|production|prd|live) ]]; then
clearer-engineering/scripts/detect-project.sh:25:            DETECTED_ENV="production"
clearer-engineering/scripts/detect-project.sh:42:    if [[ -f ".env.production" ]]; then
clearer-engineering/scripts/detect-project.sh:43:        DETECTED_ENV="production"
clearer-engineering/scripts/detect-project.sh:44:        ENV_EVIDENCE="File .env.production present"
clearer-engineering/scripts/detect-project.sh:53:                if [[ "$VAL" =~ (prod|production|prd|live) ]]; then
clearer-engineering/scripts/detect-project.sh:54:                    DETECTED_ENV="production"
clearer-engineering/scripts/detect-project.sh:76:        if [[ "$BRANCH_LOWER" =~ ^(main|master|production|prod)$ ]]; then
clearer-engineering/scripts/detect-project.sh:77:            DETECTED_ENV="production"
clearer-engineering/scripts/detect-project.sh:78:            ENV_EVIDENCE="Git branch '${CURRENT_BRANCH}' (canonical production branch)"
clearer-engineering/scripts/detect-project.sh:97:    production)
clearer-engineering/scripts/detect-project.sh:98:        echo "Safety Gate Policy:   PRODUÇÃO STRICT (Comandos destrutivos são FORA DE COGITAÇÃO - DENY)"
clearer-engineering/scripts/detect-project.sh:101:        echo "Safety Gate Policy:   HOMOLOGAÇÃO GATED (Exige confirmação com 2 ALERTAS + Backup e Rollback)"
clearer-engineering/scripts/detect-project.sh:104:        echo "Safety Gate Policy:   DESENVOLVIMENTO (Destrutivos permitidos com prontidão de backup/rollback)"
clearer-engineering/scripts/ceh_core/rm.py:189:        if env == "production":
clearer-engineering/scripts/ceh_core/rm.py:207:        if env == "production":
clearer-engineering/scripts/ceh_core/lexer.py:2:lexer.py - Analisador léxico e normalizador de pipelines de shell do CEH.
clearer-engineering/scripts/ceh_core/rules.py:2:rules.py - Padrões de segurança declarativos do Safety Gate do CEH.
clearer-engineering/scripts/safety-gate.py:30:from ceh_core.lexer import (
clearer-engineering/scripts/safety-gate.py:103:            return True, None, [], None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
clearer-engineering/scripts/safety-gate.py:109:            return True, None, [], None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
clearer-engineering/scripts/safety-gate.py:144:    if env == "production":
clearer-engineering/scripts/safety-gate.py:239:    explicit_env: str | None = None,
clearer-engineering/scripts/safety-gate.py:274:                explicit_env=explicit_env,
clearer-engineering/scripts/safety-gate.py:297:                        explicit_env=explicit_env,
clearer-engineering/scripts/safety-gate.py:310:            explicit_env=explicit_env,
clearer-engineering/scripts/safety-gate.py:367:        if target_repo and explicit_env is None:
clearer-engineering/scripts/safety-gate.py:368:            sub_env, sub_env_evidence = detect_environment(explicit_env=None, target_dir=target_repo)
clearer-engineering/scripts/safety-gate.py:412:    if is_git_push and env in ("production", "staging"):
clearer-engineering/scripts/safety-gate.py:429:    explicit_env: str | None = None,
clearer-engineering/scripts/safety-gate.py:442:            "development" if explicit_env is None else explicit_env,
clearer-engineering/scripts/safety-gate.py:450:    env, env_evidence = detect_environment(explicit_env, cmd_normalized, target_dir=base_cwd)
clearer-engineering/scripts/safety-gate.py:476:                sub_inner, explicit_env=explicit_env, base_cwd=current_cwd,
clearer-engineering/scripts/safety-gate.py:494:            new_env, new_ev = detect_environment(explicit_env=explicit_env, target_dir=current_cwd)
clearer-engineering/scripts/safety-gate.py:499:        sub_eval_env, sub_eval_ev = detect_environment(explicit_env=explicit_env, cmd_line=sub, target_dir=eval_cwd)
clearer-engineering/scripts/safety-gate.py:501:            repo_env, repo_ev = detect_environment(explicit_env=None, target_dir=tgt_repo)
clearer-engineering/scripts/safety-gate.py:509:        if (unresolved_cd or is_unres) and ENV_SEVERITY.get(effective_env, 0) < ENV_SEVERITY.get("production", 0):
clearer-engineering/scripts/safety-gate.py:510:            effective_env, effective_ev = "production", "Incerteza: destino não resolvível (Invariante 7)"
clearer-engineering/scripts/safety-gate.py:526:                explicit_env=explicit_env,
clearer-engineering/scripts/safety-gate.py:599:    parser = argparse.ArgumentParser(description="CEH Safety Gate Command Checker")
clearer-engineering/scripts/safety-gate.py:601:    parser.add_argument("--env", type=str, default=None, help="Explicit environment override (development|staging|production)")
clearer-engineering/scripts/safety-gate.py:605:        decision, reason, env, use_case = evaluate_command(args.check, explicit_env=args.env)
clearer-engineering/scripts/ceh_core/find.py:13:from .lexer import resolve_command_head
clearer-engineering/scripts/ceh_core/find.py:111:                    sub_res = eval_fn(sub_cmd_str, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
clearer-engineering/scripts/ceh_core/find.py:170:        if env in ("production", "staging"):
clearer-engineering/scripts/ceh_core/find.py:174:    if env == "production":
clearer-engineering/scripts/ceh_core/git.py:2:git.py - Analisador por tokens de comandos Git sensíveis para o Safety Gate do CEH.
clearer-engineering/scripts/conselho-seniores.sh:19:#   - agy    (Antigravity)  -> Harness, Safety Gate & Invariantes de Ambiente
clearer-engineering/scripts/ceh_core/environment.py:6:PROD_SEGMENTS = set(["prod", "production", "prd", "live"]) | {"preprod"}
clearer-engineering/scripts/ceh_core/environment.py:8:ENV_SEVERITY = {"development": 0, "staging": 1, "production": 2}
clearer-engineering/scripts/ceh_core/environment.py:19:    """Normalizes environment string to: 'production', 'staging', or 'development'."""
clearer-engineering/scripts/ceh_core/environment.py:21:    if any(t in segments for t in PROD_SEGMENTS): return "production"
clearer-engineering/scripts/ceh_core/environment.py:28:    if any(s in ("main", "master", "production", "prod") for s in segments) or any(s in PROD_SEGMENTS for s in segments): return "production"
clearer-engineering/scripts/ceh_core/environment.py:67:            if v_env in ("production", "staging"): found.append((v_env, f"Explicit assignment {k}={v}"))
clearer-engineering/scripts/ceh_core/environment.py:68:            elif k.lower() in ("git_dir", "git_work_tree") and (is_unresolved_cd_target(v) or normalize_env(v) == "production"):
clearer-engineering/scripts/ceh_core/environment.py:69:                found.append(("production", f"Explicit git target {k}={v}"))
clearer-engineering/scripts/ceh_core/environment.py:79:                    if is_unresolved_cd_target(arg_c) or normalize_env(arg_c) == "production": found.append(("production", f"Explicit env {c}"))
clearer-engineering/scripts/ceh_core/environment.py:82:                    if is_unresolved_cd_target(arg_c) or normalize_env(arg_c) == "production": found.append(("production", f"Explicit env {c}"))
clearer-engineering/scripts/ceh_core/environment.py:86:                    if v_env in ("production", "staging"): found.append((v_env, f"Explicit env assignment {k}={v}"))
clearer-engineering/scripts/ceh_core/environment.py:87:                    elif k.lower() in ("git_dir", "git_work_tree") and (is_unresolved_cd_target(v) or normalize_env(v) == "production"):
clearer-engineering/scripts/ceh_core/environment.py:88:                        found.append(("production", f"Explicit env git target {k}={v}"))
clearer-engineering/scripts/ceh_core/environment.py:99:                    if v_env in ("production", "staging"): found.append((v_env, f"Explicit variable flag {tok} {arg}"))
clearer-engineering/scripts/ceh_core/environment.py:107:            if v_env in ("production", "staging"):
clearer-engineering/scripts/ceh_core/environment.py:113:            if cd_env in ("production", "staging"): found.append((cd_env, f"Working directory context {tok} {target}"))
clearer-engineering/scripts/ceh_core/environment.py:114:            elif is_unresolved_cd_target(target): found.append(("production", f"Unresolved cd target {tok} {target} (Invariante 7)"))
clearer-engineering/scripts/ceh_core/environment.py:180:        if f_env in ("production", "staging"): context_env, is_persistent = f_env, True
clearer-engineering/scripts/ceh_core/environment.py:188:                if f_env in ("production", "staging"): context_env, is_persistent = f_env, True; break
clearer-engineering/scripts/ceh_core/environment.py:231:    explicit_env: str | None = None,
clearer-engineering/scripts/ceh_core/environment.py:236:    if explicit_env: return normalize_env(explicit_env), f"Explicit parameter (--env {explicit_env})"
clearer-engineering/scripts/ceh_core/environment.py:251:                if (d / ".env.production").is_file(): context_env, context_evidence = "production", f"Configuration file {d / '.env.production'}"; break
clearer-engineering/scripts/ceh_core/environment.py:268:        if any(s in ["main", "master", "production", "prod"] for s in segments) or any(s in PROD_SEGMENTS for s in segments):
clearer-engineering/scripts/ceh_core/environment.py:269:            b_env, b_ev = "production", f"Git branch '{branch}' (canonical production branch)"
clearer-engineering/skills/clearer-adhd/SKILL.md:64:1. **Safety Gates em `HOMOLOGACAO` e `PRODUCAO`**:
clearer-engineering/tests/test_cert_protection.py:68:        envs = ["development", "staging", "production"]
clearer-engineering/tests/test_cert_protection.py:71:                dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_cert_protection.py:94:            dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_cert_protection.py:111:            dec, reason, _, _ = safety_gate.evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_cert_protection.py:131:            dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/run-e2e-simulation.sh:8:# 2. Safety Gate Hook PreToolUse Pipeline (DENY, ASK, ALLOW & RTK Evasion Immunity)
clearer-engineering/tests/run-e2e-simulation.sh:115:# PHASE 2: Safety Gate Hook & RTK Evasion Immunity (PreToolUse)
clearer-engineering/tests/run-e2e-simulation.sh:117:log_header "PHASE 2: Safety Gate PreToolUse & RTK Evasion Immunity (E2E)"
clearer-engineering/tests/run-e2e-simulation.sh:133:                log_ok "Safety Gate Check: '$cmd' [$env_var] -> $decision ($extra_check)"
clearer-engineering/tests/run-e2e-simulation.sh:135:                log_error "Safety Gate Check: '$cmd' returned $decision but missed '$extra_check'"
clearer-engineering/tests/run-e2e-simulation.sh:138:            log_ok "Safety Gate Check: '$cmd' [$env_var] -> $decision"
clearer-engineering/tests/run-e2e-simulation.sh:141:        log_error "Safety Gate Check: '$cmd' [$env_var] expected '$expected_decision', got '$decision'. Output: $result"
clearer-engineering/tests/run-e2e-simulation.sh:185:test_gate_check "git reset --hard HEAD~1" "production" "deny" "CEH PRODUCTION LOCK"
clearer-engineering/tests/run-e2e-simulation.sh:186:test_gate_check "rtk git reset --hard HEAD~1" "production" "deny" "CEH PRODUCTION LOCK"
clearer-engineering/tests/run-e2e-simulation.sh:187:test_gate_check "rtk php artisan migrate:fresh" "production" "deny" "CEH PRODUCTION LOCK"
clearer-engineering/tests/run-e2e-simulation.sh:199:test_gate_check "npm test" "production" "allow"
clearer-engineering/tests/run-e2e-simulation.sh:200:test_gate_check "git status" "production" "allow"
clearer-engineering/tests/run-e2e-simulation.sh:201:test_gate_check "rtk git status" "production" "allow"
clearer-engineering/tests/run-e2e-simulation.sh:284:log_step "5.3 Safety Gate Unit Matrix (including RTK)"
clearer-engineering/tests/run-e2e-simulation.sh:286:log_ok "Safety Gate Unit Matrix passed."
clearer-engineering/tests/run-e2e-simulation.sh:293:bash "$PLUGIN_DIR/tests/run-all-tests.sh" >/dev/null
clearer-engineering/tests/cluster1_acceptance.py:110:    c1 = "rm -rf scratch/cache; php artisan " + "migrate:fresh" + " --env=production"
clearer-engineering/tests/cluster1_acceptance.py:111:    ret, out = run_gate(c1, env="production")
clearer-engineering/tests/cluster1_acceptance.py:116:    c2 = "rm -rf scratch/cache && php artisan " + "migrate:fresh" + " --env=production"
clearer-engineering/tests/cluster1_acceptance.py:117:    ret, out = run_gate(c2, env="production")
clearer-engineering/tests/cluster1_acceptance.py:122:    c3 = "false || rm -rf scratch/cache; php artisan " + "migrate:fresh" + " --env=production"
clearer-engineering/tests/cluster1_acceptance.py:123:    ret, out = run_gate(c3, env="production")
clearer-engineering/tests/cluster1_acceptance.py:128:    c4 = "rm -rf scratch/cache & php artisan " + "migrate:fresh" + " --env=production"
clearer-engineering/tests/cluster1_acceptance.py:129:    ret, out = run_gate(c4, env="production")
clearer-engineering/tests/cluster1_acceptance.py:134:    c5 = "rm -rf scratch/cache; ph''p artisan " + "migrate:fresh" + " --env=production"
clearer-engineering/tests/cluster1_acceptance.py:135:    ret, out = run_gate(c5, env="production")
clearer-engineering/tests/cluster1_acceptance.py:140:    c6 = "p$'h'p artisan " + "migrate:fresh" + " --env=production"
clearer-engineering/tests/cluster1_acceptance.py:141:    ret, out = run_gate(c6, env="production")
clearer-engineering/tests/cluster1_acceptance.py:152:    c8 = 'rm -rf scratch/cache; "php artisan ' + 'migrate:fresh' + ' --env=production'
clearer-engineering/tests/cluster1_acceptance.py:153:    ret, out = run_gate(c8, env="production")
clearer-engineering/tests/cluster1_acceptance.py:158:    c9 = "rm -rf scratch/cache\nphp artisan " + "migrate:fresh" + " --env=production"
clearer-engineering/tests/cluster1_acceptance.py:159:    ret, out = run_gate(c9, env="production")
clearer-engineering/tests/cluster1_acceptance.py:164:    c10 = 'rm -rf scratch/cache "$(php artisan ' + 'migrate:fresh' + ' --env=production)"'
clearer-engineering/tests/cluster1_acceptance.py:165:    ret, out = run_gate(c10, env="production")
clearer-engineering/tests/cluster1_acceptance.py:171:    ret, out = run_gate(c11, env="production")
clearer-engineering/tests/cluster1_acceptance.py:176:    c12 = "php artis\\\nan " + "migrate:fresh" + " --env=production"
clearer-engineering/tests/cluster1_acceptance.py:177:    ret, out = run_gate(c12, env="production")
clearer-engineering/tests/cluster1_acceptance.py:429:    ret, out = run_gate(cmd, env="production", cwd=repo_root)
clearer-engineering/tests/test_git_canonicalization.py:34:    def test_g2_destructive_checkout_variants_in_production(self):
clearer-engineering/tests/test_git_canonicalization.py:44:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:48:    def test_g2_destructive_restore_variants_in_production(self):
clearer-engineering/tests/test_git_canonicalization.py:57:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:62:        decision, reason, env, use_case = evaluate_command("git checkout .", explicit_env="staging")
clearer-engineering/tests/test_git_canonicalization.py:69:        decision, reason, env, use_case = evaluate_command("git checkout .", explicit_env="development")
clearer-engineering/tests/test_git_canonicalization.py:86:            for env in ["development", "staging", "production"]:
clearer-engineering/tests/test_git_canonicalization.py:87:                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:104:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:125:            # Sem explicit_env: detecta a partir do repositório em tmp_dir (main -> production)
clearer-engineering/tests/test_git_canonicalization.py:126:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env=None)
clearer-engineering/tests/test_git_canonicalization.py:127:            self.assertEqual(env, "production", f"Esperado ambiente 'production' detectado em -C, mas obteve '{env}'")
clearer-engineering/tests/test_git_canonicalization.py:144:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_git_canonicalization.py:162:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:176:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:190:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:201:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:223:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:238:            dec_prod, _, _, uc_prod = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:242:            dec_sta, reason_sta, _, _ = evaluate_command(cmd, explicit_env="staging")
clearer-engineering/tests/test_git_canonicalization.py:247:            dec_dev, _, _, _ = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_git_canonicalization.py:262:            for env in ["development", "staging", "production"]:
clearer-engineering/tests/test_git_canonicalization.py:263:                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:275:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:293:            for env in ["development", "staging", "production"]:
clearer-engineering/tests/test_git_canonicalization.py:294:                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:308:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:324:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:333:            for env in ["development", "staging", "production"]:
clearer-engineering/tests/test_git_canonicalization.py:334:                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:351:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:361:            for env in ["development", "staging", "production"]:
clearer-engineering/tests/test_git_canonicalization.py:362:                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:378:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:388:            for env in ["development", "staging", "production"]:
clearer-engineering/tests/test_git_canonicalization.py:389:                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:403:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:421:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:431:            for env in ["development", "staging", "production"]:
clearer-engineering/tests/test_git_canonicalization.py:432:                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:380:    for env in ('development', 'staging', 'production'):
clearer-engineering/tests/test_gate_differential_fuzz.py:381:        dec, reason, env_res, uc = gate.evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:509:            for env in ("development", "staging", "production"):
clearer-engineering/tests/test_gate_differential_fuzz.py:510:                base_dec, base_r, _, base_uc = gate.evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:515:                    w_dec, w_r, _, w_uc = gate.evaluate_command(w_cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:585:            for env in ("development", "staging", "production"):
clearer-engineering/tests/test_gate_differential_fuzz.py:586:                base_dec, base_r, _, base_uc = gate.evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:591:                    p_dec, p_r, _, p_uc = gate.evaluate_command(p_cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:639:            dec, reason, env, uc = gate.evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:35:    def test_s1_production_var_www_dist_denied(self):
clearer-engineering/tests/test_rm_targets.py:37:        decision, reason, env, use_case = evaluate_command("rm -rf /var/www/site/dist", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:41:    def test_s1_production_srv_app_build_denied(self):
clearer-engineering/tests/test_rm_targets.py:43:        decision, reason, env, use_case = evaluate_command("rm -rf /srv/app/build", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:47:    def test_s1_production_opt_prod_app_dist_denied(self):
clearer-engineering/tests/test_rm_targets.py:49:        decision, reason, env, use_case = evaluate_command("rm -rf /opt/prod/app/dist/", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:53:    def test_s1_production_etc_nginx_coverage_denied(self):
clearer-engineering/tests/test_rm_targets.py:55:        decision, reason, env, use_case = evaluate_command("rm -rf /etc/nginx/coverage/", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:59:    def test_s1_production_relative_escaping_cwd_denied(self):
clearer-engineering/tests/test_rm_targets.py:61:        decision, reason, env, use_case = evaluate_command("rm -rf ../../prod-release/dist", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:67:    def test_s1_control_dist_production_allowed(self):
clearer-engineering/tests/test_rm_targets.py:69:        decision, reason, env, use_case = evaluate_command("rm -rf dist/", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:73:    def test_s1_control_dot_build_production_allowed(self):
clearer-engineering/tests/test_rm_targets.py:75:        decision, reason, env, use_case = evaluate_command("rm -rf ./build", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:79:    def test_s1_control_tmp_ceh_x_production_allowed(self):
clearer-engineering/tests/test_rm_targets.py:81:        decision, reason, env, use_case = evaluate_command("rm -rf /tmp/ceh-x", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:85:    def test_s1_control_file_txt_production_allowed(self):
clearer-engineering/tests/test_rm_targets.py:87:        decision, reason, env, use_case = evaluate_command("rm -f a.txt", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:96:        decision, reason, env, use_case = evaluate_command("rm -rf $PWD", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:102:        decision, reason, env, use_case = evaluate_command('rm -rf "$PWD"/*', explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:109:        decision, reason, env, use_case = evaluate_command("rm -rf $OLDPWD", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:114:    def test_s2_unresolved_env_var_oldpwd_production_denied(self):
clearer-engineering/tests/test_rm_targets.py:116:        decision, reason, env, use_case = evaluate_command("rm -rf $OLDPWD", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:133:                "rm -rf $PWD", explicit_env="development", base_cwd=eval_project_dir
clearer-engineering/tests/test_rm_targets.py:153:        decision, reason, env, use_case = evaluate_command("rm -rf /home/user/projeto/build", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:159:        decision, reason, env, use_case = evaluate_command("rm -rf /home/user/projeto/src/old", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:165:        decision, reason, env, use_case = evaluate_command("rm -rf /opt/myapp/cache", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:171:        decision, reason, env, use_case = evaluate_command("rm -rf /var/tmp/ceh-x", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:177:        decision, reason, env, use_case = evaluate_command("rm -rf /usr/local/lib/node_modules/foo", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:186:        decision, reason, env, use_case = evaluate_command("rm -rf //", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:193:        decision, reason, env, use_case = evaluate_command("rm -rf /./", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:200:        decision, reason, env, use_case = evaluate_command("rm -rf ../..", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:206:        decision, reason, env, use_case = evaluate_command("rm -rf ./*", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:213:        decision, reason, env, use_case = evaluate_command("rm -rf ~root", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:220:    def test_r3_production_safe_reason_does_not_contain_env_development(self):
clearer-engineering/tests/test_rm_targets.py:222:        decision, reason, env, use_case = evaluate_command("rm -rf dist/", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:233:        dec_dev, _, _, uc_dev = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="development")
clearer-engineering/tests/test_rm_targets.py:237:        dec_sta, _, _, uc_sta = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="staging")
clearer-engineering/tests/test_rm_targets.py:241:        dec_pro, _, _, uc_pro = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:251:    def test_t1_production_build_parent_src_denied(self):
clearer-engineering/tests/test_rm_targets.py:253:        decision, reason, env, use_case = evaluate_command("rm -rf build/../src", explicit_env="production")
clearer-engineering/tests/test_rm_targets.py:257:    def test_t1_production_coverage_parent_git_denied(self):
clearer-engineering/tests/test_rm_targets.py:259:        decision, reason, env, use_case = evaluate_command("rm -rf coverage/../.git", explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:38:    def test_g1_multitarget_build_and_src_production(self):
clearer-engineering/tests/cluster4_acceptance.py:39:        """G1: rm -rf build/ src/ in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:41:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:44:    def test_g1_multitarget_safe_and_system_dir_production(self):
clearer-engineering/tests/cluster4_acceptance.py:45:        """G1: rm -rf a.txt /var/lib/postgresql in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:47:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:53:    def test_g2_git_checkout_dot_production(self):
clearer-engineering/tests/cluster4_acceptance.py:54:        """G2: git checkout . in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:56:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:59:    def test_g2_git_restore_dot_production(self):
clearer-engineering/tests/cluster4_acceptance.py:60:        """G2: git restore . in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:62:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:65:    def test_g2_git_checkout_dashdash_dot_production(self):
clearer-engineering/tests/cluster4_acceptance.py:66:        """G2: git checkout -- . in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:68:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:74:    def test_g3_git_C_reset_hard_production(self):
clearer-engineering/tests/cluster4_acceptance.py:75:        """G3: git -C . reset --hard in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:77:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:80:    def test_g3_git_no_pager_reset_hard_production(self):
clearer-engineering/tests/cluster4_acceptance.py:81:        """G3: git --no-pager reset --hard in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:83:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:92:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/cluster4_acceptance.py:98:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/cluster4_acceptance.py:104:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/cluster4_acceptance.py:107:    def test_g4_rm_long_flags_root_production(self):
clearer-engineering/tests/cluster4_acceptance.py:108:        """G4: rm --recursive --force / in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:110:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:116:    def test_control_rm_rf_dist_production(self):
clearer-engineering/tests/cluster4_acceptance.py:118:        decision, reason, env, use_case = evaluate_command("rm -rf dist/", explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:122:    def test_control_rm_rf_node_modules_cache_production(self):
clearer-engineering/tests/cluster4_acceptance.py:124:        decision, reason, env, use_case = evaluate_command("rm -rf node_modules/.cache", explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:128:    def test_control_rm_f_a_txt_production(self):
clearer-engineering/tests/cluster4_acceptance.py:130:        decision, reason, env, use_case = evaluate_command("rm -f a.txt", explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:134:    def test_control_rm_rf_dot_build_production(self):
clearer-engineering/tests/cluster4_acceptance.py:136:        decision, reason, env, use_case = evaluate_command("rm -rf ./build", explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:143:    def test_g5_find_delete_root_production(self):
clearer-engineering/tests/cluster4_acceptance.py:144:        """G5: find / -delete in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:146:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:149:    def test_g5_find_exec_rm_production(self):
clearer-engineering/tests/cluster4_acceptance.py:150:        """G5: find . -name x -exec rm {} + in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:152:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:155:    def test_g5_python_shutil_rmtree_production(self):
clearer-engineering/tests/cluster4_acceptance.py:156:        """G5: python3 -c 'import shutil; shutil.rmtree("/srv")' in production must be denied (today: allow)"""
clearer-engineering/tests/cluster4_acceptance.py:158:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:196:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/cluster4_acceptance.py:226:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/run-all-tests.sh:3:# run-all-tests.sh - Comprehensive Test Suite for CLEARER Engineering Harness
clearer-engineering/tests/run-all-tests.sh:52:# 2. Safety Gate Unit & Environment Tests
clearer-engineering/tests/run-all-tests.sh:53:run_test "Safety Gate: Hard block catastrophic 'rm -rf /' (DENY in any env)" \
clearer-engineering/tests/run-all-tests.sh:56:run_test "Safety Gate: Production tier strictly blocks destructive commands (DENY)" \
clearer-engineering/tests/run-all-tests.sh:57:    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git push origin main --force' --env production | grep -q '\"decision\": \"deny\"'"
clearer-engineering/tests/run-all-tests.sh:59:run_test "Safety Gate: Staging tier requires confirmation with 2 explicit alerts (ASK)" \
clearer-engineering/tests/run-all-tests.sh:62:run_test "Safety Gate: Staging tier asks for git clean -fdx (ASK)" \
clearer-engineering/tests/run-all-tests.sh:65:run_test "Safety Gate: Development tier permits destructive actions with rollback notice (ALLOW)" \
clearer-engineering/tests/run-all-tests.sh:68:run_test "Safety Gate: Comprehensive Safety Matrix Suite (24 test cases including RTK)" \
clearer-engineering/tests/run-all-tests.sh:71:run_test "Safety Gate: Allow safe command 'npm test' (ALLOW)" \
clearer-engineering/tests/run-all-tests.sh:74:run_test "Safety Gate: Allow safe command 'git status' (ALLOW)" \
clearer-engineering/tests/run-all-tests.sh:77:run_test "Safety Gate: Allow safe RTK command 'rtk git status' (ALLOW)" \
clearer-engineering/tests/run-all-tests.sh:80:run_test "Safety Gate: Block destructive RTK command in production (DENY)" \
clearer-engineering/tests/run-all-tests.sh:81:    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rtk php artisan migrate:fresh' --env production | grep -q '\"decision\": \"deny\"'"
clearer-engineering/tests/run-all-tests.sh:83:run_test "Safety Gate: Staging tier asks for RTK destructive command with 2 alerts (ASK)" \
clearer-engineering/tests/run-all-tests.sh:86:run_test "Safety Gate: Hard block catastrophic RTK 'rtk rm -rf /' (DENY in any env)" \
clearer-engineering/tests/run-all-tests.sh:89:run_test "Safety Gate: Allow safe scratch cleanup 'rm -rf scratch/temp' (ALLOW)" \
clearer-engineering/tests/run-all-tests.sh:92:run_test "Safety Gate: Allow safe single file checkout 'git checkout app/Model.php' (ALLOW)" \
clearer-engineering/tests/run-all-tests.sh:95:run_test "Safety Gate: Pre-Push CI Gate blocks git push without CI flight certificate (DENY)" \
clearer-engineering/tests/run-all-tests.sh:98:run_test "Safety Gate: Pre-Push CI Gate allows git push with valid matching flight certificate (ALLOW)" \
clearer-engineering/tests/run-all-tests.sh:101:run_test "Safety Gate: Pre-Push CI Gate blocks git push when flight certificate is outdated (DENY)" \
clearer-engineering/tests/run-all-tests.sh:203:run_test "Golden Corpus: Snapshot de decisões do Safety Gate (diff vazio)" \
clearer-engineering/tests/run-all-tests.sh:234:run_test "Environment Differential: Rede diferencial da detecção sem explicit_env (PR-07b)" \
clearer-engineering/tests/test_hook_context.py:119:    def test_case_4_relative_cwd_without_workspace_escalates_to_production(self):
clearer-engineering/tests/test_hook_context.py:125:        # Destructive command -> deny (escalated to production)
clearer-engineering/tests/test_hook_context.py:181:        target_path, explicit_env, force_deny_push = resolve_hook_target(payload)
clearer-engineering/tests/test_hook_context.py:184:        self.assertIsNone(explicit_env)
clearer-engineering/tests/test_environment_tokens.py:63:        self.assertEqual(normalize_env("production"), "production")
clearer-engineering/tests/test_environment_tokens.py:64:        self.assertEqual(normalize_env("prod"), "production")
clearer-engineering/tests/test_environment_tokens.py:65:        self.assertEqual(normalize_env("live"), "production")
clearer-engineering/tests/test_environment_tokens.py:66:        self.assertEqual(normalize_env("preprod"), "production")
clearer-engineering/tests/test_environment_tokens.py:85:            ("php artisan migrate:fresh", "production", "deny"),
clearer-engineering/tests/test_environment_tokens.py:86:            ("php artisan db:wipe # staging", "production", "deny"),
clearer-engineering/tests/test_environment_tokens.py:87:            ("php artisan migrate:fresh --env=staging", "production", "deny"),
clearer-engineering/tests/test_environment_tokens.py:88:            ("terraform destroy -var env=staging", "production", "deny"),
clearer-engineering/tests/test_environment_tokens.py:104:        # Caminho contendo production não vira produção
clearer-engineering/tests/test_environment_tokens.py:105:        env_path, _ = detect_environment(cmd_line="rm -rf build/production-assets", target_dir=repo_dev)
clearer-engineering/tests/test_environment_tokens.py:119:            (repo_dev, "APP_ENV=production php artisan migrate:fresh", "production"),
clearer-engineering/tests/test_environment_tokens.py:120:            (repo_dev, "kubectl --context prod-cluster delete pod x", "production"),
clearer-engineering/tests/test_environment_tokens.py:122:            (repo_dev, "git log --grep=production", "development"),
clearer-engineering/tests/test_environment_tokens.py:125:            (repo_main, "APP_ENV=local git reset --hard", "production"),
clearer-engineering/tests/test_environment_tokens.py:126:            (repo_main, "env CEH_ENV=staging git reset --hard", "production"),
clearer-engineering/tests/test_environment_tokens.py:138:            ("cd /srv/production && php artisan migrate:fresh", "production", "deny"),
clearer-engineering/tests/test_environment_tokens.py:139:            ("php artisan migrate:fresh --environment=production", "production", "deny"),
clearer-engineering/tests/test_environment_tokens.py:140:            ("terraform destroy -var env=production", "production", "deny"),
clearer-engineering/tests/test_environment_tokens.py:141:            ("DJANGO_SETTINGS_MODULE=app.settings.production python manage.py flush --noinput", "production", None),
clearer-engineering/tests/test_environment_tokens.py:153:        """Handoff 031 AF1: cd <repo-main> && git reset --hard -> deny/production."""
clearer-engineering/tests/test_environment_tokens.py:159:        self.assertEqual(decision, "deny", f"AF1 falhou: {cmd} deveria ser deny/production, mas foi {decision} ({reason})")
clearer-engineering/tests/test_environment_tokens.py:160:        self.assertEqual(eval_env, "production", f"AF1 falhou: ambiente deveria ser production, mas foi {eval_env}")
clearer-engineering/tests/test_environment_tokens.py:163:        """Handoff 032 AG1: (cd <repo-main> && git reset --hard) -> deny/production sem vazamento."""
clearer-engineering/tests/test_environment_tokens.py:167:        # Subshell isolado com comando destrutivo no repo em main -> deny/production
clearer-engineering/tests/test_environment_tokens.py:170:        self.assertEqual(decision, "deny", f"AG1 falhou: {cmd} deveria ser deny/production, mas foi {decision} ({reason})")
clearer-engineering/tests/test_environment_tokens.py:171:        self.assertEqual(eval_env, "production", f"AG1 falhou: ambiente deveria ser production, mas foi {eval_env}")
clearer-engineering/tests/test_environment_tokens.py:179:        """Handoff 032 AG2: cd para destino incerto/dinâmico resulta em contexto production (Invariante 7)."""
clearer-engineering/tests/test_environment_tokens.py:182:        # Destino não resolvível seguido de comando destrutivo -> deny / production
clearer-engineering/tests/test_environment_tokens.py:192:            self.assertEqual(eval_env, "production", f"AG2 falhou: {cmd} deveria ser production, mas foi {eval_env}")
clearer-engineering/tests/test_environment_tokens.py:198:        self.assertEqual(eval_env, "production", f"AG2 custo aceito falhou: ambiente deveria ser production, mas foi {eval_env}")
clearer-engineering/tests/test_environment_tokens.py:248:            (f"{{ cd {repo_main}; git checkout -- .; }}", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:249:            (f"env -C {repo_main} git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:250:            (f"env --chdir={repo_main} git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:251:            (f"sudo -D {repo_main} git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:252:            (f"sudo --chdir={repo_main} git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:253:            (f"GIT_DIR={repo_main}/.git GIT_WORK_TREE={repo_main} git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:254:            (f"export GIT_DIR={repo_main}/.git && git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:255:            ("cd && git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:256:            ("cd ~ && git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:257:            (f"(cd {repo_main} && git reset --hard)", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:280:            ("git switch main && git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:281:            ("git checkout main && git reset --hard", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:282:            ("source .env.production && php artisan migrate:fresh", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:283:            (". ./prod.env && php artisan migrate:fresh", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:284:            ("cp .env.production .env && php artisan migrate:fresh", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:285:            ("echo APP_ENV=production > .env && php artisan db:wipe", "deny", "production"),
clearer-engineering/tests/test_environment_tokens.py:327:            ("source_env_prod", lambda d, c: f"source .env.production && {c}"),
clearer-engineering/tests/test_environment_tokens.py:328:            ("cp_env_prod", lambda d, c: f"cp .env.production .env && {c}"),
clearer-engineering/tests/test_environment_tokens.py:350:                    "production",
clearer-engineering/tests/test_environment_tokens.py:351:                    f"Invariante de equivalência violada: {form_name} não detectou production para {mod_cmd} (obteve {mod_env})"
clearer-engineering/tests/test_safety_matrix.py:3:test_safety_matrix.py - Comprehensive Unit Tests for CEH Safety Gate across 3 environments
clearer-engineering/tests/test_safety_matrix.py:47:        "name": "Database migrate fresh in production",
clearer-engineering/tests/test_safety_matrix.py:49:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:71:        "name": "Git reset hard in production",
clearer-engineering/tests/test_safety_matrix.py:73:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:87:        "name": "Git push force in production",
clearer-engineering/tests/test_safety_matrix.py:89:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:110:        "name": "Filesystem bulk deletion in production",
clearer-engineering/tests/test_safety_matrix.py:112:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:126:        "name": "Terraform destroy in production",
clearer-engineering/tests/test_safety_matrix.py:128:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:137:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:144:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:165:        "name": "Catastrophic rm root in production",
clearer-engineering/tests/test_safety_matrix.py:167:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:174:        "name": "RTK database migrate fresh in production",
clearer-engineering/tests/test_safety_matrix.py:176:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:181:        "name": "RTK proxy database migrate fresh in production",
clearer-engineering/tests/test_safety_matrix.py:183:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:196:        "name": "RTK git reset hard in production",
clearer-engineering/tests/test_safety_matrix.py:198:        "env": "production",
clearer-engineering/tests/test_safety_matrix.py:226:        decision, reason, env, use_case = evaluate_command(tc["cmd"], explicit_env=tc["env"])
clearer-engineering/tests/run-adversarial-tests.sh:108:OUTPUT_PROD=$(python3 "$PLUGIN_DIR/scripts/safety-gate.py" --check "git reset --hard HEAD" --env production 2>&1 || true)
clearer-engineering/tests/test_pre_push_refspecs.py:88:            dec, reason, env, uc = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_pre_push_refspecs.py:100:            dec, reason, env, uc = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_pre_push_refspecs.py:111:            dec, reason, env, uc = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_pre_push_refspecs.py:127:            dec_dev, _, _, uc_dev = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_pre_push_refspecs.py:131:            dec_sta, _, _, uc_sta = evaluate_command(cmd, explicit_env="staging")
clearer-engineering/tests/test_pre_push_refspecs.py:135:            # Em production: deny (com use_case GIT_HISTORY)
clearer-engineering/tests/test_pre_push_refspecs.py:136:            dec_prod, _, _, uc_prod = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_pre_push_refspecs.py:137:            self.assertEqual(dec_prod, "deny", f"Deleção '{cmd}' deveria ser deny em production, obtido '{dec_prod}'")
clearer-engineering/tests/test_pre_push_refspecs.py:143:        dec_cert, _, _, _ = evaluate_command("git push --forc origin HEAD:main", explicit_env="development")
clearer-engineering/tests/test_pre_push_refspecs.py:147:        dec_uncert, reason, _, uc = evaluate_command("git push --forc origin outro:main", explicit_env="development")
clearer-engineering/tests/test_pre_push_refspecs.py:156:        dec, reason, env, uc = evaluate_command(cmd_dash_c, explicit_env="development")
clearer-engineering/tests/test_pre_push_refspecs.py:161:        dec_cd, reason_cd, env_cd, uc_cd = evaluate_command(cmd_cd, explicit_env="development")
clearer-engineering/scripts/ceh_core/interpreters_extra.py:49:    if env == "production":
clearer-engineering/scripts/ceh_core/interpreters_extra.py:117:                    sub_res = eval_fn(unescaped, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
clearer-engineering/scripts/ceh_core/interpreters_extra.py:180:                    sub_res = eval_fn(unescaped, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
clearer-engineering/scripts/ceh_core/interpreters_extra.py:190:                    sub_res = eval_fn(unescaped, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
clearer-engineering/tests/tools/build_corpus.py:173:    raw("bash clearer-engineering/tests/run-all-tests.sh"),
clearer-engineering/tests/test_environment_differential.py:3:test_environment_differential.py - Rede diferencial da detecção de ambiente sem explicit_env (PR-07c).
clearer-engineering/tests/test_environment_differential.py:11:5. Avaliado nas branches dev, release/qa-1, main e feature/evaluation sem explicit_env.
clearer-engineering/tests/test_environment_differential.py:78:        "cd /srv/production && php artisan migrate:fresh",
clearer-engineering/tests/test_environment_differential.py:79:        "php artisan migrate:fresh --environment=production",
clearer-engineering/tests/test_environment_differential.py:80:        "terraform destroy -var env=production",
clearer-engineering/tests/test_environment_differential.py:81:        "DJANGO_SETTINGS_MODULE=app.settings.production python manage.py flush --noinput",
clearer-engineering/tests/test_environment_differential.py:84:        "STAGE=production serverless deploy",
clearer-engineering/tests/test_environment_differential.py:86:        "helm upgrade --set env=production my-app ./chart",
clearer-engineering/tests/test_environment_differential.py:89:        "php artisan migrate:fresh --stage=production",
clearer-engineering/tests/test_environment_differential.py:90:        "aws s3 rm s3://bucket --profile production",
clearer-engineering/tests/test_environment_differential.py:92:        "rm -rf build/production-assets",
clearer-engineering/tests/test_environment_differential.py:94:        "git log --grep=production",
clearer-engineering/tests/test_environment_differential.py:104:        '(cd /srv/production && git reset --hard)',
clearer-engineering/tests/test_environment_differential.py:106:        '(cd /srv/production && npm test)',
clearer-engineering/tests/test_environment_differential.py:116:    env_names_prod = ["production", "prod"]
clearer-engineering/tests/test_environment_differential.py:136:        "/srv/production", "/srv/staging", "/srv/dev", "/srv/local",
clearer-engineering/tests/test_environment_differential.py:137:        "config/production", "config/staging", "build/production-assets",
clearer-engineering/tests/test_environment_differential.py:138:        '"$PROD_DIR"', '"$DIR"', "'-'", "~/production", "~/dev",
clearer-engineering/tests/test_environment_differential.py:294:        """Avalia baseline vs gate atual sem explicit_env em múltiplos repositórios."""
clearer-engineering/tests/fixtures/gate_corpus.txt:137:RAW:bash clearer-engineering/tests/run-all-tests.sh
clearer-engineering/tests/run_claude_pr00e_eval.py:283:- **F5 Neutralizado:** O par E3a/E3b prova causalmente que o bloqueio do `git reset --hard` decorre estritamente da intervenção do Safety Gate do CEH.
clearer-engineering/tests/test_review_batteries.py:61:            decision, _reason, _env, use_case = safety_gate.evaluate_command(command, explicit_env=env)
clearer-engineering/tests/cluster2_acceptance.py:18:RUN_ALL_TESTS = PLUGIN_ROOT / "tests" / "run-all-tests.sh"
clearer-engineering/tests/test_rm_fuzz.py:80:            env = rng.choice(["development", "staging", "production"])
clearer-engineering/tests/test_rm_fuzz.py:82:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env, base_cwd=cwd)
clearer-engineering/tests/tools/snapshot_gate.py:3:snapshot_gate.py - Golden Corpus Snapshot Tool for CEH Safety Gate
clearer-engineering/tests/tools/snapshot_gate.py:87:    environments = ["development", "staging", "production"]
clearer-engineering/tests/tools/snapshot_gate.py:113:                    decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/tools/snapshot_gate.py:149:                    decision, reason, _, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/tools/snapshot_gate.py:166:                    decision, reason, _, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/tools/snapshot_gate.py:226:    parser = argparse.ArgumentParser(description="CEH Safety Gate Snapshot Tool")
clearer-engineering/tests/fixtures/review_batteries.txt:4:#   env        development | staging | production
clearer-engineering/tests/fixtures/review_batteries.txt:62:production|deny|H015-S1|rm -rf /var/www/site/dist
clearer-engineering/tests/fixtures/review_batteries.txt:63:production|deny|H015-S1|rm -rf /srv/app/build
clearer-engineering/tests/fixtures/review_batteries.txt:64:production|deny|H015-S1|rm -rf /opt/prod/app/dist/
clearer-engineering/tests/fixtures/review_batteries.txt:65:production|deny|H015-S1|rm -rf /etc/nginx/coverage/
clearer-engineering/tests/fixtures/review_batteries.txt:66:production|deny|H015-S1|rm -rf ../../prod-release/dist
clearer-engineering/tests/fixtures/review_batteries.txt:67:production|allow/FILESYSTEM_SAFE|H015-S1-controle|rm -rf dist/
clearer-engineering/tests/fixtures/review_batteries.txt:68:production|allow/FILESYSTEM_SAFE|H015-S1-controle|rm -rf ./build
clearer-engineering/tests/fixtures/review_batteries.txt:69:production|allow/FILESYSTEM_SAFE|H015-S1-controle|rm -rf /tmp/ceh-x
clearer-engineering/tests/fixtures/review_batteries.txt:70:production|allow/FILESYSTEM_SAFE|H015-S1-controle|rm -f a.txt
clearer-engineering/tests/fixtures/review_batteries.txt:71:production|allow/FILESYSTEM_SAFE|H015-S1-controle|rm -rf node_modules/.cache
clearer-engineering/tests/fixtures/review_batteries.txt:72:production|allow/FILESYSTEM_SAFE|H015-S1-controle|rm -rf dist/assets
clearer-engineering/tests/fixtures/review_batteries.txt:82:production|deny|H016-T1|rm -rf build/../src
clearer-engineering/tests/fixtures/review_batteries.txt:83:production|deny|H016-T1|rm -rf coverage/../.git
clearer-engineering/tests/fixtures/review_batteries.txt:84:production|deny|H016-T1|rm -rf dist/../../etc
clearer-engineering/tests/fixtures/review_batteries.txt:85:production|deny/CATASTROPHIC|H016-T1|rm -rf ./dist/../..
clearer-engineering/tests/fixtures/review_batteries.txt:86:production|deny/CATASTROPHIC|H016-T1|rm -rf tmp/../
clearer-engineering/tests/fixtures/review_batteries.txt:87:production|deny/CATASTROPHIC|H016-T1|rm -rf /tmp/../etc
clearer-engineering/tests/fixtures/review_batteries.txt:88:production|deny/CATASTROPHIC|H016-T1|rm -rf /tmp/../home/user
clearer-engineering/tests/fixtures/review_batteries.txt:89:production|deny|H016-T1|rm -rf ../a.txt
clearer-engineering/tests/fixtures/review_batteries.txt:90:production|deny|H016-T1|rm -rf /etc/passwd.bak
clearer-engineering/tests/fixtures/review_batteries.txt:91:production|deny/CATASTROPHIC|H016-T1|rm -rf dist/../../../
clearer-engineering/tests/fixtures/review_batteries.txt:94:production|deny|H017-G2|git checkout .
clearer-engineering/tests/fixtures/review_batteries.txt:95:production|deny|H017-G2|git checkout -- .
clearer-engineering/tests/fixtures/review_batteries.txt:96:production|deny|H017-G2|git checkout HEAD -- .
clearer-engineering/tests/fixtures/review_batteries.txt:97:production|deny|H017-G2|git checkout -f
clearer-engineering/tests/fixtures/review_batteries.txt:98:production|deny|H017-G2|git checkout :/
clearer-engineering/tests/fixtures/review_batteries.txt:99:production|deny|H017-G2|git checkout -- '*'
clearer-engineering/tests/fixtures/review_batteries.txt:100:production|deny|H017-G2|git restore .
clearer-engineering/tests/fixtures/review_batteries.txt:101:production|deny|H017-G2|git restore --staged --worktree .
clearer-engineering/tests/fixtures/review_batteries.txt:102:production|deny|H017-G2|git restore --source=HEAD .
clearer-engineering/tests/fixtures/review_batteries.txt:103:production|deny|H017-G2|git restore :/
clearer-engineering/tests/fixtures/review_batteries.txt:104:production|deny|H017-G2|git checkout HEAD .
clearer-engineering/tests/fixtures/review_batteries.txt:105:production|deny|H017-G2|git checkout @ -- .
clearer-engineering/tests/fixtures/review_batteries.txt:106:production|deny|H017-G2|git checkout --force main
clearer-engineering/tests/fixtures/review_batteries.txt:107:production|deny|H017-G2|git checkout -- *
clearer-engineering/tests/fixtures/review_batteries.txt:108:production|deny|H017-G2|git restore -W -S .
clearer-engineering/tests/fixtures/review_batteries.txt:109:production|deny|H017-G2|git restore --worktree -- .
clearer-engineering/tests/fixtures/review_batteries.txt:110:production|deny|H017-G2|git restore -s HEAD .
clearer-engineering/tests/fixtures/review_batteries.txt:111:production|deny|H017-G2|git checkout -f -- app/x.php
clearer-engineering/tests/fixtures/review_batteries.txt:112:production|deny|H017-U1|git checkout -- ./
clearer-engineering/tests/fixtures/review_batteries.txt:113:production|deny|H017-G3|git -C . reset --hard
clearer-engineering/tests/fixtures/review_batteries.txt:114:production|deny|H017-G3|git --no-pager reset --hard
clearer-engineering/tests/fixtures/review_batteries.txt:115:production|deny|H017-G3|git -P reset --hard
clearer-engineering/tests/fixtures/review_batteries.txt:116:production|deny|H017-G3|git --paginate reset --hard
clearer-engineering/tests/fixtures/review_batteries.txt:117:production|deny|H017-G3|git --no-pager -C . reset --hard
clearer-engineering/tests/fixtures/review_batteries.txt:118:production|deny|H017-U3|git switch -f main
clearer-engineering/tests/fixtures/review_batteries.txt:119:production|deny|H017-U3|git switch --discard-changes main
clearer-engineering/tests/fixtures/review_batteries.txt:120:production|allow|H017-controle|git checkout app/Model.php
clearer-engineering/tests/fixtures/review_batteries.txt:121:production|allow|H017-controle|git checkout main
clearer-engineering/tests/fixtures/review_batteries.txt:122:production|allow|H017-controle|git checkout -b feature
clearer-engineering/tests/fixtures/review_batteries.txt:123:production|allow|H017-controle|git checkout feature/login
clearer-engineering/tests/fixtures/review_batteries.txt:124:production|allow|H017-controle|git checkout -- app/Model.php
clearer-engineering/tests/fixtures/review_batteries.txt:125:production|allow|H017-controle|git checkout v1.2.0
clearer-engineering/tests/fixtures/review_batteries.txt:126:production|allow|H017-controle|git restore --staged app/Model.php
clearer-engineering/tests/fixtures/review_batteries.txt:127:production|allow|H017-controle|git status
clearer-engineering/tests/fixtures/review_batteries.txt:128:production|allow|H017-controle|git -C sub status
clearer-engineering/tests/fixtures/review_batteries.txt:129:production|allow|H017-controle|git --no-pager log -5
clearer-engineering/tests/fixtures/review_batteries.txt:130:production|allow|H017-U2|git -P diff
clearer-engineering/tests/fixtures/review_batteries.txt:131:production|allow|H017-U2|git -P log -5
clearer-engineering/tests/fixtures/review_batteries.txt:132:production|allow|H017-controle|git switch main
clearer-engineering/tests/fixtures/review_batteries.txt:133:production|allow|H017-controle|git switch -c feature
clearer-engineering/tests/fixtures/review_batteries.txt:140:production|deny|H017-G5|find . -name '*.pyc' -delete
clearer-engineering/tests/fixtures/review_batteries.txt:141:production|deny|H017-G5-ja-coberto|find . -exec rm -rf {} +
clearer-engineering/tests/fixtures/review_batteries.txt:142:production|deny|H017-G5|python3 -c 'import shutil; shutil.rmtree("/srv")'
clearer-engineering/tests/fixtures/review_batteries.txt:143:production|deny|H017-G5|node -e 'require("fs").rmSync("db",{recursive:true})'
clearer-engineering/tests/fixtures/review_batteries.txt:144:production|deny|H017-G5|perl -e 'unlink glob "*"'
clearer-engineering/tests/fixtures/review_batteries.txt:145:production|allow|H017-G5-controle|find . -name '*.log'
clearer-engineering/tests/fixtures/review_batteries.txt:146:production|allow|H017-G5-controle|grep -r "shutil.rmtree" .
clearer-engineering/tests/fixtures/review_batteries.txt:147:production|allow|H017-G5-controle|python3 -c 'print(1)'
clearer-engineering/tests/fixtures/review_batteries.txt:148:production|allow|H017-G5-controle|node -e 'console.log(1)'
clearer-engineering/tests/fixtures/review_batteries.txt:151:production|deny|H019-U1|git checkout -- ././
clearer-engineering/tests/fixtures/review_batteries.txt:152:production|deny|H019-U1|git checkout -- "./"
clearer-engineering/tests/fixtures/review_batteries.txt:153:production|deny|H019-U1|git checkout -- ./ app/x.php
clearer-engineering/tests/fixtures/review_batteries.txt:154:production|deny|H019-U1|git restore -- ./
clearer-engineering/tests/fixtures/review_batteries.txt:155:production|deny|H019-U1|git checkout HEAD -- ./
clearer-engineering/tests/fixtures/review_batteries.txt:156:production|deny|H019-U1|git checkout -- ./.
clearer-engineering/tests/fixtures/review_batteries.txt:157:production|deny|H019-U1|git checkout -- .//
clearer-engineering/tests/fixtures/review_batteries.txt:158:production|deny|H019-U1|git restore --worktree ./
clearer-engineering/tests/fixtures/review_batteries.txt:159:production|deny|H019-U1|git checkout -- :/
clearer-engineering/tests/fixtures/review_batteries.txt:160:production|deny|H019-U3|git switch --force main
clearer-engineering/tests/fixtures/review_batteries.txt:161:production|deny|H019-U3|git switch -f -c x
clearer-engineering/tests/fixtures/review_batteries.txt:162:production|deny|H019-U3|git switch --discard-changes
clearer-engineering/tests/fixtures/review_batteries.txt:163:production|allow|H019-controle|git switch -
clearer-engineering/tests/fixtures/review_batteries.txt:164:production|allow|H019-controle|git checkout -- ./app/Model.php
clearer-engineering/tests/fixtures/review_batteries.txt:165:production|allow|H019-controle|git checkout ./app/Model.php
clearer-engineering/tests/fixtures/review_batteries.txt:166:production|allow|H019-controle|git checkout -- ./src
clearer-engineering/tests/fixtures/review_batteries.txt:168:production|deny|H019-V1|git checkout -- src/..
clearer-engineering/tests/fixtures/review_batteries.txt:169:production|deny|H019-V1|git checkout -- ":(top)"
clearer-engineering/tests/fixtures/review_batteries.txt:170:production|deny|H019-V1|git restore ':(top).'
clearer-engineering/tests/fixtures/review_batteries.txt:171:production|deny|H019-V1|git checkout -- app/..
clearer-engineering/tests/fixtures/review_batteries.txt:172:production|deny|H019-V1|git checkout -- ./src/../
clearer-engineering/tests/fixtures/review_batteries.txt:173:production|deny|H019-V1|git checkout -- ':!x'
clearer-engineering/tests/fixtures/review_batteries.txt:174:production|deny|H019-V1|git checkout -- ':^x'
clearer-engineering/tests/fixtures/review_batteries.txt:175:production|deny|H019-V1|git restore ':(exclude)x'
clearer-engineering/tests/fixtures/review_batteries.txt:176:production|allow|H019-V1-controle|git checkout -- :/app/Model.php
clearer-engineering/tests/fixtures/review_batteries.txt:178:production|deny|H019-V2|git switch -C main
clearer-engineering/tests/fixtures/review_batteries.txt:179:production|deny|H019-V2|git checkout -B main
clearer-engineering/tests/fixtures/review_batteries.txt:180:production|allow|H019-V2-controle|git checkout -b feature
clearer-engineering/tests/fixtures/review_batteries.txt:181:production|allow|H019-V2-controle|git switch -c feature
clearer-engineering/tests/fixtures/review_batteries.txt:183:production|allow|H019-V3|git restore --staged .
clearer-engineering/tests/fixtures/review_batteries.txt:184:production|allow|H019-V3|git restore --staged ./
clearer-engineering/tests/fixtures/review_batteries.txt:185:production|allow|H019-V3|git restore -S .
clearer-engineering/tests/fixtures/review_batteries.txt:186:production|allow|H019-V3|git restore --staged -- .
clearer-engineering/tests/fixtures/review_batteries.txt:187:production|deny|H019-V3-controle|git restore -S -W .
clearer-engineering/tests/fixtures/review_batteries.txt:191:production|deny|H020-V1|git checkout HEAD src/..
clearer-engineering/tests/fixtures/review_batteries.txt:192:production|deny|H020-V1|git restore -s HEAD src/..
clearer-engineering/tests/fixtures/review_batteries.txt:193:production|deny|H020-V1|git restore --source=HEAD~2 -- src/..
clearer-engineering/tests/fixtures/review_batteries.txt:194:production|deny|H020-V1|git checkout -- ':/app/../..'
clearer-engineering/tests/fixtures/review_batteries.txt:196:production|allow|H020-V4|git checkout feature/add-pdf
clearer-engineering/tests/fixtures/review_batteries.txt:197:production|allow|H020-V4|git checkout fix-leaf
clearer-engineering/tests/fixtures/review_batteries.txt:198:production|allow|H020-V4|git switch hotfix-ref
clearer-engineering/tests/fixtures/review_batteries.txt:199:production|allow|H020-V4|git checkout -- app/self-ref
clearer-engineering/tests/fixtures/review_batteries.txt:200:production|deny|H020-V4-controle|git checkout -qf main
clearer-engineering/tests/fixtures/review_batteries.txt:201:production|deny|H020-V4-controle|git switch -f hotfix-ref
clearer-engineering/tests/fixtures/review_batteries.txt:203:production|deny|H020-V5|git restore --pathspec-from-file=list.txt
clearer-engineering/tests/fixtures/review_batteries.txt:204:production|deny|H020-V5|git checkout --pathspec-from-file=list.txt
clearer-engineering/tests/fixtures/review_batteries.txt:205:production|deny|H020-V5|git restore --pathspec-from-file -
clearer-engineering/tests/fixtures/review_batteries.txt:207:production|deny|H020-agente-V1|git checkout -- a/b/../..
clearer-engineering/tests/fixtures/review_batteries.txt:208:production|deny|H020-agente-V1|git restore ":(top,glob)*"
clearer-engineering/tests/fixtures/review_batteries.txt:209:production|deny|H020-agente-V1|git checkout -- ":(top,icase)*"
clearer-engineering/tests/fixtures/review_batteries.txt:210:production|allow|H020-agente-controle|git checkout ":(top)app/Services/PaymentService.php"
clearer-engineering/tests/fixtures/review_batteries.txt:211:production|allow|H020-agente-controle|git restore ":/config/app.php"
clearer-engineering/tests/fixtures/review_batteries.txt:212:production|deny|H020-agente-V2|git switch -C feature/new-workflow
clearer-engineering/tests/fixtures/review_batteries.txt:216:production|deny|H021-W1|git checkout . app/x
clearer-engineering/tests/fixtures/review_batteries.txt:217:production|deny|H021-W1|git checkout src/.. app/x
clearer-engineering/tests/fixtures/review_batteries.txt:218:production|deny|H021-W1-controle|git checkout app/x .
clearer-engineering/tests/fixtures/review_batteries.txt:219:production|allow|H021-W1-controle|git checkout main app/x
clearer-engineering/tests/fixtures/review_batteries.txt:221:production|deny|H021-W2|git checkout --forc main
clearer-engineering/tests/fixtures/review_batteries.txt:222:production|deny|H021-W2|git switch --discard main
clearer-engineering/tests/fixtures/review_batteries.txt:223:production|deny|H021-W2|git switch --force-c main
clearer-engineering/tests/fixtures/review_batteries.txt:224:production|deny|H021-W2|git restore --staged --work .
clearer-engineering/tests/fixtures/review_batteries.txt:225:production|deny|H021-W2|git restore --pathspec-from=list.txt
clearer-engineering/tests/fixtures/review_batteries.txt:226:production|deny|H021-W2-controle|git restore --stag --work .
clearer-engineering/tests/fixtures/review_batteries.txt:227:production|allow|H021-W2-controle|git checkout --quiet main
clearer-engineering/tests/fixtures/review_batteries.txt:228:production|allow|H021-W2-controle|git switch --detach HEAD~1
clearer-engineering/tests/fixtures/review_batteries.txt:230:production|deny|H021-W3|git checkout -- '*.php'
clearer-engineering/tests/fixtures/review_batteries.txt:231:production|deny|H021-W3|git restore '*.php'
clearer-engineering/tests/fixtures/review_batteries.txt:232:production|deny|H021-W3|git checkout -- ./*
clearer-engineering/tests/fixtures/review_batteries.txt:233:production|deny|H021-W3|git checkout -- '**'
clearer-engineering/tests/fixtures/review_batteries.txt:234:production|deny|H021-W3|git restore -- '[a-z]*'
clearer-engineering/tests/fixtures/review_batteries.txt:235:production|allow|H021-W3-controle|git checkout -- src/*
clearer-engineering/tests/fixtures/review_batteries.txt:236:production|allow|H021-W3-controle|git checkout -- 'src/*.php'
clearer-engineering/tests/fixtures/review_batteries.txt:238:production|deny|H021-W4|git checkout -- "$PWD"
clearer-engineering/tests/fixtures/review_batteries.txt:239:production|deny|H021-W4|git restore $DIR
clearer-engineering/tests/fixtures/review_batteries.txt:240:production|deny|H021-W4|git checkout -- ~
clearer-engineering/tests/fixtures/review_batteries.txt:242:production|deny|H021-agente-W1|git checkout ./src/.. app/Model.php
clearer-engineering/tests/fixtures/review_batteries.txt:243:production|deny|H021-agente-W2|git switch --discard-c main
clearer-engineering/tests/fixtures/review_batteries.txt:244:production|deny|H021-agente-W3|git checkout -- "?*.js"
clearer-engineering/tests/fixtures/review_batteries.txt:245:production|deny|H021-agente-W4|git checkout -- ~/projects/repo
clearer-engineering/tests/fixtures/review_batteries.txt:246:production|allow|H021-agente-controle|git checkout -- tests/*
clearer-engineering/tests/fixtures/review_batteries.txt:247:production|allow|H021-agente-controle|git switch --guess main
clearer-engineering/tests/fixtures/review_batteries.txt:251:production|deny|H022-X1|git checkout -- ':/!x'
clearer-engineering/tests/fixtures/review_batteries.txt:252:production|deny|H022-X1|git checkout -- ':/^x'
clearer-engineering/tests/fixtures/review_batteries.txt:253:production|deny|H022-X1|git restore ':/!app'
clearer-engineering/tests/fixtures/review_batteries.txt:254:production|deny|H022-X1|git checkout -- ':/!:x'
clearer-engineering/tests/fixtures/review_batteries.txt:255:production|allow|H022-X1-controle|git restore ':/app/x'
clearer-engineering/tests/fixtures/review_batteries.txt:256:production|allow|H022-X1-controle|git checkout -- ':/:app/x'
clearer-engineering/tests/fixtures/review_batteries.txt:258:production|deny|H022-agente-X1|git checkout -- ':^/src'
clearer-engineering/tests/fixtures/review_batteries.txt:259:production|deny|H022-agente-X1|git restore ':!/app/Services'
clearer-engineering/tests/fixtures/review_batteries.txt:260:production|allow|H022-agente-controle|git checkout -- ':/config/database.php'
clearer-engineering/tests/fixtures/review_batteries.txt:264:production|allow|H023-Y4|git checkout -- ':app/x'
clearer-engineering/tests/fixtures/review_batteries.txt:265:production|allow|H023-Y4-controle|git checkout -- '::app/x'
clearer-engineering/tests/fixtures/review_batteries.txt:266:production|deny|H023-X1-controle|git checkout -- ':^/!x'
clearer-engineering/tests/fixtures/review_batteries.txt:267:production|deny|H023-X1-controle|git checkout -- ':(top,exclude)x'
clearer-engineering/tests/fixtures/review_batteries.txt:273:production|deny|H024-G5|find .. -exec rm {} \;
clearer-engineering/tests/fixtures/review_batteries.txt:274:production|deny|H024-G5-ja-coberto|find . -type f -exec sh -c 'rm -f "$1"' _ {} \;
clearer-engineering/tests/fixtures/review_batteries.txt:275:production|deny|H024-G5|find build -ok rm {} \;
clearer-engineering/tests/fixtures/review_batteries.txt:277:production|allow|H024-G5-controle|find . -name '*.pyc' -print
clearer-engineering/tests/fixtures/review_batteries.txt:281:production|deny|H024-G5|env python3 -c "import os; os.remove('a')"
clearer-engineering/tests/fixtures/review_batteries.txt:282:production|deny|H024-G5|python3.12 -c "import pathlib; pathlib.Path('db').unlink()"
clearer-engineering/tests/fixtures/review_batteries.txt:283:production|deny|H024-G5-ja-coberto|python3 -c "import os; os.system('rm -rf build')"
clearer-engineering/tests/fixtures/review_batteries.txt:284:production|deny|H024-G5-ja-coberto|node --eval "require('child_process').execSync('rm -rf dist')"
clearer-engineering/tests/fixtures/review_batteries.txt:285:production|allow|H024-G5-controle|python3 script.py
clearer-engineering/tests/fixtures/review_batteries.txt:286:production|allow|H024-G5-controle|python3 -c "import os; print(os.getcwd())"
clearer-engineering/tests/fixtures/review_batteries.txt:287:production|allow|H024-G5-controle|echo "shutil.rmtree"
clearer-engineering/tests/fixtures/review_batteries.txt:288:production|allow|H024-G5-controle|node -e "console.log(require('fs').existsSync('db'))"
clearer-engineering/tests/fixtures/review_batteries.txt:297:production|allow|H025-controle|find . -name '*.log' -exec ls {} \;
clearer-engineering/tests/fixtures/review_batteries.txt:299:production|deny/CATASTROPHIC|H025-AA2|bash -c "find / -delete"
clearer-engineering/tests/fixtures/review_batteries.txt:306:production|deny|H025-AA3|python3 -Ic 'import shutil; shutil.rmtree("db")'
clearer-engineering/tests/fixtures/review_batteries.txt:307:production|deny|H025-AA3|perl -le 'unlink glob "*"'
clearer-engineering/tests/fixtures/review_batteries.txt:309:production|deny|H025-AA3|node -e "require('node:fs').rmSync('db',{recursive:true})"
clearer-engineering/tests/fixtures/review_batteries.txt:314:production|allow|H025-controle|python3 -c "l=[1]; print(len(l))"
clearer-engineering/tests/fixtures/review_batteries.txt:315:production|allow|H025-controle|perl -le 'print 1'
clearer-engineering/tests/fixtures/review_batteries.txt:316:production|allow|H025-controle|cat s.py | python3
clearer-engineering/tests/fixtures/review_batteries.txt:321:production|deny/CATASTROPHIC|H026-AB1|nice find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:322:production|deny/CATASTROPHIC|H026-AB1|timeout 10 find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:323:production|deny/CATASTROPHIC|H026-AB1|sudo -u deploy find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:324:production|deny/CATASTROPHIC|H026-AB1|nohup find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:325:production|deny/CATASTROPHIC|H026-AB1|timeout 5 python3 -c "import shutil; shutil.rmtree('/')"
clearer-engineering/tests/fixtures/review_batteries.txt:326:production|deny/CATASTROPHIC|H026-AB1|sudo -u root bash -c "find / -delete"
clearer-engineering/tests/fixtures/review_batteries.txt:327:production|deny/CATASTROPHIC|H026-AB1|timeout 5 bash -c "find / -delete"
clearer-engineering/tests/fixtures/review_batteries.txt:328:production|deny/CATASTROPHIC|H026-AB1|exec bash -c "find / -delete"
clearer-engineering/tests/fixtures/review_batteries.txt:329:production|deny/CATASTROPHIC|H026-AB1|xargs -I{} sh -c 'find / -delete'
clearer-engineering/tests/fixtures/review_batteries.txt:330:production|deny/CATASTROPHIC|H026-AB1|eval "find / -delete"
clearer-engineering/tests/fixtures/review_batteries.txt:331:production|deny/CATASTROPHIC|H026-AB1|su -c "find / -delete"
clearer-engineering/tests/fixtures/review_batteries.txt:332:production|deny/CATASTROPHIC|H026-AB1|watch -n1 "find / -delete"
clearer-engineering/tests/fixtures/review_batteries.txt:333:production|deny|H026-AB1|nice git checkout -- .
clearer-engineering/tests/fixtures/review_batteries.txt:334:production|allow|H026-controle|nice npm run build
clearer-engineering/tests/fixtures/review_batteries.txt:335:production|allow|H026-controle|timeout 5 git status
clearer-engineering/tests/fixtures/review_batteries.txt:336:production|allow|H026-controle|sudo -u deploy ls /var/www
clearer-engineering/tests/fixtures/review_batteries.txt:337:production|allow|H026-controle|watch -n1 "git status"
clearer-engineering/tests/fixtures/review_batteries.txt:338:production|allow|H026-controle|time python3 -c "print(1)"
clearer-engineering/tests/fixtures/review_batteries.txt:346:production|deny/CATASTROPHIC|H027-AC1|sudo --user deploy find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:347:production|deny/CATASTROPHIC|H027-AC1|sudo -iu root find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:348:production|deny/CATASTROPHIC|H027-AC1|taskset -c 0 find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:349:production|deny/CATASTROPHIC|H027-AC1|xargs --max-args 1 find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:350:production|deny/CATASTROPHIC|H027-AC1|env -S 'find / -delete'
clearer-engineering/tests/fixtures/review_batteries.txt:351:production|deny|H027-AC1|sudo --user deploy git checkout -- .
clearer-engineering/tests/fixtures/review_batteries.txt:352:production|allow|H027-controle|sudo --user deploy systemctl status nginx
clearer-engineering/tests/fixtures/review_batteries.txt:353:production|allow|H027-controle|taskset -c 0 npm test
clearer-engineering/tests/fixtures/review_batteries.txt:354:production|allow|H027-controle|env -S 'npm run build'
clearer-engineering/tests/fixtures/review_batteries.txt:358:production|deny/CATASTROPHIC|H028-AD1|setsid find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:359:production|deny/CATASTROPHIC|H028-AD1|flock /tmp/lock find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:360:production|deny/CATASTROPHIC|H028-AD1|chroot / find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:361:production|deny/CATASTROPHIC|H028-AD1|busybox find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:362:production|deny/CATASTROPHIC|H028-AD1|strace -f find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:363:production|deny/CATASTROPHIC|H028-AD1|ssh host find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:364:production|deny/CATASTROPHIC|H028-AD1|docker exec app find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:365:production|deny|H028-AD1|setsid git checkout -- .
clearer-engineering/tests/fixtures/review_batteries.txt:366:production|allow|H028-controle|sudo apt install git
clearer-engineering/tests/fixtures/review_batteries.txt:367:production|allow|H028-controle|man find
clearer-engineering/tests/fixtures/review_batteries.txt:368:production|allow|H028-controle|which python3
clearer-engineering/tests/fixtures/review_batteries.txt:369:production|allow|H028-controle|sudo -u git ls
clearer-engineering/tests/fixtures/review_batteries.txt:370:production|allow|H028-controle|git commit -m "find / -delete"
clearer-engineering/tests/fixtures/review_batteries.txt:371:production|allow|H028-controle|grep -rn find src/
clearer-engineering/tests/fixtures/review_batteries.txt:372:production|allow|H028-controle|docker exec app php artisan route:list
clearer-engineering/tests/fixtures/review_batteries.txt:381:production|deny|H028-AD4|php -r 'array_map("unlink", glob("*"));'
clearer-engineering/tests/fixtures/review_batteries.txt:387:production|allow|H028-controle|php -r 'echo PHP_VERSION;'
clearer-engineering/tests/fixtures/review_batteries.txt:388:production|allow|H028-controle|awk '{print $1}' access.log
clearer-engineering/tests/fixtures/review_batteries.txt:389:production|allow|H028-controle|php artisan route:list
clearer-engineering/tests/fixtures/review_batteries.txt:396:production|allow|H029-AE1|which git bash perl python3 node
clearer-engineering/tests/fixtures/review_batteries.txt:397:production|allow|H029-AE1|echo git git git git
clearer-engineering/tests/fixtures/review_batteries.txt:398:production|allow|H029-AE1|command -v git bash zsh fish
clearer-engineering/tests/fixtures/review_batteries.txt:399:production|deny/CATASTROPHIC|H029-AE1-controle|echo git git git git find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:400:production|deny/CATASTROPHIC|H029-AE1-controle|setsid nice timeout 5 sudo -u x find / -delete
clearer-engineering/tests/fixtures/review_batteries.txt:405:production|allow|H029-controle|php -f script.php
clearer-engineering/tests/fixtures/review_batteries.txt:406:production|allow|H029-controle|awk -f prog.awk data.txt
clearer-engineering/tests/fixtures/review_batteries.txt:407:production|allow|H029-controle|bun run build
clearer-engineering/tests/fixtures/review_batteries.txt:418:production|allow|H038-controle|cat .ceh/last-ci-run.json
clearer-engineering/tests/fixtures/review_batteries.txt:419:production|allow|H038-controle|ls .ceh
clearer-engineering/tests/fixtures/review_batteries.txt:420:production|allow|H038-controle|jq .status .ceh/last-ci-run.json
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:3:{"command": "git status", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-000-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:6:{"command": "git status -s", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-001-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:9:{"command": "git log -n 10", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-002-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:12:{"command": "git log --oneline -n 5", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-003-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:15:{"command": "git diff", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-004-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:18:{"command": "git diff --stat", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-005-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:21:{"command": "git diff HEAD~1", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-006-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:24:{"command": "git branch", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-007-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:27:{"command": "git branch -a", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-008-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:30:{"command": "git branch --show-current", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-009-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:33:{"command": "git checkout dev", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-010-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:36:{"command": "git checkout -b feature/auth-system", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-011-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:39:{"command": "git checkout main", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-012-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:42:{"command": "git checkout staging", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-013-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:45:{"command": "git checkout app/Models/User.php", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-014-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:48:{"command": "git checkout config/app.php", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-015-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:51:{"command": "git restore app/Services/PaymentService.php", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-016-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:54:{"command": "git restore --staged README.md", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-017-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:57:{"command": "git add .", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-018-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:60:{"command": "git add README.md", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-019-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:63:{"command": "git add -A", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-020-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:66:{"command": "git commit -m \"feat: implement safety gate\"", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-021-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:69:{"command": "git commit -m \"fix: resolve edge case\"", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-022-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:72:{"command": "git show HEAD", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-023-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:75:{"command": "git show --stat", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-024-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:78:{"command": "git rev-parse HEAD", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-025-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:81:{"command": "git rev-parse --abbrev-ref HEAD", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-026-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:84:{"command": "git remote -v", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-027-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:87:{"command": "git fetch origin", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-028-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:90:{"command": "git pull origin dev", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-029-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:93:{"command": "git tag v1.0.0", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-030-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:96:{"command": "git stash", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-031-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:99:{"command": "git stash pop", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-032-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:102:{"command": "git stash list", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-033-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:105:{"command": "git reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-034-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:108:{"command": "git reset --hard HEAD~1", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-035-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:111:{"command": "git reset --hard origin/main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-036-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:114:{"command": "git reset --hard HEAD", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-037-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:117:{"command": "git reset --hard dev", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-038-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:120:{"command": "git clean -f", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-039-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:123:{"command": "git clean -fd", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-040-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:126:{"command": "git clean -fdx", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-041-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:129:{"command": "git clean -fx", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-042-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:132:{"command": "git push origin main --force", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-043-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:135:{"command": "git push -f origin main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-044-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:138:{"command": "git push origin main --force-with-lease", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-045-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:141:{"command": "git push origin dev --force", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-046-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:144:{"command": "git push origin staging --force", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-047-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:147:{"command": "git push origin +dev", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-048-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:150:{"command": "git push origin dev", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-049-pro", "type": "command", "use_case": "PRE_PUSH_CI"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:153:{"command": "git checkout .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-050-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:156:{"command": "git restore .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-051-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:159:{"command": "git checkout -- .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-052-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:162:{"command": "git -C . reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-053-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:165:{"command": "git --no-pager reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-054-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:168:{"command": "git branch -D feature/old", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-055-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:171:{"command": "git push origin --delete feature/old", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-056-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:174:{"command": "ls -la", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-057-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:177:{"command": "pwd", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-058-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:180:{"command": "mkdir -p storage/logs", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-059-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:183:{"command": "mkdir -p build/tmp", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-060-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:186:{"command": "touch app/test.txt", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-061-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:189:{"command": "cat package.json", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-062-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:192:{"command": "grep -r \"test\" src/", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-063-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:195:{"command": "find . -name \"*.py\"", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-064-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:198:{"command": "find src -type f", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-065-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:201:{"command": "rm app/test.txt", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-066-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:204:{"command": "rm -f temp.log", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-067-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:207:{"command": "rm -rf scratch/temp", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-068-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:210:{"command": "rm -rf .cache", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-069-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:213:{"command": "rm -rf tmp/cache", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-070-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:216:{"command": "rm -rf storage/framework/cache", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-071-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:219:{"command": "cp -r src/ dst/", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-072-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:222:{"command": "mv old.txt new.txt", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-073-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:225:{"command": "head -n 20 file.txt", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-074-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:228:{"command": "tail -n 20 file.txt", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-075-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:231:{"command": "wc -l file.txt", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-076-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:234:{"command": "df -h", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-077-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:237:{"command": "du -sh .", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-078-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:240:{"command": "chmod +x script.sh", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-079-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:243:{"command": "echo \"hello\" > log.txt", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-080-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:246:{"command": "whoami", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-081-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:249:{"command": "rm -rf /", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-082-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:252:{"command": "rm -rf /*", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-083-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:255:{"command": "rm -r -f /", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-084-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:258:{"command": "rm --recursive --force /", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-085-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:261:{"command": "rm -rf $HOME", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-086-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:264:{"command": "rm -rf ~", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-087-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:267:{"command": "rm -rf /etc", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-088-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:270:{"command": "rm -rf /usr", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-089-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:273:{"command": "rm -rf /var", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-090-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:276:{"command": "rm -rf /bin", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-091-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:279:{"command": "rm -rf .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-092-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:282:{"command": "rm -rf ..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-093-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:285:{"command": "rm -rf build/ src/", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-094-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:288:{"command": "rm -rf a.txt /var/lib/postgresql", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-095-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:291:{"command": "rm -rf /srv", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-096-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:294:{"command": "rm -rf /opt", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-097-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:297:{"command": "find / -delete", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-098-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:300:{"command": "find . -name x -exec rm {} +", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-099-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:303:{"command": "find /var -type f -delete", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-100-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:306:{"command": "python3 -c \"import shutil; shutil.rmtree(\\\"/srv\\\")\"", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-101-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:309:{"command": "python3 -c \"import os; os.remove(\\\"/etc/passwd\\\")\"", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-102-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:312:{"command": ":(){ :|:& };:", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-103-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:315:{"command": "php artisan migrate", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-104-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:318:{"command": "php artisan migrate:status", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-105-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:321:{"command": "php artisan migrate:rollback", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-106-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:324:{"command": "php artisan db:seed", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-107-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:327:{"command": "php artisan migrate:fresh", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-108-pro", "type": "command", "use_case": "DATABASE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:330:{"command": "php artisan db:wipe", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-109-pro", "type": "command", "use_case": "DATABASE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:333:{"command": "php artisan migrate:fresh --seed", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-110-pro", "type": "command", "use_case": "DATABASE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:336:{"command": "python3 manage.py migrate", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-111-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:339:{"command": "python3 manage.py showmigrations", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-112-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:342:{"command": "python3 manage.py flush", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-113-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:345:{"command": "npx prisma migrate dev", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-114-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:348:{"command": "npx prisma migrate deploy", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-115-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:351:{"command": "npx prisma migrate reset", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-116-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:354:{"command": "alembic upgrade head", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-117-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:357:{"command": "alembic downgrade base", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-118-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:360:{"command": "npm test", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-119-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:363:{"command": "npm run test:unit", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-120-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:366:{"command": "npm run test:e2e", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-121-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:369:{"command": "npm run lint", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-122-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:372:{"command": "pytest", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-123-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:375:{"command": "pytest tests/", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-124-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:378:{"command": "pytest -v", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-125-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:381:{"command": "pytest -k test_auth", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-126-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:384:{"command": "python3 -m unittest", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-127-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:387:{"command": "python3 -m unittest discover", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-128-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:390:{"command": "composer test", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-129-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:393:{"command": "cargo test", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-130-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:396:{"command": "cargo clippy", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-131-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:399:{"command": "go test ./...", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-132-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:402:{"command": "ruff check .", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-133-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:405:{"command": "eslint .", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-134-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:408:{"command": "php artisan test", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-135-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:409:{"command": "bash clearer-engineering/tests/run-all-tests.sh", "decision": "allow", "env": "development", "has_alerts": false, "id": "CMD-136-dev", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:410:{"command": "bash clearer-engineering/tests/run-all-tests.sh", "decision": "allow", "env": "staging", "has_alerts": false, "id": "CMD-136-sta", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:411:{"command": "bash clearer-engineering/tests/run-all-tests.sh", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-136-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:414:{"command": "bash clearer-engineering/scripts/test-runner.sh", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-137-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:417:{"command": "bash clearer-engineering/scripts/preflight.sh", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-138-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:420:{"command": "npm run build", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-139-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:423:{"command": "npm install", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-140-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:426:{"command": "npm ci", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-141-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:429:{"command": "composer install", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-142-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:432:{"command": "composer update", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-143-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:435:{"command": "pip install -r requirements.txt", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-144-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:438:{"command": "cargo build", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-145-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:441:{"command": "cargo build --release", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-146-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:444:{"command": "go build ./...", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-147-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:447:{"command": "docker build -t app .", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-148-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:450:{"command": "docker compose up -d", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-149-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:453:{"command": "docker compose ps", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-150-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:456:{"command": "docker compose down", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-151-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:459:{"command": "docker compose logs", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-152-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:462:{"command": "terraform plan", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-153-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:465:{"command": "terraform destroy", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-154-pro", "type": "command", "use_case": "INFRASTRUCTURE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:468:{"command": "kubectl delete pod app", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-155-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:471:{"command": "kubectl delete namespace default", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-156-pro", "type": "command", "use_case": "INFRASTRUCTURE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:474:{"command": "curl -s http://localhost:8000", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-157-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:477:{"command": "rtk git status", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-158-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:480:{"command": "rtk git diff", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-159-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:483:{"command": "rtk git log -n 5", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-160-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:486:{"command": "rtk pytest", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-161-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:489:{"command": "rtk npm test", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-162-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:492:{"command": "rtk cargo test", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-163-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:495:{"command": "rtk ruff check", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-164-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:498:{"command": "rtk php artisan test", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-165-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:501:{"command": "rtk git reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-166-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:504:{"command": "rtk git reset --hard HEAD~1", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-167-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:507:{"command": "rtk git clean -fd", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-168-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:510:{"command": "rtk php artisan migrate:fresh", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-169-pro", "type": "command", "use_case": "DATABASE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:513:{"command": "rtk rm -rf /", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-170-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:516:{"command": "rtk git push origin main --force", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-171-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:519:{"command": "git status && ls -la", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-172-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:522:{"command": "npm test && git status", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-173-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:525:{"command": "git status; ls", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-174-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:528:{"command": "git status || true", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-175-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:531:{"command": "echo \"hello world\"", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-176-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:534:{"command": "printf \"%s\\n\" \"test\"", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-177-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:537:{"command": "env | grep APP", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-178-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:540:{"command": "which python3", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-179-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:543:{"command": "uname -a", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-180-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:546:{"command": "date -u", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-181-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:549:{"command": "sleep 1", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-182-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:552:{"command": "git status; git reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-183-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:555:{"command": "git status && git reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-184-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:558:{"command": "ls -la || rm -rf /", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-185-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:561:{"command": "rm -rf / &", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-186-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:564:{"command": "rm -rf \"\"/", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-187-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:567:{"command": "rm -rf $'\\x2f'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-188-pro", "type": "command", "use_case": "PARSER_FAIL_CLOSED"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:570:{"command": "echo $(rm -rf /)", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-189-pro", "type": "command", "use_case": "PARSER_FAIL_CLOSED"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:573:{"command": "echo ${rm_rf_var}", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-190-pro", "type": "command", "use_case": "PARSER_FAIL_CLOSED"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:576:{"command": "rm -rf \\\n/", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-191-pro", "type": "command", "use_case": "PARSER_FAIL_CLOSED"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:582:{"host": "claude", "id": "HOOK-197-claude", "response": {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO (Caso de Uso: Controle de Versão (Git)): Destructive Git reset discarding uncommitted changes (git reset --hard).\nAmbiente detectado: PRODUCTION (Evidência: Explicit parameter (--env production)).\nExecução bloqueada para prevenir perda de dados e indisponibilidade."}}, "type": "hook"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:589:{"command": "rm -rf /home/user/projeto/build", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-202-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:592:{"command": "rm -rf /home/user/projeto/src/old", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-203-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:595:{"command": "rm -rf /opt/myapp/cache", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-204-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:598:{"command": "rm -rf /var/tmp/ceh-x", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-205-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:601:{"command": "rm -rf /usr/local/lib/node_modules/foo", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-206-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:604:{"command": "rm -rf //", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-207-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:607:{"command": "rm -rf /./", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-208-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:610:{"command": "rm -rf ../..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-209-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:613:{"command": "rm -rf ./*", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-210-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:616:{"command": "rm -rf ~root", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-211-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:619:{"command": "rm -rf /var/www/site/dist", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-212-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:622:{"command": "rm -rf /srv/app/build", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-213-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:625:{"command": "rm -rf /opt/prod/app/dist/", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-214-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:628:{"command": "rm -rf /etc/nginx/coverage/", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-215-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:631:{"command": "rm -rf ../../prod-release/dist", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-216-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:634:{"command": "rm -rf /tmp/ceh-x", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-217-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:637:{"command": "rm -rf $PWD", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-218-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:640:{"command": "rm -rf \"$PWD\"/*", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-219-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:643:{"command": "rm -rf $OLDPWD", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-220-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:646:{"command": "rm -rf build/../src", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-221-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:649:{"command": "rm -rf coverage/../.git", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-222-pro", "type": "command", "use_case": "FILESYSTEM"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:652:{"command": "rm -rf /home/user/..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-223-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:655:{"command": "rm -rf /usr/local/../..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-224-pro", "type": "command", "use_case": "CATASTROPHIC"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:658:{"command": "git restore .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-225-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:661:{"command": "git restore --staged --worktree .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-226-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:664:{"command": "git restore --source=HEAD .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-227-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:667:{"command": "git restore :/", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-228-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:670:{"command": "git restore -W -S .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-229-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:673:{"command": "git restore --worktree -- .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-230-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:676:{"command": "git restore -s HEAD .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-231-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:679:{"command": "git restore ./", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-232-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:682:{"command": "git restore -- ./", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-233-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:685:{"command": "git checkout .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-234-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:688:{"command": "git checkout -- .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-235-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:691:{"command": "git checkout ./", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-236-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:694:{"command": "git checkout -- ./", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-237-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:697:{"command": "git checkout .//", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-238-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:700:{"command": "git checkout ./.", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-239-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:703:{"command": "git checkout HEAD .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-240-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:706:{"command": "git checkout HEAD -- .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-241-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:709:{"command": "git checkout @ -- .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-242-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:712:{"command": "git checkout --force main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-243-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:715:{"command": "git checkout -f", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-244-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:718:{"command": "git checkout :/", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-245-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:721:{"command": "git checkout -- '*'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-246-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:724:{"command": "git checkout -- *", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-247-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:727:{"command": "git checkout -f -- app/x.php", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-248-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:730:{"command": "git switch -f main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-249-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:733:{"command": "git switch --discard-changes main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-250-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:736:{"command": "git switch --force main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-251-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:739:{"command": "git -C . reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-252-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:742:{"command": "git --no-pager reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-253-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:745:{"command": "git -P reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-254-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:748:{"command": "git --paginate reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-255-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:751:{"command": "git --no-pager -C . reset --hard", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-256-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:754:{"command": "git checkout app/Model.php", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-257-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:757:{"command": "git checkout feature/login", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-258-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:760:{"command": "git checkout -- app/Model.php", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-259-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:763:{"command": "git checkout v1.2.0", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-260-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:766:{"command": "git restore --staged app/Model.php", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-261-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:769:{"command": "git -C sub status", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-262-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:772:{"command": "git --no-pager log -5", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-263-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:775:{"command": "git -P diff", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-264-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:778:{"command": "git -P log -5", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-265-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:781:{"command": "git switch main", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-266-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:784:{"command": "git switch -c feature", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-267-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:787:{"command": "git switch -b feature", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-268-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:790:{"command": "git checkout src/..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-269-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:793:{"command": "git checkout -- app/..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-270-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:796:{"command": "git restore src/..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-271-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:799:{"command": "git restore -- app/..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-272-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:802:{"command": "git checkout ':(top)'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-273-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:805:{"command": "git checkout ':(top).'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-274-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:808:{"command": "git restore ':(top)'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-275-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:811:{"command": "git restore ':(top).'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-276-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:814:{"command": "git checkout ':!x'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-277-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:817:{"command": "git checkout ':^x'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-278-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:820:{"command": "git checkout ':(exclude)x'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-279-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:823:{"command": "git restore ':!x'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-280-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:826:{"command": "git checkout HEAD src/..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-281-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:829:{"command": "git restore -s HEAD src/..", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-282-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:832:{"command": "git checkout ':/app/../..'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-283-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:835:{"command": "git restore ':/app/../..'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-284-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:838:{"command": "git switch -C main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-285-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:841:{"command": "git switch -C feature-x origin/main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-286-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:844:{"command": "git checkout -B main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-287-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:847:{"command": "git checkout -B release/1.0", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-288-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:850:{"command": "git restore --staged .", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-289-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:853:{"command": "git restore -S .", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-290-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:856:{"command": "git restore --staged :", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-291-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:859:{"command": "git restore --staged :(", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-292-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:862:{"command": "git restore --staged :!x", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-293-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:865:{"command": "git restore --staged --worktree .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-294-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:868:{"command": "git restore -S -W .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-295-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:871:{"command": "git restore -W -S .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-296-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:874:{"command": "git restore --worktree --staged :/", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-297-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:877:{"command": "git checkout feature/add-pdf", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-298-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:880:{"command": "git checkout fix-leaf", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-299-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:883:{"command": "git switch hotfix-ref", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-300-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:886:{"command": "git checkout -- app/self-ref", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-301-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:889:{"command": "git checkout -b fix-leaf", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-302-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:892:{"command": "git switch -c hotfix-ref", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-303-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:895:{"command": "git restore --pathspec-from-file=list.txt", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-304-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:898:{"command": "git checkout --pathspec-from-file=list.txt", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-305-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:901:{"command": "git restore --pathspec-file-nul", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-306-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:904:{"command": "git checkout . app/x", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-307-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:907:{"command": "git checkout src/.. app/x", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-308-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:910:{"command": "git checkout app/x .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-309-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:913:{"command": "git checkout main app/x", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-310-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:916:{"command": "git checkout --forc main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-311-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:919:{"command": "git switch --discard main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-312-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:922:{"command": "git switch --force-c main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-313-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:925:{"command": "git restore --staged --work .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-314-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:928:{"command": "git restore --pathspec-from=list.txt", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-315-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:931:{"command": "git restore --stag --work .", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-316-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:934:{"command": "git checkout --quiet main", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-317-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:937:{"command": "git switch --detach HEAD~1", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-318-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:940:{"command": "git checkout -- '*.php'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-319-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:943:{"command": "git restore '*.php'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-320-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:946:{"command": "git checkout -- ./*", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-321-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:949:{"command": "git checkout -- '**'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-322-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:952:{"command": "git restore -- '[a-z]*'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-323-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:955:{"command": "git checkout -- src/*", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-324-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:958:{"command": "git checkout -- 'src/*.php'", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-325-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:961:{"command": "git checkout -- \"$PWD\"", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-326-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:964:{"command": "git restore $DIR", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-327-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:967:{"command": "git checkout -- ~", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-328-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:970:{"command": "git checkout ./src/.. app/Model.php", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-329-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:973:{"command": "git switch --discard-c main", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-330-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:976:{"command": "git checkout -- \"?*.js\"", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-331-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:979:{"command": "git checkout -- ~/projects/repo", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-332-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:982:{"command": "git checkout -- tests/*", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-333-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:985:{"command": "git switch --guess main", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-334-pro", "type": "command", "use_case": "GENERAL"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:988:{"command": "git checkout -- ':/!x'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-335-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:991:{"command": "git checkout -- ':/^x'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-336-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:994:{"command": "git restore ':/!app'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-337-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:997:{"command": "git checkout -- ':/!:x'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-338-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:1000:{"command": "git restore ':/app/x'", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-339-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:1003:{"command": "git checkout -- ':/:app/x'", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-340-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:1006:{"command": "git checkout -- ':^/src'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-341-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:1009:{"command": "git restore ':!/app/Services'", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-342-pro", "type": "command", "use_case": "GIT_HISTORY"}
clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl:1012:{"command": "git checkout -- ':/config/database.php'", "decision": "allow", "env": "production", "has_alerts": false, "id": "CMD-343-pro", "type": "command", "use_case": "FILESYSTEM_SAFE"}

hook: PreToolUse
hook: PreToolUse Completed
exec
/usr/bin/zsh -lc "rg --files docs | head -30; rg -n \"def .*split|split.*command|operator|Safety Gate|safety_gate|evaluate_command|check_command\" clearer-engineering --glob '*.py' --glob '"'!tests/fixtures/*'"' | head -100; sed -n '125,180p' clearer-engineering/tests/run-all-tests.sh" in .
 succeeded in 0ms:
docs/risk_dial.md
docs/adhd_methodology_analysis.md
docs/skills_and_commands.md
docs/architecture.md
docs/safety_gate.md
docs/evidence_semantics.md
docs/agents_guide.md
docs/plano-validacao-revisao-conselho-seniors.md
docs/coding_standards.md
docs/clearer_protocol.md
docs/examples.md
docs/installation.md
docs/plano-implementacao-elevacao-ceh.md
docs/architecture/system-one-epistemology.md
docs/architecture/ci-governance-policy.md
docs/architecture/adr-007-protecao-certificado-modelo-ameacas.md
docs/architecture/runtime-and-ci-adapters.md
docs/temp_implementation/r1_commands.txt
docs/temp_implementation/README.md
docs/temp_implementation/scripts/validate_r2.py
docs/temp_implementation/scripts/validate_r6.py
docs/temp_implementation/scripts/probe_cluster1_contract_gaps.sh
docs/temp_implementation/scripts/validate_r5.py
docs/temp_implementation/scripts/validate_r4.py
docs/temp_implementation/scripts/validate_r3.py
docs/temp_implementation/scripts/e11_matrix_runner.py
docs/temp_implementation/scripts/validate_r10.py
docs/temp_implementation/scripts/validate_r7.py
docs/temp_implementation/scripts/validate_r8.py
docs/temp_implementation/scripts/validate_r9.py
clearer-engineering/scripts/evidence_report.py:123:        spec = importlib.util.spec_from_file_location("ceh_safety_gate", HERE.with_name("safety-gate.py"))
clearer-engineering/scripts/ceh_core/__init__.py:1:"""ceh_core - Módulos internos reutilizáveis do Safety Gate do CEH."""
clearer-engineering/scripts/ceh_core/git.py:2:git.py - Analisador por tokens de comandos Git sensíveis para o Safety Gate do CEH.
clearer-engineering/scripts/ceh_core/lexer.py:14:def split_shell_pipeline(cmd_line: str) -> tuple[list[str] | None, str | None]:
clearer-engineering/scripts/safety-gate.py:103:            return True, None, [], None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
clearer-engineering/scripts/safety-gate.py:109:            return True, None, [], None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
clearer-engineering/scripts/safety-gate.py:272:            return evaluate_command(
clearer-engineering/scripts/safety-gate.py:295:                    s_res = evaluate_command(
clearer-engineering/scripts/safety-gate.py:308:        return evaluate_command(
clearer-engineering/scripts/safety-gate.py:327:        sub_eval, env, env_evidence=env_evidence, base_cwd=base_cwd, eval_fn=evaluate_command, depth=depth
clearer-engineering/scripts/safety-gate.py:336:        sub_eval, env, env_evidence=env_evidence, base_cwd=base_cwd, eval_fn=evaluate_command, depth=depth
clearer-engineering/scripts/safety-gate.py:427:def evaluate_command(
clearer-engineering/scripts/safety-gate.py:475:            evaluations.append(evaluate_command(
clearer-engineering/scripts/safety-gate.py:572:        result = evaluate_hook_payload(payload, evaluate_command)
clearer-engineering/scripts/safety-gate.py:599:    parser = argparse.ArgumentParser(description="CEH Safety Gate Command Checker")
clearer-engineering/scripts/safety-gate.py:605:        decision, reason, env, use_case = evaluate_command(args.check, explicit_env=args.env)
clearer-engineering/tests/run_claude_pr00e_eval.py:283:- **F5 Neutralizado:** O par E3a/E3b prova causalmente que o bloqueio do `git reset --hard` decorre estritamente da intervenção do Safety Gate do CEH.
clearer-engineering/scripts/ceh_core/rules.py:2:rules.py - Padrões de segurança declarativos do Safety Gate do CEH.
clearer-engineering/scripts/hook_context.py:150:    evaluate_command_fn: Callable[[str, str | None], tuple[str, str, str, str]],
clearer-engineering/scripts/hook_context.py:175:        decision, reason, _, _ = evaluate_command_fn(cmd_line, explicit_env)
clearer-engineering/scripts/hook_context.py:227:    evaluate_command_fn: Callable[[str, str | None], tuple[str, str, str, str]],
clearer-engineering/scripts/hook_context.py:267:    evaluate_command_fn: Callable[[str, str | None], tuple[str, str, str, str]],
clearer-engineering/scripts/hook_context.py:292:    return handler(tool_name, payload, evaluate_command_fn)
clearer-engineering/tests/test_hook_context.py:21:spec = importlib.util.spec_from_file_location("safety_gate", str(SCRIPTS_DIR / "safety-gate.py"))
clearer-engineering/tests/test_hook_context.py:22:safety_gate = importlib.util.module_from_spec(spec)
clearer-engineering/tests/test_hook_context.py:23:spec.loader.exec_module(safety_gate)
clearer-engineering/tests/test_hook_context.py:73:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:94:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:115:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:136:        res_reset = evaluate_hook_payload(payload_reset, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:151:        res_status = evaluate_hook_payload(payload_status, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:165:        res_push = evaluate_hook_payload(payload_push, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:187:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:201:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:221:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:236:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:312:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_hook_context.py:344:        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
clearer-engineering/tests/test_gate_differential_fuzz.py:381:        dec, reason, env_res, uc = gate.evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:510:                base_dec, base_r, _, base_uc = gate.evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:515:                    w_dec, w_r, _, w_uc = gate.evaluate_command(w_cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:586:                base_dec, base_r, _, base_uc = gate.evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:591:                    p_dec, p_r, _, p_uc = gate.evaluate_command(p_cmd, explicit_env=env)
clearer-engineering/tests/test_gate_differential_fuzz.py:639:            dec, reason, env, uc = gate.evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_git_canonicalization.py:24:safety_gate = import_module("safety-gate")
clearer-engineering/tests/test_git_canonicalization.py:25:evaluate_command = safety_gate.evaluate_command
clearer-engineering/tests/test_git_canonicalization.py:44:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:57:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:62:        decision, reason, env, use_case = evaluate_command("git checkout .", explicit_env="staging")
clearer-engineering/tests/test_git_canonicalization.py:69:        decision, reason, env, use_case = evaluate_command("git checkout .", explicit_env="development")
clearer-engineering/tests/test_git_canonicalization.py:87:                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:104:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:126:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env=None)
clearer-engineering/tests/test_git_canonicalization.py:144:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_git_canonicalization.py:162:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:176:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:190:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:201:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:223:            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:238:            dec_prod, _, _, uc_prod = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:242:            dec_sta, reason_sta, _, _ = evaluate_command(cmd, explicit_env="staging")
clearer-engineering/tests/test_git_canonicalization.py:247:            dec_dev, _, _, _ = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/test_git_canonicalization.py:263:                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:275:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:294:                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:308:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:324:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:334:                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:351:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:362:                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:378:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:389:                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_git_canonicalization.py:403:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:421:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/test_git_canonicalization.py:432:                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
clearer-engineering/tests/test_rm_fuzz.py:25:safety_gate = import_module("safety-gate")
clearer-engineering/tests/test_rm_fuzz.py:26:evaluate_command = safety_gate.evaluate_command
clearer-engineering/tests/test_rm_fuzz.py:82:            decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env, base_cwd=cwd)
clearer-engineering/tests/test_safety_matrix.py:3:test_safety_matrix.py - Comprehensive Unit Tests for CEH Safety Gate across 3 environments
clearer-engineering/tests/test_safety_matrix.py:22:safety_gate = import_module("safety-gate")
clearer-engineering/tests/test_safety_matrix.py:23:evaluate_command = safety_gate.evaluate_command
clearer-engineering/tests/test_safety_matrix.py:226:        decision, reason, env, use_case = evaluate_command(tc["cmd"], explicit_env=tc["env"])
clearer-engineering/tests/cluster4_acceptance.py:22:safety_gate = import_module("safety-gate")
clearer-engineering/tests/cluster4_acceptance.py:23:evaluate_command = safety_gate.evaluate_command
clearer-engineering/tests/cluster4_acceptance.py:41:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:47:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:56:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:62:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:68:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:77:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:83:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:89:    def test_g4_rm_split_flags_root_development(self):
clearer-engineering/tests/cluster4_acceptance.py:92:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/cluster4_acceptance.py:98:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/cluster4_acceptance.py:104:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
clearer-engineering/tests/cluster4_acceptance.py:110:        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:118:        decision, reason, env, use_case = evaluate_command("rm -rf dist/", explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:124:        decision, reason, env, use_case = evaluate_command("rm -rf node_modules/.cache", explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:130:        decision, reason, env, use_case = evaluate_command("rm -f a.txt", explicit_env="production")
clearer-engineering/tests/cluster4_acceptance.py:136:        decision, reason, env, use_case = evaluate_command("rm -rf ./build", explicit_env="production")
run_test "Script: diff-audit.sh execution" \
    "bash '$PLUGIN_DIR/scripts/diff-audit.sh' | grep 'CEH Diff & Blast Radius Audit' >/dev/null"

run_test "Script: evidence-report canônico (seções do Response Contract e veredito calculado por evidência)" \
    "python3 '$PLUGIN_DIR/tests/test_evidence_report.py' >/dev/null 2>&1"

# 5. Deterministic Test Runner & Non-Masking Tests
run_test "Test Runner: Success scenario returns exit code 0" \
    "TMP=\$(mktemp -d); (cd \"\$TMP\" && bash \"$PLUGIN_DIR/scripts/test-runner.sh\" 'true' | grep 'STATUS:    PASS' >/dev/null); RES=\$?; rm -rf \"\$TMP\"; test \$RES -eq 0"

run_test "Test Runner: Failing test correctly reports FAIL without masking" \
    "TMP=\$(mktemp -d); RUNNER_OUTPUT=\$(cd \"\$TMP\" && bash \"$PLUGIN_DIR/scripts/test-runner.sh\" 'false' 2>&1); RUNNER_EXIT=\$?; rm -rf \"\$TMP\"; [[ \$RUNNER_EXIT -ne 0 && \"\$RUNNER_OUTPUT\" == *'STATUS:    FAIL'* ]]"

run_test "Test Runner: Runtime Adapter gracefully handles stopped containers on native host" \
    "TMP=\$(mktemp -d); touch \"\$TMP/docker-compose.yml\"; (cd \"\$TMP\" && bash \"$PLUGIN_DIR/scripts/test-runner.sh\" 'true' | grep -q 'Executando diretamente no Host Nativo'); RES=\$?; rm -rf \"\$TMP\"; test \$RES -eq 0"

# 6. Global Agent Profile Availability & Tools Configuration
run_test "Agent Profile in profiles/ has write and execution tools declared" \
    "grep -q 'write_to_file' '$PLUGIN_DIR/profiles/clearer-harness.agent.md' && grep -q 'run_command' '$PLUGIN_DIR/profiles/clearer-harness.agent.md'"


run_test "Plugin Subagent 'ceh-implementer' has code editing tools" \
    "grep -q 'write_to_file' '$PLUGIN_DIR/agents/implementer/agent.md' && grep -q 'replace_file_content' '$PLUGIN_DIR/agents/implementer/agent.md'"

run_test "Plugin Subagent 'ceh-test-engineer' has execution and editing tools" \
    "grep -q 'run_command' '$PLUGIN_DIR/agents/test-engineer/agent.md' && grep -q 'write_to_file' '$PLUGIN_DIR/agents/test-engineer/agent.md'"

run_test "Skill: clearer-bugfix implements Systematic Debugging 5 Blocking Gates" \
    "grep -q 'Gate 0 — TRIAGE' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md' && grep -q 'Gate 1 — REPRODUCE' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md' && grep -q 'Gate 2 — ISOLATE' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md' && grep -q 'Gate 3 — ROOT CAUSE' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md' && grep -q 'Gate 4 — FIX & HARDEN' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md'"

run_test "Skill: native learned-lesson skill packaged with dev-memory support" \
    "test -f '$PLUGIN_DIR/skills/learned-lesson/SKILL.md' && grep -q 'Learned Lesson Engine v2.0' '$PLUGIN_DIR/skills/learned-lesson/SKILL.md' && grep -q 'dev-memory' '$PLUGIN_DIR/skills/learned-lesson/SKILL.md'"

run_test "Subagent: ceh-investigator includes Falsifiable Hypotheses Matrix guidance" \
    "grep -q 'Matriz de Hipóteses Falsificáveis' '$PLUGIN_DIR/agents/investigator/agent.md'"

run_test "Subagent: ceh-reviewer verifies regression detector and anti-opportunistic refactoring" \
    "grep -q 'clearer-bugfix' '$PLUGIN_DIR/agents/reviewer/agent.md' && grep -q 'Detector' '$PLUGIN_DIR/agents/reviewer/agent.md'"

run_test "Skill: clearer-adhd packaged with Ponytail UX 10 Heuristics & Break-Rules" \
    "test -f '$PLUGIN_DIR/skills/clearer-adhd/SKILL.md' && grep -q 'Lead with Action' '$PLUGIN_DIR/skills/clearer-adhd/SKILL.md' && grep -q 'Break-Rules' '$PLUGIN_DIR/skills/clearer-adhd/SKILL.md' && grep -q 'Ponytail UX' '$PLUGIN_DIR/rules/AGENTS.md'"

# 7. Shell Aliases Configuration
run_test "Shell alias template in config/aliases.sh declares 'agy-ceh'" \
    "grep -q \"^alias agy-ceh='agy --agent clearer-harness'\" '$PLUGIN_DIR/config/aliases.sh'"

run_test "Shell alias template in config/aliases.sh declares 'ceh-evals'" \
    "grep -q '^alias ceh-evals=' '$PLUGIN_DIR/config/aliases.sh'"

# 8. Deterministic Smoke-Eval Suite
run_test "Smoke-Eval: Harness falsifiability and fail-closed criteria (5/5 PASS)" \
    "python3 '$PLUGIN_DIR/tests/cluster2_acceptance.py' --clean-eval-smoke >/dev/null"

# 9. Cluster 1 Acceptance Suite (R1, R2, R5) and CI contract tests (T1-T6)
run_test "Cluster 1 Acceptance: R1, R2, R5 e contratos T1-T6 (38 cenários)" \
    "python3 '$PLUGIN_DIR/tests/cluster1_acceptance.py' >/dev/null"

hook: PreToolUse
hook: PreToolUse Completed
exec
/usr/bin/zsh -lc "cat clearer-engineering/scripts/ceh_core/lexer.py; sed -n '427,505p' clearer-engineering/scripts/safety-gate.py; sed -n '1,120p' clearer-engineering/tests/test_gate_differential_fuzz.py; sed -n '1,160p' docs/safety_gate.md" in .
 succeeded in 0ms:
"""
lexer.py - Analisador léxico e normalizador de pipelines de shell do CEH.
Contém:
- split_shell_pipeline: Decompõe pipelines em comandos atômicos com parser caractere a caractere (FSM).
- normalize_command_for_evaluation: Remove aspas superficiais de comandos (quote-removal).
"""
from __future__ import annotations

import os
import re
import shlex


def split_shell_pipeline(cmd_line: str) -> tuple[list[str] | None, str | None]:
    """
    Decompõe uma linha de comando em subcomandos atômicos, respeitando aspas simples e duplas,
    escapes e operadores de controle de shell (;, &&, ||, |, &).
    Rejeita construções que impeçam inspeção determinística de segurança em Fail-Closed:
    - ANSI-C quoting ($'...') e locale quoting ($"...")
    - Subshells ($(...) ou `...`)
    - Process substitution (<(...) ou >(...))
    - Aspas ou escapes não balanceados
    """
    tokens, buf, i, n = [], [], 0, len(cmd_line)
    quote, escaped, paren_depth = None, False, 0

    while i < n:
        c = cmd_line[i]
        if escaped:
            buf.append(c)
            escaped = False
            i += 1
            continue

        if c == "\\":
            if quote == "'":
                buf.append(c)
            else:
                if i + 1 < n and cmd_line[i+1] in ("\n", "\r"):
                    return None, "Continuação de linha por barra invertida (line continuation) detectada"
                escaped = True
                buf.append(c)
            i += 1
            continue

        if quote:
            if c == quote:
                quote = None
                buf.append(c)
                i += 1
                continue

            # Dentro de aspas duplas, o shell avalia subshells e expansões de parâmetros
            if quote == '"':
                if c == "`":
                    return None, "Backtick subshell (`...`) detectada dentro de aspas duplas"
                if c == "$" and i + 1 < n and cmd_line[i+1] == "(":
                    return None, "Subshell ($(...)) detectada dentro de aspas duplas"
                if c == "$" and i + 1 < n and cmd_line[i+1] == "{":
                    return None, "Expansão de parâmetro (${...}) detectada dentro de aspas duplas"

            buf.append(c)
            i += 1
            continue

        if c in ("'", '"'):
            # Detecta ANSI-C ou locale quoting ($'...' ou $"...")
            if i > 0 and cmd_line[i-1] == "$":
                return None, "ANSI-C ($'...') ou locale ($\"...\") quoting detectado"
            quote = c
            buf.append(c)
            i += 1
            continue

        # Detecta subshells ou substituições de processo fora de aspas
        if c == "`":
            return None, "Backtick subshell (`...`) detectada"
        if c == "$" and i + 1 < n and cmd_line[i+1] == "(":
            return None, "Subshell ($(...)) detectada"
        if c == "$" and i + 1 < n and cmd_line[i+1] == "{":
            return None, "Expansão de parâmetro (${...}) detectada"
        if c in ("<", ">") and i + 1 < n and cmd_line[i+1] == "(":
            return None, "Process substitution (<(...) ou >(...)) detectada"

        if c == "(" and (i == 0 or cmd_line[i-1] in (" ", "\t", ";", "&", "|", "(", "\n", "\r")):
            paren_depth += 1
            buf.append(c)
            i += 1
            continue
        if c == ")" and paren_depth > 0:
            paren_depth -= 1
            buf.append(c)
            i += 1
            continue

        if paren_depth > 0:
            buf.append(c)
            i += 1
            continue

        def flush():
            nonlocal buf
            sub = "".join(buf).strip()
            if sub:
                tokens.append(sub)
            buf = []

        # Operadores de controle e terminadores de instrução (;, \n, \r\n)
        if c in (";", "\n", "\r"):
            flush()
            if c == "\r" and i + 1 < n and cmd_line[i+1] == "\n":
                i += 2
            else:
                i += 1
            continue

        if c == "&":
            if i + 1 < n and cmd_line[i+1] == "&":
                flush()
                i += 2
                continue
            prev_char = cmd_line[i-1] if i > 0 else ""
            next_char = cmd_line[i+1] if i + 1 < n else ""
            if prev_char == ">" or next_char == ">" or (prev_char in ("1", "2") and i > 1 and cmd_line[i-2] == ">"):
                buf.append(c)
                i += 1
                continue
            flush()
            i += 1
            continue

        if c == "|":
            if i + 1 < n and cmd_line[i+1] == "|":
                flush()
                i += 2
                continue
            flush()
            i += 1
            continue

        buf.append(c)
        i += 1

    if quote:
        return None, "Aspas não fechadas na linha de comando"
    if escaped:
        return None, "Caractere de escape pendente no final da linha"
    if paren_depth != 0:
        return None, "Parênteses não balanceados na linha de comando"

    last_sub = "".join(buf).strip()
    if last_sub:
        tokens.append(last_sub)
    return tokens, None


def extract_subshell_command(subcmd: str) -> str | None:
    """Extrai o comando interno de um subshell ( ... ) preservando contexto."""
    s = subcmd.strip()
    if not s.startswith("("):
        return None
    depth, quote, escaped = 0, None, False
    for i, c in enumerate(s):
        if escaped:
            escaped = False; continue
        if c == "\\":
            if quote != "'": escaped = True
            continue
        if quote:
            if c == quote: quote = None
            continue
        if c in ("'", '"'):
            quote = c; continue
        if c == "(":
            depth += 1
        elif c == ")" and depth > 0:
            depth -= 1
            if depth == 0: return s[1:i].strip()
    return None


def normalize_command_for_evaluation(subcmd: str) -> str:
    """
    Remove aspas superficiais de palavras de comando (quote-removal) para prevenir evasões
    como p''hp artisan migrate:fresh. Se shlex falhar, retorna o subcomando original.
    """
    try:
        tokens = shlex.split(subcmd, posix=True)
        if tokens:
            return " ".join(tokens)
    except Exception:
        pass
    return subcmd


def _consume_flags(tokens: list[str], idx: int, arg_opts: set[str]) -> int:
    n = len(tokens)
    while idx < n and tokens[idx].startswith("-"):
        tok = tokens[idx]
        if tok == "--":
            return idx + 1
        if (tok in arg_opts or (not tok.startswith("--") and len(tok) > 1 and f"-{tok[-1]}" in arg_opts)) and idx + 1 < n:
            idx += 2
        elif any(tok.startswith(opt + "=") for opt in arg_opts):
            idx += 1
        else:
            idx += 1
    return idx


def resolve_command_head(tokens: list[str]) -> tuple[int, str | None]:
    """
    Identifica o comando executável real consumindo prefixos transparentes ou
    identificando executores de string (Handoff 026 §3, Handoff 027 §3, AB1/AC1).
    """
    n, idx = len(tokens), 0
    while idx < n:
        tok = os.path.basename(tokens[idx])
        if tok == "rtk":
            idx += 2 if (idx + 1 < n and tokens[idx + 1] == "proxy") else 1
            continue
        if tok in ("nohup", "builtin"):
            idx += 2 if (idx + 1 < n and tokens[idx + 1] == "--") else 1
            continue
        if tok == "command":
            idx = _consume_flags(tokens, idx + 1, set())
            continue
        if tok == "exec":
            idx = _consume_flags(tokens, idx + 1, {"-a"})
            continue
        if tok == "nice":
            idx = _consume_flags(tokens, idx + 1, {"-n", "--adjustment"})
            if idx < n and re.match(r"^-\d+$", tokens[idx]): idx += 1
            continue
        if tok == "timeout":
            idx = _consume_flags(tokens, idx + 1, {"-k", "--kill-after", "-s", "--signal"})
            if idx < n and not tokens[idx].startswith("-"): idx += 1
            continue
        if tok in ("sudo", "doas"):
            idx = _consume_flags(tokens, idx + 1, {"-u", "-g", "-h", "-p", "-r", "-t", "-T", "-C"})
            continue
        if tok == "env":
            for i in range(idx + 1, n):
                c = tokens[i]
                if c in ("-S", "--split-string") and i + 1 < n: return idx, tokens[i + 1]
                if c.startswith(("-S=", "--split-string=")): return idx, c.split("=", 1)[1]
                if c.startswith("-S") and len(c) > 2: return idx, c[2:]
            idx += 1
            while idx < n:
                c = tokens[idx]
                if c in ("-u", "--unset", "-C", "--chdir") and idx + 1 < n: idx += 2
                elif c == "--": idx += 1; break
                elif c.startswith("-") or ("=" in c and not c.startswith("=")): idx += 1
                else: break
            continue
        if tok == "time":
            idx = _consume_flags(tokens, idx + 1, {"-o", "--output", "-f", "--format"})
            continue
        if tok in ("stdbuf", "ionice", "chrt", "taskset"):
            start_i = idx
            idx = _consume_flags(tokens, idx + 1, {"-i", "-o", "-e", "-c", "--cpu-list", "-n", "-p", "-P", "-u"})
            if tok == "taskset":
                has_cpu = any(t in ("-c", "--cpu-list") or t.startswith(("-c=", "--cpu-list=")) or (t.startswith("-") and not t.startswith("--") and "c" in t) for t in tokens[start_i:idx])
                if not has_cpu and idx < n and not tokens[idx].startswith("-"): idx += 1
            elif tok == "chrt" and idx < n and not tokens[idx].startswith("-"): idx += 1
            continue
        if tok == "xargs":
            idx = _consume_flags(tokens, idx + 1, {"-n", "-P", "-d", "-s", "-E", "-L", "-I"})
            continue
        if tok == "eval": return idx, " ".join(tokens[idx + 1:])
        if tok == "su":
            for i in range(idx + 1, n):
                t = tokens[i]
                if t in ("-c", "--command") and i + 1 < n: return idx, tokens[i + 1]
                if t.startswith("-c="): return idx, t[3:]
                if t.startswith("--command="): return idx, t[10:]
            break
        if tok == "watch":
            i = _consume_flags(tokens, idx + 1, {"-n", "--interval"})
            if i < n: return idx, " ".join(tokens[i:])
            break
        break
    return idx, None


def substitute_positional_args(script: str, args: list[str]) -> str:
    """Substitui argumentos posicionais ($0, $1..., ${0}, "$@") em scripts de shell (AB3)."""
    if not args: return script
    res = script
    if len(args) > 1:
        res = res.replace('"$@"', " ".join(f'"{a}"' for a in args[1:])).replace('$@', " ".join(args[1:]))
    elif len(args) == 1:
        res = res.replace('"$@"', '').replace('$@', '')
    for idx, val in enumerate(args):
        res = re.sub(r'\$\{' + str(idx) + r'\}|\$' + str(idx) + r'(?!\d)', val, res)
    return res

def evaluate_command(
    cmd_line: str,
    explicit_env: str | None = None,
    base_cwd: Path | str | None = None,
    depth: int = 0,
    scan_suffixes: bool = True,
) -> tuple[str, str, str, str]:
    """
    Evaluates a command line string against environment safety rules, decomposing
    compound commands and aggregating decisions with priority: CATASTROPHIC > DENY > ASK > ALLOW.
    """
    if depth > 3:
        return (
            "deny",
            f"[CEH SAFETY GATE - FAIL-CLOSED] Limite de profundidade de recursão/desembrulho excedido (depth={depth} > 3).",
            "development" if explicit_env is None else explicit_env,
            "CATASTROPHIC",
        )

    if not cmd_line or not cmd_line.strip():
        return "allow", "Empty command", "development", "GENERAL"

    cmd_normalized = cmd_line.strip()
    env, env_evidence = detect_environment(explicit_env, cmd_normalized, target_dir=base_cwd)

    # Decompõe linha em subcomandos atômicos via FSM Lexer
    subcommands, parse_err = split_shell_pipeline(cmd_normalized)
    if parse_err:
        return (
            "deny",
            f"[CEH SAFETY GATE - FAIL-CLOSED] Sintaxe complexa ou quoting não suportado rejeitado: {parse_err}.\n"
            f"Ambiente: {env.upper()}. Para segurança estrita, use comandos atômicos sem subshells ou construções não homologadas.",
            env,
            "PARSER_FAIL_CLOSED",
        )

    if not subcommands:
        return "allow", "Empty command after decomposition", env, "GENERAL"

    evaluations = []
    current_cwd = Path(base_cwd).resolve() if base_cwd else Path.cwd()
    current_env, current_env_ev = env, env_evidence
    persistent_repo: Path | None = None
    unresolved_cd = False

    for sub in subcommands:
        sub_inner = extract_subshell_command(sub)
        if sub_inner is not None:
            evaluations.append(evaluate_command(
                sub_inner, explicit_env=explicit_env, base_cwd=current_cwd,
                depth=depth + 1, scan_suffixes=scan_suffixes,
            ))
            continue

        try: sub_tokens = shlex.split(sub, posix=True, comments=True)
        except Exception: sub_tokens = sub.split()

        eff_cwd, tgt_repo, is_unres, is_persist, ctx_env, clean_toks = resolve_target_context(
            sub_tokens, current_cwd, persistent_repo
        )
        if not clean_toks: continue

        if is_unres:
            unresolved_cd = True
        if is_persist:
            if eff_cwd and eff_cwd.is_dir(): current_cwd = eff_cwd
            if tgt_repo: persistent_repo = tgt_repo
            new_env, new_ev = detect_environment(explicit_env=explicit_env, target_dir=current_cwd)
            if ENV_SEVERITY.get(new_env, 0) > ENV_SEVERITY.get(current_env, 0):
                current_env, current_env_ev = new_env, new_ev

        eval_cwd = eff_cwd if (eff_cwd and eff_cwd.is_dir()) else current_cwd
        sub_eval_env, sub_eval_ev = detect_environment(explicit_env=explicit_env, cmd_line=sub, target_dir=eval_cwd)
        if tgt_repo:
            repo_env, repo_ev = detect_environment(explicit_env=None, target_dir=tgt_repo)
            if ENV_SEVERITY.get(repo_env, 0) > ENV_SEVERITY.get(sub_eval_env, 0):
                sub_eval_env, sub_eval_ev = repo_env, repo_ev

        effective_env, effective_ev = current_env, current_env_ev
#!/usr/bin/env python3
"""
test_gate_differential_fuzz.py - Fuzz diferencial contra a linha de base homologada (PR-QA-A2).

Especificação (Handoffs 022 e 023):
1. Linha de base: lê o SHA em tests/fixtures/gate_baseline.txt (avançado exclusivamente pela revisão).
2. Extração hermética: extrai o gate da linha de base via git archive para diretório temporário.
3. Hermeticidade (Y3): avalia ambos os gates dentro de um repositório git temporário (git init -b dev)
   e um HOME temporário isolado.
4. Entradas completas (Y1):
   - Corpus decodificado (RAW: literal, B64: base64 decodificado; HOOK/INTEGRATION ignorados).
   - Baterias de testes adversariais (review_batteries.txt).
   - ≥ 3000 comandos gerados deterministicamente por gramática com semente fixa (random.Random(42)),
     cobrindo abreviações (--forc, --work, --discard, --pathspec-from), checkout -B, switch --force-create,
     pathspec de variáveis e til, find com -delete catastrófico e one-liners de interpretador.
5. Comparação em 3 ambientes: DEVELOPMENT, HOMOLOGACAO (STAGING), PRODUCTION.
6. Detecção estrita de relaxamentos:
   - Transições de severidade decrescente (deny -> ask, deny -> allow, ask -> allow).
   - Saída de estado CATASTROPHIC.
   - Qualquer relaxamento não autorizado em tests/fixtures/relaxamentos_justificados.txt REPROVA o teste.
7. Orçamento de tempo (Y2): impresso no log como meta (< 20s), sem asserção de TimeoutError.
"""
from __future__ import annotations

import base64
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"


def get_git_repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / ".git").exists():
            return parent
    return cur.parents[2]


REPO_ROOT = get_git_repo_root()
SCRIPTS_DIR = REPO_ROOT / "clearer-engineering" / "scripts"

BASELINE_FILE = FIXTURES_DIR / "gate_baseline.txt"
RELAXATIONS_FILE = FIXTURES_DIR / "relaxamentos_justificados.txt"
CORPUS_FILE = FIXTURES_DIR / "gate_corpus.txt"
BATTERY_FILE = FIXTURES_DIR / "review_batteries.txt"

sys.path.insert(0, str(SCRIPTS_DIR))


def load_corpus_commands(corpus_path: Path) -> list[str]:
    """Carrega comandos do corpus decodificando RAW: e B64: (ignora HOOK e INTEGRATION)."""
    cmds = []
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("HOOK:") or line.startswith("INTEGRATION:"):
            continue
        if line.startswith("RAW:"):
            cmds.append(line[4:].strip())
        elif line.startswith("B64:"):
            try:
                decoded = base64.b64decode(line[4:]).decode("utf-8").strip()
                cmds.append(decoded)
            except Exception:
                pass
        else:
            cmds.append(line)
    return cmds


def load_battery_commands(battery_path: Path) -> list[str]:
    """Carrega comandos das baterias adversariais de revisão."""
    cmds = []
    for line in battery_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 3)
        if len(parts) >= 4:
            cmds.append(parts[3].strip())
    return cmds


def generate_grammar_commands(seed: int = 42, target_unique: int = 3500) -> list[str]:
    """
    Gera >= 3000 comandos únicos por gramática determinística com semente fixa (Y1).
    Cobre:
    - abreviações de opção longa (--forc, --discard, --work, --pathspec-from, --stage, --sourc);
    - checkout -B, switch --force-create, --pathspec-from-file/--pathspec-file-nul;
    - $VAR / ${VAR} sem aspas e ~/x como pathspec do git;
    - find com -delete e com caminho inicial catastrófico (/, ~, /etc, ..);
    - one-liners de interpretador (python3 -c, node -e, perl -e, ruby -e) inócuos e destrutivos.
    """
    rng = random.Random(seed)
    cmds: set[str] = set()

    rm_flags = [
        "-rf", "-fr", "-r", "-f", "-i", "-I", "-v", "--recursive", "--force",
        "-r -f", "-rf --", "-f -r", "-r --force", "-v -r -f", "--no-preserve-root -rf"
    ]
    rm_targets = [
        ".", "..", "...", "/", "//", "///", "/etc", "/etc/hosts", "/var/log", "/tmp", "/tmp/foo",
        "/home", "/home/user", "/home/user/project", "/home/user/project/build",
        "src", "src/", "src/*", "src/app", "src/../app", "src/../../etc",
        "dist", "dist/", "build", "build/bundle.js", "coverage", "scratch",
        "node_modules/.cache", ".cache", "$PWD", "$OLDPWD", "$HOME", "${PWD}", "${HOME}",
        "~", "~/project", "~/.bashrc", "*.py", "test_*.py", "app.py", "file with space.txt",
        "./dist/../src", "./build/../.git", "dist/../../etc", "/tmp/../etc"
    ]
    rm_prefixes = ["rm", "rtk rm", "/bin/rm", "rm -v", "sudo rm"]

# Guia do Safety Gate & Políticas de Proteção por Ambiente

O **Safety Gate** é a barreira ativa de proteção do *CLEARER Engineering Harness (CEH)*. Ele intercepta comandos de shell no estágio `PreToolUse` antes de sua execução real, identificando previamente o ambiente alvo (`DEV`, `HOMOLOGAÇÃO` ou `PRODUÇÃO`) e aplicando **rigores granulares conforme os casos de uso**.

---

## 1. Identificação Prévia de Ambiente (Environment Awareness)

Antes de avaliar qualquer comando destrutivo, o Safety Gate determina o ambiente ativo seguindo uma ordem estrita de precedência:

1. **Parâmetro Explícito**: Flag `--env <development|staging|production>` via CLI.
2. **Contexto no Comando**: Menções explícitas a targets de produção/homologação na linha de comando (`--env=production`, `target=prod`, etc.).
3. **Variáveis de Ambiente**: `CEH_ENV`, `APP_ENV`, `NODE_ENV`, `ENVIRONMENT`, `ENV`, `STAGE`.
4. **Arquivos de Configuração**: `.env.production`, `.env.staging`, `.env.homolog`, `.env.local`, `.env`.
5. **Branch Git Ativa**: Se a branch for `main`, `master` ou `production` sem `.env` local declarando explicitamente dev, o rigor é preventivamente escalado para **PRODUÇÃO**.
6. **Fallback Seguro**: `development`.

---

## 2. Matriz de Rigores Granulares por Caso de Uso

| Caso de Uso | Exemplos de Comandos | Desenvolvimento (`DEV`) | Homologação (`STAGING`) | Produção (`PRODUÇÃO`) |
|---|---|---|---|---|
| **1. Banco de Dados / Migrações** | `migrate:fresh`, `db:wipe`, `DROP DATABASE`, `DROP TABLE`, `TRUNCATE`, `DELETE` sem `WHERE` | **ALLOW** (com aviso de backup/rollback local) | **ASK** (2 Alertas: Impacto HML + Backup/Rollback obrigatórios) | **DENY** (Fora de cogitação) |
| **2. Controle de Versão (Git Destrutivo)** | `git reset --hard`, `git clean -fdx`, `git push --force`, `git branch -D` | **ALLOW** (descarte local liberado para correções/spikes) | **ASK** (2 Alertas: Impacto branch compartilhada + backup de branch) | **DENY** (Bloqueio em branches protegidas: `main`, `prod`) |
| **3. Governança de CI (Pre-Push Gate)** | `git push` (em projetos com `.github/workflows/` ou `.gitlab-ci.yml`) | **ALLOW com Certificado de Voo** (`.ceh/last-ci-run.json` válido no HEAD). **DENY** se não testado ou desatualizado. | **ALLOW com Certificado de Voo**. **DENY** se não testado ou desatualizado. | **ALLOW com Certificado de Voo**. **DENY** se não testado ou desatualizado. |
| **4. Sistema de Arquivos (Filesystem)** | `rm -rf <dir>`, remoção em massa | **ALLOW** (para pastas do workspace, build, cache, scratch) | **ASK** (2 Alertas: impacto storage compartilhado) | **DENY** (Proibido apagar diretórios fora de temp/logs) |
| **5. Infraestrutura & Nuvem** | `terraform destroy`, `kubectl delete ns`, `docker system prune -a` | **ALLOW** (para containers/volumes locais dev) | **ASK** (2 Alertas: impacto de infraestrutura compartilhada) | **DENY** (Fora de cogitação) |
| **6. Execução Segura (Build/Test)** | `npm test`, `pest`, `phpunit`, `npm run build`, `git status` | **ALLOW** | **ALLOW** | **ALLOW** |
| **7. Catastrófico de Sistema Operacional** | `rm -rf /`, `rm -rf ~`, `mkfs`, fork bombs, `gcloud projects delete` | **DENY** | **DENY** | **DENY** |

---

## 3. Comportamento Detalhado por Nível de Ambiente

### Pre-Push CI Safety Gate (Tolerância Zero a Pipeline Vermelho)
Em qualquer projeto onde for detectada infraestrutura de integração contínua:
- O agente **NUNCA** pode executar `git push` com base apenas em testes parciais, linters ou checagens isoladas.
- O Safety Gate valida fisicamente se `.ceh/last-ci-run.json` existe, se possui `status: "PASS"`, `exit_code: 0` e se o `commit_hash` registrado é rigorosamente idêntico ao commit hash atual do repositório (`git rev-parse HEAD`).
- Se houver divergência ou falha, o gate bloqueia imediatamente com **`DENY`** e instrui a execução da suíte canônica de testes via `bash scripts/test-runner.sh`.

### A. Desenvolvimento & Teste (`DEV` / `TEST` / `LOCAL`)
- **Regra**: Destrutivos de desenvolvimento são **PERMITIDOS (`ALLOW`)**.
- **Justificativa**: O desenvolvedor e o agente precisam de agilidade para iterar em schemas, resetar banco local, rodar fixtures de teste e descartar código de spike para correções.
- **Salvaguarda**: O Safety Gate emite aviso de prontidão de backup/rollback prévio para permitir recuperação imediata em caso de erro.
- **Exceção**: Comandos catastróficos de sistema operacional (`rm -rf /`, `mkfs`) mantêm **`DENY`**.

### B. Homologação (`HOMOLOGAÇÃO` / `STAGING` / `UAT`)
- **Regra**: Comandos destrutivos exigem **CONFIRMAÇÃO OBRIGATÓRIA (`ASK`)** com **dois alertas explícitos**:
  - **⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]**: Alerta sobre o caso de uso e blast radius no ambiente compartilhado de validação.
  - **⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]**: Exige comprovação de que o comando de BACKUP prévio foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.

### C. Produção (`PRODUÇÃO` / `PROD`)
- **Regra**: Comandos destrutivos estão **FORA DE COGITAÇÃO (`DENY` Absoluto)**.
- **Justificativa**: O agente de IA nunca deve executar operações destrutivas em banco produtivo, force-push em branches principais ou remoção massiva de infraestrutura em ambiente de produção.

---

## 4. Como Funciona a Interceptação

O script [`scripts/safety-gate.py`](../clearer-engineering/scripts/safety-gate.py) recebe a chamada da ferramenta em formato JSON via hook `PreToolUse`:

```json
{
  "toolCall": {
    "name": "run_command",
    "args": {
      "CommandLine": "php artisan migrate:fresh"
    }
  }
}
```

E retorna a resposta em JSON auditável consumida nativamente pelo Google Antigravity:

```json
{
  "decision": "ask",
  "reason": "[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE - Caso de Uso: Banco de Dados]\n⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]: O comando possui potencial destrutivo/estrutural (Destructive Laravel migration).\n   Ambiente detectado: STAGING (Evidência: Environment variable APP_ENV=staging).\n⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]: É obrigatório certificar-se de que o comando de BACKUP prévio foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.\nConfirma a execução com rollback assegurado?",
  "environment": "staging",
  "use_case": "DATABASE"
}
```

---

## 5. Imunidade a Evasão & Neutralização de Proxies CLI (RTK)

Para viabilizar a economia massiva de tokens de terminal via ferramentas como o **RTK (Rust Token Killer)** sem comprometer a segurança, o Safety Gate possui um mecanismo de normalização de prefixos:

```python
# Strip preventivo do proxy CLI para avaliar o comando real
cmd_eval = re.sub(r"^\s*rtk(?:\s+proxy)?\s+", "", cmd_normalized)
```

### Garantias de Segurança:
1. **Zero Bypass em Produção (`DENY`)**:
   - Um comando como `rtk php artisan migrate:fresh` ou `rtk git reset --hard HEAD~1` é avaliado exatamente como `php artisan migrate:fresh` ou `git reset --hard HEAD~1`. Em ambiente de produção, ele é sumariamente bloqueado com decisão `DENY` ("fora de cogitação").
2. **Confirmação em Dois Alertas em Homologação (`ASK`)**:
   - Comandos destrutivos envelopados por `rtk` em `staging` continuam exigindo os dois alertas obrigatórios (Impacto HML + Salvaguardas de Backup/Rollback).
3. **Bloqueio Catastrófico Universal**:
   - Tentativas de evasão como `rtk rm -rf /` ou `rtk proxy rm -rf /` são interceptadas de forma imediata como `CATASTROPHIC BLOCK` em qualquer ambiente (inclusive `development`).
4. **Validação Contínua via Testes Automatizados**:
   - A suíte [`test_safety_matrix.py`](../clearer-engineering/tests/test_safety_matrix.py) valida matematicamente todos os cenários envelopados por `rtk`, garantindo conformidade determinística e regressão zero.


codex
VEREDITO: RESSALVAS  
CERTEZA: 0.96 — O plano descreve o lexer e o `evaluate_command` como alvo do fuzz; no repositório, o lexer já divide comandos por `;`, `&&`, `||`, `|` e novas linhas, e o gate agrega decisões com prioridade `CATASTROPHIC > DENY > ASK > ALLOW`. Também já existe `test_gate_differential_fuzz.py`, com geração determinística, corpus adversarial e avaliação em três ambientes. Esses fatos sustentam os riscos abaixo, mas não permitem confirmar os 2.000 casos propostos, pois o novo teste ainda não existe.

ANALISE_ESPECIALIZADA:  
O invariante proposto é relevante, mas está subespecificado como propriedade formal. “Segmento destrutivo” precisa ser definido por uma fonte independente do gate — por exemplo, uma gramática de casos com rótulo esperado — para evitar que o gerador e o teste compartilhem a mesma classificação errada. Cada comando composto gerado deve preservar a relação entre o comando executável e seu rótulo; aspas e parênteses podem mudar essa semântica, e texto destrutivo dentro de uma string não prova que houve segmento destrutivo executável.

A regra declarada exige `deny`, mas a agregação documentada também admite `CATASTROPHIC`, enquanto comandos com controle de estado, como `git push`, podem ter regras próprias. Especifique o resultado proibido como “nunca `allow`” ou restrinja os casos a operações cujo resultado contratual seja `deny`. Em ambos os casos, valide que o ambiente efetivo é `production`; caso contrário, o teste pode passar sem exercitar a política pretendida.

Os 2.000 casos aleatórios não garantem cobertura dos conectores, aspas e fronteiras perigosas, nem que a mutação de `||` seja detectada. Exija cobertura explícita por classe de operador, posição do segmento destrutivo, quoting balanceado e desbalanceado, além de casos fixos mínimos para cada classe. O fuzz deve complementar os casos determinísticos, não substituí-los. A alegação de que uma falha apresentará o “comando exato mínimo” também não decorre do plano: impressão da entrada reproduzível é direta; redução automática a um comando mínimo exige um algoritmo de shrinking especificado.

Por fim, o plano promete validar mutations de conteúdo com caminho **e linha**, mas isso requer que o parser de Markdown/YAML preserve localização; testar apenas existência de campos ou destinos não garante diagnósticos com linha. E a meta de 60 testes precisa ser conferida contra o mecanismo real de contagem: acrescentar dois `run_test` não assegura esse total se a linha de base de 58 estiver desatualizada ou os testes forem contabilizados por outro critério.

RISCOS_IDENTIFICADOS:

- Oráculo circular ou falso positivo se “destrutivo” for identificado pelo mesmo lexer/regras que estão sob teste.
- Mutação de `||` não detectada por geração aleatória sem cobertura garantida desse operador em uma composição destrutiva.
- A exigência literal de `deny` conflitar com decisões `CATASTROPHIC` ou outras decisões válidas para casos especiais; alternativamente, comandos rotulados incorretamente como destrutivos.
- Casos com aspas ou parênteses classificarem texto presente como execução efetiva, sem modelar a semântica da composição.
- “Comando mínimo” e diagnóstico com linha serem critérios não implementáveis com as garantias descritas.
- Contagem final de 60 testes não comprovada a partir da linha de base apresentada.

RECOMENDACAO_FINAL:  
Antes de homologar, refine o fuzz para usar um gerador por gramática com rótulos-oráculo independentes, cobertura obrigatória por operador e casos fixos de regressão; afirme como propriedade que nenhum caso rotulado destrutivo avaliado efetivamente em `production` resulte em `allow`. Registre entradas reproduzíveis e, se “mínimo” for requisito, especifique shrinking. Para o conteúdo, declare como serão obtidas as linhas dos diagnósticos. Confirme a contagem de testes pelo contador real da suíte e inclua evidência da execução das mutações, em vez de apenas o comportamento esperado.
tokens used
37,456
VEREDITO: RESSALVAS  
CERTEZA: 0.96 — O plano descreve o lexer e o `evaluate_command` como alvo do fuzz; no repositório, o lexer já divide comandos por `;`, `&&`, `||`, `|` e novas linhas, e o gate agrega decisões com prioridade `CATASTROPHIC > DENY > ASK > ALLOW`. Também já existe `test_gate_differential_fuzz.py`, com geração determinística, corpus adversarial e avaliação em três ambientes. Esses fatos sustentam os riscos abaixo, mas não permitem confirmar os 2.000 casos propostos, pois o novo teste ainda não existe.

ANALISE_ESPECIALIZADA:  
O invariante proposto é relevante, mas está subespecificado como propriedade formal. “Segmento destrutivo” precisa ser definido por uma fonte independente do gate — por exemplo, uma gramática de casos com rótulo esperado — para evitar que o gerador e o teste compartilhem a mesma classificação errada. Cada comando composto gerado deve preservar a relação entre o comando executável e seu rótulo; aspas e parênteses podem mudar essa semântica, e texto destrutivo dentro de uma string não prova que houve segmento destrutivo executável.

A regra declarada exige `deny`, mas a agregação documentada também admite `CATASTROPHIC`, enquanto comandos com controle de estado, como `git push`, podem ter regras próprias. Especifique o resultado proibido como “nunca `allow`” ou restrinja os casos a operações cujo resultado contratual seja `deny`. Em ambos os casos, valide que o ambiente efetivo é `production`; caso contrário, o teste pode passar sem exercitar a política pretendida.

Os 2.000 casos aleatórios não garantem cobertura dos conectores, aspas e fronteiras perigosas, nem que a mutação de `||` seja detectada. Exija cobertura explícita por classe de operador, posição do segmento destrutivo, quoting balanceado e desbalanceado, além de casos fixos mínimos para cada classe. O fuzz deve complementar os casos determinísticos, não substituí-los. A alegação de que uma falha apresentará o “comando exato mínimo” também não decorre do plano: impressão da entrada reproduzível é direta; redução automática a um comando mínimo exige um algoritmo de shrinking especificado.

Por fim, o plano promete validar mutations de conteúdo com caminho **e linha**, mas isso requer que o parser de Markdown/YAML preserve localização; testar apenas existência de campos ou destinos não garante diagnósticos com linha. E a meta de 60 testes precisa ser conferida contra o mecanismo real de contagem: acrescentar dois `run_test` não assegura esse total se a linha de base de 58 estiver desatualizada ou os testes forem contabilizados por outro critério.

RISCOS_IDENTIFICADOS:

- Oráculo circular ou falso positivo se “destrutivo” for identificado pelo mesmo lexer/regras que estão sob teste.
- Mutação de `||` não detectada por geração aleatória sem cobertura garantida desse operador em uma composição destrutiva.
- A exigência literal de `deny` conflitar com decisões `CATASTROPHIC` ou outras decisões válidas para casos especiais; alternativamente, comandos rotulados incorretamente como destrutivos.
- Casos com aspas ou parênteses classificarem texto presente como execução efetiva, sem modelar a semântica da composição.
- “Comando mínimo” e diagnóstico com linha serem critérios não implementáveis com as garantias descritas.
- Contagem final de 60 testes não comprovada a partir da linha de base apresentada.

RECOMENDACAO_FINAL:  
Antes de homologar, refine o fuzz para usar um gerador por gramática com rótulos-oráculo independentes, cobertura obrigatória por operador e casos fixos de regressão; afirme como propriedade que nenhum caso rotulado destrutivo avaliado efetivamente em `production` resulte em `allow`. Registre entradas reproduzíveis e, se “mínimo” for requisito, especifique shrinking. Para o conteúdo, declare como serão obtidas as linhas dos diagnósticos. Confirme a contagem de testes pelo contador real da suíte e inclua evidência da execução das mutações, em vez de apenas o comportamento esperado.
