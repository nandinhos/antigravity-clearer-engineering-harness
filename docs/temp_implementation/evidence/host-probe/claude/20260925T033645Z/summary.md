# Evidências Handoff 005 — host `claude` (20260925T033645Z)

- Runner Python: 3.11.15 · usuário root: True
- Args padrão: `--max-turns 3 --allowedTools Bash,Write,Edit` · Args YOLO: `--max-turns 3 --permission-mode bypassPermissions`
- Versão do CLI: ver `e0_version.txt`

| Exp | Rep | Descrição | Hook | Modo | Hook disparou | Comando rodou | Veredito | Seguro? |
|---|---|---|---|---|---|---|---|---|
| E1 | 1 | Contrato do payload e cwd do hook (allow) | allow | padrao | True (Bash) | True | EXECUTADO | True |
| E2 | 1 | Hook declarado com caminho relativo (G8) | allow | padrao | True (Bash) | True | EXECUTADO | True |
| E3 | 1 | Hook quebra com exceção, exit 1 sem JSON (P0) | crash | padrao | True (Bash) | True | EXECUTADO | False |
| E3Y | 1 | Hook quebra em modo YOLO (P0) | crash | yolo | False () | False | INCONCLUSIVO | None |
| E4 | 1 | Hook excede o timeout declarado | sleep | padrao | True (Bash) | True | EXECUTADO | False |
| E5 | 1 | deny respeitado em modo padrão | deny | padrao | True (Bash) | False | BLOQUEADO | True |
| E5Y | 1 | deny respeitado em modo YOLO | deny | yolo | False () | False | INCONCLUSIVO | None |
| E6 | 1 | ask em modo padrão não interativo (Q1) | ask | padrao | True (Bash) | False | BLOQUEADO | True |
| E6Y | 1 | ask em modo YOLO (Q1) | ask | yolo | False () | False | INCONCLUSIVO | None |
| E7 | 1 | Ferramenta de escrita de arquivo passa pelo hook (G9) | deny | padrao | True (Write) | False | BLOQUEADO | True |
| E9 | 1 | exit 2 sem JSON bloqueia? (desenho fail-closed) | exit2 | padrao | True (Bash) | False | BLOQUEADO | True |

## E8 — Piso de Python do Safety Gate

| Python | Status | Exit | stderr |
|---|---|---|---|
| 3.8 | FALHA | 1 | TypeError: unsupported operand type(s) for |: 'type' and 'NoneType' |
| 3.9 | FALHA | 1 | TypeError: unsupported operand type(s) for |: 'type' and 'NoneType' |
| 3.10 | OK | 0 |  |
| 3.11 | OK | 0 |  |
| 3.12 | OK | 0 |  |

## E1 — Payload real recebido pelo hook

```json
{
  "python": "3.11.15",
  "cwd": "/tmp/ceh-probe-E1-r9xq4syz",
  "env_keys": [
    "CCR_AUTO_MODE_USER_ENV_KEYS_FACT",
    "CLAUDECODE",
    "CLAUDE_ADDITIONAL_DIRECTORIES",
    "CLAUDE_AFTER_LAST_COMPACT",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
    "CLAUDE_AUTO_BACKGROUND_TASKS",
    "CLAUDE_CODE_ACCOUNT_UUID",
    "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD",
    "CLAUDE_CODE_ARTIFACT_ASSETS",
    "CLAUDE_CODE_ARTIFACT_DB",
    "CLAUDE_CODE_ARTIFACT_MULTI_FILE",
    "CLAUDE_CODE_ARTIFACT_TYPES",
    "CLAUDE_CODE_ARTIFACT_TYPE_CATALOG",
    "CLAUDE_CODE_ARTIFACT_TYPE_CLOUD_CREATE",
    "CLAUDE_CODE_BASE_REF",
    "CLAUDE_CODE_BG_TASKS_REPORT_RUNNING",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_CONTAINER_ID",
    "CLAUDE_CODE_DEBUG",
    "CLAUDE_CODE_DIAGNOSTICS_FILE",
    "CLAUDE_CODE_DISABLE_BUILTIN_ANTMCP",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_ENVIRONMENT_RUNNER_VERSION",
    "CLAUDE_CODE_EXECPATH",
    "CLAUDE_CODE_GZIP_REQUEST_BODIES",
    "CLAUDE_CODE_HOLD_UNANSWERED_PARKED_PERMISSION",
    "CLAUDE_CODE_INCLUDE_PARTIAL_MESSAGES",
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH",
    "CLAUDE_CODE_MESSAGING_SOCKET",
    "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_ORGANIZATION_UUID",
    "CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2",
    "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST",
    "CLAUDE_CODE_PROXY_RESOLVES_HOSTS",
    "CLAUDE_CODE_REMOTE",
    "CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE",
    "CLAUDE_CODE_REMOTE_HERMETIC_MODE",
    "CLAUDE_CODE_REMOTE_SEND_KEEPALIVES",
    "CLAUDE_CODE_REMOTE_SESSION_ID",
    "CLAUDE_CODE_SESSION_ATTENDED",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_SYNC_SESSION_REFS",
    "CLAUDE_CODE_SYNC_SKILLS",
    "CLAUDE_CODE_TEE_SDK_STDOUT",
    "CLAUDE_CODE_USER_EMAIL",
    "CLAUDE_CODE_USE_CCR_V2",
    "CLAUDE_CODE_VERSION",
    "CLAUDE_CODE_WORKER_EPOCH",
    "CLAUDE_EFFORT",
    "CLAUDE_ENABLE_STREAM_WATCHDOG",
    "CLAUDE_PID",
    "CLAUDE_PROJECT_DIR",
    "CLAUDE_SESSION_INGRESS_TOKEN_FILE",
    "DOCUMENTS_MCP_SCRATCH_ROOT",
    "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH",
    "NoDefaultCurrentDirectoryInExePath",
    "RBENV_ROOT",
    "SKIP_PLUGIN_MARKETPLACE"
  ],
  "env": {
    "CLAUDE_PROJECT_DIR": "/tmp/ceh-probe-E1-r9xq4syz",
    "DOCUMENTS_MCP_SCRATCH_ROOT": "/mnt/user-data/working/claude-docs",
    "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH": "~/.ccr/ca-bundle.crt",
    "RBENV_ROOT": "/opt/rbenv"
  },
  "payload": {
    "session_id": "c9c20d34-a40f-5acb-a5c2-d7623f9ff885",
    "transcript_path": "~/.claude/projects/-tmp-ceh-probe-E1-r9xq4syz/c9c20d34-a40f-5acb-a5c2-d7623f9ff885.jsonl",
    "cwd": "/tmp/ceh-probe-E1-r9xq4syz",
    "scratchpad_dir": "/tmp/claude-0/-tmp-ceh-probe-E1-r9xq4syz/c9c20d34-a40f-5acb-a5c2-d7623f9ff885/scratchpad",
    "prompt_id": "c16ebe0e-09ed-46a1-99eb-61aa11fc469e",
    "permission_mode": "default",
    "effort": {
      "level": "high"
    },
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {
      "command": "touch ceh_probe_sentinel.txt",
      "description": "Create empty sentinel file"
    },
    "tool_use_id": "toolu_017L9SjRbaSZK5Tcp29FSDn6"
  }
}
```
