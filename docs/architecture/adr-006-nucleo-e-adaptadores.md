# ADR 006: Separação entre Núcleo Portável (Stdlib-Only) e Adaptadores de Host

## Status
**ACEITO & CONCLUÍDO** (Núcleo desacoplado em `ceh_core/` com interface canônica `evaluate(Request) -> Decision`; adaptadores para Google Antigravity, Claude Code e Muse Code implementados em `clearer-engineering/scripts/adapters/`; suíte de conformidade cross-host com 1.016 casos validada em 100% de paridade na v2.0.0 e refinada com remediação Hermes na v2.1.0)

---

## Contexto & Problema

O **CLEARER Engineering Harness (CEH)** foi inicialmente concebido como um plugin de governança acoplado ao ecossistema do Google Antigravity. O objetivo de evolução arquitetural do harness é estruturar as políticas de segurança e engenharia sob um **núcleo de comportamento desacoplado**, a partir do qual adaptadores para diferentes ambientes (Antigravity, Claude Code, Muse Code, terminal) possam ser integrados mantendo regras equivalentes.

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
  - **Claude Code Adapter**: Tradução bidirecional para o hook `PreToolUse` do Claude Code (`adapters/claude.py`).
  - **Muse Code Adapter**: Protocolo de interceptação baseado em payload JSON do Muse (`adapters/muse.py` e `adapters/fallback.py`).
  - **Terminal / CLI Adapter**: Scripts executáveis como `agy-ceh` e `ceh-branches`.
- **Conformidade Cross-Host & Empacotador**:
  - Empacotador determinístico multi-host em `tools/package.py` para Antigravity, Claude Code e Muse Code.
  - Suíte de conformidade cross-host garantindo que os três adaptadores produzam idênticos vereditos para a matriz canônica de 1.016 comandos.

---

## Consequências e Benefícios Observados

- **Desacoplamento Arquitetural**: A política de segurança reside centralizada no núcleo `ceh_core/`, separada dos pontos de injeção e hooks do host.
- **Auditoria e Evolução Centralizadas**: Correções de regras, novos bloqueios e ajustes léxicos ocorrem em ponto único do repositório.
- **Baixa Latência de Inicialização**: A execução do Safety Gate opera estritamente com módulos nativos da biblioteca padrão Python, sem a sobrecarga de inicialização de frameworks externos.
