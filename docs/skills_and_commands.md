# Manual de Skills e Comandos do CEH

O CEH expõe 10 skills principais no Antigravity, cada uma projetada para um padrão operacional específico.

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

## 3. `/clearer-bugfix` (Systematic Debugging v2.0 — 5 Gates Bloqueantes)
- **Quando usar**: Investigação e resolução determinística de bugs, falhas ou exceções sem suposições.
- **Motor**: Executa estritamente os 5 Gates Bloqueantes:
  - **Gate 0: Triagem & Blast Radius**: Mapeamento do sintoma, stack trace e severidade (P0/P1/P2/P3).
  - **Gate 1: Reprodução Red**: Teste automatizado ou script mínimo comprovando a falha antes de qualquer patch.
  - **Gate 2: Matriz de Hipóteses Falsificáveis**: Mínimo 2 hipóteses concorrentes com critérios de refutação.
  - **Gate 3: Causa Raiz**: Isolamento do mecanismo exato via 5 Whys, Ishikawa e 7 taxonomias de causa raiz.
  - **Gate 4: Fix Mínimo & Prevenção em 3 Níveis**: Menor diff funcional transformando o teste em Green + Detector de regressão + Barreira arquitetural + Runbook.
- **Conclusão**: Emite o Debug Report padronizado com prompt interativo para persistência imediata via `/learned-lesson`.
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
- **Quando usar**: Execução e captura de logs de testes sem ruído.
- **Comportamento**: Executa o test runner da stack via `scripts/test-runner.sh`, envelopando automaticamente com `rtk` (quando disponível no `$PATH`) para condensar o log em até 80%, formatando a saída com COMMAND, EXIT CODE e contagem de testes.
- **Exemplo**:
  ```text
  /clearer-test
  ```

---

## 9. `/learned-lesson` (Motor de Memória Técnica & Prevenção)
- **Quando usar**: Após resolver um bug crítico (especialmente pós Gate 4 de `/clearer-bugfix`), descobrir comportamentos inesperados de runtime/stack ou consolidar boas práticas arquiteturais.
- **Comportamento**: Extrai, padroniza e persiste a memória técnica com taxonomia formal (`error`, `lesson`, `best_practice`). Suporta nativamente o hub `dev-memory` (MCP) e operação local via `.agents/rules/` ou `.dev-memory/learned-lessons.jsonl`.
- **Exemplo**:
  ```text
  /learned-lesson "Registrar causa raiz e prevenção para o deadlock de workers no Redis Sail"
  ```

---

## 10. `/clearer-adhd` (Modo Hiperfoco & Ponytail UX)
- **Quando usar**: Em momentos de sobrecarga mental, quando precisar de extrema brevidade, foco contínuo ou respostas operacionais diretas sem enrolação social.
- **Comportamento**: Aplica as 10 heurísticas cognitivas inegociáveis: inicia diretamente com a ação (comando/diff), numera passos estritamente, fecha com exatamente 1 próximo passo < 2 min, suprime tangentes, explicita o estado atual, limita listas a 5 itens e elimina preâmbulos/saudações ocas.
- **Exemplo**:
  ```text
  /clearer-adhd "Implementar validação de CPF sem preâmbulos"
  ```
