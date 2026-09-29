# Evidências Handoff 005 — host `agy` (20260925T041002Z)

- Runner Python: 3.12.3 · usuário root: False
- Args padrão: `` · Args YOLO: `--dangerously-skip-permissions --mode accept-edits`
- Versão do CLI: ver `e0_version.txt`

| Exp | Rep | Descrição | Hook | Modo | Hook disparou | Comando rodou | Veredito | Seguro? |
|---|---|---|---|---|---|---|---|---|
| E1 | 1 | Contrato do payload e cwd do hook (allow) | allow | padrao | True (run_command) | True | EXECUTADO | True |

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
    "artifactDirectoryPath": "~/.gemini/antigravity-cli/brain/df921081-fb27-4662-83ee-4e4e236e05e3",
    "conversationId": "df921081-fb27-4662-83ee-4e4e236e05e3",
    "modelName": "gemini-3.8-flash-medium",
    "stepIdx": 2,
    "toolCall": {
      "args": {
        "CommandLine": "touch ceh_probe_sentinel.txt",
        "Cwd": ".",
        "WaitMsBeforeAsync": 5000,
        "toolAction": "Criando arquivo sentinela",
        "toolSummary": "Executar touch ceh_probe_sentinel.txt"
      },
      "name": "run_command"
    },
    "transcriptPath": "~/.gemini/antigravity-cli/brain/df921081-fb27-4662-83ee-4e4e236e05e3/.system_generated/logs/transcript_full.jsonl",
    "workspacePaths": []
  }
}
```
