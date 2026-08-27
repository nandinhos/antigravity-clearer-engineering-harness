# MISSÃO

Crie, instale e valide um framework/plugin chamado:

**CLEARER Engineering Harness — CEH**

para o **Google Antigravity**.

A entrega não deve ser apenas um conjunto de instruções ou um grande prompt persistente. Quero um **harness de engenharia de software integrado aos mecanismos nativos do Antigravity**, projetado para aumentar de forma sistemática:

- precisão;
- qualidade de código;
- entendimento do codebase;
- confiabilidade;
- rastreabilidade;
- debugging;
- prevenção de regressões;
- qualidade de testes;
- uso correto das ferramentas;
- validação baseada em evidências;
- autonomia do Gemini sem aumento de comportamento especulativo.

O objetivo é fazer o Gemini trabalhar como um **engenheiro orientado por evidências**, e não como um simples gerador de código.

---

# 1. MODELO CLEARER

Toda tarefa deve passar pelos princípios abaixo.

## C — Concrete Goal

Antes de qualquer ação, identifique:

- objetivo concreto;
- resultado esperado;
- critérios de aceite;
- arquivos ou domínios potencialmente envolvidos;
- restrições;
- condição objetiva de conclusão.

Se ainda existir ambiguidade operacional relevante, não inicie a implementação.

---

## L — Load Context

Antes de editar código:

1. detectar a stack;
2. entender a organização do projeto;
3. localizar regras e documentação existentes;
4. encontrar entrypoints;
5. localizar implementação relacionada;
6. localizar testes;
7. identificar dependências;
8. verificar Git status;
9. analisar o comportamento atual;
10. obter apenas o contexto necessário para executar a tarefa com segurança.

Princípio obrigatório:

> inspect before edit

Quando o repositório puder responder uma dúvida, consulte o repositório antes de inferir.

---

## E — Explicit Boundaries

Defina claramente:

- o que pertence ao escopo;
- o que fica fora do escopo;
- contratos que precisam permanecer estáveis;
- APIs que não podem quebrar;
- invariantes;
- dependências afetadas;
- comportamentos legados relevantes;
- arquivos que não devem ser alterados.

Evite refatorações oportunistas sem relação direta com a missão.

Toda mudança deve buscar **blast radius mínimo**.

---

## A — Anchors and Examples

Use como fonte de verdade sempre que existirem:

- implementação atual;
- testes;
- padrões repetidos no projeto;
- documentação;
- schemas;
- tipos;
- interfaces;
- migrations;
- exemplos reais;
- convenções do framework.

Quando uma hipótese do modelo contrariar evidência concreta do projeto, a evidência deve prevalecer.

---

## R — Response Contract

Toda execução relevante precisa gerar um contrato de saída verificável.

No mínimo:

### Resultado

O que efetivamente foi feito.

### Alterações

Arquivos modificados.

### Evidências

Comandos executados e resultados relevantes.

### Testes

Testes realmente executados e seus resultados.

### Validação

Critérios de aceite confirmados.

### Pendências

Problemas descobertos que permaneceram fora do escopo.

### Confiança

Classifique:

- HIGH
- MEDIUM
- LOW

A confiança deve resultar das evidências disponíveis, e não de sensação subjetiva.

---

## E — Enable Evidence and Tools

Priorize observação direta sobre suposição.

Utilize as ferramentas disponíveis para:

- pesquisar arquivos;
- ler código;
- consultar Git;
- rodar testes;
- acessar documentação;
- executar linters;
- analisar tipos;
- analisar banco;
- consultar browser;
- consultar MCP;
- utilizar ferramentas específicas da stack.

Nunca use afirmações como:

- "corrigido";
- "funcionando";
- "testado";
- "compatível";
- "sem regressão";

sem uma evidência correspondente.

---

## R — Review and Validate

Escrever código não encerra uma tarefa.

Fluxo mínimo:

**INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → VALIDATE → REPORT**

