# Evidência de Justificativa de Diff do Golden Corpus e Comparação Diferencial (PR-05e)

Este documento registra a evolução do Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) e a **comparação diferencial automatizada** entre o gate do **PR-05d** (`41e665f`) e o do **PR-05e**, atendendo estritamente ao **Handoff 022** para fechamento do achado X1 (magia curta combinada de pathspec: `:/!x`, `:/^x`, `:/!:x`) e X2 (varredura irrestrita de session IDs em todo o `docs/`).

## Resumo Executivo das Alterações
- Total de avaliações no Golden Corpus anterior (PR-05d): **985**
- Registros preexistentes alterados: **0** (100% das 985 avaliações antigas permanecem idênticas)
- Novos comandos adicionados ao corpus: **9 comandos** (6 destrutivos e 3 controles seguros)
- Novas avaliações geradas (9 × 3 ambientes): **27 avaliações**
- Total consolidado pós-PR-05e: **1012 avaliações**

---

## 1. Intactabilidade das Decisões Preexistentes (Auditoria de Regressão Zero)
Uma verificação de integridade comparou as 985 primeiras linhas do novo `gate_corpus.expected.jsonl` com o snapshot de referência (`41e665f`):
- Total de divergências em decisões antigas: **0**
- Relaxamentos em comandos antigos: **0**
- Veredito: **NENHUMA decisão pré-existente foi alterada ou enfraquecida.**

---

## 2. Comparação Diferencial Registrada (PR-05d vs PR-05e nos 3 Ambientes)
Todos os 357 comandos únicos presentes no Golden Corpus e nas baterias de revisão foram executados sob o gate de `41e665f` e sob o gate do PR-05e em DEV, STAGING e PRODUCTION (1071 avaliações totais).

### Resultado Consolidado:
- **Total de comandos avaliados:** 357
- **Total de avaliações (× 3 ambientes):** 1071
- **Decisões idênticas:** 1063
- **Apertos de segurança (tightenings: allow → deny/ask):** 8
- **Relaxamentos de segurança (relaxations: deny → allow/ask):** **0 (ZERO)**

### Detalhamento dos 8 Apertos de Segurança (X1):
- `git checkout -- ':/!:x'`: allow → ask (STAGING), allow → deny (PRODUCTION)
- `git checkout -- ':/!x'`: allow → ask (STAGING), allow → deny (PRODUCTION)
- `git checkout -- ':/^x'`: allow → ask (STAGING), allow → deny (PRODUCTION)
- `git restore ':/!app'`: allow → ask (STAGING), allow → deny (PRODUCTION)

### Transições de Relaxamento:
**NENHUMA transição de relaxamento detectada.**

---

## 3. Fundamentação Normativa da Sintaxe de Pathspec (gitglossary)
Conforme a seção *pathspec* do `git help gitglossary`:
> "In the short form, the leading magic signature starts with a ':' and is followed by zero or more magic characters:
> '/' makes the pattern match from the root of the working tree.
> '!' or '^' excludes the path from being processed.
> A colon ':' can be used to terminate the magic signature and separate it from the pattern..."

O analisador consome a assinatura de mnemônicos (`/`, `!`, `^`) e o terminador `:` opcional:
- Se contiver `!` ou `^` (exclusão/negação), a operação descarta tudo exceto o padrão excluído -> classificado como **amplo** (`True`).
- Se contiver `/`, o padrão restante é avaliado a partir da raiz do repositório (com as checagens normativas de `$`/`~`, normalização lexical e glob no 1º segmento).

---

## 4. Orçamento de Linhas Core (Conformidade Bounded Core)
- `ceh_core/git.py`: **296 linhas** (Teto: 300)
- `ceh_core/rules.py`: **63 linhas** (Teto: 300)
- `safety-gate.py`: **410 linhas** (Teto: 650)
- `test-runner.sh`: **193 linhas** (Teto: 200)
