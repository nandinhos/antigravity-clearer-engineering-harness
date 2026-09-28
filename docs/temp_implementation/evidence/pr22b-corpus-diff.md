# Diff e Auditoria do Golden Corpus Snapshot — PR-22b (AV1/AV2/AV3 / G9)

## 1. Resumo Executivo
- **Total de Avaliações**: 1024 avaliações no Golden Corpus Snapshot.
- **Entradas Adicionadas em `gate_corpus.txt`**: Linhas 367-370 (4 comandos cobrindo flags de gravação e escrita do git direcionadas a `.ceh/last-ci-run.json`).
- **Total de Decisões Alteradas nas Existentes**: 0 alterações nas 1012 avaliações anteriores (zero regressões).
- **Novas Decisões Avaliadas**: 12 novas avaliações (4 comandos × 3 ambientes: development, staging, production), todas categorizadas estritamente como `deny` com `use_case: "CERTIFICATE_INTEGRITY"`.
- **Conformidade de Snapshot**: `python3 clearer-engineering/tests/tools/snapshot_gate.py --check` -> **100% CONFORME (1024 avaliações idênticas, diff vazio)**.

---

## 2. Detalhamento Linha a Linha das Adições no Snapshot

### `CMD-344` (`git diff --output=.ceh/last-ci-run.json`)
- **Linhas no Snapshot**:
  - `CMD-344-dev`: `{"command": "git diff --output=.ceh/last-ci-run.json", "decision": "deny", "env": "development", "has_alerts": false, "id": "CMD-344-dev", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
  - `CMD-344-sta`: `{"command": "git diff --output=.ceh/last-ci-run.json", "decision": "deny", "env": "staging", "has_alerts": false, "id": "CMD-344-sta", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
  - `CMD-344-pro`: `{"command": "git diff --output=.ceh/last-ci-run.json", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-344-pro", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
- **Classificação**: **Aperto e Proteção de Integridade (G9 / AV1)**.
- **Justificativa Técnica**: `git diff` aceita a opção `--output=<arquivo>`, que grava o resultado no sistema de arquivos. O direcionamento para `.ceh/last-ci-run.json` constitui violação de integridade de certificado, bloqueada incondicionalmente em todos os ambientes.

### `CMD-345` (`git log -1 --output=.ceh/last-ci-run.json`)
- **Linhas no Snapshot**:
  - `CMD-345-dev`: `{"command": "git log -1 --output=.ceh/last-ci-run.json", "decision": "deny", "env": "development", "has_alerts": false, "id": "CMD-345-dev", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
  - `CMD-345-sta`: `{"command": "git log -1 --output=.ceh/last-ci-run.json", "decision": "deny", "env": "staging", "has_alerts": false, "id": "CMD-345-sta", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
  - `CMD-345-pro`: `{"command": "git log -1 --output=.ceh/last-ci-run.json", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-345-pro", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
- **Classificação**: **Aperto e Proteção de Integridade (G9 / AV1)**.
- **Justificativa Técnica**: `git log` com `--output=<arquivo>` (especialmente combinado a `--format`) permite gravar texto arbitrário e forjar certificados de CI. O gate intercepta a presença de qualquer flag de escrita e nega o comando com `CERTIFICATE_INTEGRITY`.

### `CMD-346` (`git show --output=.ceh/last-ci-run.json HEAD`)
- **Linhas no Snapshot**:
  - `CMD-346-dev`: `{"command": "git show --output=.ceh/last-ci-run.json HEAD", "decision": "deny", "env": "development", "has_alerts": false, "id": "CMD-346-dev", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
  - `CMD-346-sta`: `{"command": "git show --output=.ceh/last-ci-run.json HEAD", "decision": "deny", "env": "staging", "has_alerts": false, "id": "CMD-346-sta", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
  - `CMD-346-pro`: `{"command": "git show --output=.ceh/last-ci-run.json HEAD", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-346-pro", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
- **Classificação**: **Aperto e Proteção de Integridade (G9 / AV1)**.
- **Justificativa Técnica**: `git show` com `--output=<arquivo>` redireciona a saída para disco, sendo barrado preventivamente quando o alvo é `.ceh/`.

### `CMD-347` (`git log -1 -o .ceh/last-ci-run.json`)
- **Linhas no Snapshot**:
  - `CMD-347-dev`: `{"command": "git log -1 -o .ceh/last-ci-run.json", "decision": "deny", "env": "development", "has_alerts": false, "id": "CMD-347-dev", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
  - `CMD-347-sta`: `{"command": "git log -1 -o .ceh/last-ci-run.json", "decision": "deny", "env": "staging", "has_alerts": false, "id": "CMD-347-sta", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
  - `CMD-347-pro`: `{"command": "git log -1 -o .ceh/last-ci-run.json", "decision": "deny", "env": "production", "has_alerts": false, "id": "CMD-347-pro", "type": "command", "use_case": "CERTIFICATE_INTEGRITY"}`
- **Classificação**: **Aperto e Proteção de Integridade (G9 / AV1)**.
- **Justificativa Técnica**: Variante curta `-o` de `--output` para gravação de arquivos em subcomandos do git. Identificada e bloqueada com `CERTIFICATE_INTEGRITY`.

---

## 3. Verificação de Invariantes e Não-Regressão
1. **Zero Relaxamentos Não Autorizados**: As redes diferenciais (`test_gate_differential_fuzz.py` e `test_environment_differential.py`) confirmam que apenas os 5 comandos legítimos do AM2 autorizados em `relaxamentos_justificados.txt` restam como relaxamentos em relação à linha de base `d6bf922`.
2. **Preservação de Leituras Puras**: Leituras legítimas como `git status --ignored .ceh`, `du -sh .ceh`, `git diff app.py`, `git show HEAD:app.txt` permanecem `allow`.
3. **Resguardo de AV2**: Comandos arbitrários com `--exclude .ceh` (ex: `python3 -c "..." --exclude .ceh`) não têm suas opções removidas por `strip_ceh_exclusions`, mantendo o bloqueio fail-closed por alvo opaco.
