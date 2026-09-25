# Inventário de Capacidade de Hooks — Conselho de Seniores (Handoff 005)

**Data da Coleta:** 2026-09-25T04:20:00Z  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Ambiente:** Host Linux / WSL2 (Ubuntu) — Usuário não-root  

---

## 1. Matriz de Suporte a Hooks em Tempo de Execução (`OBSERVED`)

| CLI | Versão Detectada | Suporte a Hooks / Plugins | Mecanismo de Interceptação Identificado | Veredito de Adaptabilidade |
|---|---|---|---|---|
| **`agy`** (Antigravity CLI) | `1.2.9` | **SIM (NATIVO)** | `PreToolUse` hook via `hooks.json` no plugin. | **ALVO PRIMÁRIO (100% Medido & Fail-Closed)** |
| **`claude`** (Claude Code) | `2.1.281` | **SIM (NATIVO)** | `PreToolUse` hook via `.claude/settings.json` ou plugins. | **ALVO SECUNDÁRIO (100% Medido & Fail-Open)** |
| **`codex`** (Codex CLI) | `0.156.1` | **SIM** | Sistema de plugins com `--dangerously-bypass-hook-trust`. | **ADAPTÁVEL (Via Plugin Hook)** |
| **`gemini`** (Gemini CLI) | `0.50.0` | **SIM** | `gemini hooks` / gerenciamento de hooks nativos. | **ADAPTÁVEL (Via Gemini Hook)** |
| **`hermes`** (Hermes Agent) | `v0.21.0` | **SIM** | Shell-script hooks (`hermes hooks`, `--accept-hooks`). | **ADAPTÁVEL (Via Shell Hook)** |
| **`muse`** (Muse Code) | `1.3.0` | **SIM** | Sistema de plugins e bundles (`muse plugins`). | **ADAPTÁVEL (Via Plugin Hook)** |
| **`agent`** | `2026.09.15` | **SIM** | `--plugin-dir <path>` e `agent plugin`. | **ADAPTÁVEL (Via Plugin Hook)** |
| **`cursor`** | Server build | **NÃO (CLI HEADLESS)** | Não expõe comando CLI de hook; depende de extensões VSCode. | **SEM HOOK (Exige Branch Protection / IDE)** |

---

## 2. Principais Achados no Antigravity CLI (`agy`) — Prioridade 1

Com base nas 22 execuções completas (2 repetições) registradas em `docs/temp_implementation/evidence/host-probe/agy/20260925T041046Z/`:

1. **P0 (Crash & Timeout do Hook): FAIL-CLOSED NATIVO**
   - Quando o hook quebra (`E3`: exceção/crash) ou estoura o timeout (`E4`: sleep), o Antigravity **NÃO executa o comando** (`BLOQUEADO` / `Seguro: True`).
   - Diferença crucial com o Claude Code: o Antigravity é resiliente por padrão e impede comandos órfãos sem aprovação.
2. **Q1 (Modo YOLO vs Safety Gate): DENY É INVIOLÁVEL**
   - Nos experimentos `E5` e `E5Y`, a resposta `deny` do hook bloqueou o comando de forma absoluta, inclusive sob `--dangerously-skip-permissions --mode accept-edits`.
3. **Q2 & G9 (Ferramentas de Escrita de Arquivo): MITIGÁVEL VIA HOOK**
   - O experimento `E7` comprovou que `write_to_file` dispara o hook `PreToolUse` e é interceptado com sucesso (`BLOQUEADO` / `Seguro: True`).
4. **Q4 (Piso de Python do Host): PYTHON 3.11+ / 3.12**
   - O `agy` executou o hook usando Python `3.12.3` com exit code 0 em todos os testes.
