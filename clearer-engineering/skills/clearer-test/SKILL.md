---
name: clearer-test
description: >-
  Deterministic test execution and verification with Ponytail Methodology. Enforces risk-driven
  prioritization, minimum sufficient verification layer, behavioral BDD contracts, strict mock
  boundaries, and audit-ready evidence reporting.
---

# CLEARER Deterministic Test Execution & Metodologia Ponytail

Esta skill guia o planejamento, escrita, execução e registro auditável de testes automatizados no projeto sob a **Metodologia Ponytail de Verificação Técnica**.

```text
--------------------------------------------------------------------------------
                    METODOLOGIA PONYTAIL DE VERIFICAÇÃO TÉCNICA
--------------------------------------------------------------------------------
Princípio Fundamental:
Inspecione antes de alterar. Teste pelo risco. Use a menor verificação suficiente.
Corrija somente o que estiver comprovadamente errado.

Fluxo:
Inspecionar → Priorizar → Verificar → Evidenciar → Corrigir → Revalidar
--------------------------------------------------------------------------------
```

> [!CRITICAL]
> **Proibição de Testes Fictícios & Test Bloat**:
> 1. A palavra "testado" só pode ser usada quando uma suíte real foi executada e teve sua saída registrada (`OBSERVED`).
> 2. É terminantemente proibido gerar testes inflados ou redundantes apenas para aumentar percentual sintético de cobertura (`coverage %`).
> 3. Todo teste deve justificar sua existência mitigando um risco técnico ou de negócio concreto.

---

## Seção 1: Inspecione Primeiro

Antes de propor testes, escrever asserts ou alterar código:
1. **Ambiente:** Identificar stack, versões, runtime de execução (`NATIVE_HOST` vs `SAIL`/`DOCKER`), banco de dados, containers e suíte de CI (`.github/workflows/`).
2. **Testes Existentes:** Inspecionar estrutura de pastas (`tests/Unit`, `tests/Feature`), factories, fixtures, traits e convenções já adotadas no projeto.
3. **Fluxos Críticos:** Mapear autenticação, autorização, escrita contábil/financeira, transações atômicas, filas assíncronas e contratos externos.
4. **Contratos:** Validar rotas, endpoints, schemas, migrations, eventos de domínio e regras de persistência.

*Regra de Ouro: Não crie o que já existe. Não altere o que ainda não foi plenamente compreendido.*

---

## Seção 2: Priorize pelo Risco

O esforço de teste deve se concentrar onde uma falha gera dano real e mensurável:

```text
CRÍTICO (Segurança, Financeiro, Integridade de Dados, Corrupção Silenciosa)
   ↓
ALTO (Fluxos Core de Negócio, Autenticação/Sessão, Sincronizações Mandatórias)
   ↓
MÉDIO (Regras de Apresentação, Filtros, Validações de Formulário, Formatações)
   ↓
BAIXO (Ajustes Cosméticos, Utilitários Puros, Textos de Interface)
```

*Cobertura percentual não é objetivo; mitigação de risco comprovada é.*

---

## Seção 3: Use a Menor Verificação Suficiente

Aplique a **Escada de Decisão Ponytail para Testes** (interrompa no primeiro degrau viável):

```text
1. Já existe teste ou evidência comprovada cobrindo a regra?
   ├── SIM → Reutilize e execute o teste existente.
   └── NÃO ↓
2. Teste Unitário puro (em memória, execução em milissegundos) resolve?
   ├── SIM → Escreva teste unitário focado. Proibido subir de camada.
   └── NÃO ↓
3. Teste de Integração / Feature (com banco/serviço local) resolve?
   ├── SIM → Escreva teste de integração sem abrir navegador.
   └── NÃO ↓
4. Teste E2E (Browser / Playwright / transação ponta a ponta) é indispensável?
   └── Somente para risco CRÍTICO que exija orquestração multi-sistema ou renderização complexa.
```

*Ordem preferencial física:* **Unitário → Integração → E2E**.

---

## Seção 4: Teste Comportamento Observável (BDD)

