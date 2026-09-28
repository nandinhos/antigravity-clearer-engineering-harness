# Diff e Auditoria do Corpus de Testes — PR-10 (G9)

## 1. Resumo Executivo
- **Total de Avaliações**: 1012 avaliações no Golden Corpus Snapshot.
- **Entradas Alteradas em `gate_corpus.txt`**: Linhas 193-196 (substituição dos payloads sintéticos híbridos de `HOOK:agy` pelos payloads reais observados com estrutura `toolCall`).
- **Total de Decisões Alteradas**: Exatamente 1 alteração em 1012 avaliações (`HOOK-195-agy`).
- **Conformidade de Snapshot**: `python3 snapshot_gate.py --check` -> **100% CONFORME (diff vazio)**.

## 2. Detalhamento Linha a Linha das Mudanças no Snapshot

### `HOOK-195-agy` (Linha 580 de `gate_corpus.expected.jsonl`)
- **Payload Testado**:
  ```json
  {"toolCall": {"name": "write_to_file", "args": {"TargetFile": "/tmp/test.txt"}}}
  ```
- **Decisão Anterior (PR-09)**:
  `{"decision": "deny", "reason": "[CEH HOOK ERROR] Ferramenta desconhecida 'write_to_file': fail-closed ativado."}`
- **Decisão Nova (PR-10)**:
  `{"decision": "allow"}`
- **Classificação**: **Liberação Pretendida e Esperada**.
- **Justificativa Técnica**: O PR-10 implementou o suporte e proteção a ferramentas de escrita/edição de arquivos (`write_to_file`, `replace_file_content`, `multi_replace_file_content` no Antigravity IDE; `Write`, `Edit`, etc. no Claude Code). Arquivos comuns fora de `.ceh/` (como `/tmp/test.txt`) devem ser permitidos com contrato nativo `{"decision": "allow"}` observado no E11; apenas alvos dentro de `.ceh/` sofrem bloqueio `deny`.

### Verificação de Não-Regressão e Invariantes
- Zero relaxamentos de segurança não pretendidos em comandos destrutivos ou de produção.
- `rm -rf /` continua categoricamente bloqueado como `deny` em `HOOK-194-agy` (`[CEH CATASTROPHIC BLOCK]`).
- `git reset --hard` continua com confirmação/permissão de DEV em `HOOK-193-agy`.
- `git status` continua permitido em `HOOK-192-agy`.
