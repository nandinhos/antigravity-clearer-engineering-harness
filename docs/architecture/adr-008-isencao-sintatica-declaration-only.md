# ADR 008: Isenção Sintática (AST-Based) para Módulos Puramente Declarativos

## Status
**ACEITO & REGISTRADO** (Decisão de fronteira arquitetural preventiva; nenhum gate de contagem de linhas arbitrário foi introduzido no CEH na v2.1.2+)

---

## Contexto & Problema

Em toolkits e linters de desenvolvimento assistido por IA (como observado no `vibe-coding-toolkit`), é comum a introdução de limites rígidos de tamanho de arquivos (por exemplo, tetos arbitrários de 350 linhas com regras de ESLint). 

No entanto, a imposição de tetos ingênuos de linhas baseados em contagem cega de texto (`wc -l` ou regex) gera consequências deletérias no ciclo de vida de software:
1. **Fragmentação Artificial de Código:** Força a quebra não-natural de contratos, schemas de banco de dados, interfaces TypeScript, enums exaustivos ou definições de tipos compostos em dezenas de arquivos minúsculos, degradando a legibilidade e aumentando o consumo de tokens na inspeção de contexto.
2. **Falsos Positivos em Arquivos Declarativos:** Arquivos que contêm exclusivamente tipos, schemas Zod/Prisma/Drizzle ou interfaces de domínio possuem baixa ou nula complexidade ciclomática de execução, não justificando a penalização por tamanho.
3. **Falsos Negativos por Evasão:** Arquivos com lógica executável densa conseguem se disfarçar abaixo do limite de linhas através de minificação, supressão de quebras de linha ou compactação estética prejudicial.

---

## Decisão Arquitetural

1. **Rejeição de Tetos Arbitrários Imediatos:**
   - O CEH **rejeita** a imposição preventiva de tetos genéricos de tamanho de arquivo (ex.: 350 linhas) em sua suíte nuclear de auditoria (`diff-audit.sh`), por constituir overengineering não fundamentado em dor observada.
2. **Princípio de Isenção Sintática (AST-Based):**
   - Caso venha a existir demanda comprovada por governança de tamanho de módulos, a aferição **NUNCA** será realizada por contagem ingênua de linhas ou por heurísticas de extensão/nome de arquivo.
   - Qualquer verificação futura DEVE inspecionar a árvore sintática abstrata (AST) da linguagem:
     - Módulos contendo exclusivamente declarações de tipos, contratos, interfaces e schemas declarativos sem statements imperativos executáveis são **isentos por definição sintática**.
     - A introdução de uma única instrução com efeito colateral em runtime revoga a isenção do arquivo.
3. **Par de Provas Obrigatório:**
   - Nenhum gate dessa natureza poderá ser ativado sem um par determinístico de testes:
     - Fixture A: Arquivo puramente declarativo extenso (>350 linhas) aprovado com exit code 0.
     - Fixture B: O mesmo arquivo acrescido de 1 linha executável reprovado deterministicamente.

---

## Consequências e Benefícios

- **Preservação da Filosofia Ponytail (Anti-Overengineering):** Zero linhas de código inútil de linters foram adicionadas ao core do harness.
- **Proteção contra Regressões Futuras:** Garante que evoluções futuras do `diff-audit.sh` não quebrem arquivos de tipos ou schemas ricos do ecossistema moderno.
