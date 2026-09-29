# Evidência Técnica: PR-19c — Shellcheck Fixado por Versão e SHA-256 em Job Único

**Data:** 2026-09-27  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Antecessor:** [Handoff 045](../handoffs/handoff-045-revisao-pr19b-despacho-pr19c-pr18.md)  
**Ressalvas Endereçadas:** AS1 (determinismo de linter cross-platform) e AS2 (isolamento de controles negativos em branch descartável)

---

## 1. Contexto e Motivação (AS1)
No PR-19b, observou-se que o runner do macOS instalava o ShellCheck via Homebrew (versão 0.11.0, rolling release), enquanto o runner Ubuntu instalava via apt (`0.9.0-1`). Como o ShellCheck agora bloqueia o build estritamente, qualquer atualização futura no upstream do Homebrew poderia introduzir novas regras (como o SC2329 introduzido na v0.11.0) e reprovar a esteira sem nenhuma alteração no código do repositório.

Além disso, a análise estática de shell scripts não depende de sistema operacional nem de versão de runtime de Python.

---

## 2. Implementação do PR-19c

### 2.1. Execução Exclusiva em Job Único
No arquivo [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), os steps de instalação e execução do ShellCheck foram condicionados para rodar **apenas** quando:
```yaml
if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.12'
```
Nos outros 3 jobs da matriz (`ubuntu-latest/py3.9`, `macos-latest/py3.9`, `macos-latest/py3.12`), o linter de shell é pulado (skipped), economizando tempo de runner e eliminando redundância analítica.

### 2.2. Binário Oficial Fixado com Conferência SHA-256
A instalação foi desvinculada dos gerenciadores de pacotes (`apt` e `brew`). O binário oficial é baixado diretamente dos releases oficiais do projeto `koalaman/shellcheck`:
- **Versão:** `v0.11.0` (Linux x86_64)
- **URL Canônica:** `https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz`
- **Hash SHA-256 Criptográfico:** `8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198`

O workflow calcula o SHA-256 do arquivo baixado via `sha256sum` e aborta a execução (`exit 1`) caso ocorra divergência de hash.

### 2.3. Correção na Lição Aprendida
O documento [learned_lesson_ci_parity_linter_drift.md](./learned_lesson_ci_parity_linter_drift.md) foi corrigido para registrar:
- A versão real do apt que estava em uso no Ubuntu: `0.9.0-1` (distribuição Noble 24.04).
- A política formal de mitigação: versão fixada com hash SHA-256 em job único, onde atualizações de linter passam a ser PRs conscientes de engenharia.

---

## 3. Prova de Falsificabilidade em Branch Descartável (AS2)
Em conformidade com a ressalva AS2 do Handoff 045, o controle negativo do ShellCheck foi isolado na branch temporária descartável `claude/negctl-19c`, garantindo que a branch principal de trabalho permaneça com histórico 100% limpo e verde.

- **Branch Descartável:** `claude/negctl-19c` (removida do repositório local e remoto após o teste)
- **Workflow Run:** [Run 36344146427](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344146427)
- **Job de Falsificabilidade Bloqueado:** [Job 108689850093 (ubuntu-latest - Python 3.12)](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344146427/job/108689850093)
- **Resultado do Step 9 (`Install Official Fixed Shellcheck`):** `success` (download e validação do SHA-256 concluídos com sucesso)
- **Resultado do Step 10 (`Run Shellcheck`):** `failure` (exit code 1 devido a injeção deliberada de SC2086 em `task-monitor.sh:97`)
- **Impacto a Jusante:** Todos os steps subsequentes (11 a 21, incluindo o upload do relatório e a suíte canônica) foram sumariamente bloqueados (`skipped`).
- **Jobs de macOS e Python 3.9:** O step do ShellCheck foi pulado (`skipped`) como esperado pelo filtro de matriz.

---

## 4. Resultado Comprovado no Servidor (`OBSERVED`) — 100% Verde

No commit oficial [`3d1812b`](https://github.com/nandinhos/antigravity-clearer-engineering-harness/commit/3d1812b838286bd90a19404ceeb46464a2da5329), a esteira do GitHub Actions concluiu com **100% de sucesso em todos os 4 jobs da matriz**:

- **Workflow Run:** [Run 36344441316](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344441316)
- **Status:** `completed`, **Conclusion:** `success` (21/21 steps por job)

| Job | Plataforma | Python | ShellCheck v0.11 (SHA-256) | E2E & Suíte Canônica | Veredito |
|---|---|---|---|---|---|
| [Job 108690703022](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344441316/job/108690703022) | `ubuntu-latest` | 3.9 | `skipped` (job único) | `success` | **`success`** 🟢 |
| [Job 108690703011](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344441316/job/108690703011) | `ubuntu-latest` | 3.12 | `success` (0 avisos) | `success` | **`success`** 🟢 |
| [Job 108690703031](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344441316/job/108690703031) | `macos-latest` | 3.9 | `skipped` (job único) | `success` | **`success`** 🟢 |
| [Job 108690702902](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344441316/job/108690702902) | `macos-latest` | 3.12 | `skipped` (job único) | `success` | **`success`** 🟢 |

