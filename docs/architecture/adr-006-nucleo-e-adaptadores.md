# ADR 006: Separação entre Núcleo Portável (Stdlib-Only) e Adaptadores de Host

## Status
**ACEITO** (Direção arquitetural adotada; núcleo implementado em `ceh_core/` e adaptador Antigravity ativo; adaptadores adicionais e suíte de conformidade multi-host planejados para a Onda 4 / v2.0.0)

---

## Contexto & Problema

O **CLEARER Engineering Harness (CEH)** foi inicialmente concebido como um plugin de governança acoplado ao ecossistema do Google Antigravity. O objetivo de evolução arquitetural do harness é estruturar as políticas de segurança e engenharia sob um **núcleo de comportamento desacoplado**, a partir do qual adaptadores para diferentes ambientes (Antigravity, Claude Code, Cursor, Codex, terminal) possam ser integrados mantendo regras equivalentes.

Se a lógica de segurança, parsing de shell e avaliação de regras depender de APIs proprietárias de um único host ou de dependências externas pesadas, a replicação do harness para outros ambientes resultará em divergência semântica e complexidade de manutenção.

---

## Decisão Arquitetural

Adotamos a **Separação Arquitetural entre Núcleo e Adaptadores de Host**:

### 1. Núcleo de Políticas (*Core Policy Engine* — Python Stdlib-Only)
- Localizado em `clearer-engineering/scripts/ceh_core/` e acionado via `safety-gate.py` e `test-runner.sh`.
- **Restrição Inegociável**: Operação do código Python do núcleo 100% restrita à biblioteca padrão (`stdlib-only` Python 3.9+), sem dependências via `pip`.
- **Requisitos de Runtime de Shell**:
  - Scripts do ciclo de vida de instalação (`install.sh`, `uninstall.sh`): compatíveis com Apple Legacy Bash 3.2+ (com verificação estrita de sintaxe e recusa fail-closed defensivo no CI macOS).
  - Scripts de orquestração avançada e ferramentas auxiliares (como `conselho-seniores.sh`): requerem Bash 4.3+ (uso de `local -n` e arrays associativas `declare -A`; no macOS CI, executados sob Bash Homebrew 5+).
- Responsabilidades do Núcleo:
  - Lexer e tokenizer determinístico de shell (`ceh_core/lexer.py`).
  - Ponto único de normalização de caminhos e comandos (`ceh_core/normalize.py`).
  - Classificação formal de ambientes `DEV`, `STAGING`, `PROD` (`ceh_core/environment.py`).
  - Avaliação estrita de comandos destrutivos (`rm`, `git`, interpretadores) com prioridade `CATASTROPHIC > DENY > ASK > ALLOW`.
  - Certificação local e hermética de CI (`.ceh/last-ci-run.json`).

### 2. Adaptadores de Host (*Host Adapters*)
Os adaptadores são camadas de integração responsáveis por traduzir o protocolo de interceptação de ferramentas específico de cada host para a interface canônica do núcleo:

- **Adaptadores Implementados e Validados**:
  - **Antigravity Hook Adapter**: `hooks.json` intercepta chamadas de ferramenta e invoca `safety-gate.py`.
  - **Terminal / CLI Adapter**: Scripts executáveis como `agy-ceh` e `ceh-branches`.
- **Adaptadores Planejados (Trabalho Futuro — Onda 4 / v2.0.0)**:
  - Adaptadores dedicados para Claude Code (`hosts/claude-code/`), Cursor e outros ambientes, conforme cronograma da Onda 4.
  - Suíte formal de conformidade multi-host para demonstrar empiricamente a equivalência de vereditos entre os diferentes adaptadores antes de declarar paridade funcional.

---

## Consequências e Benefícios Observados

- **Desacoplamento Arquitetural**: A política de segurança reside centralizada no núcleo `ceh_core/`, separada dos pontos de injeção e hooks do host.
- **Auditoria e Evolução Centralizadas**: Correções de regras, novos bloqueios e ajustes léxicos ocorrem em ponto único do repositório.
- **Baixa Latência de Inicialização**: A execução do Safety Gate opera estritamente com módulos nativos da biblioteca padrão Python, sem a sobrecarga de inicialização de frameworks externos.
