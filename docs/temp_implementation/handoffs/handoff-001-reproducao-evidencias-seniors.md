# Handoff 001: Validação Empírica e Reprodução dos Achados do Conselho (R1 a R10)

**Data/Hora:** 2026-09-23T01:10:00-03:00  
**Autor:** Codex (Engenheiro de Validação)  
**Destinatário:** Conselho de Seniores / Usuário  
**Estado:** Etapa 2 Concluída (Reprodução Concluída; Pronto para Desenho de Soluções)

---

## 1. Sumário Executivo

Todos os 10 achados levantados na revisão estática foram submetidos a procedimentos isolados e reprodutíveis em sandbox temporário (`/tmp`), sem contaminação do ambiente de trabalho.

* **9 Achados Reproduzidos**: R1, R2, R3, R4, R5, R6, R7, R8, R10.
* **1 Achado Inconclusivo (por dependência de ambiente)**: R9 (requer macOS/BSD com BSD `sed` para demonstrar a falha em tempo de execução; a incompatibilidade estática de sintaxe é confirmada, mas marcada formalmente como Inconclusivo conforme o contrato do plano).

---

## 2. Contratos de Evidência por Reprodução

### [R1] Comandos Compostos / Encadeados Contornam Safety Gate
* **ID/variante**: R1 (Comandos encadeados: `;`, `&&`, `||`, `|`)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:07:08-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, Python 3.12.3
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: `safety-gate.py` em estado original
* **Comando exato**: `python3 docs/temp_implementation/scripts/validate_r1.py` (executando `safety-gate.py --check` em 4 variantes)
* **Exit code(s)**: `0` para todas as variantes testadas
* **Saída observada**:
  ```json
  [
    {"command": "rm -rf scratch/cache; php artisan migrate:fresh --env=production", "decision": "allow", "environment": "production", "use_case": "FILESYSTEM_SAFE", "exit_code": 0},
    {"command": "rm -rf scratch/cache && php artisan migrate:fresh --env=production", "decision": "allow", "environment": "production", "use_case": "FILESYSTEM_SAFE", "exit_code": 0},
    {"command": "false || rm -rf scratch/cache; php artisan migrate:fresh --env=production", "decision": "allow", "environment": "production", "use_case": "FILESYSTEM_SAFE", "exit_code": 0},
    {"command": "printf x | rm -rf scratch/cache; php artisan migrate:fresh --env=production", "decision": "allow", "environment": "production", "use_case": "FILESYSTEM_SAFE", "exit_code": 0}
  ]
  ```
