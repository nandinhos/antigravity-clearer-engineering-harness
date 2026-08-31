# Coding Policy & Staff Engineering Craftsmanship

## 1. Inspect Before Edit & Context Grounding
- Sempre leia os arquivos alvo e seus testes antes de propor ou aplicar edições.
- Entenda os padrões de nomenclatura, estilo de código, injeção de dependências e arquitetura existentes no repositório.
- A única fonte da verdade é o código e schemas observados (`OBSERVED`).

## 2. Blast Radius Mínimo & Precisão Cirúrgica
- Limite as alterações estritamente ao escopo da tarefa.
- Proibido reformatar arquivos inteiros ou introduzir ruído cosmético que dificulte o code review.
- Preserve contratos de APIs públicas, interfaces, schemas e invariantes de tipos existentes.

## 3. Tipagem Estrita & Código Idiomático
- Utilize tipagem forte e explícita em todas as assinaturas públicas e privadas.
- Evite tipos genéricos ou permissivos (`any`, `mixed`, `dynamic`) sem validação de tipo na borda (*type narrowing/guards*).
- Escreva código auto-documentado: nomes reveladores de intenção e responsabilidade única.

## 4. Engenharia Defensiva & Resiliência
- Trate sempre cenários de borda: entradas nulas/indefinidas, listas vazias, timeouts e desconexões.
- Aplique *fail-fast* com mensagens de erro semânticas e contextuais.
- Isole regras de negócio de detalhes de persistência e transporte (Clean Architecture / SOLID).

## 5. Root-Cause First para Bugs
- Nunca aplique um patch cego para esconder sintomas.
- Siga rigorosamente: Sintoma → Reprodução → Observação → Hipótese → Causa Raiz → Teste de Regressão → Correção Mínima.

