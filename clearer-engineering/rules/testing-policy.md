# Testing Policy & Verification Standards

## 1. Verificação Determinística
- A expressão "testado" só pode ser utilizada se a suíte de testes correspondente foi realmente executada no ambiente.
- O registro de teste deve sempre conter:
  - **COMMAND**: O comando exato disparado.
  - **EXIT CODE**: O código de retorno retornado pelo processo.
  - **RESULT**: Quantidade de testes executados, passaram, falharam ou foram ignorados.

## 2. Proibição de Fake Pass
- Falhas de teste jamais podem ser omitidas ou mascaradas como sucesso.
- Se os testes não puderem ser executados por ausência de ambiente ou dependência externa, declare explicitamente como `NOT RUN` com o motivo técnico objetivo.