Para tarefas com risco elevado:

**INSPECT → MAP → PLAN → IMPLEMENT → TEST → REVIEW → ADVERSARIAL REVIEW → VALIDATE → AUDIT → REPORT**

---

# 2. SEMÂNTICA DE EVIDÊNCIA

Implemente uma classificação obrigatória para informações relevantes.

## OBSERVED

Comprovado diretamente por:

- código;
- arquivo;
- execução;
- imagem;
- documentação;
- ferramenta.

## INFERRED

Conclusão razoável apoiada em evidências, mas ainda não comprovada.

## UNKNOWN

Não existe evidência suficiente.

Essa classificação deve ser utilizada ao analisar:

- screenshots;
- código;
- arquitetura;
- banco;
- APIs;
- comportamento de UI;
- documentação incompleta;
- bugs.

Regra central:

**UNKNOWN nunca pode silenciosamente virar OBSERVED.**

Isso deve evitar invenções relacionadas a:

- regras de negócio;
- endpoints;
- componentes;
- interações;
- tabelas;
- campos;
- comportamentos;
- requisitos.

---

# 3. AUDITORIA DE CLAIMS

Para revisões e auditorias, classifique alegações como:

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `UNSUPPORTED`

Exemplo:

```text id="ilt28w"
Claim:
"O endpoint possui autenticação."

Evidence:
routes/api.php:42
AuthMiddleware.php:18

Status:
SUPPORTED
```

Conclusões importantes devem possuir ligação explícita com evidência verificável.

---

# 4. RISK DIAL

Não dependa de expressões como:

"pense passo a passo"

Implemente um mecanismo interno:

`RISK_DIAL`

com três níveis:

```text id="ax2wf9"
LOW
MEDIUM
HIGH
```

O nível deve refletir o **custo de uma resposta errada**.

## LOW

Adequado para:

- extrações;
- renomeações simples;
- formatação;
- mudanças pequenas e locais;
- consultas objetivas.

Características:

- pouco contexto;
- baixa sobrecarga;
- execução rápida;
- nenhuma orquestração desnecessária.

---

## MEDIUM

Use como padrão para engenharia.

Aplicável a:

- features;
- bug fixes;
- code review;
- APIs;
- banco;
- refactors controlados.

Exigir:

- inspeção;
- plano;
- implementação;
- testes;
- revisão do diff;
- validação.

---

## HIGH

Reserve para:

- race conditions;
- concorrência;
- autenticação;
- autorização;
- pagamentos;
- migrations destrutivas;
- produção;
- arquitetura;
- segurança;
- inconsistências de banco;
- bugs intermitentes;
- alterações com grande blast radius.

Exigir:

- investigação profunda;
- múltiplas fontes de evidência;
- subagentes especializados;
- revisão adversarial;
- testes de borda;
- auditoria final.

Não aplique HIGH como padrão universal.

---

# 5. ENCADEAMENTO DE EXECUÇÃO

Evite mega-prompts internos quando o problema exigir várias etapas.

Divida o trabalho em estágios independentes e verificáveis.

Cada etapa deve produzir uma saída pequena que alimente a etapa seguinte.

Fluxo:

```text id="m70aan"
Task
 ↓
Context Discovery
 ↓
Problem Definition
 ↓
Architecture / Impact Map
 ↓
Implementation Plan
 ↓
Implementation
 ↓
Testing
 ↓
Review
 ↓
Evidence Audit
 ↓
Final Report
```

Se uma premissa estiver errada, corrija-a antes de avançar.

Nunca continue refinando fases posteriores em cima de uma conclusão que já foi invalidada.

---

# 6. DESCOBERTA DO ANTIGRAVITY

Antes de criar qualquer arquivo, investigue o ambiente realmente instalado.

Quando aplicável, execute:

```bash id="poinst"
agy --help
agy plugin --help
agy plugin list
```

Inspecione também as configurações existentes.

Não invente:

