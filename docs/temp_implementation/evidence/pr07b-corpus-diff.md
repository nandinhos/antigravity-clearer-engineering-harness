# Golden Corpus Snapshot Diff — PR-07b

- **Data/Hora**: 2026-09-26T23:30:00Z
- **Commit Avaliado**: HEAD (`PR-07b`)
- **Comando de Verificação**: `python3 clearer-engineering/tests/tools/snapshot_gate.py --check`

## 1. Resultado da Comparação
```
✔ Golden Corpus Snapshot 100% CONFORME (1012 avaliações idênticas, diff vazio)
```

## 2. Relaxamentos Autorizados de Detecção sem explicit_env (Handoff 031 §3.3)
Registrados em `clearer-engineering/tests/fixtures/relaxamentos_justificados.txt` sob o ID `H031-PR07`:

1. `development|rm -rf build/production-assets|deny->allow|H031-PR07`
2. `development|cat docs/staging-notes.md|ask->allow|H031-PR07`
3. `development|git log --grep=production|deny->allow|H031-PR07`
4. `development|docker compose -f docker-compose.staging.yml ps|ask->allow|H031-PR07`
5. `development|git reset --hard|ask->allow|H031-PR07` (na branch `feature/evaluation`)

Zero relaxamentos em comandos destrutivos na `main` ou em comandos que contenham sinais explícitos por forma (`cd /srv/production`, `--environment=production`, `-var env=production`, `DJANGO_SETTINGS_MODULE=app.settings.production`).
