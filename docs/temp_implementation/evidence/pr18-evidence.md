# Evidência Técnica: PR-18 — Validação de Esquema no Lugar de Grep em Markdown & Fuzzing do Lexer

**Data:** 2026-09-27  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Antecessor:** [Handoff 045](../handoffs/handoff-045-revisao-pr19b-despacho-pr19c-pr18.md)  
**Item do Plano:** T3 / PR-18 (§4 do Handoff 045)  
**Deliberação Técnica:** [Ata do Conselho de Seniores](../conselho/20260927_171054/ata_conselho.md)

---

## 1. Contexto e Motivação (T3)
No Handoff 045 (§4), o revisor identificou a fragilidade das checagens estruturais em `run-all-tests.sh:142–165`, que utilizavam `grep -q` para verificar a presença de ferramentas e padrões em arquivos Markdown de agentes e skills. Essa abordagem apresentava falsos positivos e não validava a integridade semântica real (estrutura YAML, esquemas de campos obrigatórios, resolução de links e existência física de ferramentas e skills).

Além disso, definiu-se a necessidade de um teste de robustez determinístico por fuzzing in-process sobre o analisador léxico (`ceh_core/lexer.py`) e o Safety Gate (`safety-gate.py`).

---

## 2. Implementação Concluída

### 2.1. Catálogo Versionado de Ferramentas (`tool_catalog.json`)
- **Arquivo Criado:** `clearer-engineering/config/tool_catalog.json`
- **Ferramentas Catalogadas:** 23 ferramentas nativas do Antigravity IDE/CLI (`run_command`, `write_to_file`, `replace_file_content`, `view_file`, `grep_search`, `list_dir`, etc.).
- **Mapeamento de Evidência Física:** Cada ferramenta possui metadados contratuais (`name`, `description`, `source_type: "native_agy"`, `evidence_file`) apontando para arquivo físico verificado em `docs/temp_implementation/evidence/host-probe/agy/tools/inventory.json`.

### 2.2. Correção de Links Quebrados em Documentação
- Identificados e corrigidos **24 links relativos quebrados** nos arquivos de documentação do plugin:
  - `clearer-engineering/README_PT.md`: 12 links corrigidos (`./docs/...` -> `../docs/...`).
  - `clearer-engineering/README.md`: 12 links corrigidos (`./docs/...` -> `../docs/...`).
- Verificação exaustiva confirmou **0 links quebrados** entre todos os 93 links relativos dos 30 arquivos Markdown do repositório.

### 2.3. Validação Formal de Esquema de Conteúdo (`test_content_schema.py`)
- **Arquivo Criado:** `clearer-engineering/tests/test_content_schema.py` (15 testes unitários).
- **Cobertura de Contratos:**
  - Frontmatter YAML válido com `name` e `description` não-vazios em todos os agentes, skills e perfis.
  - Conformidade de nomenclatura (`name` estritamente idêntico ao nome do diretório correspondente).
  - Toda menção a `/nome` de skill nos perfis e agentes resolve para um arquivo físico existente (`skills/<nome>/SKILL.md`).
  - Todas as ferramentas declaradas nos perfis e subagentes existem no catálogo versionado.
  - Todos os links relativos em Markdown resolvem para alvos físicos existentes com indicação de arquivo e linha em diagnósticos.

### 2.4. Fuzzing Determinístico In-Process do Lexer (`test_lexer_fuzz.py`)
- **Arquivo Criado:** `clearer-engineering/tests/test_lexer_fuzz.py`
- **Arquitetura (Parecer Codex & Antigravity):**
  - Semente determinística fixa: `random.Random(1337)`.
  - Execução **100% in-process / in-memory** via `importlib.util` (zero forks de subprocesso, tempo de execução: ~0.58s).
  - Cobertura obrigatória por classe de operador (`;`, `&&`, `||`, `|`, `\n`) combinando segmentos seguros e destrutivos.
  - **Invariante Formal Inegociável:** Sob `--env production`, nenhuma cadeia contendo segmento destrutivo pode receber a decisão `allow` (`decision != 'allow'`).
  - **Fail-Closed:** Erros de sintaxe ou parsing escalam compulsoriamente para `deny` (`severity="PARSER_FAIL_CLOSED"`).

### 2.5. Integração na Suíte Canônica (`run-all-tests.sh`)
- Substituídos os greps estruturais de ferramentas pelas chamadas formais aos validadores:
  - Teste 30: `Tool Catalog (23 ferramentas mapeadas para evidências físicas)`
  - Teste 31: `Content Schema (perfis, subagentes e links relativos)`
  - Teste 32: `Lexer Fuzzing (fuzzing determinístico in-process com 2.000 casos)`
- Mantidas e documentadas as asserções de texto sobre políticas e padrões declarados (Gates de debug, learned-lesson, Ponytail UX e aliases).

---

## 3. Provas de Falsificabilidade por Mutação

### 3.1. Falsificabilidade do Content Schema (`test_content_schema.py`)
- **Mutação Injetada:** Injeção temporária de link quebrado na linha 233 de `clearer-engineering/skills/clearer-bugfix/SKILL.md`.
- **Resultado Observado:** O teste falhou deterministicamente com AssertionError, acusando o arquivo e a linha exata do link quebrado:
  ```
  AssertionError: Encontrados 1 links quebrados em arquivos Markdown:
    clearer-engineering/skills/clearer-bugfix/SKILL.md:233 -> docs/nao-existe.md (alvo não existe)
  ```
- **Restauração:** Arquivo restaurado ao estado limpo imediatamente após a prova.

### 3.2. Falsificabilidade do Fuzzing do Lexer (`test_lexer_fuzz.py`)
- **Mutação Injetada:** Desativação temporária da interceptação de padrões destrutivos em `clearer-engineering/scripts/safety-gate.py` (simulando vazamento de comando destrutivo para `allow` em produção).
- **Resultado Observado:** O teste falhou deterministicamente em **0.007s** com exit code 1, capturando 5 violações de invariante e imprimindo os comandos mínimos violadores:
  ```
  AssertionError: Fuzzing do Lexer FALHOU com 5 violação(ões) no teste in-process:
  Caso #1 VIOLOU INVARIANTE:
    Comando: 'cargo check ; git reset --hard'
    Decisão recebida: allow (esperado != 'allow')
  ```
- **Restauração:** Arquivo restaurado ao estado limpo imediatamente após a prova.

---

## 4. Resultado da Suíte Canônica Local (`OBSERVED`) — 58/58 PASS (100%)

Execução da suíte canônica completa em ambiente local limpo:
- **Comando:** `bash clearer-engineering/tests/run-all-tests.sh`
- **Total de Testes:** 58
- **Testes Aprovados:** 58 (100%)
- **Testes Reprovados:** 0
- **Auditoria Documental (`doc-audit.py`):** 7/7 checagens aprovadas.
