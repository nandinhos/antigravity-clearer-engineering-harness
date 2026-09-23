# ADR 004: Governança de CI Mandatória e Pre-Push Safety Gate (Zero-Tolerance Pipeline Red)

## Status
**APROVADO** (Implementado na branch `dev-ci-safety-gate`)

---

## Contexto & O Incidente de Origem

Em ambientes orientados a esteiras de Integração Contínua (GitHub Actions, GitLab CI), agentes autônomos de IA frequentemente buscam otimizar a velocidade e a cota de tokens executando apenas linters ou testes isolados (ex: `Pest Architecture`, `PHPStan`, `git status`). Essa prática cria uma **falsa sensação de estabilidade**, culminando em quebras de esteira após o push.

### Estudo de Caso: Incidente `refactor-radar` (P1)
No repositório `refactor-radar` (commit `e33408b`, resolvido no commit `f5beddf`), a pipeline do GitHub Actions quebrou com 2 falhas na suíte `Tests\Feature\OperationsLookupTest`:
1. `contagem de artifact_kinds: Failed asserting that 6 is identical to 5`.
2. `slug de ação fora do padrão: Failed asserting that 'export_database' matches convention 'action:noun-verb'`.

### Análise dos 5 Porquês
1. **Por que o CI quebrou?** A asserção de contagem de lookups e a validação de convenção de nomenclatura falharam.
2. **Por que a contagem divergiu?** Um novo `artifact_kind` foi adicionado ao domínio sem que os testes existentes fossem atualizados.
3. **Por que a nova ação estava fora da convenção?** Foi nomeada sem obedecer ao padrão semântico adotado pelo projeto.
4. **Por que essas falhas não foram capturadas localmente antes do push?** O agente executou apenas linters estáticos e testes de arquitetura parciais para poupar tempo/tokens, assumindo erroneamente que "o sistema estava verde".
5. **Por que o `git push` foi autorizado?** Porque o harness tratava o `git push` padrão como comando benigno (`ALLOW`), sem exigir prova documental da execução integral da suíte de testes do CI vinculada ao commit hash local.

---

## Decisão Arquitetural

Adotamos uma política estrita de **Tolerância Zero a Pipeline Vermelho** (*Zero-Tolerance Pipeline Red*), sustentada por 4 pilares determinísticos:

### 1. Cláusula de Governança Inegociável
Em qualquer projeto onde for detectada infraestrutura de CI ativa (`.github/workflows/` ou `.gitlab-ci.yml`), **é terminantemente proibido subir código em `dev`, `staging` ou `main` que não esteja 100% verde**. 
- Nenhuma suíte de CI pode ser omitida ou substituída por checagens parciais de conveniência.

### 2. Certificado de Voo Local (`.ceh/last-ci-run.json`)
O executor de testes oficial do harness (`scripts/test-runner.sh`) foi atualizado para atuar como autoridade de certificação local. Ao concluir a suíte de testes:
- Identifica o commit hash local exato (`git rev-parse HEAD`).
- Registra o comando de teste executado, o exit code e o status (`PASS` ou `FAIL`).
- Emite o certificado estruturado em `.ceh/last-ci-run.json`.

```json
{
  "commit_hash": "a1b2c3d4e5f6...",
  "timestamp": "2026-09-20T00:50:00Z",
  "command": "npm test",
  "status": "PASS",
  "exit_code": 0
}
```

### 3. Pre-Push Safety Gate Automático (`scripts/safety-gate.py`)
O mecanismo de interceptação de comandos do harness passa a validar comandos `git push` contra o estado do repositório:
- Se o projeto possuir CI ativa, qualquer invocação de `git push` exige a existência de um certificado de voo válido.
- **Condições de Bloqueio Imediato (`DENY`)**:
  - Certificado ausente (`.ceh/last-ci-run.json` não encontrado).
  - Status diferente de `PASS` ou exit code $\neq 0$.
  - Descompasso de hash: o commit atual do repositório divergiu do commit registrado no certificado (código alterado após a execução dos testes).

### 4. Prevenção de "Testes Congeladores" e Shift-Left de Convenções
- **Auditoria de Lookups**: A skill `clearer-review` passa a conter verificação atômica para modificações em catálogos de domínio (enums, seeders, lookups), alertando sobre asserções de contagem cega (`assertCount(5)`) que provocam assertion drift.
- **Shift-Left de Convenções**: Convenções de nomenclatura e contratos de domínio devem ser validados via testes de arquitetura estática (AST / ArchUnit / Pest Architecture), garantindo que nomes inválidos sejam interceptados na máquina do desenvolvedor.

### 5. Delimitação Formal do Modelo de Ameaça e Regra de Parada

- **Modelo de Ameaça Local**:
  O certificado local protege contra **erro e atalho de um agente cooperativo**: rodar só parte da suíte, mascarar uma falha com `|| true`, testar um worktree diferente do commit, esquecer de rodar. Contra fraude ativa ou agente hostil que deliberadamente forje certificados locais, a autoridade de release é o **CI remoto na nuvem**. Esse controle remoto (branch protection e status checks obrigatórios) é uma **dependência operacional externa necessária**, classificada formalmente como `UNKNOWN` no escopo local do harness (não verificada diretamente pelo checkout local), cabendo à governança do repositório mantê-la ativa no provedor Git.
- **Regra de Parada**:
  Um bypass só vira código se um agente apressado puder produzi-lo sem intenção de burlar. Casos que exijam intenção deliberada de fraude ou inspeção profunda de conteúdo de código inline são classificados em "Fora do modelo" e não geram heurísticas nem denylists.
- **Fora do Modelo**:
  - Certificado forjado à mão (`.ceh/last-ci-run.json`).
  - Código inline de interpretador (família `-e`, `-c`, `-p`, `-E`).
  - Conteúdo interno dos scripts de teste declarados em manifestos.
  - Cobertura dos jobs da CI pelo comando canônico (responsabilidade humana na esteira).
  - Refspec cuja origem não é o HEAD.
  - Testes que alteram arquivos durante a execução.
- **Regra de Uso e Canonicidade**:
  O comando canônico é o que o humano declara em `.ceh/config.json` (`canonical_test_command`), ou o comando auto-detectado pelo repositório. Para garantir a integridade da configuração e impedir adulterações por arquivos ignorados ou desatualizados, `.ceh/config.json` **deve obrigatoriamente estar rastreado e commitado em HEAD**, sem modificações no worktree. Se a CI possuir múltiplos jobs, o humano declara uma suíte agregadora que os execute de ponta a ponta.

---

## Consequências e Princípio Ponytail (Zero Overengineering)

- **Zero Dependências Novas**: A solução utiliza estritamente utilitários já existentes no CEH (`python3`, `bash`, `git`, `jq`).
- **Fail-Closed com Mensagem Acionável**: Quando o gate bloqueia um `git push`, ele instrui exatamente o comando a ser executado (`bash scripts/test-runner.sh`), eliminando perda de tempo.
- **Blast Radius Mínimo**: Projetos sem esteira de CI continuam com o fluxo de push tradicional desimpedido em branches permitidas (`dev`).
