# Handoff 060 — Playbook Agnóstico de Integração Multi-Harness (CEH Core)

- **Versão de Referência:** CEH v1.3.0 (Commit `1b26e10` / `staging`)
- **Status:** **Pronto para Consumo Externo** (ADR-006 implementado e homologado)
- **Destinatários:** Agentes de IA e Desenvolvedores operando em harnesses externos (Muse, Codex, Claude Code, Cursor, Hermes, CLI custom).
- **Repositório Fonte:** [antigravity-clearer-engineering-harness](https://github.com/nandinhos/antigravity-clearer-engineering-harness)

---

## 1. Objetivo deste Documento

Este handoff é um **guia técnico autossuficiente e executável**. Ao ser lido por qualquer agente de IA (como no Muse ou no Codex) dentro de seu respectivo repositório, ele fornece todas as especificações e contratos necessários para:
1. Plugar o **Núcleo de Políticas Portável (`ceh_core`)** do CLEARER Engineering Harness sem reescrever lógica de regras.
2. Adotar as **Regras Cognitivas e Protocolo CLEARER** (`AGENTS.md`) como instruções de sistema do host.
3. Configurar a **interceptação pré-execução (Safety Gate)** de comandos shell no formato nativo do host.

---

## 2. Visão Arquitetural Desacoplada (ADR-006)

O CEH opera sob estrita separação entre **Núcleo de Políticas** e **Adaptador de Host**:

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      HOST ESPECÍFICO (Muse / Codex)                    │
 │                                                                        │
 │   Prompt de Sistema             Mecanismo de Interceptação             │
 │   (Instruções CLEARER)          (PreToolUse / Hook / Proxy / Wrapper)  │
 └─────────────────┬───────────────────────────────┬──────────────────────┘
                   │                               │
                   │                               │ Executa CLI ou
                   │                               │ importa módulo
                   ▼                               ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      NÚCLEO DO CEH (ceh_core/)                         │
 │                                                                        │
 │  • Stdlib-Only (Python 3.9+)       • Sem dependências externas         │
 │  • Lexer & Tokenizer               • Normalização Canônica             │
 │  • Detecção de Ambientes           • Avaliação de Comandos Destrutivos │
 │    (DEV, STAGING, PROD)              (rm, git, push, find, scripts)    │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Componentes do Núcleo Portável (`ceh_core/`)

O diretório [`clearer-engineering/scripts/ceh_core/`](../../../clearer-engineering/scripts/ceh_core) é 100% autocontido (stdlib Python):

| Módulo | Responsabilidade | Contrato Principal |
|---|---|---|
| **`environment.py`** | Classificação de ambiente (`DEV`, `STAGING`, `PROD`) por variáveis, `.env`, branch Git e tokens de shell com resolução física de symlinks (D04). | `detect_environment(explicit_env, cmd_line, target_dir)` $\to$ `(env, evidence)` |
| **`rm.py`** | Avaliação de comandos de exclusão (`rm`, `rm -rf`), atalhos seguros (`tmp/`, `scratch/`), proteção de raiz e detecção catastrófica. | `evaluate_rm_command(cmd, env, env_evidence, base_cwd)` $\to$ `(decision, reason, env, severity)` |
| **`git.py`** | Avaliação de comandos Git destrutivos (`reset --hard`, `clean -fd`, `checkout -f`, `branch -D`). | `evaluate_git_command(...)` $\to$ `(decision, reason, env, severity)` |
| **`push.py`** | Validação de `git push` contra o certificado local da suíte de CI (`.ceh/last-ci-run.json`). | `evaluate_push_command(...)` $\to$ `(decision, reason, env, severity)` |
| **`find.py`** | Bloqueio de deleção via `find -delete` ou `find -exec rm`. | `evaluate_find_command(...)` $\to$ `(decision, reason, env, severity)` |
| **`interpreters.py`** | Avaliação de subshells (`bash -c`, `python -c`, `sh -c`). | `evaluate_interpreter_command(...)` $\to$ `(decision, reason, env, severity)` |
| **`lexer.py`** | Tokenizer e FSM Lexer determinístico para operadores de shell (`&&`, `\|\|`, `;`, pipelines). | `split_shell_pipeline(cmd)` $\to$ `(subcommands, error)` |
| **`normalize.py`** | Ponto único de normalização de caminhos, aspas e variáveis de ambiente. | `normalize_path(path, cwd, resolve_home)` $\to$ `str` |

---

## 4. O Contrato de Decisão do Safety Gate

Qualquer chamada ao Safety Gate produz um veredito de 4 elementos:

```python
decision, reason, evaluated_env, severity = evaluate_command(
    cmd_line="rm -rf /",
    explicit_env=None,
    base_cwd=Path.cwd()
)
```

1. **`decision`** (Precedência estrita: `CATASTROPHIC > DENY > ASK > ALLOW`):
   - **`allow`**: Comando liberado para execução direta.
   - **`ask`**: Exige confirmação humana explícita (ex: comandos perigosos em `DEV` ou qualquer impacto em `STAGING`).
   - **`deny`**: Comando rejeitado sumariamente (ex: catástrofes de SO ou comandos destrutivos em `PROD`).
2. **`reason`**: Justificativa auditável com a evidência de suporte (`OBSERVED`).
3. **`evaluated_env`**: `"development"`, `"staging"` ou `"production"`.
4. **`severity`**: `"CATASTROPHIC"`, `"FILESYSTEM"`, `"VERSION_CONTROL"`, `"CI_PIPELINE"`, `"GENERAL"`.

---

## 5. Como Integrar no Repositório do seu Novo Harness

Ao abrir este handoff em um projeto do **Muse**, **Codex** ou outro agente, siga os 3 passos de integração:

### Passo 1: Disponibilizar o Núcleo no Projeto
Escolha **uma** das opções de distribuição para o novo repositório:
- **Opção A (Symlink / Referência Local — Recomendada em máquina local):**
  Criar um symlink ou link relativo apontando para a pasta `clearer-engineering/scripts/ceh_core/` do CEH instalado:
  ```bash
  mkdir -p ./ceh && ln -s ~/.gemini/config/plugins/clearer-engineering/scripts/ceh_core ./ceh/ceh_core
  ```
- **Opção B (Git Submodule ou Cópia Vendorizada):**
  Copiar a pasta `ceh_core/` e os scripts [`safety-gate.py`](../../../clearer-engineering/scripts/safety-gate.py) e [`test-runner.sh`](../../../clearer-engineering/scripts/test-runner.sh) para a pasta `vendor/ceh/` do novo projeto.

---

### Passo 2: Configurar o Host Adapter (Interceptador de Ferramentas)
No harness do host (Muse, Codex etc.), identifique como ferramentas de terminal (`execute_command`, `bash`, `terminal`) são despachadas:

1. **Via CLI Wrapper / Subprocesso (Universal):**
   Antes de despachar o comando no terminal do host, execute a checagem:
   ```bash
   python3 path/to/safety-gate.py --check "<comando>"
   ```
   - Código de retorno `0` $\to$ Decisão `ALLOW` (permitir execução).
   - Código de retorno `1` $\to$ Decisão `ASK` (solicitar confirmação humana com o alerta gerado).
   - Código de retorno `2` $\to$ Decisão `DENY` (bloquear execução e exibir o motivo).

2. **Via Importação Direta em Python (se o host for em Python):**
   ```python
   from ceh.ceh_core.environment import detect_environment
   from ceh.ceh_core.rm import evaluate_rm_command
   from ceh.scripts.safety_gate import evaluate_command

   decision, reason, env, sev = evaluate_command(tool_input_command, base_cwd=current_project_dir)
   if decision == "deny":
       raise SecurityException(f"CEH Bloqueio: {reason}")
   elif decision == "ask":
       prompt_user_for_confirmation(reason)
   ```

---

### Passo 3: Injetar as Regras de Engenharia do CLEARER
Adicione o conteúdo de [`clearer-engineering/rules/AGENTS.md`](../../../clearer-engineering/rules/AGENTS.md) às instruções de sistema do seu host:
- **No Codex:** Adicionar ao prompt de sistema ou arquivo de instruções do projeto (`.codex/instructions.md`).
- **No Muse:** Adicionar às regras globais ou de workspace (`.muse/rules.md`).
- **No Claude Code:** Adicionar ao `CLAUDE.md`.

**Elementos Fundamentais do Prompt:**
- Protocolo CLEARER (Concrete Goal, Load Context, Explicit Boundaries, Anchors, Response Contract, Enable Tools, Review & Validate).
- Semântica de Evidência: `OBSERVED` (fato demonstrado), `INFERRED` (conclusão lógica) e `UNKNOWN` (sem dados).
- Rigor por Ambiente: `DEV` (liberdade com salvaguarda), `STAGING` (2 alertas para ações destrutivas) e `PROD` (`DENY` absoluto para comandos destrutivos).
- Ponytail Mode: Senior minimalista, zero preâmbulos vazios, passos curtos e foco em diff mínimo.

---

## 6. Checklist de Validação do Host Adapter (Smoke Test)

Para certificar que o novo harness está devidamente protegido pelo CEH, execute os 4 testes de validação:

```bash
# 1. Comando Benigno (deve retornar ALLOW / exit 0)
python3 path/to/safety-gate.py --check "ls -la"
# Esperado: [ALLOW]

# 2. Comando Catastrófico de Sistema (deve retornar DENY / exit 2)
python3 path/to/safety-gate.py --check "rm -rf /"
# Esperado: [DENY] Hard block: Attempting recursive deletion of root directory '/'

# 3. Comando Destrutivo sob Ambiente Simulado de Produção (deve retornar DENY / exit 2)
python3 path/to/safety-gate.py --check "rm -rf config/" --env production
# Esperado: [DENY] [CEH PRODUCTION LOCK]

# 4. Push sem Certificado de CI (deve retornar DENY / exit 2)
python3 path/to/safety-gate.py --check "git push origin dev"
# Esperado: [DENY] [CEH PRE-PUSH CI GATE]
```

Se os 4 testes responderem com o comportamento esperado, o **harness está formalmente homologado e integrado sob a governança do CEH v1.3.0**.
