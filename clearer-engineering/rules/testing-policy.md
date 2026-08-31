# Testing Policy & Verification Standards

## 1. Verificação Determinística & Não-Mascarada
- A expressão "testado" só pode ser utilizada se a suíte de testes correspondente foi realmente executada no ambiente.
- O registro de teste deve sempre conter:
  - **COMMAND**: O comando exato disparado.
  - **EXIT CODE**: O código de retorno retornado pelo processo.
  - **RESULT**: Quantidade de testes executados, passaram, falharam ou foram ignorados.

## 2. Testes Comportamentais & Cenários de Borda
- Todo novo recurso ou correção de bug deve ser acompanhado de testes determinísticos focados em comportamento real.
- Teste explicitamente cenários felizes (*happy path*), cenários de falha (*unhappy path*), valores nulos, vazios e limites numéricos.
- Evite mocks excessivos que escondam quebras de integração reais.

## 3. Auto-Reparo Fundamentado em Evidências
- Se um teste falhar durante o ciclo de desenvolvimento, o agente realiza **1 iteração de diagnóstico e ajuste cirúrgico**, baseando-se no stack trace e asserção observada.
- Se o teste continuar falhando após a iteração de ajuste, o agente ativa o checkpoint por exceção e emite handoff com o diagnóstico objetivo.

## 4. Proibição Absoluta de Fake Pass
- Falhas de teste jamais podem ser omitidas, ignoradas ou mascaradas como sucesso.
- Se os testes não puderem ser executados por ausência de ambiente ou dependência externa, declare explicitamente como `NOT RUN` com o motivo técnico objetivo.

