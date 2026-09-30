# Evidência E13 — Caracterização de Hooks na IDE do Antigravity

**Data/Hora:** 2026-09-30T03:15:00Z
**Host:** Antigravity IDE (`2.5.5-ecfbad74d93962fc8ca485d93ab9b4f3d4cb6cf8`)
**Contexto de Execução:** IDE (GUI/Desktop com host daemon `agy-ide`), em contraste com o CLI headless analisado no Handoff 007.
**Objetivo:** Falsificar ou demonstrar de forma irrefutável em `OBSERVED` a hipótese de que o executor de hooks da IDE do Antigravity opera em *fail-open* diante de códigos de saída `!= 0` (inclusive o `exit 2` padrão do CEH v1.4.0), exigindo `exit 0` com JSON de negação para efetivar o bloqueio de ferramentas.

---

## 1. Inventário de Ambiente e Configuração

- **Versão da IDE:** `2.5.5` (commit `ecfbad74d93962fc8ca485d93ab9b4f3d4cb6cf8`).
- **Configuração de Hooks:** `~/.gemini/config/hooks.json`.
  - Evento: `PreToolUse` para `run_command`, `write_to_file`, `replace_file_content`, `multi_replace_file_content`.
  - Comando: `python3 ~/.gemini/config/plugins/clearer-engineering/scripts/safety-gate.py`.
- **Arquivo de Configuração Completo:** [`host_inventory.json`](./host_inventory.json).

---

## 2. Diff do Safety Gate Instalado vs v1.4.0 Oficial

Arquivo de diff: [`diff_installed_vs_v140.diff`](./diff_installed_vs_v140.diff).
A única diferença entre a instalação que bloqueava na sessão e o código da tag `v1.4.0` consistia em 3 linhas cirúrgicas em `handle_hook()`:

```diff
--- /tmp/safety_gate_v140_official.py
+++ ~/.gemini/config/plugins/clearer-engineering/scripts/safety-gate.py
@@ -584,6 +584,9 @@
             if isinstance(hso, dict):
                 decision = hso.get("permissionDecision", "allow")
 
+        if "toolCall" in payload:
+            sys.exit(0)
+
         if decision == "deny":
             sys.exit(2)
         elif decision == "ask":
```

---

## 3. Matriz Experimental dos Braços (Sonda `probe_e13.py`)

Canário de teste: criação de sentinela em diretório temporário (`/tmp/e13-test/sentinela-hook-*`).
Arquivo de registro bruto: [`invocations.jsonl`](./invocations.jsonl).

| Braço | Resposta do Hook (Sonda) | Exit Code do Hook | Comportamento Observado na IDE | Veredito |
|---|---|---|---|---|
| **`allow`** | `{"decision": "allow"}` | `0` | **Executou** (`sentinela-hook-allow` criado) | PASS (comportamento esperado) |
| **`deny/0`** | `{"decision": "deny", "reason": "..."}` | `0` | **BLOQUEOU** (`tool call denied with reason...`) | **PASS (bloqueio efetivo)** |
| **`deny/2`** | `{"decision": "deny", "reason": "..."}` | `2` | **EXECUTOU** (`sentinela-hook-deny2` criado) | **FAIL-OPEN COMPROVADO** |
| **`exit2`** | Sem JSON (apenas stderr) | `2` | **EXECUTOU** (`sentinela-hook-exit2` criado) | **FAIL-OPEN COMPROVADO** |
| **`crash`** | Exceção não tratada (`RuntimeError`) | `1` | **EXECUTOU** (`sentinela-hook-crash` criado) | **FAIL-OPEN COMPROVADO** |

---

## 4. Braço Final — CEH v1.4.0 Oficial (Ponta a Ponta)

- **Instalação:** `safety-gate.py` idêntico à tag `v1.4.0` (sem a edição local de `sys.exit(0)`).
- **Canário:** `touch .ceh/canario-hook`.
- **Resposta do Gate:** O gate avaliou o comando e emitiu `decision: deny` com `exit 2` (`[CEH CERTIFICATE INTEGRITY - G9/AL1] ⛔ Tentativa de escrita/modificação de .ceh/`).
- **Comportamento Observado:** O comando **EXECUTOU LIVREMENTE** na IDE do Antigravity (exit code 0 da tool call).
- **Evidência Física:** O arquivo `.ceh/canario-hook` foi **criado fisicamente** no diretório `.ceh/`.
- **Higienização:** O arquivo `.ceh/canario-hook` foi imediatamente removido (`rm -f .ceh/canario-hook`).

---

## 5. Conclusão Técnica e Causa Raiz

1. O executor de hooks da **IDE do Antigravity** trata qualquer código de saída `!= 0` retornado pelo processo do hook como **falha de infraestrutura do hook** e adota política de **fail-open**, deixando a ferramenta executar.
2. Na **v1.4.0**, como o CEH responde a negações com `exit 2` para compatibilidade com outros runtimes, **todas as negações na IDE do Antigravity falham silenciosamente em fail-open**.
3. Para garantir bloqueio efetivo na IDE do Antigravity, o hook **deve responder com `sys.exit(0)`** emitindo o objeto JSON `{"decision": "deny", "reason": "..."}` no `stdout`.