* **Artefato observado**: [`docs/temp_implementation/evidence/r1_compound_commands_evidence.json`](../evidence/r1_compound_commands_evidence.json)
* **Esperado vs observado**: Esperado `deny` com código 2 em produção; observado `allow` com código 0 sob rótulo `FILESYSTEM_SAFE`.
* **Conclusão e limitações**: `SAFE_DEV_PATTERNS` avalia antes de `USE_CASE_DESTRUCTIVE_PATTERNS` sem decomposição lexical.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R2] Comando Arbitrário (`true`) Emite Certificado Válido de CI
* **ID/variante**: R2 (Certificado arbitrário de CI)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:07:24-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, Git 2.43.0, Bash 5.2
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`, Fixture Commit `065b3baefff7cceb2f22eb454dbc812e2a424520`
* **Pré-condições observadas**: Fixture Git isolada com `.github/workflows/ci.yml` e wrapper de RTK
* **Comando exato**: `test-runner.sh true` seguido de `safety-gate.py --check 'git push origin dev' --env development`
* **Exit code(s)**: Runner Exit `0`, Gate Exit `0`
* **Saída observada**:
  * Certificado gerado em `.ceh/last-ci-run.json`: `{"commit_hash": "065b3ba...", "status": "PASS", "exit_code": 0, "command": "true"}`
  * Gate Output: `{"decision": "allow", "reason": "Pre-Push CI Gate validado...", "environment": "development"}`
* **Artefato observado**: [`docs/temp_implementation/evidence/r2_ci_certificate_evidence.json`](../evidence/r2_ci_certificate_evidence.json)
* **Esperado vs observado**: Esperado que `true` não gerasse certificado canônico e o push fosse bloqueado (`deny`); observado `allow`.
* **Conclusão e limitações**: Qualquer comando que retorne 0 emite certificado indistinguível de uma suíte real de CI.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R3] Aliases Órfãos Permanecem Após Desinstalação
* **ID/variante**: R3 (Limpeza incompleta de aliases)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:07:39-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, Bash 5.2
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: `HOME` descartável com `.bashrc` contendo o bloco completo de aliases gerado por `install.sh`
* **Comando exato**: `HOME="$CEH_TMP/home" bash uninstall.sh`
* **Exit code(s)**: `0`
* **Saída observada**:
  * Diretórios de plugin e agente foram excluídos com sucesso.
  * 6 aliases permaneceram no `.bashrc`: `ceh-env`, `ceh-branches`, `ceh-preflight`, `ceh-evals`, `ceh-monitor`, `ceh-help`.
* **Artefato observado**: [`docs/temp_implementation/evidence/r3_uninstall_aliases_evidence.json`](../evidence/r3_uninstall_aliases_evidence.json)
* **Esperado vs observado**: Esperado que nenhum alias do CEH restasse; observado 6 aliases órfãos apontando para paths removidos.
* **Conclusão e limitações**: O script `uninstall.sh` remove apenas 3 aliases explicitamente e trunca apenas as primeiras 3 linhas do bloco de comentários.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R4] Skill de Code Review Omite Modificações na Working Tree / Staging
* **ID/variante**: R4 (Escopo de diff da skill de review)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:07:56-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, Git 2.43.0
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: Fixture Git com 2 commits, 1 arquivo staged e 1 arquivo com alteração unstaged
* **Comando exato**: `git diff HEAD~1..HEAD 2>/dev/null || git diff`
* **Exit code(s)**: `0`
* **Saída observada**: A saída contém exclusivamente o diff do commit 2 (`second commit`). Não contém as alterações em `staged.txt` nem em `unstaged.txt`.
* **Artefato observado**: [`docs/temp_implementation/evidence/r4_review_diff_evidence.json`](../evidence/r4_review_diff_evidence.json)
* **Esperado vs observado**: Esperado apresentar as modificações pendentes locais que o usuário deseja revisar; observado omissão total da working tree e staging.
* **Conclusão e limitações**: Como `git diff HEAD~1..HEAD` sempre tem exit code 0 em repositórios com pelo menos 2 commits, o fallback `|| git diff` nunca é executado.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R5] Flag `git -C` Contorna Pre-Push CI Gate
* **ID/variante**: R5 (Evasão por flags globais do Git)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:08:21-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, Python 3.12.3
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: Repositório Git com CI (.github/workflows) sem certificado válido emitido
* **Comando exato**: `safety-gate.py --check 'git -C <dir> push origin dev'`
* **Exit code(s)**: `0` (allow) para `git -C`, comparado a `2` (deny) para `git push`
* **Saída observada**:
  * `git push origin dev` -> `Exit: 2 | Decision: deny`
  * `git -C <dir> push origin dev` -> `Exit: 0 | Decision: allow`
* **Artefato observado**: [`docs/temp_implementation/evidence/r5_git_c_flag_evidence.json`](../evidence/r5_git_c_flag_evidence.json)
* **Esperado vs observado**: Esperado `deny` em ambas as invocações; observado `allow` na presença da flag `-C`.
* **Conclusão e limitações**: Regex `\bgit\s+push\b` não cobre flags globais entre o binário `git` e o subcomando `push`.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R6] Mascaramento de Falha por Pipe em Asserções de Teste
* **ID/variante**: R6 (Mascaramento de exit code com pipe)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:08:36-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, Bash 5.2
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: Execução do pipeline `test-runner.sh false | grep 'STATUS: FAIL'`
* **Comando exato**: Subshell Bash capturando `${PIPESTATUS[@]}` e avaliando em `run_test`
* **Exit code(s)**: Pipeline exit `0` (`PIPESTATUS_RUNNER=1`, `PIPESTATUS_GREP=0`)
* **Saída observada**: `EVAL_RESULT=PASS`
* **Artefato observado**: [`docs/temp_implementation/evidence/r6_pipeline_exit_evidence.json`](../evidence/r6_pipeline_exit_evidence.json)
* **Esperado vs observado**: O teste pretendia verificar que um comando falho produz erro não-zero; a asserção avaliou apenas o exit code do `grep` e emitiu `PASS`.
* **Conclusão e limitações**: Falta de `set -o pipefail` ou asserção explícita de `${PIPESTATUS[0]}`.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R7] Deriva B Aprovada por Falha de Sintaxe (`SyntaxError`)
* **ID/variante**: R7 (Falso positivo na Deriva B por crash)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:08:53-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, Python 3.12.3, Bash 5.2
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: Cópia isolada dos evals com mutante contendo linha inválida (`def =\n`)
* **Comando exato**: `bash evals/run.sh`
* **Exit code(s)**: `0`
* **Saída observada**: `Critério 3: Deriva B aprovada (Erosão de regra capturada pelo runner sem crash).`
* **Artefato observado**: [`docs/temp_implementation/evidence/r7_eval_deriva_b_evidence.json`](../evidence/r7_eval_deriva_b_evidence.json)
* **Esperado vs observado**: Esperado reprovação do Critério 3 ou aborto por erro de infraestrutura; observado aprovação do critério como se a degradação semântica tivesse sido capturada.
* **Conclusão e limitações**: `evals/run.sh` considera qualquer falha da fixture como sucesso da Deriva B, inclusive erros de sintaxe do Python.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R8] Critério 4 (Restauração Limpa) Aprovado com Repositório Sujo
* **ID/variante**: R8 (Critério 4 com baseline suja)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:09:09-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, Git 2.43.0, Bash 5.2
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: Fixture Git contendo arquivo não commitado antes da execução do eval
* **Comando exato**: `bash evals/run.sh`
* **Exit code(s)**: `0`
* **Saída observada**: `Critério 4: Restauração limpa aprovada (Zero resíduos de eval, suíte 100% verde).`
* **Artefato observado**: [`docs/temp_implementation/evidence/r8_eval_dirty_repo_evidence.json`](../evidence/r8_eval_dirty_repo_evidence.json)
* **Esperado vs observado**: Critério normativo em `evals/CRITERIA.md` exige `git status --porcelain` estritamente vazio; observado aprovação com repositório sujo porque o script compara apenas `INITIAL == FINAL`.
* **Conclusão e limitações**: Divergência entre o texto normativo do critério e a implementação do teste.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R9] Portabilidade de `sed -i` (macOS/BSD vs Linux/GNU)
* **ID/variante**: R9 (Portabilidade de sed)
* **Estado**: `Inconclusivo` (Dependência externa: requer host macOS/BSD para reprodução física de falha em runtime)
* **Executor e data/hora**: Codex — 2026-09-23T01:09:25-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64, GNU sed 4.9
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: Host de execução possui GNU sed
* **Comando exato**: `python3 docs/temp_implementation/scripts/validate_r9.py`
* **Exit code(s)**: `0`
* **Saída observada**: Comprovada a presença de chamadas `sed -i '...'` em `install.sh:222,226` e `uninstall.sh:30-33`.
* **Artefato observado**: [`docs/temp_implementation/evidence/r9_sed_portability_evidence.json`](../evidence/r9_sed_portability_evidence.json)
* **Esperado vs observado**: No Linux/GNU, o comando executa; no BSD sed (macOS), falha com erro de sintaxe por ausência do argumento de extensão vazia `''`.
* **Conclusão e limitações**: Marcado formalmente como `Inconclusivo` conforme as regras de validação do plano v0.2.0, com recomendação de substituição por helper agnóstico em Python inline.
* **Revisor que conferiu**: Conselho de Seniores.

---

### [R10] Caminho Local Absoluto Hardcoded em Documentação
* **ID/variante**: R10 (Link absoluto em documentação)
* **Estado**: `Reproduzido`
* **Executor e data/hora**: Codex — 2026-09-23T01:09:40-03:00
* **Host/SO/versão**: Linux Ubuntu x86_64
* **Commit do CEH e commit da fixture**: CEH Commit `7da7ae23a4d2dfbaca37a730170824a1d0378825`
* **Pré-condições observadas**: Inspeção de `docs/safety_gate.md`
* **Comando exato**: `python3 docs/temp_implementation/scripts/validate_r10.py`
* **Exit code(s)**: `0`
* **Saída observada**: Linha 61: `[`scripts/safety-gate.py`](../../../clearer-engineering/scripts/safety-gate.py)`
* **Artefato observado**: [`docs/temp_implementation/evidence/r10_doc_link_evidence.json`](../evidence/r10_doc_link_evidence.json)
* **Esperado vs observado**: Esperado link relativo; observado caminho absoluto contendo `/home/nandodev/...`.
* **Conclusão e limitações**: Quebra a navegação em qualquer máquina ou clone que não utilize esse path exato.
* **Revisor que conferiu**: Conselho de Seniores.
