---
name: clearer-bugfix
description: >-
  Systematic Debugging v2.0 com 5 gates bloqueantes (RFC 2119), Matriz de Hipóteses falsificáveis,
  isolamento determinístico (Red -> Minimal Patch -> Green), Prevenção em 3 Níveis e integração nativa
  com learned-lesson para retenção permanente de conhecimento.
version: 2.0.0
---

# CLEARER Systematic Debugging Engine v2.0
### Workflow Determinístico de Depuração em 5 Gates Bloqueantes

Esta skill estabelece o processo científico e determinístico para encontrar e corrigir a causa raiz de qualquer falha sem palpites ou refatorações oportunistas. Nenhum gate avança sem comprovação empírica por artefato.

> [!CRITICAL]
> **Princípio Fundamental (RFC 2119):**
> Nunca chute a causa. Prove com artefato.
> Linguagem normativa: DEVE, NÃO DEVE, BLOQUEADO SE.
> Sem teste vermelho prévio e sem evidência observada = SEM AVANÇO.

---

## 🧭 Visão Geral dos 5 Gates Bloqueantes

```text
GATE 0: TRIAGE ──────► GATE 1: REPRODUCE (Red) ──► GATE 2: ISOLATE (Hipóteses)
      │                       │                             │
      ▼                       ▼                             ▼
[P0-P3 & SLA]          [Teste que FALHA]             [Arquivo:Linha Provado]
                              │                             │
                              ▼                             ▼
                    GATE 3: ROOT CAUSE ──────────► GATE 4: FIX & HARDEN (Green)
                              │                             │
                              ▼                             ▼
                     [5 Porques / 7 Tipos]        [Fix Mínimo + 3 Detectores]
                                                            │
                                                            ▼
                                                [Saída: Debug Report + learned-lesson]
```

| Gate | Nome | Output Obrigatório (em memória) | Gate Bloqueante |
|---|---|---|---|
| **0** | **TRIAGE** | Classificação P0-P3, owner, SLA, ambiente (`DEV`/`HOMOLOGACAO`/`PRODUCAO`), branch/commit. | **BLOQUEADO SE**: sem severidade ou sem ambiente identificado. |
| **1** | **REPRODUCE** | Passos mínimos (3-5), teste automatizado que **FALHA AGORA** (Red), log de stack trace capturado. | **BLOQUEADO SE**: "funciona na minha máquina" ou teste de repro não executado. |
| **2** | **ISOLATE** | **Matriz de Hipóteses Falsificáveis** (mínimo 2), toolbox de isolamento (Graphify AST, logs, bisect), `arquivo:linha` exato. | **BLOQUEADO SE**: sem matriz, com apenas 1 hipótese ou sem `arquivo:linha` demonstrado. |
| **3** | **ROOT CAUSE** | Classificação em 1 dos 7 tipos, cadeia causal completa e **5 Porques** + Ishikawa. | **BLOQUEADO SE**: descreve sintoma como causa ("validação falha" não é causa raiz). |
| **4** | **FIX & HARDEN** | Fix mínimo (sem refatoração junta), teste que falhava agora passa (**Green**), suite sem regressão e **Prevenção em 3 Níveis**. | **BLOQUEADO SE**: teste ainda falha, suite com regressão ou sem detector automatizado. |

---

## Gate 0 — TRIAGE

**Objetivo:** Priorizar, definir impacto e identificar o ambiente antes de investigar.

**DEVE responder em texto:**
```markdown
**Triage:** P0|P1|P2|P3 — [uma linha clara de impacto]
**Ambiente:** DEV | HOMOLOGACAO | PRODUCAO (Evidência: branch/commit/.env)
**Owner / Papel:** [desenvolvedor ou agente responsável]
**SLA / Timebox:** [P0: 2h | P1: 4h | P2: 1 dia | P3: backlog]
**Rota / Módulo / Tabela Afetada:** [ex: /api/v1/checkout, OrdersTable]
```

**Classificação de Severidade:**
- **P0**: Sistema fora do ar, perda de dados ou transações financeiras incorretas em produção.
- **P1**: Funcionalidade crítica quebrada sem workaround disponível.
- **P2**: Bug com workaround viável ou escopo restrito.
- **P3**: Inconsistência cosmética, ruído de log ou débito técnico.

> ⛔ **BLOQUEADO SE:** Severidade, ambiente ou escopo não informados. NÃO inicie o Gate 1 sem Triage.

---

## Gate 1 — REPRODUCE

**Objetivo:** Tornar o bug determinístico, isolado e comprovado por código.

