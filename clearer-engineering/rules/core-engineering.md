# CLEARER Protocol & Core Engineering Principles

## 1. O Ciclo Completo de Engenharia (Pipeline Contínuo)
Toda alteração de código passa pelas etapas fundamentais, executadas de forma contínua em tarefas de nível MEDIUM:
- **Inspect**: Inspecione o estado atual do repositório, dependências, branches e arquivos alvo.
- **Plan**: Defina o problema, o blast radius, os arquivos envolvidos, os contratos preservados e a estratégia de testes.
- **Implement**: Aplique as mudanças cirurgicamente com padrões de alto nível (SOLID, tipagem estrita).
- **Test**: Execute a suíte de testes real e capture o exit code e saídas brutas.
- **Review**: Realize uma revisão crítica e adversarial do diff gerado (`scripts/diff-audit.sh`).
- **Validate**: Confirme se os critérios de aceite foram integralmente atendidos.
- **Report**: Emita o relatório final de evidências auditáveis (Response Contract).

## 2. Risk Dial e Automação de Execução
- **LOW**: Alterações simples, cosméticas ou leituras. Execução rápida e direta sem overhead.
- **MEDIUM (Padrão de Engenharia)**: Execução contínua em turno único (Single-Turn End-to-End). O agente orquestra todo o ciclo CLEARER sem paradas artificiais se o escopo estiver delimitado.
- **HIGH**: Componentes críticos (autenticação core, transações financeiras, concorrência complexa, migrações destrutivas). Exige isolamento em subagentes especializados, revisão adversarial profunda e checkpoint humano explícito.

## 3. Gestão por Exceção
O agente opera de ponta a ponta e só transfere o controle ao desenvolvedor (handoff) caso ocorra ambiguidade de requisitos, disparo do Safety Gate, falha de teste após auto-reparo ou escopo classificado como HIGH.

