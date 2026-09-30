# Evidência E13b — Canário com Edição Local de Diagnóstico (Teste Manual Pré-PR #5)

**Data/Hora:** 2026-09-30T02:26:16Z (UTC)  
**Versão Base:** `v1.4.0` com patch manual de diagnóstico em `~/.gemini/config/plugins/clearer-engineering/scripts/safety-gate.py`  
**Host:** Google Antigravity IDE (PreToolUse Hook)  
**Status:** **BLOQUEADO (`OBSERVED`)** — Prova empírica de que `deny` com `exit 0` bloqueia na IDE

---

## 1. Contexto da Investigação

Às `01:58:27Z` (Step 1244), ao executar `touch .ceh/canario-hook` com a `v1.4.0` oficial instalada, constatou-se que o arquivo foi criado com `exit 0`. A v1.4.0 emitia `sys.exit(2)` em decisões de `deny`, e a IDE do Antigravity tratava qualquer `exit != 0` como falha do hook, liberando a execução do comando (fail-open).

O arquivo foi removido imediatamente (`rm -f .ceh/canario-hook` no Step 1248). Para isolar a causa raiz e testar a hipótese de que a IDE exigia JSON de `deny` com `exit 0`, o agente realizou edições locais de diagnóstico diretamente no script instalado no ambiente.

---

## 2. Diff do Gate Instalado Durante o Teste Manual

Diff reconstruído diretamente a partir dos Steps 1363 (`02:24:58Z`) e 1377 (`02:26:00Z`) da transcrição da sessão (`transcript_full.jsonl`):

```diff
--- a/scripts/safety-gate.py (v1.4.0 oficial)
+++ b/scripts/safety-gate.py (gate instalado com edição local de diagnóstico)
@@ -547,6 +547,12 @@ def handle_hook():
     """Processes PreToolUse hook JSON from stdin."""
     try:
         raw_input = sys.stdin.read()
+        try:
+            with open("/tmp/ceh_hook_debug.log", "a") as f:
+                f.write(f"HOOK_INVOKED: {raw_input}\n")
+        except Exception:
+            pass
         if not raw_input.strip():
             return
@@ -591,6 +597,9 @@ def handle_hook():
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

## 3. Disparo na IDE e Resposta Bruta do Antigravity

Chamada executada na IDE (Step 1381 da transcrição, `2026-09-30T02:26:16Z`):
```json
{
  "name": "run_command",
  "args": {
    "CommandLine": "touch .ceh/canario-hook",
    "Cwd": "/home/<user>/projects/clearer-engineering-harness",
    "WaitMsBeforeAsync": 5000,
    "toolAction": "Executando teste canário touch .ceh/canario-hook sob o hook ajustado",
    "toolSummary": "Teste canário final"
  }
}
```

Resposta bruta da IDE Antigravity (Step 1382 da transcrição, `2026-09-30T02:26:22Z`):
```text
Created At: 2026-09-29T23:26:22-03:00
Completed At: 2026-09-29T23:26:22-03:00
Error invalid tool call: model output error: invalid tool call error (invalid_args) tool call denied with reason: [CEH CERTIFICATE INTEGRITY - G9/AL1] ⛔ Tentativa de escrita/modificação de .ceh/ ou certificado de CI (touch). Apenas leituras puras são permitidas.
```

---

## 4. Conclusão do Teste Manual

Esse teste empírico comprovou a hipótese de que a IDE Antigravity bloqueia a ferramenta quando recebe a decisão `deny` em stdout com `exit 0`. Esse resultado serviu como base técnica para a formulação do PR #5 e o release formal da `v1.4.1`.
