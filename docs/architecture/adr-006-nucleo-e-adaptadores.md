# ADR 006: Separação entre Núcleo Portável (Stdlib-Only) e Adaptadores de Host

## Status
**APROVADO** (Implementado no CEH v1.3.0+)

---

## Contexto & Problema

O **CLEARER Engineering Harness (CEH)** nasceu originalmente como um plugin de governança acoplado ao ecossistema do Google Antigravity. Entretanto, o objetivo estratégico do harness é atuar como um **núcleo de comportamento e segurança portável**, capaz de prover as mesmas garantias determinísticas (Safety Gate, classificação de ambientes, governança de CI e auditoria de evidências) em múltiplos hosts:
- Google Antigravity (IDE e CLI)
- Claude Code / Anthropic Agent
- OpenAI Codex / CLI
- Cursor / Windsurf / DSH
- Ambientes de Terminal puro e CI/CD

Se o código de segurança, parsing de shell e avaliação de regras depender de APIs proprietárias, SDKs de hosts específicos ou bibliotecas externas não padronizadas, a replicação do harness para outros ambientes resultará em divergência semântica e potenciais brechas de segurança.

---

## Decisão Arquitetural

Adotamos a **Arquitetura de Núcleo Limpo e Adaptadores Desacoplados (Hexagonal / Ports and Adapters)**:

### 1. Núcleo Autocontido (*Core Policy Engine* — Stdlib-Only)
- Localizado em `clearer-engineering/scripts/ceh_core/` e acionado via `safety-gate.py` e `test-runner.sh`.
- **Restrição Inegociável**: Operação 100% restrita à biblioteca padrão (`stdlib-only` Python 3.9+ e Bash POSIX). Zero dependências via `pip`, zero frameworks externos.
- Responsabilidades do Núcleo:
  - Lexer e tokenizer determinístico de shell (`ceh_core/lexer.py`).
  - Ponto único de normalização de caminhos e comandos (`ceh_core/normalize.py`).
  - Classificação formal de ambientes `DEV`, `STAGING`, `PROD` (`ceh_core/environment.py`).
  - Avaliação estrita de comandos destrutivos (`rm`, `git`, interpretadores) com prioridade `CATASTROPHIC > DENY > ASK > ALLOW`.
  - Certificação local e hermética de CI (`.ceh/last-ci-run.json`).

### 2. Adaptadores de Host (*Host Adapters*)
- Os adaptadores são camadas finas responsáveis unicamente por traduzir o protocolo específico de cada host para a interface canônica do núcleo (`safety-gate.py --check <cmd>` ou JSON stdin/stdout):
  - **Antigravity Hook Adapter**: `hooks.json` intercepta `PreToolUse` e invoca `safety-gate.py`.
  - **CLI Adapter**: Scripts executáveis como `agy-ceh` e `ceh-branches`.
  - **Claude Code / Cursor Adapters**: Hooks de pré-execução que despacham chamadas para o motor Python do CEH.
- Os adaptadores **NÃO** reimplementam regras de segurança, não contêm lógica de bypass e nunca afrouxam as decisões do núcleo.

---

## Consequências e Benefícios

- **Portabilidade Total**: O mesmo motor de regras avalia comandos localmente, em containers ou na esteira de CI com comportamento idêntico.
- **Auditoria Centralizada**: Toda evolução, correção de brechas ou adição de comandos ocorre no núcleo `ceh_core`, propagando-se automaticamente a todos os adaptadores.
- **Baixa Pegada de Memória & Inicialização Instantânea**: Sem dependências pesadas, o Safety Gate executa em poucos milissegundos (< 50ms).
