# Guia de Subagentes Especializados do CEH

O *CLEARER Engineering Harness* divide as responsabilidades críticas de engenharia entre 6 subagentes especializados, evitando que um único modelo atue concomitantemente como planejador, desenvolvedor, testador e auditor.

---

## 1. `ceh-investigator` (Context Investigator)

- **Modo de Operação**: Estritamente Read-Only.
- **Responsabilidade**: Explorar o código-fonte, localizar rotas, controllers, models, schemas e testes sem editar nada.
- **Entrada**: Objetivo concreto da tarefa.
- **Saída**: **Evidence Pack** (YAML com categorização `OBSERVED`, `INFERRED`, `UNKNOWN`, arquivos relevantes e riscos).
- **Proibições**: Nunca cria ou edita arquivos. Nunca inventa símbolos que não foram encontrados.

---

## 2. `ceh-architect` (Solution Architect)

- **Modo de Operação**: Planejamento e Design de Software.
- **Responsabilidade**: Analisar o Evidence Pack, delimitar o blast radius, mapear contratos invariantes e desenhar a estratégia técnica.
- **Entrada**: Evidence Pack do Investigator.
- **Saída**: **Implementation Plan** (Objetivo, arquivos, alterações cirúrgicas, contratos e estratégia de testes).
- **Proibições**: Não escreve o código final de produção. Foca estritamente no plano executável.

---

## 3. `ceh-implementer` (Precision Implementer)

- **Modo de Operação**: Escrita e Edição Cirúrgica.
- **Responsabilidade**: Implementar as alterações especificadas no Implementation Plan respeitando o estilo e padrões existentes.
- **Entrada**: Implementation Plan do Architect.
- **Saída**: Modificações nos arquivos e resumo das alterações.
- **Proibições**: Não faz refatorações fora do escopo. Não declara a tarefa como concluída (o sucesso depende de testes e review independentes).

---

## 4. `ceh-test-engineer` (Test Engineer)

- **Modo de Operação**: Verificação Automatizada e Qualidade.
- **Responsabilidade**: Escrever testes de regressão (Red/Green), executar as suítes de testes e capturar saídas brutas.
- **Entrada**: Código modificado e estratégia de testes.
- **Saída**: Registro determinístico de testes (COMMAND, EXIT CODE, contagem de testes PASS / FAIL / NOT RUN).
- **Proibições**: Nunca mascara testes com falha como sucesso (*fake pass*).

---

## 5. `ceh-reviewer` (Adversarial Diff Reviewer)

- **Modo de Operação**: Auditoria Crítica de Diff.
- **Responsabilidade**: Analisar o Git diff com postura declaradamente adversarial para encontrar falhas antes que cheguem à produção.
- **Entrada**: `git diff` e saída do `scripts/diff-audit.sh`.
- **Saída**: Lista de Findings classificados por severidade:
  - `BLOCKER`: Quebra crítica, crash, falha grave de segurança.
  - `HIGH`: Regressão funcional, quebra de contrato de API.
  - `MEDIUM`: Falta de tratamento de edge cases (null, timeouts).
  - `LOW`: Melhoria pontual de legibilidade.
  - `INFO`: Nota informativa.
- **Proibições**: Não autoriza tarefas com achados BLOCKER ou HIGH pendentes.

---

## 6. `ceh-evidence-auditor` (Final Evidence Auditor)

- **Modo de Operação**: Tribunal de Evidências.
- **Responsabilidade**: Confrontar cada claim feito durante a entrega contra as evidências reais registradas.
- **Entrada**: Relatórios de teste, achados do reviewer e diffs.
- **Saída**: Veredito final (`APPROVED`, `NEEDS_EVIDENCE`, `REJECTED`) e Response Contract completo.
- **Proibições**: Nunca aceita afirmações não suportadas por logs reais.
