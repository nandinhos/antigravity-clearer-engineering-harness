# Evidência Técnica: PR-18b — Proveniência Verificável no Catálogo, Propriedade do Lexer e Falsificabilidade

**Data:** 2026-09-27  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Antecessor:** [Handoff 046](../handoffs/handoff-046-revisao-pr19c-pr18-despacho-pr18b.md)  
**Item do Plano:** PR-18b (Despacho do Handoff 046 §3)  
**Commits Antecessores:** `91658ab`, `702b972`, `dc97ccb`, `6f912ca`

---

## 1. Contexto e Despacho do Handoff 046
No Handoff 046 (§2), o revisor sênior aprovou a integridade do gate (0 relaxamentos), a correção dos 24 links quebrados e o parser hermético stdlib (4/4 jobs verdes no run 36350731370), porém bloqueou a homologação do PR-18 devido a dois pontos epistemológicos e dois de processo:
1. **AT1 (Alto):** Presença de arquivo autoral escrito pelo agente (`inventory.json`) dentro do diretório reservado a sondas físicas (`docs/temp_implementation/evidence/host-probe/`), fazendo declarações passarem por evidência `OBSERVED`. Além disso, o teste anterior só checava existência física do arquivo, não seu conteúdo.
2. **AT2 (Médio):** O teste aleatório anterior testava apenas a decisão do gate, que possui defesa em profundidade com `re.search`. A mutação do `||` não provocava falha no teste anterior porque a camada de regras interceptava o comando de qualquer forma.
3. **AT4 (Baixo):** Resíduos de caminho local `/home/nandodev` nos arquivos `.txt` das atas do Conselho e parecer do Claude vazio.
4. **AT5 (Processo):** Mutações de falsificabilidade devem ser executadas exclusivamente em clones isolados, mantendo o worktree de trabalho e os scripts core do gate 100% limpos.

---

## 2. Implementação Concluída no PR-18b

### 2.1. AT1 — Resolução de Proveniência Verificável e Remoção de Arquivo Autoral
- **Remoção de Arquivo Autoral:** O arquivo autoral `docs/temp_implementation/evidence/host-probe/agy/tools/inventory.json` e seu diretório pai foram sumariamente removidos. O diretório `evidence/host-probe/` agora contém **estritamente capturas físicas de sondas**.
- **Enum Estrito de Evidência no Catálogo (`tool_catalog.json` v1.1.0):**
  - `payload`: Exige arquivo `.jsonl` gravado por sonda real contendo a invocação comprovada da ferramenta (`toolCall.name == <nome>` no agy ou `tool_name == <nome>` no Claude). Comprovado para 4 ferramentas:
    - `run_command` (`agy` em `E1-r1/invocations.jsonl`)
    - `write_to_file` (`agy` em `E11-allow-write-padrao/invocations.jsonl`)
    - `Bash` (`claude` em `E1-r1/invocations.jsonl`)
    - `Write` (`claude` em `E7-r1/invocations.jsonl`)
  - `host_doc`: Exige captura de saída do host (`--help` ou documentação oficial) contendo textualmente o nome da ferramenta. Comprovado para:
    - `Edit` (`claude` no `e0_help.txt`)
  - `declared`: Nome declarado sem captura de sonda disponível. Nenhuma entrada `declared` aponta para dentro de `host-probe/`. Todas trazem `declaration_source` e `declaration_reason`. Comprovado e rotulado para 18 ferramentas (16 agy nativas e 2 claude: `MultiEdit`, `NotebookEdit`).
- **Validação de Conteúdo Real em `test_content_schema.py`:**
  - O teste agora abre e analisa o conteúdo dos arquivos de evidência: para `payload`, itera sobre as linhas do JSONL verificando o campo exato; para `host_doc`, verifica a presença do nome da ferramenta; para `declared`, valida a ausência de links espúrios para `host-probe/` e emite relatório auditável.

