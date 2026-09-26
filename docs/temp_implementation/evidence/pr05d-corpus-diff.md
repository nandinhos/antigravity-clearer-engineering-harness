# Evidência de Justificativa de Diff do Golden Corpus e Comparação Diferencial (PR-05d)

Este documento registra formalmente a evolução do Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) e a **comparação diferencial automatizada** entre o gate do **PR-05c** (`c2b191d`) e o do **PR-05d**, atendendo estritamente aos requisitos do **Handoff 021** para resolução dos achados W1 (avaliação de todos os posicionais), W2 (resolução de prefixos de opções longas), W3 (glob no primeiro segmento), W4 (variável `$` e til `~` no pathspec) e W5 (helper unificado de decisão por ambiente).

## Resumo Executivo das Alterações
- Total de avaliações no Golden Corpus anterior (PR-05c): **901**
- Registros preexistentes alterados: **0** (100% das 901 avaliações antigas permanecem idênticas)
- Novos comandos adicionados ao corpus: **28 comandos** (22 destrutivos e 6 controles seguros)
- Novas avaliações geradas (28 × 3 ambientes): **84 avaliações**
- Total consolidado pós-PR-05d: **985 avaliações**

---

## 1. Intactabilidade das Decisões Preexistentes (Auditoria de Regressão Zero)
Uma verificação de integridade comparou as 901 primeiras linhas do novo `gate_corpus.expected.jsonl` com o snapshot de referência (`c2b191d`):
- Total de divergências em decisões antigas: **0**
- Relaxamentos em comandos antigos: **0**
- Veredito: **NENHUMA decisão pré-existente foi alterada ou enfraquecida.**

---

## 2. Comparação Diferencial Registrada (PR-05c vs PR-05d nos 3 Ambientes)
Em cumprimento ao item 3 e critério de aceite do Handoff 021 (antecipação do PR-QA-A), todos os 348 comandos únicos presentes no Golden Corpus e nas baterias de revisão foram executados sob o gate de `c2b191d` e sob o gate do PR-05d em DEV, STAGING e PRODUCTION (1044 avaliações totais).

### Resultado Consolidado:
- **Total de comandos avaliados:** 348
- **Total de avaliações (× 3 ambientes):** 1044
- **Decisões idênticas:** 1006
- **Apertos de segurança (tightenings: allow → deny/ask):** 38
- **Relaxamentos de segurança (relaxations: deny → allow/ask):** **0 (ZERO)**

### Detalhamento dos 38 Apertos de Segurança (W1, W2, W3, W4):
Todos os apertos correspondem estritamente aos fechamentos das vulnerabilidades e regressões apontadas no Handoff 021:

1. **W1 (Avaliação de todos os posicionais em checkout):**
   - `git checkout . app/x`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git checkout src/.. app/x`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git checkout ./src/.. app/Model.php`: allow → ask (STAGING), allow → deny (PRODUCTION)

2. **W2 (Prefixos e abreviações de opções longas):**
   - `git checkout --forc main`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git switch --discard main`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git switch --force-c main`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git switch --discard-c main`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git restore --staged --work .`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git restore --pathspec-from=list.txt`: allow → ask (STAGING), allow → deny (PRODUCTION)

3. **W3 (Glob no primeiro segmento do pathspec):**
   - `git checkout -- '*.php'`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git restore '*.php'`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git checkout -- ./*`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git checkout -- '**'`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git restore -- '[a-z]*'`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git checkout -- "?*.js"`: allow → ask (STAGING), allow → deny (PRODUCTION)

4. **W4 (Variáveis ou til no pathspec):**
   - `git checkout -- "$PWD"`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git restore $DIR`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git checkout -- ~`: allow → ask (STAGING), allow → deny (PRODUCTION)
   - `git checkout -- ~/projects/repo`: allow → ask (STAGING), allow → deny (PRODUCTION)

### Transições de Relaxamento:
**NENHUMA transição de relaxamento detectada.**

---

## 3. Controles Seguros Preservados (`allow` em todos os ambientes)
- `git checkout main app/x` (W1 controle: refs de branch não colapsam para amplo)
- `git checkout --quiet main` (W2 controle: opção inócua conhecida)
- `git switch --detach HEAD~1` (W2 controle: opção inócua conhecida)
- `git switch --guess main` (W2 controle: opção inócua conhecida)
- `git checkout -- src/*` (W3 controle: glob em subdiretório seguro)
- `git checkout -- 'src/*.php'` (W3 controle: glob em subdiretório seguro)
- `git checkout -- tests/*` (W3 controle: glob em subdiretório seguro)

---

## 4. Orçamento de Linhas Core (Conformidade Bounded Core)
- `ceh_core/git.py`: **262 linhas** (Teto: 300)
- `ceh_core/rules.py`: **63 linhas** (Teto: 300)
- `safety-gate.py`: **390 linhas** (Teto: 650)
- `test-runner.sh`: **193 linhas** (Teto: 200)
