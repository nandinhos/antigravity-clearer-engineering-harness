# Evidências Handoff 005 — host `agy` (20260925T040852Z)

- Runner Python: 3.12.3 · usuário root: False
- Args padrão: `` · Args YOLO: `--dangerously-skip-permissions --mode accept-edits`
- Versão do CLI: ver `e0_version.txt`

| Exp | Rep | Descrição | Hook | Modo | Hook disparou | Comando rodou | Veredito | Seguro? |
|---|---|---|---|---|---|---|---|---|
| E1 | 1 | Contrato do payload e cwd do hook (allow) | allow | padrao | True (run_command) | False | BLOQUEADO | False |

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
    "artifactDirectoryPath": "~/.gemini/antigravity-cli/brain/6c977c98-a4ca-4af1-93dc-27919bebb6e7",
    "conversationId": "6c977c98-a4ca-4af1-93dc-27919bebb6e7",
    "modelName": "gemini-3.8-flash-medium",
    "stepIdx": 2,
    "toolCall": {
      "args": {
        "CommandLine": "touch ceh_probe_sentinel.txt",
        "Cwd": "~/.gemini/antigravity-cli/scratch",
        "WaitMsBeforeAsync": 5000,
        "toolAction": "Creating sentinel file",
        "toolSummary": "Sentinel file creation"
      },
      "name": "run_command"
    },
    "transcriptPath": "~/.gemini/antigravity-cli/brain/6c977c98-a4ca-4af1-93dc-27919bebb6e7/.system_generated/logs/transcript_full.jsonl",
    "workspacePaths": []
  }
}
```
