# Matriz Experimental E11 — Caracterização de Hooks no Antigravity CLI (`agy`)

- **Timestamp**: `20260927T034219Z`
- **Versão do agy**: `1.2.11`
- **Total de Casos Avaliados**: 12 (3 braços x 2 ferramentas x 2 modos)

| Exp ID | Braço | Ferramenta | Modo CLI | Exit Code | Arquivo Criado? | Hook Acionou? | Tempo (s) |
|---|---|---|---|---|---|---|---|
| `E11-ctrl-write-padrao` | `controle` | `write` | `padrao` | 0 | ✅ SIM | NÃO | 8.38 |
| `E11-allow-write-padrao` | `allow` | `write` | `padrao` | 0 | ✅ SIM | SIM | 8.91 |
| `E11-vazio-write-padrao` | `vazio` | `write` | `padrao` | 0 | ❌ NÃO | SIM | 9.91 |
| `E11-ctrl-write-yolo` | `controle` | `write` | `yolo` | 0 | ✅ SIM | NÃO | 12.0 |
| `E11-allow-write-yolo` | `allow` | `write` | `yolo` | 0 | ✅ SIM | SIM | 10.8 |
| `E11-vazio-write-yolo` | `vazio` | `write` | `yolo` | 0 | ❌ NÃO | SIM | 9.12 |
| `E11-ctrl-shell-padrao` | `controle` | `shell` | `padrao` | 0 | ✅ SIM | NÃO | 7.94 |
| `E11-allow-shell-padrao` | `allow` | `shell` | `padrao` | 0 | ✅ SIM | SIM | 10.31 |
| `E11-vazio-shell-padrao` | `vazio` | `shell` | `padrao` | 0 | ❌ NÃO | SIM | 8.94 |
| `E11-ctrl-shell-yolo` | `controle` | `shell` | `yolo` | 0 | ✅ SIM | NÃO | 10.43 |
| `E11-allow-shell-yolo` | `allow` | `shell` | `yolo` | 0 | ✅ SIM | SIM | 11.87 |
| `E11-vazio-shell-yolo` | `vazio` | `shell` | `yolo` | 0 | ❌ NÃO | SIM | 12.72 |

## Conclusão Objetiva baseada em Fatos Observados (`OBSERVED`)

1. **Hipótese de Autoaprovação Espúria Refutada**:
   - A hipótese alternativa levantada no Handoff 038 AL2 (de que `{"decision": "allow"}` estaria pulando uma confirmação interativa do agy que `{}` estaria esperando) foi **rejeitada por evidência física direta**.
   - No braço de controle (**sem nenhum hook ativo**), tanto em modo padrão quanto em modo YOLO, para `write_to_file` e para `run_command`, o CLI `agy` executa a ação diretamente e grava o arquivo com sucesso (Linhas 9, 12, 15, 18).
   - O comportamento do braço `allow` é **100% equivalente ao comportamento de controle nativo do host** (Linhas 10, 13, 16, 19).

2. **Comportamento do Retorno Vazio `{}` no Antigravity**:
   - Quando um hook do Antigravity retorna `{}` (objeto vazio sem a chave `decision`), a engine do agy interpreta a ausência de decisão afirmativa como bloqueio/recusa de autorização (`❌ NÃO`, Linhas 11, 14, 17, 20), impedindo a execução de qualquer ferramenta.
   - Portanto, responder `{}` no agy **não devolve o fluxo nativo** — ele quebra e bloqueia permanentemente toda ferramenta permitida.

3. **Decisão Canônica de Engenharia (Handoff 038 §3)**:
   - "Se o controle grava → o allow explícito é neutro, e a implementação atual está correta. Registre como `OBSERVED`."
   - A implementação em `hook_context.py` (que retorna `{"decision": "allow"}` para o Antigravity e `{}` para o Claude Code) é a arquitetura canônica e correta de ambos os hosts.

