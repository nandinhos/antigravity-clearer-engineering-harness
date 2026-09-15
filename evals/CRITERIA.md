# Critérios Formais do Smoke-Eval (CEH Meta-Eval)

Documento normativo e imutável. Define as condições de aprovação binária da dinâmica de evals do **CLEARER Engineering Harness (CEH)**.

---

## 1. Princípio da Imutabilidade

Este documento DEVE ser escrito antes da primeira execução e NÃO PODE sofrer alterações retroativas após a observação dos resultados.
Se uma rodada de avaliação falhar em qualquer um dos 5 critérios estabelecidos, o veredito obrigatório é **DESCARTAR** o candidato e documentar a falha em Architecture Decision Record (ADR), sem readequação conveniente de limites.

---

## 2. As 5 Condições Obrigatórias de Aprovação (5/5)

Para ser classificado como `APROVADO`, o harness candidato DEVE satisfazer concomitantemente todas as 5 condições:

### Condição 1: Baseline Estável (3x Verde Consecutivo)
- O runner DEVE executar a suíte canônica de fixtures por 3 (três) vezes consecutivas.
- Todas as 3 execuções DEVEM retornar exit code `0` com 100% de asserções atendidas.
- A asserção baseia-se exclusivamente em tokens contratuais observáveis (`CEH-SAFETY`, `ALLOW`, `WARN`/`ASK`, `DENY`) e códigos de saída (`0`, `1`, `2`).
- Nenhuma chamada a LLM-as-a-judge ou serviço externo de rede é permitida.

### Condição 2: Deriva A — Falha de Infraestrutura (Fail-Closed)
- Simula a ausência física do mecanismo de segurança (ex: hook renomeado, caminho inexistente ou corrompido).
- O runner DEVE falhar imediatamente com veredito explícito de `INFRA-FAIL` e exit code não-zero (`1`).
- Sob NENHUMA hipótese o runner pode emitir um falso positivo ("verde silencioso") quando o mecanismo de guarda estiver inacessível.

### Condição 3: Deriva B — Mutação Semântica Silenciosa
- Simula uma degradação sutil de regra (ex: supressão do termo `"prod"` ou relaxamento de regex no classificador de ambiente).
- O runner DEVE acusar falha comportamental (vermelho de regra) nas fixtures que dependem do termo degradado.
- A falha DEVE ser determinística, sem crash de interpretador, mantendo os códigos de saída canônicos e capturando a escalada indevida de permissão.

### Condição 4: Restauração Limpa (Byte-a-Byte)
- Após a injeção das Derivas A e B, o repositório DEVE ser restaurado ao estado baseline exato.
- A verificação de `git status --porcelain` DEVE ser estritamente vazia (zero resíduos ou arquivos órfãos).
- A re-execução do runner após restauração DEVE retornar `100% PASS` (verde).

### Condição 5: Teto Rígido de Tempo de Parede (Wall Time < 60s)
- O tempo total de parede cronometrado para o ciclo completo (Baseline 3x + Deriva A + Deriva B + Restauração) DEVE ser inferior a **60 segundos**.
- Meta nominal de engenharia: inferior a **10 segundos** em ambiente local.
- Qualquer corrida que atinja ou ultrapasse 60 segundos DEVE ser imediatamente marcada como `TIMEOUT / FAIL`.

---

## 3. Matriz de Veredito Binário

| Resultado dos Critérios | Decisão | Ação Mandatória |
|---|---|---|
| **5 de 5 Atendidos** | `APROVA` | Homologação na branch `dev` como baseline de integridade. |
| **< 5 Atendidos (Qualquer falha)** | `DESCARTA` | Rejeição sumária, registro do motivo em ADR de descarte e expurgo da branch. |

---

## 4. Fixtures Canônicas de Referência

O runner mede o contrato contra a matriz de 4 casos essenciais:
1. **Comandos Equivalentes**: Veredito idêntico para variações de forma (`git push origin main --force` e `git push origin main -f` ambos bloqueados em produção).
2. **Operação Benigna**: Operações de leitura e status (`git status`, `ls`) liberadas em qualquer ambiente.
3. **Matriz de Ambientes**: Comandos com impacto estrutural (`php artisan migrate:fresh` ou equivalentes de banco) comportam-se conforme a matriz de segurança:
   - `development`: `allow` com prontidão de backup;
   - `staging`: `ask` com confirmação em 2 alertas;
   - `production`: `deny` incondicional.
4. **Catastróficos**: Padrões de destruição global (`rm -rf /`, fork bomb) bloqueados sumariamente em qualquer ambiente.