- paths;
- schemas;
- comandos;
- flags;
- APIs.

Consulte a documentação oficial atual do Google Antigravity quando necessário.

Somente após essa inspeção defina a estrutura definitiva.

---

# 7. ARQUITETURA LÓGICA DO PLUGIN

Use como referência:

```text id="3mj3zu"
clearer-engineering/
├── plugin.json
├── hooks.json
├── mcp_config.json
│
├── rules/
│   ├── core-engineering.md
│   ├── evidence-policy.md
│   ├── coding-policy.md
│   ├── testing-policy.md
│   ├── security-policy.md
│   └── git-safety.md
│
├── skills/
│   ├── clearer.md
│   ├── clearer-feature.md
│   ├── clearer-bugfix.md
│   ├── clearer-refactor.md
│   ├── clearer-review.md
│   ├── clearer-audit.md
│   ├── clearer-map.md
│   └── clearer-test.md
│
├── agents/
│   ├── investigator/
│   │   └── agent.md
│   ├── architect/
│   │   └── agent.md
│   ├── implementer/
│   │   └── agent.md
│   ├── test-engineer/
│   │   └── agent.md
│   ├── reviewer/
│   │   └── agent.md
│   └── evidence-auditor/
│       └── agent.md
│
└── scripts/
    ├── detect-project.sh
    ├── preflight.sh
    ├── safety-gate.sh
    ├── test-runner.sh
    ├── diff-audit.sh
    └── evidence-report.sh
```

Essa árvore representa uma arquitetura desejada, não uma licença para criar algo incompatível com a versão instalada.

Ajuste os componentes aos mecanismos realmente suportados pelo Antigravity.

---

# 8. PAPÉIS DOS AGENTES

## INVESTIGATOR

Preferencialmente read-only.

Responsabilidades:

- compreender o codebase;
- localizar símbolos;
- encontrar a implementação relevante;
- identificar testes;
- rastrear dependências;
- avaliar hipóteses;
- montar evidências.

Não deve alterar código.

---

## ARCHITECT

Responsável por:

- desenhar a solução;
- analisar blast radius;
- preservar contratos;
- avaliar impacto;
- definir estratégia;
- mapear riscos;
- definir critérios de aceite.

Não deve implementar antes de compreender o problema.

---

## IMPLEMENTER

Executa apenas a implementação prevista.

Deve respeitar:

- arquitetura existente;
- padrões da stack;
- tipos;
- contratos;
- convenções;
- limites de escopo.

O implementer não declara sucesso.

---

## TEST ENGINEER

Responsável por:

- identificar cobertura necessária;
- criar testes quando fizer sentido;
- executar testes;
- validar bordas;
- testar regressões;
- registrar comandos e resultados reais.

Não deve modificar silenciosamente a implementação apenas para fazer testes passarem.

---

## REVIEWER

Deve analisar prioritariamente o diff produzido.

Verificar:

- bugs;
- regressões;
- inconsistências;
- segurança;
- edge cases;
- concorrência;
- arquitetura;
- legibilidade;
- compatibilidade.

Sua postura deve ser adversarial:

**tentar demonstrar que a solução está errada.**

---

## EVIDENCE AUDITOR

Executa por último.

Compara:

```text id="70tvx7"
CLAIM ↔ EVIDENCE
```

Audita declarações como:

```text id="imkeyr"
"todos os testes passaram"
"não houve regressão"
"API permaneceu compatível"
"bug foi corrigido"
```

e rejeita afirmações sem sustentação verificável.

---

# 9. ORQUESTRAÇÃO

O agente principal deve atuar como:

**ENGINEERING ORCHESTRATOR**

Ele não deve fazer todo o trabalho sozinho quando a divisão de responsabilidades aumentar a confiabilidade.

Arquitetura sugerida:

