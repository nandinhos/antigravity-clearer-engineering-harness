# Handoff 058 — PR-20b homologado; despacho D04

- **Data/Hora:** 2026-09-28T17:33:35-03:00
- **Instância:** Revisor sênior independente do CEH
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **HEAD de implementação e CI:** `0fcd686724cc0c86b17a496d4be380cbc82a47c8`
- **HEAD de revisão:** `0fcd686724cc0c86b17a496d4be380cbc82a47c8`
- **CI remoto:** Run [36479192752](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36479192752), `success`, 4/4 jobs; SHA coincide com o commit final.
- **Risco:** MÉDIO para as alterações do PR-20b; D04 continua separado como risco de integração.

## 1. Veredito

- **PR-20b: HOMOLOGADO.** Os achados D05 e D06 do Handoff 056 foram corrigidos com escopo factual adequado e prova de regressão ligada ao script real.
- **D04: ABERTO, INFERRED, não homologado.** A tentativa controlada anterior foi bloqueada pelo PreToolUse antes da execução. Isso não confirma nem refuta o risco; permanece condição para homologação geral/merge da branch.

## 2. Evidências do revisor

- **D05 — SUPPORTED:** ADR-006 e `docs/architecture/README.md` distinguem os instaladores, cuja validação Apple Legacy Bash 3.2 é sintaxe e recusa fail-closed, dos orquestradores que requerem Bash 4.3+. `conselho-seniores.sh` usa `local -n` e arrays associativas; o job macOS instala Bash Homebrew antes da suíte normal.
- **D06 — SUPPORTED:** `test_conselho_output_dir.py` agora invoca `bash <script real> --print-output-dir`. Reproduzi os três cenários: cwd em repositório do usuário, script instalado fora do repo e fallback sem Git; todos passaram. Em clone temporário, a base passou e uma mutação da implementação de `resolve_default_output_dir` falhou com exit code 1.
- **Suíte:** `bash clearer-engineering/scripts/test-runner.sh` certificado no HEAD `0fcd686`, exit 0, 63/63.
- **Evals:** `bash evals/run.sh` certificado no HEAD `0fcd686`, exit 0, 5/5 (`APROVA`).
- **Auditoria documental:** `python3 clearer-engineering/scripts/doc-audit.py`, exit 0, 7/7; `git diff --check e486816..0fcd686`, exit 0.
- **Evidence report:** `bash clearer-engineering/scripts/evidence-report.sh --base e486816 --strict`, `VERIFICADO`; captura suíte/evals no HEAD `0fcd686` e worktree limpa.
- **CI remoto:** Run 36479192752, quatro jobs concluídos `success` em Ubuntu/macOS × Python 3.9/3.12, no SHA final `0fcd686`.

## 3. D04 e sequência

O risco de diferença entre cwd lexical e físico sob symlink permanece sem reprodução dinâmica autorizada. A tentativa anterior foi bloqueada pelo hook com ambiente `unknown`; não foi repetida nem movida para outro executor.

**Próximo gate:** o responsável pela política deve indicar uma rota permitida para o ensaio em diretórios temporários. O ensaio deve observar detecção de ambiente num ancestral físico, classificação de caminho relativo pelo gate e decisão de `rm`, sem executar a exclusão. Até lá, não homologar a branch inteira nem promover merge.
