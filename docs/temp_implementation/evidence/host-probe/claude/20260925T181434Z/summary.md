# Evidências de contrato de hook (sonda v2) — host `claude` (20260925T181434Z)

- Runner Python: 3.12.3 · usuário root: False
- Args padrão: `--max-turns 3 --allowedTools Bash,Write,Edit` · Args YOLO: `--max-turns 3 --permission-mode bypassPermissions`
- Versão do CLI: ver `e0_version.txt` · plugin do CEH instalado: False · isolamento: não

| Exp | Rep | Descrição | Hook | Modo | CEH ativo | Hook disparou | Comando rodou | Veredito | Seguro? | Desvios |
|---|---|---|---|---|---|---|---|---|---|---|
| E3Y | 1 | Hook quebra em modo YOLO (P0) | crash | yolo | False | True (Bash) | True | EXECUTADO | False | 0 |
| E5Y | 1 | deny respeitado em modo YOLO | deny | yolo | False | True (Bash) | False | BLOQUEADO | True | 0 |
| E6Y | 1 | ask em modo YOLO (Q1) | ask | yolo | False | True (Bash) | False | BLOQUEADO | True | 0 |
| E3Y | 2 | Hook quebra em modo YOLO (P0) | crash | yolo | False | True (Bash) | True | EXECUTADO | False | 0 |
| E5Y | 2 | deny respeitado em modo YOLO | deny | yolo | False | True (Bash) | False | BLOQUEADO | True | 0 |
| E6Y | 2 | ask em modo YOLO (Q1) | ask | yolo | False | True (Bash) | False | BLOQUEADO | True | 0 |

## E8 — Piso de Python do Safety Gate

| Python | Status | Exit | stderr |
|---|---|---|---|
| 3.8 | NAO_DISPONIVEL |  |  |
| 3.9 | NAO_DISPONIVEL |  |  |
| 3.10 | NAO_DISPONIVEL |  |  |
| 3.11 | OK | 0 |  |
| 3.12 | OK | 0 |  |