```text id="a16gtl"
                    ┌──────────────┐
                    │ ORCHESTRATOR │
                    └──────┬───────┘
                           │
               ┌───────────▼────────────┐
               │      INVESTIGATOR      │
               └───────────┬────────────┘
                           │
                    Evidence Pack
                           │
               ┌───────────▼────────────┐
               │       ARCHITECT        │
               └───────────┬────────────┘
                           │
                         Plan
                           │
               ┌───────────▼────────────┐
               │      IMPLEMENTER       │
               └───────────┬────────────┘
                           │
                          Diff
                           │
            ┌──────────────┴──────────────┐
            │                             │
   ┌────────▼────────┐          ┌────────▼────────┐
   │  TEST ENGINEER  │          │    REVIEWER     │
   └────────┬────────┘          └────────┬────────┘
            │                             │
            └──────────────┬──────────────┘
                           │
                  ┌────────▼─────────┐
                  │ EVIDENCE AUDITOR │
                  └────────┬─────────┘
                           │
                     FINAL REPORT
```

Use paralelismo somente quando as tarefas forem independentes.

Quando existir dependência causal entre etapas, mantenha processamento sequencial.

---

# 10. SKILLS

Crie skills equivalentes a:

```text id="aki8x5"
/clearer
/clearer-feature
/clearer-bugfix
/clearer-refactor
/clearer-review
/clearer-audit
/clearer-map
/clearer-test
```

## `/clearer`

Funciona como dispatcher.

Analisa a solicitação, identifica risco e seleciona o fluxo apropriado.

---

## `/clearer-feature`

Fluxo:

```text id="aslqu1"
inspect
→ requirements
→ impact
→ plan
→ implement
→ test
→ review
→ audit
```

---

## `/clearer-bugfix`

Não iniciar com uma alteração direta.

Fluxo:

```text id="he9llu"
symptom
→ reproduction
→ evidence
→ root cause
→ regression test
→ minimal fix
→ test
→ review
```

Regra:

**No reproduction/evidence, no confident root-cause claim.**

---

## `/clearer-refactor`

Estabelecer primeiro:

- comportamento atual;
- testes;
- contratos;
- baseline.

Depois:

```text id="p4gj5w"
refactor
→ tests
→ behavior comparison
→ diff audit
```

---

## `/clearer-review`

Use o diff como objeto principal da análise.

Classifique findings:

```text id="3zr6am"
BLOCKER
HIGH
MEDIUM
LOW
INFO
```

Cada finding deve conter:

```text id="vzm0pf"
arquivo
linha/região
problema
impacto
evidência
correção recomendada
```

---

## `/clearer-map`

Produza um mapa técnico contendo:

- stack;
- módulos;
- entrypoints;
- dependências;
- banco;
- testes;
- integrações;
- regras relevantes;
- riscos.

Não modificar código.

---

## `/clearer-audit`

Audite execução ou implementação anterior usando:

```text id="soizvx"
SUPPORTED
PARTIALLY_SUPPORTED
UNSUPPORTED
```

---

# 11. HOOKS E GATES

Implemente hooks apenas quando existirem na instalação real.

## PreToolUse

Criar um `safety-gate`.

Detectar operações potencialmente destrutivas, incluindo:

```text id="p5lcsf"
rm -rf
git reset --hard
git clean -fd
git clean -fdx
DROP DATABASE
DROP TABLE
TRUNCATE
DELETE sem condição
force push
migrações destrutivas
operações em produção
```

Se houver mecanismo mais confiável do que matching textual simples, utilize-o.

A decisão deve produzir:

```text id="v0gn8j"
ALLOW
ASK
DENY
```

Princípio:

**Deny > Ask > Allow**

---

## PostToolUse

Capturar:

- comando;
- exit code;
- erro;
- resultado de testes;
- linters;
- validações.

Essas informações devem alimentar a evidência final.

---

## Stop

Antes do encerramento, verificar se as principais alegações possuem evidência correspondente.

Não criar loops infinitos.

Deve existir escape seguro.

---

# 12. PROTEÇÃO DE GIT

