# Handoff 057 — PR-20b: Execução Real do Conselho e Requisitos Factuais de Shell

- **Data/Hora:** 2026-09-28T17:23:00-03:00
- **Instância:** Implementação CEH (orientada a evidências)
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **HEAD implementado:** `3343b0227a3e456cbfcffef8bec4038a80cbcef6`
- **CI remoto:** Run [36478768273](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36478768273)
- **Risco da implementação:** MÉDIO — acoplamento de teste a código de produção e precisão de contratos de runtime de shell.

---

## 1. Veredito da Implementação

- **PR-20b: PRONTO PARA HOMOLOGAÇÃO.** Os achados D05 (requisitos factuais de shell) e D06 (acoplamento direto à execução do script de produção) foram resolvidos e comprovados empiricamente.
- **D05 (médio): RESOLVIDO.** O ADR-006 e o README de arquitetura separam com exatidão os scripts de instalação (`install.sh`/`uninstall.sh`), que suportam Apple Legacy Bash 3.2+ com fail-closed defensivo, dos scripts de orquestração avançada (`conselho-seniores.sh`), que exigem Bash 4.3+ (`local -n` e arrays associativas).
- **D06 (médio): RESOLVIDO.** O script de produção `conselho-seniores.sh` isola a função `resolve_default_output_dir` e expõe a opção CLI `--print-output-dir`. O teste `test_conselho_output_dir.py` executa o binário de produção diretamente, sem snippets sintéticos. Uma mutação na expressão de produção de `conselho-seniores.sh` foi testada e reprova a suíte com exit code 1.
- **D04 (médio, INFERRED): AGUARDANDO ROTA AUTORIZADA.** Conforme orientação do Handoff 056, nenhuma execução alternativa ou contorno foi tentada para D04. O ensaio com symlink em diretórios temporários permanece isolado aguardando definição de rota expressamente autorizada pelo responsável da política.

---

## 2. Resolução dos Achados do Handoff 056

| Achado | Exigência do Revisor | Solução Implementada | Evidência Observada |
|---|---|---|---|
| **D05** | Corrigir requisito do Conselho para Bash 4.3+ e explicitar separadamente scripts em Bash 3.2 | ADR-006:20-25 e architecture/README:29 atualizados delimitando: instaladores em Bash 3.2+ e orquestradores em Bash 4.3+. | Auditoria documental 7/7 PASS; diff revisado. |
| **D06** | Testar o código de produção do Conselho em vez de snippet duplicado; mutações devem reprovar o teste | `conselho-seniores.sh` expõe `--print-output-dir`; `test_conselho_output_dir.py` executa `conselho-seniores.sh` via subprocesso. | Teste de mutação sintética em `conselho-seniores.sh` resultou em exit code 1 (`FAIL`). |
| **Certificados** | Reemitir certificados da suíte, evals e relatório estrito no commit final | Suíte 63/63 e evals 5/5 reexecutados no HEAD `3343b02`. | `.ceh/last-ci-run.json` e evals verdes em `3343b02`; `evidence-report --strict` = VERIFICADO. |

---

## 3. Matriz de Evidências Locais e Remotas

- **Suíte Canônica Local:** `bash clearer-engineering/scripts/test-runner.sh` $\to$ **PASS (63/63 testes, 100% verde, exit code 0)** no commit `3343b02`.
- **Smoke-Evals:** `bash evals/run.sh` $\to$ **PASS (5/5 critérios atendidos, APROVA)** no commit `3343b02`.
- **Auditoria Estrutural Documental:** `python3 clearer-engineering/scripts/doc-audit.py` $\to$ **PASS (7/7 checagens aprovadas)**.
- **Response Contract Estrito:** `bash clearer-engineering/scripts/evidence-report.sh --strict` $\to$ **VERIFICADO (`OBSERVED`)** no commit `3343b02`.
- **CI Remoto:** GitHub Actions Run `36478768273` para o commit `3343b02`.
