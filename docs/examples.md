# Exemplos Práticos de Uso do CEH

Este documento apresenta fluxos reais de engenharia utilizando o **CLEARER Engineering Harness** em diferentes ecossistemas.

---

## 1. Exemplo: Criação de Feature em TypeScript / Next.js (Risk: MEDIUM)

### Prompt do Desenvolvedor:
```text
/clearer-feature "Implementar endpoint POST /api/v1/auth/reset-password com envio de token assinado e expiração de 15 minutos"
```

### Ciclo Executado pelo CEH:
1. **INSPECT**:
   - `scripts/detect-project.sh` identifica Node.js, TypeScript, Next.js e Vitest.
   - Lê `app/api/auth/` e `lib/jwt.ts`.
2. **PLAN**:
   - Mapeia criação de `app/api/v1/auth/reset-password/route.ts` e `lib/tokens.ts`.
   - Contratos estáveis: Não alterar a rota legada `/api/auth/reset`.
3. **IMPLEMENT**:
   - Gera as rotas e funções com blast radius mínimo.
4. **TEST**:
   - Dispara `scripts/test-runner.sh` (`pnpm test`).
   - 12 testes passam com exit code 0.
5. **REVIEW**:
   - `scripts/diff-audit.sh` valida que não há tokens expostos ou conflitos.
6. **REPORT**:
   - Emite o Response Contract com confiança `HIGH`.

---

## 2. Exemplo: Correção de Bug em Laravel / PHP (Risk: MEDIUM)

### Prompt do Desenvolvedor:
```text
/clearer-bugfix "Erro no cálculo de frete quando o cliente tem cupom de frete grátis e o carrinho ultrapassa 50kg"
```

### Ciclo Root-Cause First Executado:
1. **SYMPTOM**: O cálculo cobra frete indevido quando o peso excede 50kg, ignorando o cupom `FRETE_GRATIS`.
2. **REPRODUCTION**: Escreve o teste `tests/Feature/ShippingCalculationTest.php` reproduzindo a falha.
3. **OBSERVATION**: O teste falha (`Status: FAIL, Exit code: 1`).
4. **ROOT CAUSE**: No `ShippingService.php:54`, a regra de peso máximo (`if ($weight > 50)`) executava antes da validação do cupom.
5. **MINIMAL FIX**: Inverte a precedência da checagem para respeitar o cupom de isenção total.
6. **REGRESSION TEST**: Reexecuta `vendor/bin/pest` -> Todos os testes passam (`Status: PASS, Exit code: 0`).
7. **REVIEW & AUDIT**: Claim "Bug corrigido" é classificado como `SUPPORTED`.

---

## 3. Exemplo: Refatoração em Python / FastAPI (Risk: MEDIUM)

### Prompt do Desenvolvedor:
```text
/clearer-refactor "Extrair lógica de conexão de banco de dados do main.py para um repositório assíncrono em app/db/session.py"
```

### Ciclo de Refactor Seguro:
1. **BASELINE**: Executa `pytest` antes de editar. Todos os 45 testes passam.
2. **REFACTOR**: Move a inicialização do SQLAlchemy para `app/db/session.py` sem alterar as dependências injetadas nas rotas.
3. **RE-RUN TESTS**: Executa novamente `pytest`. 45 testes continuam passando.
4. **DIFF AUDIT**: Verifica que as assinaturas das rotas no `main.py` não sofreram alteração.
5. **REPORT**: Confirma integridade comportamental.