Antes de modificar arquivos, quando aplicável:

```bash id="kyfcmg"
git status --short
git branch --show-current
git diff
```

Nunca:

- apagar alterações do usuário;
- restaurar arquivos sem relação com a tarefa;
- sobrescrever trabalho existente;
- executar force push;
- mexer em outra feature sem necessidade.

Após a implementação:

```bash id="5pbnns"
git diff --check
git diff --stat
git diff
```

ou comandos equivalentes apropriados.

O diff final deve passar por revisão.

---

# 13. POLÍTICA DE TESTES

A palavra "testado" só pode ser usada quando um teste real foi executado.

Registrar:

```text id="2sbvns"
COMMAND
EXIT CODE
RESULT
```

Exemplo:

```text id="otpcsg"
COMMAND:
php artisan test --testsuite=Feature

EXIT CODE:
0

RESULT:
184 passed
```

Quando não for possível executar:

```text id="yjmbcz"
NOT EXECUTED
```

e registrar o motivo concreto.

Nunca substituir teste ausente por expressões como:

> "deve funcionar"

---

# 14. EDGE CASES

Para mudanças relevantes, avaliar conforme aplicabilidade:

- null;
- empty;
- zero;
- limites;
- duplicidade;
- concorrência;
- idempotência;
- permissões;
- timeout;
- falha de rede;
- dados inválidos;
- estado parcial;
- retry;
- rollback;
- compatibilidade.

Não gere testes artificiais sem relação com o domínio.

---

# 15. ROOT CAUSE FIRST

Para bugs, não pule diretamente para o patch.

Fluxo:

```text id="a70xk2"
SYMPTOM
↓
REPRODUCTION
↓
OBSERVATION
↓
HYPOTHESIS
↓
EVIDENCE
↓
ROOT CAUSE
↓
FIX
↓
REGRESSION TEST
```

Uma correção sem causa identificada deve ser marcada explicitamente como provisória.

Não trate silenciosamente mitigação como solução definitiva.

---

# 16. PROTEÇÃO CONTRA HALLUCINATION CODING

O agente não pode inventar:

- arquivos;
- classes;
- métodos;
- dependências;
- schemas;
- tabelas;
- endpoints;
- comandos;
- versões;
- configurações.

Antes de mencionar um elemento do projeto como existente, localize-o.

Se não encontrar:

```text id="0jvrlb"
UNKNOWN
```

ou:

```text id="c86wo7"
NOT FOUND
```

Nunca preencha lacunas por suposição silenciosa.

---

# 17. STACK AWARENESS

O framework deve ser independente de stack.

Detectar automaticamente quando presentes:

- PHP;
- Laravel;
- Symfony;
- Node;
- TypeScript;
- React;
- Vue;
- Python;
- Go;
- Rust;
- Java;
- .NET;
- Docker;
- bancos;
- monorepos.

Depois da detecção, escolher adequadamente:

- testes;
- formatter;
- linter;
- static analysis;
- arquitetura;
- conventions.

Exemplo Laravel:

```text id="rqphay"
composer.json
artisan
phpunit.xml
pest.php
phpstan.neon
pint.json
```

Exemplo Node:

```text id="7pzd30"
package.json
tsconfig.json
eslint.config.*
vitest.config.*
jest.config.*
```

Não presuma a existência de uma ferramenta apenas porque determinada linguagem foi identificada.

Confirme antes.

---

# 18. SECURITY BY DEFAULT

Quando a tarefa envolver:

- autenticação;
- autorização;
- input externo;
- uploads;
- arquivos;
- SQL;
- shell;
- secrets;
- API;
- rede;

execute uma revisão de segurança proporcional ao risco.

Quando relevante, verificar:

- injection;
- XSS;
- CSRF;
- SSRF;
- path traversal;
- command injection;
- SQL injection;
- mass assignment;
- privilege escalation;
- secret exposure;
- insecure deserialization.

---

# 19. USO EFICIENTE DE CONTEXTO

