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

## 2. Categorias de Classificação com Critérios Contrastivos (Espaço Fechado)

Para cada alegação ou critério de aceite, o julgamento é univariado e contrastivo:

| Categoria | `what` (Pertence estritamente a esta categoria) | `not_for` (Pertence a outra categoria) | `examples` |
|---|---|---|---|
| **`SUPPORTED`** | Comprovada diretamente por comando executado com exit code 0 e log, arquivo lido ou linha de código inspecionada. | Afirmações plausíveis sem log de execução anexado. | `"Testes de regressão passaram com exit code 0 (14/14 verdes)."` |
| **`PARTIALLY_SUPPORTED`** | Evidência parcial existente; código existe mas teste não rodou; inferência lógica coerente sem prova física. | Total ausência de código ou arquivo inexistente. | `"A classe OrderValidator possui o método, mas a suíte Feature não foi executada."` |
| **`UNSUPPORTED`** | Nenhuma evidência concreta fornecida, suposição sem amparo, ou evidência contradiz a afirmação. | Qualquer claim com evidência física observada. | `"O sistema suporta concorrência perfeitamente (sem teste de estresse)."` |

---

## 3. Formato do Relatório de Auditoria (Dois Eixos: Decisão & Certeza)

Cada claim é avaliado de forma atômica e independente:

```text
### Claim: "O endpoint /api/v1/orders valida autenticação via Bearer token."
- Status: SUPPORTED
- Certeza: 1.0 (Evidência Física Observada)
- Evidência:
  - Arquivo: routes/api.php:24 (middleware 'auth:sanctum')
  - Teste: tests/Feature/OrderApiTest.php:15 (assertUnauthorized -> exit code 0)

### Claim: "Não ocorreram regressões no módulo de faturamento."
- Status: UNSUPPORTED
- Certeza: 0.0 (Incerteza Crítica / Ausência de Teste)
- Evidência: Nenhuma suíte de faturamento executada. Comando cobriu apenas a feature isolada.
```

---

## 4. Veredito Final de Auditoria (Agregação Determinística em Código)

O veredito final é uma função determinística dos claims atômicos, **sem texto livre de opinião**:

- **`APPROVED`**: 100% dos claims críticos são `SUPPORTED` com evidência `OBSERVED`.
- **`NEEDS_EVIDENCE`**: Pelo menos 1 claim crítico é `PARTIALLY_SUPPORTED` ou `UNSUPPORTED`. Escala para obtenção de prova física.
- **`REJECTED`**: Pelo menos 1 claim entra em contradição direta com o código real ou logs de teste. Incerteza escalada imediatamente para o desenvolvedor.