**DEVE:**
1. Documentar passos mínimos numerados (3 a 5 passos) isolando cache, estado sujo ou dados legados.
2. Capturar a evidência completa: stack trace, mensagem de erro ou log de falha.
3. Criar e executar um **teste de regressão que FALHA AGORA** comprovando o bug:
   ```php
   // Exemplo PHP/Pest
   it('deve processar o pagamento com idempotência — repro #bug-12', function () {
       // Arrange (dados que disparam o bug)
       // Act (execução da unidade suspeita)
       // Assert (falha hoje, passará no Gate 4)
   });
   ```
4. Classificar a reprodutibilidade:
   - `determinístico`: falha em 100% das execuções (teste unitário/integração é mandatório).
   - `flaky`: falha intermitente (DEVE registrar seed, taxa N/M e executar com `--repeat`).
   - `env-only`: depende de ambiente (DEVE registrar diff de env, variáveis ou versão de dependência).

> ⛔ **BLOQUEADO SE:** Alegação de "não consegui reproduzir" sem dump comparativo de ambiente, ou teste de reprodução não executado.

---

## Gate 2 — ISOLATE

**Objetivo:** Provar ONDE a falha nasce no código, não onde o sintoma explode.

**DEVE preencher obrigatoriamente a Matriz de Hipóteses Falsificáveis (mínimo 2 hipóteses):**

| # | Hipótese Concorrente | Teste de Falsificação | Resultado | Evidência Observada (`OBSERVED`) |
|---|---|---|---|---|
| **H1** | [ex: DTO chega nulo no Service] | [ex: dump/log na entrada do método] | **REFUTADA** | DTO possui payload íntegro no controller |
| **H2** | [ex: Query do Eloquent omite tenant_id] | [ex: inspecionar SQL gerado via query log] | **CONFIRMADA** | SQL gerado: `WHERE status = 1` sem tenant |

**Toolbox de Isolamento (Use a técnica que PROVA):**
- **Graphify AST First**: Consulte `graphify query/path/explain` para mapear referências e chamadas antes de abrir arquivos.
- **Bisseção Git**: `git bisect` para localizar o commit exato que introduziu a regressão.
- **Logging Cirúrgico**: Inspecione entrada e saída da unidade suspeita.
- **Diferencial**: Compare a execução de um caso de teste que passa com o que falha.

**Perguntas Obrigatórias a Responder:**
- `Arquivo:Linha` exato: `app/Services/PaymentService.php:84`
- Variável / Estado incorreto: `tenant_id = null`, esperado inteiro positivo.
- Suposição refutada: o gateway respondeu 200, a falha ocorreu na persistência local.

> ⛔ **BLOQUEADO SE:** Sem Matriz de Hipóteses, com apenas 1 hipótese levantada, ou sem `arquivo:linha` demonstrado com evidência.

---

## Gate 3 — ROOT CAUSE

**Objetivo:** Compreender o MECANISMO do problema, diferenciando causa raiz de sintoma superficial.

**DEVE:**
1. Classificar o tipo em exatamente 1 dos 7 tipos canônicos:
   - `logic`: Erro algorítmico, condicional invertida, off-by-one.
   - `data`: Estado inconsistente no banco, schema desatualizado, dados nulos inesperados.
   - `concurrency`: Race condition, deadlock, falta de lock pessimista/otimista.
   - `config`: Variável de ambiente ausente, flag invertida, porta incorreta.
   - `dependency`: Breaking change em pacote upstream, versão incompatível.
   - `env`: Diferença entre SO, extensão PHP/Node ausente, permissão de disco.
   - `integration`: Timeout de API externa, webhook não tratado, contrato quebrado.

2. Aplicar a técnica dos **5 Porques**:
   - *Sintoma:* Pedido marcado como duplicado indevidamente.
   - *Por que?* O hash de idempotência colidiu.
   - *Por que?* O timestamp foi truncado em segundos em vez de milissegundos.
   - *Por que?* O helper `now()->format('YmdHi')` omitiu segundos e microssegundos.
   - *Por que?* Snippet de código copiado de legado sem tipagem estrita.
   - **Causa Raiz Real:** Função geradora de chave de idempotência com entropia temporal insuficiente.

3. Documentar a cadeia causal completa:
   `Request -> Controller:32 -> HashHelper:15 (entropia insuficiente) -> DB Unique Index -> Exception`.

> ⛔ **BLOQUEADO SE:** Descrever o sintoma como causa ("a causa foi uma SQLSTATE[23000]" é sintoma; a causa é o valor duplicado gerado).

---

## Gate 4 — FIX & HARDEN