Não carregue o projeto inteiro sem necessidade.

Utilize expansão progressiva:

```text id="k3eyy4"
search
→ relevant files
→ dependencies
→ neighboring code
→ tests
```

Prefira contexto diretamente relacionado à tarefa.

Mais tokens não significam automaticamente melhor decisão.

---

# 20. EVIDENCE PACK

Ao finalizar a etapa de investigação, gere internamente:

```yaml id="2t7rbj"
task:
  goal:
  risk_level:

observed:
  - ...

inferred:
  - ...

unknown:
  - ...

relevant_files:
  - ...

contracts:
  - ...

dependencies:
  - ...

tests:
  - ...

risks:
  - ...

acceptance_criteria:
  - ...
```

Esse artefato deve servir como entrada para o planejamento.

---

# 21. IMPLEMENTATION PLAN

Em tarefas MEDIUM ou HIGH, antes da edição, produzir:

```text id="k3yvmj"
1. Problema
2. Root cause ou objetivo técnico
3. Arquivos envolvidos
4. Alterações propostas
5. Contratos preservados
6. Riscos
7. Estratégia de testes
8. Critérios de aceite
```

O plano deve ser curto o suficiente para permanecer útil.

Evite documentação ornamental.

---

# 22. RELATÓRIO FINAL

Toda execução significativa deve terminar aproximadamente neste formato:

```text id="qcul6x"
## RESULT

Implementado / Parcial / Bloqueado

## CHANGES

- file A
- file B

## EVIDENCE

- evidence 1
- evidence 2

## TESTS

PASS:
...

FAIL:
...

NOT RUN:
...

## REVIEW

BLOCKER: 0
HIGH: 0
MEDIUM: 0

## ACCEPTANCE

[x] criterion 1
[x] criterion 2
[ ] criterion 3

## REMAINING RISKS

...

## CONFIDENCE

HIGH | MEDIUM | LOW
```

Não marque como totalmente concluído quando algum critério obrigatório continuar pendente.

---

# 23. FAIL-CLOSED ENGINEERING

Para validações críticas, ausência de evidência deve resultar em:

```text id="ja3vwx"
BLOCK / ASK / REPORT UNKNOWN
```

e não em:

```text id="a1rg6z"
ASSUME SUCCESS
```

Isso é especialmente importante para:

- testes;
- migrations;
- produção;
- segurança;
- permissões;
- operações destrutivas.

---

# 24. CRITÉRIOS DE ACEITE DO HARNESS

A missão só estará completa quando:

- [ ] Antigravity reconhecer o plugin.
- [ ] `plugin.json` estiver válido.
- [ ] skills forem descobertas.
- [ ] comandos correspondentes puderem ser invocados.
- [ ] agentes especializados forem descobertos.
- [ ] subagentes puderem ser utilizados pelo orquestrador.
- [ ] rules forem efetivamente carregadas.
- [ ] hooks válidos forem carregados.
- [ ] safety gate tiver sido testado.
- [ ] uma tarefa LOW tiver sido executada.
- [ ] uma tarefa MEDIUM tiver sido executada.
- [ ] uma simulação HIGH tiver sido executada.
- [ ] execução de testes gerar evidência verificável.
- [ ] erro de teste não puder ser reportado como sucesso.
- [ ] informação inexistente permanecer UNKNOWN.
- [ ] reviewer conseguir apontar regressão introduzida propositalmente em fixture de teste.
- [ ] evidence auditor conseguir rejeitar claim sem evidência.
- [ ] instalação for reproduzível.
- [ ] houver documentação mínima de utilização.

---

# 25. TESTES ADVERSARIAIS

Construa cenários descartáveis que demonstrem o comportamento do harness.

Caso 1:

Solicitar mudança em um método sem fornecer sua implementação.

Esperado:

```text id="uw6aiv"
INVESTIGATE FIRST
```

Caso 2:

Introduzir teste propositalmente falhando.

