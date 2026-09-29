# Relatório de Evidências — PR-06 (G5: Deleções Indiretas com Find e Interpretadores)

**Data/Hora:** 2026-09-26T00:20:00-03:00  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Referência / Baseline:** `2820dad` (PR-QA-A2 homologado no Handoff 024)  
**Ambiente:** `development` (detectado: Default workspace fallback)  

---

## 1. Sumário Executivo e Fechamento da Onda 1

O **PR-06** implementa a blindagem contra deleções indiretas (**G5**), concluindo integralmente as vulnerabilidades de deleção de filesystem e fechando a **Onda 1 (G1–G6)** do CEH:
1. **`find` (`ceh_core/find.py`)**:
   - Analisador estrutural por tokens (188 linhas, teto ≤ 300), sem nenhuma regex nova em `rules.py`.
   - Caminhos iniciais avaliados antes da primeira expressão; padrão `.` quando omitidos.
   - Reuso estrito de `is_target_catastrophic` de `ceh_core/rm.py` para caminhos como `/`, `~`, `/etc`, `..`, `../..` (bloqueio incondicional `CATASTROPHIC`), **exceto quando o caminho for o próprio cwd (`.`)**.
   - Ações destrutivas interceptadas: `-delete`, `-exec`, `-execdir`, `-ok`, `-okdir` executando comandos destrutivos (`rm`, `unlink`, `shred`, `rmdir`) ou invocando shells (`sh`, `bash`, `zsh -c '... rm ...'`).
   - Sem caminho catastrófico, decisão graduada por ambiente (`FILESYSTEM`: DEV allow, HML ask, PROD deny). Ações não destrutivas (ex: `-print`, `-name '*.pyc'`) permanecem permitidas.
2. **Interpretadores Inline (`ceh_core/interpreters.py`)**:
   - Analisador estrutural por tokens (155 linhas, teto ≤ 300), sem regex nova em `rules.py`.
   - Resolução de cabeças desempacotando wrappers (`sudo`, `rtk`, `command`, `env`) e caminhos absolutos (`/usr/bin/python3` -> `python3`, `/usr/local/bin/node` -> `node`), suportando sufixos de versão (`python3.12`).
   - Famílias de interpretadores: Python (`python`, `python3`, `python3.12`), Node (`node`), Perl (`perl`), Ruby (`ruby`).
   - Flags de código inline: Python (`-c`), Node (`-e`, `--eval`), Perl (`-e`, `-E`), Ruby (`-e`).
   - Detecção de APIs destrutivas das respectivas stdlibs (`shutil.rmtree`, `os.remove`, `Path.unlink`, `fs.rmSync`, `unlink`, `FileUtils.rm_rf`, etc.).
   - Se algum literal de string do código inline passar em `is_target_catastrophic`, a chamada é classificada como **CATASTROPHIC** (bloqueio `deny` incondicional, inclusive em DEV). Sem literal catastrófico, decisão graduada (`FILESYSTEM`).
   - Âncoras obrigatórias preservadas: `echo "shutil.rmtree"`, `grep -r "shutil.rmtree" .`, `python3 script.py` e scripts inline sem APIs destrutivas permanecem permitidos (`allow/GENERAL`).

---

## 2. Critérios de Aceite Atendidos (`OBSERVED`)

