# Manual de Skills e Comandos do CEH

O CEH expõe 8 skills principais no Antigravity, cada uma projetada para um padrão operacional específico.

---

## 1. `/clearer` (Dispatcher Central)
- **Quando usar**: Ponto de entrada padrão para solicitações abertas.
- **Comportamento**: Analisa a solicitação, define o nível no Risk Dial (LOW, MEDIUM, HIGH) e roteia para a skill especializada correta.
- **Exemplo**:
  ```text
  /clearer "Preciso refatorar o serviço de notificações por email para suportar templates dinâmicos"
  ```

---

## 2. `/clearer-feature` (Desenvolvimento de Features)
- **Quando usar**: Implementação de novas funcionalidades ou melhorias de produto.
- **Fluxo**: `INSPECT → REQUIREMENTS → IMPACT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT`.
- **Exemplo**:
  ```text
  /clearer-feature "Implementar endpoint POST /api/v1/payments/pix com geração de payload copia-e-cola e QRCode"
  ```

---

## 3. `/clearer-bugfix` (Correção Root-Cause First)
- **Quando usar**: Investigação e resolução de bugs, falhas ou exceções.
- **Fluxo**: `SYMPTOM → REPRODUCTION → OBSERVATION → HYPOTHESIS → EVIDENCE → ROOT CAUSE → REGRESSION TEST → MINIMAL FIX → TEST → REVIEW`.
- **Exemplo**:
  ```text
  /clearer-bugfix "Erro 500 ao tentar calcular frete para CEP com formato 00000-000 sem hífens"
  ```

---

## 4. `/clearer-refactor` (Refatoração Segura)
- **Quando usar**: Melhoria de estrutura de código sem alteração do comportamento externo.
- **Fluxo**: `BASELINE TESTS → REFACTOR → TESTS RE-RUN → BEHAVIOR COMPARISON → DIFF AUDIT`.
- **Exemplo**:
  ```text
  /clearer-refactor "Extrair as validações de documento CPF/CNPJ do UserController para uma Rule dedicada"
  ```

---

## 5. `/clearer-review` (Revisão Adversarial de Diff)
- **Quando usar**: Inspeção de alterações antes de abrir um PR ou comitar código.
- **Comportamento**: Inspeciona `git diff`, executa `scripts/diff-audit.sh` e lista achados classificados em `BLOCKER`, `HIGH`, `MEDIUM`, `LOW`, `INFO`.
- **Exemplo**:
  ```text
  /clearer-review
  ```

---

## 6. `/clearer-audit` (Auditoria Formal de Claims)
- **Quando usar**: Verificação formal de que todos os critérios de aceite foram atendidos e suportados por testes.
- **Comportamento**: Cruza declarações com evidências e classifica como `SUPPORTED`, `PARTIALLY_SUPPORTED` ou `UNSUPPORTED`.
- **Exemplo**:
  ```text
  /clearer-audit
  ```

---

## 7. `/clearer-map` (Mapeamento Arquitetural)
- **Quando usar**: Onboarding em nova base de código ou descoberta de arquitetura.
- **Comportamento**: Executa análise read-only e produz mapa completo de stack, rotas, banco, testes e matriz de risco.
- **Exemplo**:
  ```text
  /clearer-map
  ```

---

## 8. `/clearer-test` (Execução Determinística de Testes)
- **Quando usar**: Execução e captura de logs brutos de testes.
- **Comportamento**: Executa o test runner da stack via `scripts/test-runner.sh` e formata a saída com COMMAND, EXIT CODE e contagem de testes.
- **Exemplo**:
  ```text
  /clearer-test
  ```
