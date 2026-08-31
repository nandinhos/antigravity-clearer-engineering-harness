# Padrões de Código e Craftsmanship de Alto Nível (CEH)

Este documento estabelece as diretrizes técnicas para garantir que qualquer alteração de código realizada no âmbito do **CLEARER Engineering Harness (CEH)** atenda aos padrões de excelência de *Staff Software Engineering*.

---

## 1. Princípios Fundamentais de Arquitetura e Design

### A. Clean Code & Responsabilidade Única (SRP)
- Funções, classes e módulos devem ter um único propósito bem delineado.
- Nomes de variáveis, funções e tipos devem revelar intenção sem necessidade de comentários supérfluos.
- Métodos longos (> 50 linhas) devem ser refatorados em sub-rotinas coesas.

### B. Tipagem Estrita e Type Narrowing
- Todas as funções públicas e privadas devem possuir tipos explícitos de entrada e retorno.
- Proibido o uso indiscriminado de `any`, `mixed` ou `object` genérico sem validação de tipo na borda (*type guards*, schemas Zod/Valibot, form requests ou DTOs tipados).
- Evitar suposições sobre a estrutura de dados externos (APIs, banco de dados, payloads de eventos).

### C. Arquitetura Defensiva & Resiliência
- **Tratamento de Nulos**: Sempre tratar explicitamente `null`, `undefined` e valores opcionais com encadeamento seguro (`?.`) e operadores de coalescência nula (`??`).
- **Fail-Fast com Semântica Clara**: Validar invariantes no início da execução e lançar exceções de domínio específicas com mensagens contextuais.
- **Isolamento de Domínio**: Regras de negócio não devem depender diretamente de detalhes de transporte (HTTP controllers) ou persistência bruta (SQL inline solto).

---

## 2. Padrões por Stack Tecnológica

### A. Ecossistema PHP / Laravel
- Utilizar **Form Requests** para validação de entrada, **DTOs** para transporte de dados e **Action Classes / Services** para regras de negócio complexas.
- Eloquent: usar sempre *Eager Loading* (`with(...)`) para evitar o problema de N+1 queries.
- Migrações: declarar tipos estritos de coluna e índices apropriados para chaves estrangeiras.

### B. Ecossistema TypeScript / Node / React
- TypeScript no modo estrito (`strict: true`).
- Imutabilidade em manipulações de estado.
- Componentes React funcionais e puros com hooks customizados isolando a lógica de negócio.
- Validação de contratos de API via schemas em tempo de execução.

### C. Ecossistema Python
- Type annotations completas com `mypy` / `typing`.
- Uso de `dataclasses` ou `Pydantic` para modelagem de dados.
- Gerenciamento de contexto com `with` para recursos (arquivos, conexões, locks).

---

## 3. Gestão de Testes e Zero Regressão

### A. Testes Comportamentais vs. Mocks Excessivos
- Priorizar testes de integração e comportamento real sobre testes repletos de mocks frágeis que não validam a interoperabilidade.
- Testar explicitamente:
  - Caminho principal (*Happy Path*)
  - Cenários de erro e exceções esperadas (*Unhappy Path*)
  - Casos de borda: listas vazias, nulos, limites de paginação e concorrência.

### B. Determinismo
- Testes não devem depender de ordem de execução ou estado compartilhado mutável.
- Seeds e factories devem gerar dados determinísticos e isolados.

---

## 4. Blast Radius Mínimo e Auto-Auditoria de Diff

Antes de concluir qualquer entrega:
1. Rodar `scripts/diff-audit.sh` para auditar o diff do Git.
2. Garantir que não há arquivos temporários, logs soltos (`console.log`, `dd()`, `print()`), ou quebras de formatação em arquivos não relacionados.
3. Emitir o **Response Contract** com evidências comprovadas (`OBSERVED` / `SUPPORTED`).
