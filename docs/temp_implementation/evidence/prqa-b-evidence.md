# Relatório de Evidências — PR-QA-B: Invariante do Motivo

**Data:** 2026-09-28  
**Ambiente:** DEVELOPMENT (`OBSERVED`)  
**Autor:** Antigravity (Pair programming com Nando Dev)  
**Objetivo:** Implementar a suíte `test_reason_invariant.py` garantindo que todo texto de motivo (`reason`) retornado pelo Safety Gate seja matematicamente coerente com a decisão (`decision`), com o caso de uso (`use_case`) e mencione o ambiente e a evidência de detecção sempre que o ambiente influenciar a decisão.

---

## 1. Contrato de Invariantes do Motivo

A suíte `clearer-engineering/tests/test_reason_invariant.py` estabelece formalmente as seguintes propriedades invariantes sobre 1.381 avaliações (338 comandos do `gate_corpus.txt` × 3 ambientes + 367 linhas de `review_batteries.txt`):

1. **Decisões `deny`:**
   - O motivo DEVE conter pelo menos um marcador de bloqueio formal de lista fechada e versionada:
     - `[CEH PRODUCTION LOCK]`
     - `[CEH CATASTROPHIC BLOCK]`
     - `[CEH CERTIFICATE INTEGRITY`
     - `[CEH PRE-PUSH CI GATE]`
     - `[CEH SAFETY GATE - FAIL-CLOSED]`
     - `[CEH SAFETY GATE - GIT]`
     - `[CEH SAFETY GATE ERROR]`
     - `[CEH HOOK ERROR]`
     - `[CEH CONTEXT LOCK]`
2. **Decisões `allow`:**
   - O motivo NÃO pode conter nenhum marcador de bloqueio de `deny`.
   - O motivo NÃO pode conter o marcador de confirmação `ALERTA`.
3. **Decisões `ask`:**
   - O motivo DEVE conter explicitamente o marcador de confirmação `ALERTA`.
4. **Consistência do Caso de Uso (`use_case`):**
   - `CERTIFICATE_INTEGRITY`: motivo menciona obrigatoriamente `CERTIFICATE INTEGRITY`.
   - `CATASTROPHIC`: motivo menciona obrigatoriamente `CATASTROPHIC`.
   - `PRE_PUSH_CI`: motivo menciona obrigatoriamente `PRE-PUSH CI GATE`.
   - `PARSER_FAIL_CLOSED`: motivo menciona obrigatoriamente `FAIL-CLOSED` ou `PARSER_FAIL_CLOSED`.
5. **Ambiente e Evidência em Regras Dependentes:**
   - Para os casos de uso graduados por ambiente (`FILESYSTEM`, `GIT_HISTORY`, `GIT_DESTRUCTIVE`, `DATABASE`, `INFRASTRUCTURE`), o motivo DEVE conter:
     - O nome do ambiente detectado em maiúsculas (`DEVELOPMENT`, `STAGING`, `PRODUCTION`).
     - A evidência física ou contexto de detecção (`EVIDÊNCIA:`, `EVIDENCIA:`, ou `SOURCE:`).

---

## 2. Ajustes de Homogeneização Cirúrgica

Para cumprir a invariante universal de ambiente e evidência, o módulo `ceh_core/rm.py` foi ajustado cirurgicamente:
- Inclusão de `Ambiente detectado: {env.upper()} (Evidência: {env_evidence})` nos motivos de exclusão destrutiva forçada/recursiva em `production` e `staging`.
- Inclusão de `Ambiente: {env.upper()} (Evidência: {env_evidence})` na liberação de `development`.
- Inclusão do marcador `⚠️ ALERTA:` e evidência nos casos de alvo incerto (`[CEH UNCERTAIN TARGET]`).

---

## 3. Resultados dos Testes Locais

- **Execução Direta:**
  `python3 clearer-engineering/tests/test_reason_invariant.py`
  - 6 testes executados em 0.254s.
  - 1.381 avaliações de comandos cobertas no total.
  - Resultado: **OK (100% PASS, 0 falhas)**.
- **Auditoria Documental:**
  `bash clearer-engineering/scripts/doc-audit.sh`
  - 7/7 checagens aprovadas.
  - Orçamento de linhas estritamente preservado:
    - `safety-gate.py`: 624 linhas (teto 650)
    - `ceh_core/rm.py`: 246 linhas (teto 300)
    - `ceh_core/rules.py`: 226 linhas (teto 300)
    - Todos os 11 componentes core dentro do limite estrito.

---

## 4. Prova de Falsificabilidade por Mutação (Clone Isolado em `/tmp`)

Executada de forma determinística via script isolado clonando o repositório em `/tmp/ceh-mutation-reason-0id5ji0x`:
1. **Mutação Aplicada:**
   No arquivo `clearer-engineering/scripts/safety-gate.py` do clone, o marcador formal `[CEH PRODUCTION LOCK]` foi substituído pelo texto neutro `[ACESSO NEGADO]`.
2. **Execução:**
   `test_reason_invariant.py` executado sobre a árvore mutada.
3. **Evidência Observada:**
   O teste **FALHOU** com exit code 1, capturando 108 violações na bateria e violações no corpus, citando expressamente os comandos e a causa:
   ```
   AssertionError: 108 != 0 : Falhas no invariante do motivo na bateria (108 violações):
   [battery:L94:H017-G2] Decisão 'deny' sem marcador de bloqueio reconhecido.
     Comando: git checkout .
     Ambiente: production
     Motivo obtido: [ACESSO NEGADO] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO...
   ```
4. **Conclusão:**
   A prova confirma que qualquer alteração de motivo para texto neutro ou sem marcadores reconhecidos reprova imediatamente a suíte, citando o comando.

---

## 5. Validação de CI Remoto (GitHub Actions)

- **Commit:** `6a9217d`
- **Run ID:** `36422792664`
- **Link Canônico:** [run 36422792664](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36422792664)
- **Status:** `completed` / `conclusion: success` (4/4 jobs aprovados)
  - `Validate (ubuntu-latest - Python 3.12)`: **success**
  - `Validate (ubuntu-latest - Python 3.9)`: **success**
  - `Validate (macos-latest - Python 3.12)`: **success**
  - `Validate (macos-latest - Python 3.9)`: **success**