### 2.2. AT2 — Propriedade Matemática do Lexer (Ida e Volta / Roundtrip) em `test_lexer_fuzz.py`
- Adicionada a suíte `test_lexer_roundtrip_property_and_delimiters`:
  - **Propriedade de Ida e Volta:** Para 500 permutações determinísticas com semente 1337 de segmentos atômicos seguros unidos por `;`, `&&`, `||`, `|` e `\n`, valida formalmente:
    $$\text{split\_shell\_pipeline}(\text{join}(segs)) == (segs, \text{None})$$
  - **Separadores dentro de aspas:** Segmentos com operadores de shell dentro de aspas simples ou duplas (`echo 'a;b'`, `echo "x || y"`, `git commit -m "feat: a && b"`, etc.) continuam como um único segmento atômico (`len == 1`).
  - **Subshell como unidade:** Expressões entre parênteses `( ... )` acumulam internamente os operadores conforme a especificação em `lexer.py:85-99`, preservando a expressão intacta.
- **Invariante de Decisão do Gate:** Mantido e documentado com honestidade como `test_safety_gate_decision_invariant_2000_cases`, explicitando que a defesa em profundidade da camada de regras garante `decision != 'allow'` mesmo que partes do analisador léxico sofram mutação.

### 2.3. AT4 — Higiene das Atas do Conselho e Extensão do `doc-audit.py`
- **Sanitização das Atas:** Todos os arquivos `.txt` em `docs/temp_implementation/conselho/20260927_171054/` foram sanitizados, substituindo caminhos absolutos locais por referências relativas ao repositório.
- **Documentação de Ausência de Resposta:** O arquivo `parecer_claude.md` vazio foi preenchido com alerta explícito registrando que o conselheiro Claude não respondeu nesta deliberação (registrado para tratamento e endurecimento no PR-21).
- **Extensão do `doc-audit.py`:** A checagem [4/7] foi estendida para inspecionar, além dos arquivos `.md`, todos os arquivos `.txt` contidos em `docs/temp_implementation/conselho/`.

---

## 3. Prova de Falsificabilidade por Mutação em Clone Isolado (AT2 & AT5)

Conforme a regra do Handoff 046 §3.4, a prova de mutação foi executada **exclusivamente em clone descartável** criado em diretório temporário isolado (`/tmp/ceh-clone-falsifiability-7HVG8Z`), preservando a árvore local intocada.

### 3.1. Mutação Injetada no Clone
Injeção da mutação requerida no Handoff 046 §3.2 sobre `ceh_core/lexer.py`: o operador `||` deixa de dividir os segmentos e passa a ser acumulado no buffer como texto literal (`buf.append("||")`):
```diff
--- a/clearer-engineering/scripts/ceh_core/lexer.py
+++ b/clearer-engineering/scripts/ceh_core/lexer.py
@@ -133,5 +133,6 @@ def split_shell_pipeline(cmd_line: str) -> tuple[list[str] | None, str | None]:
         if c == "|":
             if i + 1 < n and cmd_line[i+1] == "|":
-                flush()
-                i += 2
+                buf.append("||")
+                i += 2
                 continue
```

