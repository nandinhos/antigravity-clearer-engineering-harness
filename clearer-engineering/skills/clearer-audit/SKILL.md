---
name: clearer-audit
description: >-
  Formal evidence and claim auditor. Verifies claims against concrete execution logs,
  test results, and source code, classifying claims as SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED.
---

# CLEARER Evidence & Claim Auditor

Esta skill atua como o auditor final da entrega técnica. Sua função é confrontar cada afirmação feita com evidências observáveis e verificáveis.

---

## 1. Princípio Fundamental de Auditoria

```text
CLAIM  <─────── Verificação ───────>  EVIDENCE
```

Toda conclusão técnica precisa estar vinculada a um fato comprovado. Expressões como *"deve funcionar"*, *"testado com sucesso"* (sem log) ou *"sem regressões"* (sem suíte executada) devem ser rejeitadas como **UNSUPPORTED**.

---

## 2. Categorias de Classificação

Para cada alegação ou critério de aceite:

- **`SUPPORTED`**: Totalmente comprovada por comando executado com exit code 0, arquivo lido ou linha de código inspecionada.
- **`PARTIALLY_SUPPORTED`**: Evidência parcial existe, mas faltam dados ou há suposição não verificada.
- **`UNSUPPORTED`**: Nenhuma evidência concreta foi fornecida, ou a evidência contradiz a afirmação.

---

## 3. Formato do Relatório de Auditoria

```text
### Claim: "O endpoint /api/v1/orders valida autenticação via Bearer token."
- Status: SUPPORTED
- Evidência:
  - Arquivo: routes/api.php:24 (middleware 'auth:sanctum')
  - Teste: tests/Feature/OrderApiTest.php:15 (assertUnauthorized when unauthenticated -> exit code 0)

### Claim: "Não ocorreram regressões no módulo de faturamento."
- Status: UNSUPPORTED
- Evidência: Nenhuma suíte de testes de faturamento foi disparada. O comando executado cobriu apenas a feature isolada.
```

---

## 4. Veredito Final de Auditoria

O auditor emite o parecer final:
- **`APPROVED`**: Todos os claims críticos são SUPPORTED e critérios de aceite foram atingidos.
- **`NEEDS_EVIDENCE`**: Existem claims cruciais marcados como UNSUPPORTED ou PARTIALLY_SUPPORTED.
- **`REJECTED`**: Foram encontradas contradições diretas entre os claims e as evidências reais do código/testes.
