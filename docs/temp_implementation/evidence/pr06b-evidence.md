# Relatório de Evidências — PR-06b (Fechamento Oficial da Onda 1: G1–G6)

**Data/Hora:** 2026-09-26T00:50:00-03:00  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Referência / Baseline:** `2820dad` (PR-QA-A2 homologado no Handoff 024)  
**Handoff de Origem:** Handoff 025 (`9409303`)  
**Ambiente:** `development` (detectado: Default workspace fallback)  

---

## 1. Sumário Executivo do PR-06b

O **PR-06b** sana integralmente os 4 achados do Handoff 025 (**AA1**, **AA2**, **AA3** e **AA4**), implementando a arquitetura estrita onde **analisadores só apertam** e o **desembrulho recursivo hermético** do Safety Gate:

1. **AA1 — Regra de Composição & Analisadores só Apertam**:
   - Um analisador léxico/estrutural (`find`, `interpreters`) propõe severidade candidata e nunca encerra a avaliação com `allow`.
   - A decisão final em `safety-gate.py` é calculada com `max_severity_decision(current, candidate)` na ordem estrita: `CATASTROPHIC > deny > ask > allow`.
   - Em `find.py`: aceita `eval_fn` e `depth`; desembrulha argumentos de `-exec`, `-execdir`, `-ok`, `-okdir` substituindo `{}` por `safe_placeholder.tmp` e avaliando recursivamente via `evaluate_command`.
2. **AA2 — Desembrulho Recursivo de Embrulhos Shell e Interpretadores**:
   - `extract_shell_c_command` em `safety-gate.py`: extrai a string interna de `sh -c`, `bash -c`, `zsh -c`, `dash -c` (inclusive com flags agrupadas) e avalia recursivamente via `evaluate_command(depth=depth+1)`.
   - `extract_shell_commands_from_code` em `ceh_core/interpreters.py`: combina inspeção precisa via AST da biblioteca padrão para Python (`ast.parse` / `ast.Call`) e regex robusta para Node, Perl e Ruby, extraindo comandos passados a `os.system`, `os.popen`, `subprocess.*`, `child_process.execSync/spawnSync`, `system()` e crases.
   - Proteção de recursão: `depth > 3` aciona fail-closed imediato com veredito `CATASTROPHIC`.
3. **AA3 — Detecção Completa de Interpretadores sem Enumerar Formas**:
   - Suporte a flags agrupadas em `ceh_core/interpreters.py` (`python3 -Bc`, `-Ic`, `perl -le`, `-ne`, `node -pe`).
   - Detecção de APIs destrutivas chamadas diretamente pelo nome, sem exigir prefixo de módulo (`from shutil import rmtree; rmtree('/')`, `__import__('shutil').rmtree`, `require('node:fs')`, `const {rmSync}=require('fs')`). Falsos positivos em produção são aceitos na direção fail-closed.
   - Verificação de argumentos literais passados após o código (`sys.argv[1]` com `/` ou caminhos sensíveis passando por `is_target_catastrophic`).
4. **AA4 — Conformidade de Processo**:
   - `docs/temp_implementation/evidence/pr06b-corpus-diff.md`: justificativa linha a linha das 15 alterações do corpus (todas constituindo apertos de segurança, zero relaxamentos).
   - O plano `docs/plano-implementacao-elevacao-ceh.md` **não foi editado pelo agente** (permanece intacto na versão do Handoff 025).

---

## 2. Critérios de Aceite Atendidos (`OBSERVED`)

| Critério (Handoff 025 §3) | Estado | Evidência Física |
|---|---|---|
| As 17 linhas `PENDENTE:H025-*` ficam verdes e controles seguem verdes | **ATENDIDO** | `python3 -m unittest clearer-engineering/tests/test_review_batteries.py` -> 1/1 **OK** (todas as 17 pendências H025 desmarcadas e validadas). |
| Fuzz diferencial contra `2820dad` com 0 relaxamentos | **ATENDIDO** | `test_gate_differential_fuzz.py` (11.787 casos) -> **OK** em 2.86s. `relaxamentos_justificados.txt` com **0** adições. |
| Invariante de embrulho no fuzz implementada e validada | **ATENDIDO** | `test_wrapping_invariants` em `test_gate_differential_fuzz.py` -> **OK** (400 comandos x 3 wrappers x 3 ambientes = 3.600 avaliações com 0 violações). |
| Prova de falsificabilidade do AA1 comprovada sem bateria/corpus | **ATENDIDO** | `verify_grammar_falsifiability_aa1.py` -> com corpus e bateria vazios, a gramática acusa **75 relaxamentos** ao reintroduzir o retorno antecipado do PR-06. |
| Justificativa linha a linha do corpus em `pr06b-corpus-diff.md` | **ATENDIDO** | `docs/temp_implementation/evidence/pr06b-corpus-diff.md` documenta integralmente as 15 alterações. |
| Plano de implementação mantido intacto sem edição pelo agente | **ATENDIDO** | `git diff docs/plano-implementacao-elevacao-ceh.md` -> vazio (zero diff). |
| Orçamento de linhas de código respeitado | **ATENDIDO** | `find.py`: 211 linhas (≤ 300); `interpreters.py`: 251 linhas (≤ 300); `safety-gate.py`: 533 linhas (≤ 650); `rules.py`: 63 linhas (0 regex novas). |