**Objetivo:** Aplicar a correção com o menor diff possível, validar que o teste passa e criar imunidade definitiva contra recorrência.

**DEVE seguir rigorosamente esta ordem:**
1. **Confirmar teste ainda falha**: Reexecutar o teste do Gate 1 e registrar o log de falha (**Red**).
2. **Implementar o fix cirúrgico**: Aplicar o menor diff funcional possível na causa raiz identificada.
   - ⚠️ **PROIBIDO REFATORAR NO MESMO DIFF**: Não renomeie variáveis fora de escopo, não mexa em estilos ou arquivos vizinhos.
3. **Confirmar que o teste agora passa**: Executar o teste de reprodução e comprovar o sucesso (**Green**).
4. **Executar a suíte de testes completa**:
   ```bash
   bash scripts/test-runner.sh
   ```
   - O runner utilizará o **RTK** automaticamente para validar zero regressões sem poluir o terminal.
5. **Declarar Blast Radius & Rollback**:
   - Arquivos alterados: `[app/Helpers/Idempotency.php]`
   - Tabelas / Rotas impactadas: `[orders, POST /api/v1/orders]`
   - Comando de rollback imediato: `git revert <hash>` ou desativação de flag.
6. **Implementar Prevenção em 3 Níveis (Pelo menos o Detector é OBRIGATÓRIO):**
   - 🛡️ **Nível 1 — Detector (Mandatório):** Teste unitário/feature automatizado que quebrará caso o bug retorne.
   - 🚧 **Nível 2 — Barreira:** Tipagem estrita, constraint no banco (`UNIQUE`), validação de FormRequest ou regra de lint.
   - 📖 **Nível 3 — Runbook:** Documentação para suporte/operação em casos de incidentes P0/P1.

> ⛔ **BLOQUEADO SE:** O teste de reprodução não passar, houver regressão na suíte geral, ou se o patch não incluir um Detector automatizado.

---

## Saída Final: Debug Report & Ingestão de Memória Técnica

Ao concluir o Gate 4, emita o relatório padronizado em memória:

```markdown
# 🔬 Debug Report — <slug-do-bug> — <YYYY-MM-DD>

**Triage:** P<0-3> | **Tipo:** logic|data|concurrency|config|dependency|env|integration | **Arquivo:** `path:linha`
**Ambiente:** DEV | HOMOLOGACAO | PRODUCAO | **Commit:** <hash>

## 1. Sintoma
[Descrição objetiva do comportamento observado vs esperado]

## 2. Reprodução (Gate 1)
- Passos: 1. ... 2. ... 3. ...
- Classificação: determinístico | flaky | env-only
- Teste de Repro: `tests/Feature/IdempotencyTest.php` (FALHOU inicialmente com log comprovado)

## 3. Isolamento (Gate 2)
- Matriz de Hipóteses:
  - H1 [descrição]: REFUTADA (evidência)
  - H2 [descrição]: CONFIRMADA (evidência)
- Local isolado: `app/Helpers/Idempotency.php:18` (estado incorreto demonstrado)

## 4. Causa Raiz (Gate 3)
- Tipo: [1 dos 7 tipos canônicos]
- 5 Porques: [Resumo da cadeia causal]
- Fator Contribuinte: [falta de teste de borda, ausência de constraint, etc.]

## 5. Correção Cirúrgica (Gate 4)
- Diff essencial: [resumo do menor diff funcional aplicado]
- Blast Radius: [arquivos, rotas e tabelas]
- Rollback: `git revert <hash>`

## 6. Verificação e Evidências
- Teste de Repro: PASSOU ✓
- Suíte Geral: PASSOU (0 regressões) ✓
- Auditoria de Diff: `bash scripts/diff-audit.sh` (100% limpo) ✓

## 7. Prevenção em 3 Níveis
- [x] Detector: Teste automatizado `IdempotencyTest::it_prevents_duplicate_orders`
- [ ] Barreira: Constraint de banco adicionada / Rule de validação
- [ ] Runbook: [link ou nota operacional]

---
> 🧠 **Deseja salvar esta lição como memória permanente do projeto?**
> Responda `sim` para que a skill nativa `learned-lesson` registre o aprendizado no padrão canônico (dev-memory MCP ou `.dev-memory/learned-lessons.jsonl`), prevenindo que qualquer agente volte a cometer este erro.
```

Se o desenvolvedor responder `sim`, o agente ativa a skill nativa **[`learned-lesson`](file:///home/nandodev/projects/clearer-engineering-harness/clearer-engineering/skills/learned-lesson/SKILL.md)** para registrar o aprendizado com o payload estruturado.