### 3.2. Resultado da Execução no Clone com a Mutação
A propriedade de ida e volta **REPROVOU DETERMINISTICAMENTE** no primeiro caso avaliado (Caso #1) com **Exit Code 1**:
```text
FAIL: test_lexer_roundtrip_property_and_delimiters (__main__.TestLexerPropertiesAndFuzz.test_lexer_roundtrip_property_and_delimiters)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_lexer_fuzz.py", line 123, in test_lexer_roundtrip_property_and_delimiters
    self.assertEqual(
AssertionError: Lists differ: ['git diff || git diff', 'whoami || git status'] != ['git diff', 'git diff', 'whoami', 'git status']

First differing element 0:
'git diff || git diff'
'git diff'

Second list contains 2 additional elements.
First extra element 2:
'whoami'

- ['git diff || git diff', 'whoami || git status']
+ ['git diff', 'git diff', 'whoami', 'git status'] : Caso #1 VIOLOU PROPRIEDADE DE IDA E VOLTA DO LEXER:
  Comando original composto: 'git diff || git diff | whoami || git status'
  Segmentos esperados: ['git diff', 'git diff', 'whoami', 'git status']
  Segmentos obtidos pelo split: ['git diff || git diff', 'whoami || git status']

----------------------------------------------------------------------
Ran 2 tests in 0.589s

FAILED (failures=1)
Exit code com mutação do ||: 1
```

### 3.3. Confirmação do Comportamento do Invariante de Decisão
Durante a mesma execução com o lexer mutado, o `test_safety_gate_decision_invariant_2000_cases` continuou passando (`[SAFETY GATE INVARIANT] 2000 casos determinísticos em 0.585s`), demonstrando formalmente o diagnóstico do Handoff 046: **o invariante de decisão do gate é protegido em profundidade pelas expressões regulares das regras, enquanto a propriedade de ida e volta testa a integridade matemática da FSM do lexer**.

---

## 4. Auditoria de Estado Local e Integridade de Scripts (AT5)

A árvore de trabalho local permaneceu limpa, e o código core do analisador léxico e do Safety Gate não sofreu qualquer alteração no repositório:

### 4.1. Saída de `git diff --stat -- clearer-engineering/scripts/safety-gate.py clearer-engineering/scripts/ceh_core/`
```text
(vazia — 0 arquivos alterados, 0 inserções, 0 deleções)
```

### 4.2. Saída de `git diff --stat -- docs/plano-implementacao-elevacao-ceh.md`
```text
(vazia — 0 arquivos alterados)
```

---

## 5. Resultado da Suíte Canônica Local (`OBSERVED`) — 58/58 PASS (100%)

Execução da suíte canônica completa em ambiente local:
- **Comando:** `bash clearer-engineering/tests/run-all-tests.sh`
- **Total de Testes:** 58
- **Testes Aprovados:** 58 (100%)
- **Testes Reprovados:** 0
- **Auditoria Documental (`doc-audit.py`):** 7/7 checagens aprovadas.
- **Redes Diferenciais (`test_gate_differential_fuzz.py`):** 12.048 casos avaliados em 4.67s com 0 relaxamentos.

---

## 6. Resultado Comprovado no Servidor (`OBSERVED`) — 4/4 Jobs Verdes (100%)

No commit oficial [`62208b7`](https://github.com/nandinhos/antigravity-clearer-engineering-harness/commit/62208b75e2a1433d13916134ef3765e49e2f324a), a esteira do GitHub Actions concluiu com **100% de sucesso em todos os 4 jobs da matriz**:

- **Workflow Run:** [Run 36353326429](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36353326429)
- **Status:** `completed`, **Conclusion:** `success`
- **Jobs Validados:**
  1. `Validate (ubuntu-latest - Python 3.12)`: **success** (24 steps em 2m23s — [Job 108716061723](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36353326429/job/108716061723))
  2. `Validate (ubuntu-latest - Python 3.9)`: **success** (21 steps em 2m58s — [Job 108716061896](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36353326429/job/108716061896))
  3. `Validate (macos-latest - Python 3.12)`: **success** (22 steps em 16m43s — [Job 108716061809](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36353326429/job/108716061809))
  4. `Validate (macos-latest - Python 3.9)`: **success** (22 steps em 14m43s — [Job 108716061849](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36353326429/job/108716061849))
- **Hermeticidade e Robustez Comprovadas:**
  - O catálogo de ferramentas valida proveniência física para os tipos `payload` e `host_doc` e rotula com transparência as ferramentas `declared`.
  - A propriedade de ida e volta do analisador léxico (`split_shell_pipeline`) foi testada em 500 permutações in-process com semente 1337 em todos os runners sem falhas.
  - Zero dependências de terceiros no teste de esquema, rodando nativamente na stdlib do Python 3.9 e 3.12 em Linux e macOS.