---

## 3. Prova Física de Falsificabilidade (AA1)

Execução do script `scratch/verify_grammar_falsifiability_aa1.py`:
- **Condições:** `gate_corpus.txt` e `review_batteries.txt` completamente esvaziados (lista vazia). Apenas comandos gerados pela gramática sintética determinística (`seed=42`).
- **Defeito reintroduzido em clone isolado:** retorno antecipado de `evaluate_find_command` em `safety-gate.py` sem desembrulho de `-exec` e sem passar pelas checagens de `CATASTROPHIC`.
- **Resultado (`OBSERVED`):**
  - Comandos gerados pela gramática: 3.500.
  - Comandos de find com `-exec` destrutivo/catastrófico: 111.
  - **75 relaxamentos não autorizados detectados exclusivamente pela gramática**.
  - Exemplos acusados:
    - `development|find . -exec rm -rf / + (deny->allow)`
    - `staging|find . -exec rm -rf / + (deny->ask)`
    - `development|find . -exec rm -rf / \; (deny->allow)`
    - `staging|find . -exec rm -rf / \; (deny->ask)`

---

## 4. Bateria de Casos do Handoff 025 Homologados

| Linha | Ambiente | Decisão | Achado | Comando |
|---|---|---|---|---|
| 292 | development | deny/CATASTROPHIC | H025-AA1 | `find . -exec rm -rf / \;` |
| 293 | development | deny/CATASTROPHIC | H025-AA1 | `find . -name x -exec rm -rf ~ \;` |
| 294 | development | deny/CATASTROPHIC | H025-AA1 | `find build -delete -exec rm -rf / +` |
| 295 | development | deny/CATASTROPHIC | H025-AA1 | `find . -exec rm -rf {} /etc \;` |
| 299 | production | deny/CATASTROPHIC | H025-AA2 | `bash -c "find / -delete"` |
| 300 | development | deny/CATASTROPHIC | H025-AA2 | `sh -c "python3 -c \"import shutil; shutil.rmtree('/')\""` |
| 301 | development | deny/CATASTROPHIC | H025-AA2 | `python3 -c "import os; os.system('find / -delete')"` |
| 302 | development | deny/CATASTROPHIC | H025-AA2 | `python3 -c "import os; os.remove('x'); os.system('rm -rf /')"` |
| 305 | development | deny/CATASTROPHIC | H025-AA3 | `python3 -Bc 'import shutil; shutil.rmtree("/")'` |
| 306 | production | deny | H025-AA3 | `python3 -Ic 'import shutil; shutil.rmtree("db")'` |
| 307 | production | deny | H025-AA3 | `perl -le 'unlink glob "*"'` |
| 308 | development | deny/CATASTROPHIC | H025-AA3 | `node -pe "require('fs').rmSync('/',{recursive:true})"` |
| 309 | production | deny | H025-AA3 | `node -e "require('node:fs').rmSync('db',{recursive:true})"` |
| 310 | development | deny/CATASTROPHIC | H025-AA3 | `node -e "const {rmSync}=require('fs'); rmSync('/',{recursive:true})"` |
| 311 | development | deny/CATASTROPHIC | H025-AA3 | `python3 -c "from shutil import rmtree; rmtree('/')"` |
| 312 | development | deny/CATASTROPHIC | H025-AA3 | `python3 -c "__import__('shutil').rmtree('/')"` |
| 313 | development | deny/CATASTROPHIC | H025-AA3 | `python3 -c 'import shutil,sys; shutil.rmtree(sys.argv[1])' /` |
