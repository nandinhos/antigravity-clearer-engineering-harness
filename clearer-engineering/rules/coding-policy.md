# Coding Policy & Blast Radius Constraints

## 1. Inspect Before Edit
- Sempre leia os arquivos alvo e seus testes antes de propor ou aplicar edições.
- Entenda os padrões de nomenclatura, estilo de código e arquitetura existentes no repositório.

## 2. Blast Radius Mínimo
- Limite as alterações estritamente ao escopo da tarefa.
- Não reformate arquivos inteiros ou altere partes não relacionadas sem solicitação explícita.
- Preserve contratos de APIs públicas, interfaces e invariantes de tipos.

## 3. Root-Cause First para Bugs
- Nunca aplique um patch cego para esconder sintomas.
- Siga: Sintoma → Reprodução → Observação → Hipótese → Causa Raiz → Teste de Regressão → Correção Mínima.
