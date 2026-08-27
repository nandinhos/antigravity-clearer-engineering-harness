# CLEARER Protocol & Core Engineering Principles

## 1. O Ciclo Completo de Engenharia
Toda alteração de código passa pelas etapas fundamentais:
- **Inspect**: Inspecione o estado atual do repositório, branches e arquivos.
- **Plan**: Defina o problema, o blast radius, os arquivos envolvidos e a estratégia de testes.
- **Implement**: Aplique as mudanças com foco estrito no escopo delimitado.
- **Test**: Execute a suíte de testes relevante e capture os resultados brutos.
- **Review**: Realize uma revisão crítica e adversarial do diff gerado.
- **Validate**: Confirme se os critérios de aceite foram integralmente atendidos.
- **Report**: Emita o relatório final de evidências.

## 2. Risk Dial e Modulação de Esforço
- **LOW**: Alterações simples, cosméticas ou leituras. Execução direta com inspeção mínima.
- **MEDIUM**: Desenvolvimento padrão de software. Exige plano, testes e diff audit.
- **HIGH**: Componentes críticos (autenticação, transações financeiras, concorrência, migrações de dados). Exige isolamento em subagentes, revisão adversarial e auditoria formal.
