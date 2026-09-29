# Evidências de contrato de hook (sonda v2) — host `agy` (20260925T180256Z)

- Runner Python: 3.12.3 · usuário root: False
- Args padrão: `` · Args YOLO: `--dangerously-skip-permissions --mode accept-edits`
- Versão do CLI: ver `e0_version.txt` · plugin do CEH instalado: True · isolamento: sim (agy plugin disable/enable)

| Exp | Rep | Descrição | Hook | Modo | CEH ativo | Hook disparou | Comando rodou | Veredito | Seguro? | Desvios |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 1 | Contrato do payload e cwd do hook (allow) | allow | padrao | False | True (run_command) | True | EXECUTADO | True | 0 |
| E5 | 1 | deny respeitado em modo padrão | deny | padrao | False | True (run_command) | False | BLOQUEADO | True | 0 |

## E8 — Piso de Python do Safety Gate

| Python | Status | Exit | stderr |
|---|---|---|---|
| 3.8 | NAO_DISPONIVEL |  |  |
| 3.9 | NAO_DISPONIVEL |  |  |
| 3.10 | NAO_DISPONIVEL |  |  |
| 3.11 | OK | 0 |  |
| 3.12 | OK | 0 |  |

## E1 — Payload real recebido pelo hook

```json
{
  "python": "3.12.3",
  "cwd": "~/.gemini/config/plugins/ceh-probe",
  "pwd": "~/.gemini/config/plugins/ceh-probe",
  "oldpwd": "~/projects/clearer-engineering-harness",
  "parent_cwd": "~/.gemini/config/plugins/ceh-probe",
  "env_keys": [
    "ANTIGRAVITY_AGENT",
    "ANTIGRAVITY_CLI_ALIAS",
    "ANTIGRAVITY_CONVERSATION_ID",
    "NVM_DIR",
    "USER_ZDOTDIR",
    "XDG_RUNTIME_DIR",
    "ZDOTDIR"
  ],
  "env": {
    "NVM_DIR": "~/.nvm",
    "XDG_RUNTIME_DIR": "/mnt/wslg/runtime-dir"
  },
  "payload": {
    "artifactDirectoryPath": "~/.gemini/antigravity-cli/brain/d10f2607-9fa6-423a-b1c8-96d541cdaa2e",
    "conversationId": "d10f2607-9fa6-423a-b1c8-96d541cdaa2e",
    "modelName": "gemini-3.8-flash-medium",
    "stepIdx": 2,
    "toolCall": {
      "args": {
        "CommandLine": "touch /tmp/ceh-probe-E1-ephygh2r/ceh_probe_sentinel.txt",
        "Cwd": "/tmp/ceh-probe-E1-ephygh2r",
        "WaitMsBeforeAsync": 5000,
        "toolAction": "Criando arquivo sentinela",
        "toolSummary": "Criação de sentinela"
      },
      "name": "run_command"
    },
    "transcriptPath": "~/.gemini/antigravity-cli/brain/d10f2607-9fa6-423a-b1c8-96d541cdaa2e/.system_generated/logs/transcript_full.jsonl",
    "workspacePaths": [
      "/tmp/ceh-probe-E1-ephygh2r"
    ]
  }
}
```
