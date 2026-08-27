---
name: clearer-test
description: >-
  Deterministic test execution and verification. Runs test suites, captures raw command outputs,
  and formats verifiable test evidence (COMMAND, EXIT CODE, PASS/FAIL/NOT RUN counts).
---

# CLEARER Deterministic Test Execution

Esta skill assegura a execução e registro auditável de testes automatizados no projeto.

> [!IMPORTANT]
> **Proibição de Testes Fictícios**: A palavra "testado" só pode ser usada quando uma suíte real foi executada e teve sua saída registrada.

---

## 1. Execução Automatizada

Execute o runner de testes do harness:
```bash
bash scripts/test-runner.sh
```
Ou execute um comando de teste específico da stack (ex: `./vendor/bin/pest`, `npm test`, `pytest`, `go test ./...`).

---

## 2. Contrato de Registro de Teste

Toda execução deve registrar no relatório:

```text
==========================================
COMMAND:   <comando exato executado>
EXIT CODE: <0 para sucesso, diferente de 0 para falha>
STATUS:    <PASS | FAIL | NOT RUN>
==========================================
RESULTADO:
- Testes Executados: <N>
- Passaram:          <N>
- Falharam:          <N>
- Ignorados:         <N>
```

---

## 3. Diretrizes de Tratamento de Falhas

1. **Falhas Reais**: Se qualquer teste falhar (`EXIT CODE != 0`), reporte o status como `FAIL`. Nunca mascara falhas como sucesso ou alerte falsamente que "tudo passou".
2. **Ambiente Ausente**: Se não for possível rodar os testes devido à falta de dependências ou ambiente ausente, reporte explicitamente como `NOT RUN`, registrando a razão técnica exata.