| Critério (Handoff 024 §3) | Estado | Evidência Física |
|---|---|---|
| 15 `PENDENTE` do G5 verdes (7 de H017 e 8 de H024) | **ATENDIDO** | `python3 -m unittest clearer-engineering/tests/test_review_batteries.py` -> Ran 1 test in 0.026s, **OK** (zero falhas e zero pendências em xfail). |
| 3 RED do G5 em `cluster4_acceptance.py` verdes | **ATENDIDO** | `python3 -m unittest clearer-engineering/tests/cluster4_acceptance.py` -> Ran 20 tests in 0.043s, **OK (expected failures=1)** (resta apenas o G7 da Onda 2). |
| `rules.py` sem regex nova para find e interpretadores | **ATENDIDO** | `ceh_core/rules.py` mantido em 63 linhas, inalterado no PR-06. |
| Fuzz diferencial contra `2820dad` sem relaxamentos | **ATENDIDO** | `test_gate_differential_fuzz.py` (11.721 casos) -> **OK** em 2.42s. `relaxamentos_justificados.txt` com **0** adições. |
| Falsificabilidade da gramática nova comprovada | **ATENDIDO** | Prova física executada: desligando a resolução de cabeças com caminho absoluto (`/usr/bin/python3`) com corpus e bateria vazios, a gramática sozinha detecta **52 relaxamentos** não autorizados. |
| Z1 e Z2 implementados e certificados no commit anterior | **ATENDIDO** | Commit `e4515f9` (`fix(evidence): regex de palavras inteiras e invalidação do certificado de evals (Z1/Z2)`). |
| Orçamento de linhas de código respeitado | **ATENDIDO** | `doc-audit.py` 7/7 aprovado. `find.py`: 188 linhas (≤ 300); `interpreters.py`: 155 linhas (≤ 300); `safety-gate.py`: 422 linhas (≤ 650). |

---

## 3. Prova Física de Falsificabilidade da Gramática (G5)

A gramática combinatória determinística (`seed=42`) gera 3.500 comandos com produções de interpretadores e find:
- Cabeças: `{python3, /usr/bin/python3, env python3, python3.12, node, perl, ruby}`
- Flags: `{-c, -e, --eval}`
- Literais: `{'/', '~', 'db', '/srv', '..'}`
- Find: caminhos `{/, ~, /etc, .., ., build, ./src}` × filtros `{∅, -name '*.pyc', -type f}` × ações `{-delete, -exec rm {} +, -execdir rm -rf {} \;, -ok rm {} \;, -print}`

### Reprodução da Mutação:
Com corpus e bateria esvaziados, desabilitou-se a resolução de prefixos de caminho em `resolve_interpreter_head` (fazendo com que `/usr/bin/python3` não seja associado a Python):
- **Resultado:** **52 relaxamentos detectados exclusivamente pela gramática**.
- Exemplos capturados:
  - `[development] deny(catastrophic)->allow (/usr/bin/python3 -c "import os; os.remove('/')")`
  - `[staging] deny(catastrophic)->allow (/usr/bin/python3 -c "import os; os.remove('/')")`
  - `[production] deny->allow (/usr/bin/python3 -c "import os; os.remove('db')")`
  - `[development] deny(catastrophic)->allow (/usr/bin/python3 -c "import os; os.rmdir('/srv')")`

---

## 4. Tabela de Casos da Bateria de Revisão Homologados no PR-06

| Linha | Ambiente | Decisão | Referência | Comando |
|---|---|---|---|---|
| 136 | development | deny/CATASTROPHIC | H017-G5 | `find / -delete` |
| 137 | development | deny/CATASTROPHIC | H017-G5 | `find /etc -delete` |
| 138 | development | deny/CATASTROPHIC | H017-G5 | `find ~ -delete` |
| 140 | production | deny | H017-G5 | `find . -name '*.pyc' -delete` |
| 142 | production | deny | H017-G5 | `python3 -c 'import shutil; shutil.rmtree("/srv")'` |
| 143 | production | deny | H017-G5 | `node -e 'require("fs").rmSync("db",{recursive:true})'` |
| 144 | production | deny | H017-G5 | `perl -e 'unlink glob "*"'` |
| 271 | development | deny/CATASTROPHIC | H024-G5 | `find .. -delete` |
| 272 | development | deny/CATASTROPHIC | H024-G5 | `find / -execdir rm -rf {} +` |
| 273 | production | deny | H024-G5 | `find .. -exec rm {} \;` |
| 275 | production | deny | H024-G5 | `find build -ok rm {} \;` |
| 279 | development | deny/CATASTROPHIC | H024-G5 | `/usr/bin/python3 -c "import shutil; shutil.rmtree('/')"` |
| 280 | development | deny/CATASTROPHIC | H024-G5 | `ruby -e "FileUtils.rm_rf('/')"` |
| 281 | production | deny | H024-G5 | `env python3 -c "import os; os.remove('a')"` |
| 282 | production | deny | H024-G5 | `python3.12 -c "import pathlib; pathlib.Path('db').unlink()"` |