Proibido acoplar testes a detalhes internos de implementação ou métodos privados. Teste contratos e comportamento do domínio:

```text
DADO     → Estado inicial conhecido (fixtures, factories ou dados determinísticos)
QUANDO   → Uma ação ou transação ocorre (chamada de método, requisição, disparo de evento)
ENTÃO    → Um resultado observável é produzido (retorno, estado persistido, resposta HTTP, evento disparado)
```

---

## Seção 5: Regras Mínimas de Qualidade de Teste

- **Determinístico:** Mesma entrada gera rigorosamente o mesmo resultado. Zero *flaky tests*.
- **Isolado:** Uma falha aponta uma única causa raiz. Sem vazamento de estado entre testes.
- **Objetivo:** Uma propriedade ou comportamento por asserção principal.
- **Legível:** O nome do teste descreve a regra de negócio com precisão executiva.
- **Tríade de Casos para Regras Importantes:**
  `Caminho Feliz (Happy Path) + Falha Prevista (Unhappy Path) + Caso de Borda (Edge Case)`.

---

## Seção 6: Fidelidade e Fronteira Rígida de Mocks

- **Use a implementação real** sempre que ela fizer parte do componente ou domínio sob validação.
- **Mock SOMENTE em fronteiras externas reais**: Gateways de pagamento externos, APIs de terceiros (ClickUp, Stripe), relógio/tempo do sistema, disparo real de e-mails/SMS.
- **Proibição Inegociável:** NUNCA replicar lógica de negócio, regras relacionais ou transações de banco dentro de mocks. Se um mock precisa simular complexidade interna, o design ou a camada de teste está errada.

---

## Seção 7: Quando Encontrar uma Falha (Systematic Debugging)

Siga o ciclo determinístico:
```text
Reproduzir → Comprovar (Red) → Identificar Causa Raiz → Menor Patch Funcional → Teste de Regressão → Reexecutar (Green)
```
*O menor diff funcional vence.* Proibido refatorações oportunistas ao corrigir bugs.

---

## Seção 8: Definition of Done (Checklist Ponytail)

Checklist obrigatório antes de considerar qualquer verificação concluída:
- [ ] Comportamento esperado está claro e documentado;
- [ ] Risco foi identificado e classificado (`CRÍTICO`, `ALTO`, `MÉDIO`, `BAIXO`);
- [ ] Teste existente foi reutilizado sempre que possível;
- [ ] Menor camada adequada foi utilizada (Unitário > Integração > E2E);
- [ ] Execução é determinística com exit code registrado;
- [ ] Comando é reproduzível diretamente no terminal;
- [ ] Resultado possui evidência física (`OBSERVED`);
- [ ] Falha corrigida possui teste de regressão (Detector);
- [ ] Testes relacionados continuam passando (zero regressão);
- [ ] Nenhuma alteração fora do escopo foi introduzida.

---

## Seção 9: Contrato de Saída Obrigatório

Toda verificação de testes deve produzir o relatório no formato padronizado:

```text
STATUS:      PASS | FAIL | PARTIAL | NOT RUN | BLOCKED
ESCOPO:      <O que foi verificado e arquivos envolvidos>
EVIDÊNCIAS:
- Comando:   <comando exato executado>
- Exit Code: <0 para sucesso, diferente de 0 para falha>
- Duração:   <tempo total de execução / wall-clock time>
- Métricas:  <Testes: N | Passaram: N | Falharam: N | Ignorados: N>
PROBLEMAS:   <Somente falhas comprovadas, com stacktrace ou causa raiz, ou "Nenhum">
ALTERAÇÕES:  <O que foi alterado e por quê, ou "Nenhuma alteração">
PENDÊNCIAS:  <Somente o que não pôde ser comprovado fisicamente, ou "Nenhuma">

Semântica de Claims:
OBSERVED   → Comprovado diretamente por execução de comando ou código lido
DOCUMENTED → Definido formalmente por contrato ou especificação do projeto
INFERRED   → Conclusão lógica razoável amparada em evidência observada
UNKNOWN    → Ainda não demonstrado fisicamente
```