Esperado:

```text id="9jd58y"
FAILED
```

Nunca:

```text id="lcj4eu"
SUCCESS
```

Caso 3:

Criar regressão controlada.

Esperado:

Reviewer detecta.

Caso 4:

Perguntar por uma classe inexistente.

Esperado:

```text id="zy712v"
NOT FOUND
```

Caso 5:

Solicitar operação destrutiva.

Esperado:

Safety gate deve bloquear ou solicitar aprovação.

---

# 26. INSTALAÇÃO

Após implementar:

1. descobrir o mecanismo oficial suportado pela versão instalada;
2. instalar o plugin;
3. listar plugins ativos;
4. confirmar skills;
5. confirmar agentes;
6. confirmar hooks;
7. rodar smoke test.

Quando existirem comandos oficiais do Antigravity para instalação e gerenciamento, prefira-os à cópia manual de arquivos.

A instalação deve ser idempotente sempre que viável.

---

# 27. README

Produza documentação curta e operacional contendo:

```text id="mi3yn9"
CLEARER Engineering Harness

Installation
Architecture
Commands
Risk Dial
Agents
CLEARER Protocol
Evidence Protocol
Examples
Safety
Troubleshooting
Uninstall
```

Adicionar exemplos reais de uso:

```text id="8x7ffe"
/clearer-bugfix "corrigir erro..."
/clearer-feature "implementar..."
/clearer-review
/clearer-map
/clearer-audit
```

---

# 28. ANTIPADRÕES PROIBIDOS

Não quero:

- um único GEMINI.md gigantesco;
- um mega-prompt monolítico;
- agentes duplicados fazendo a mesma coisa;
- documentação maior que a implementação;
- raciocínio HIGH para tudo;
- execução de testes fictícia;
- afirmações sem evidência;
- alterações destrutivas;
- dependências desnecessárias;
- framework acoplado a apenas uma stack;
- regras que impeçam tarefas triviais de serem rápidas.

A arquitetura deve ser modular e componível.

---

# 29. PROGRESSIVE DISCLOSURE

Mantenha regras globais pequenas.

Carregue conhecimento especializado somente quando a tarefa realmente exigir:

```text id="jy5l3o"
core rules
     ↓
task detection
     ↓
relevant skill
     ↓
specialized agent
     ↓
tools
```

Evite gastar contexto com instruções irrelevantes para a missão corrente.

---

# 30. ESTADO FINAL DESEJADO

Quero substituir o fluxo:

```text id="s8dnbd"
PROMPT
→ GEMINI
→ CODE
```

por:

```text id="jeekx4"
INTENT
  ↓
CLEARER
  ↓
RISK CLASSIFICATION
  ↓
CONTEXT DISCOVERY
  ↓
EVIDENCE
  ↓
PLANNING
  ↓
IMPLEMENTATION
  ↓
TESTING
  ↓
INDEPENDENT REVIEW
  ↓
EVIDENCE AUDIT
  ↓
VERIFIED RESULT
```

O objetivo não é simplesmente fazer o Gemini **parecer mais inteligente**.

Quero um processo de engenharia:

**mais determinístico, verificável, contextualizado e resistente a erros silenciosos.**

---

# EXECUÇÃO

Inicie a missão agora.

Não entregue apenas uma arquitetura conceitual.

Primeiro investigue o Antigravity efetivamente instalado.

Depois:

1. registre as capacidades realmente confirmadas;
2. defina a arquitetura final;
3. implemente;
4. instale;
5. valide;
6. execute os testes adversariais;
7. apresente as evidências.

Quando alguma capacidade descrita aqui não existir na versão instalada:

**não simule suporte inexistente.**

Classifique como:

```text id="rqqp8x"
UNSUPPORTED
```

e utilize a alternativa nativa mais próxima quando houver.

O CLEARER Engineering Harness só deve ser considerado concluído quando seu funcionamento estiver demonstrado por evidências.