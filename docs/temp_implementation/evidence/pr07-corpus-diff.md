# Golden Corpus Snapshot Diff — PR-07

- **Data/Hora**: 2026-09-26T23:15:00Z
- **Commit Avaliado**: HEAD (`PR-07`)
- **Comando de Verificação**: `python3 clearer-engineering/tests/tools/snapshot_gate.py --check`

## 1. Resultado da Comparação
```
✔ Golden Corpus Snapshot 100% CONFORME (1012 avaliações idênticas, diff vazio)
```

## 2. Relaxamentos Esperados e Autorizados de Detecção (Handoff 030 §4.5)
O Golden Corpus Snapshot avalia com ambientes explícitos mapeados, registrando diff vazio. No mecanismo de detecção em tempo de execução, os seguintes relaxamentos esperados foram implementados e homologados:

1. **Branch `feature/evaluation`**: Deixa de ser falsamente classificada como `staging` (antes casava com a substring `"uat"` contida em `"evaluation"`). Agora retorna `development`.
2. **Valor `normalize_env("delivery")`**: Deixa de ser falsamente classificado como `production` (antes casava com a substring `"live"` contida em `"delivery"`). Agora retorna `development`.
3. **Caminhos de arquivo em DEV**: Caminhos contendo substrings como `build/production-assets` ou `docker-compose.staging.yml` deixam de contaminar o ambiente. Comentários `# ...` são ignorados.
4. **Invariante de Não Rebaixamento na `main`**: **Zero** comandos executados na branch `main` perderam severidade. Comandos destrutivos na `main` (`migrate:fresh`, `db:wipe # staging`, `migrate:fresh --env=staging`, `terraform destroy -var env=staging`) permanecem rigorosamente `deny / production`.
