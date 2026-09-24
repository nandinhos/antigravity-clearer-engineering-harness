---
name: conselho-seniores
description: >-
  Convoca a banca multi-agente do Conselho de Seniores (claude, codex, muse, hermes, agy, agent)
  para deliberação técnica, auditoria adversarial, análise de diffs e homologação sob o protocolo CLEARER.
---

# Conselho de Seniores (Banca Multi-Agente CEH)

O **Conselho de Seniores** é a instância máxima de revisão técnica, auditoria adversarial e homologação do CLEARER Engineering Harness (CEH).
Ele é composto por 6 modelos de fronteira operando via CLI com delegações especializadas, sob a autoridade final do Owner (`nandodev`).

---

## 1. Composição e Delegações da Banca

| Membro / CLI | Provedor / Ecossistema | Delegação Especializada | Foco de Avaliação |
|---|---|---|---|
| **`claude`** | Anthropic (Claude Code) | **Audit & Ponytail Lead** | Minimalismo (*anti-overengineering*), verificação factual de claims contra evidências (`OBSERVED`), conformidade semântica e detecção de edge cases. |
| **`codex`** | OpenAI (Codex CLI) | **Lógica Formal & Algoritmos** | Raciocínio lógico dedutivo profundo, invariantes matemáticos, estruturas de dados, tipagem estrita e concorrência/deadlocks. |
| **`muse`** | Meta (Muse Code) | **Sistemas & Portabilidade** | Arquitetura de sistemas POSIX, portabilidade Linux/macOS/BSD, segurança de runtime de shell e performance de baixo nível. |
| **`hermes`** | Hermes Agent | **Tooling & Confiabilidade** | Integração com MCPs, confiabilidade de gateways e conectores, automação de tarefas e isolamento de dependências. |
| **`agy`** | Google Antigravity | **Harness & Safety Gate** | Integridade das regras do CEH, governança de ambientes (`DEV`/`HML`/`PRD`), blast radius mínimo e bloqueio de comandos destrutivos. |
| **`agent`** | Cursor Agent | **Diff Review Cirúrgico & DX** | Higiene de Git diff, ergonomia de código, impacto na IDE e consistência com os padrões existentes da base de código. |

---

## 2. Como Acionar o Conselho

A convocação do Conselho pode ser realizada diretamente via terminal através do script orquestrador:

### Convocação Plenária (Todos os 6 Conselheiros) com Inspeção de Diff:
```bash
bash clearer-engineering/scripts/conselho-seniores.sh --all --diff
```

### Convocação Focada por Especialidade:
```bash
# Apenas Claude e Codex para avaliar lógica e conformidade de contrato:
bash clearer-engineering/scripts/conselho-seniores.sh --agent claude --agent codex --diff --prompt "Auditar rigorosamente o FSM Lexer do Safety Gate"

# Avaliar um plano, documento ou especificação prévia:
bash clearer-engineering/scripts/conselho-seniores.sh --all --file docs/plano-validacao.md
```

### Simulação Prévia (Dry-Run):
```bash
bash clearer-engineering/scripts/conselho-seniores.sh --all --diff --dry-run
```

---

## 3. Contrato de Resposta do System One

Cada conselheiro emite seu parecer preenchendo obrigatoriamente um contrato discreto e auditável:

```yaml
VEREDITO: [HOMOLOGADO | RESSALVAS | REJEITADO]
CERTEZA: [0.0 a 1.0 com base em evidência física OBSERVED]
ANALISE_ESPECIALIZADA: <análise cirúrgica sob a ótica da delegação>
RISCOS_IDENTIFICADOS: <lista de riscos reais ou 'Nenhum risco observado'>
RECOMENDACAO_FINAL: <ação direta e verificável>
```

---

## 4. Geração de Atas e Despacho Soberano

Ao término da deliberação:
1. O orquestrador salva os pareceres individuais em `docs/temp_implementation/conselho/<TIMESTAMP>/parecer_<agente>.md`.
2. Compila a **Ata de Deliberação Consolidada** em `docs/temp_implementation/conselho/<TIMESTAMP>/ata_conselho.md`.
3. O agente mediador apresenta o resumo executivo no chat, destacando os vereditos, divergências e certezas.
4. **Despacho Final**: O Owner do Repositório (`nandodev`) detém o poder inegociável de desempate, autorização de promoção ou exigência de correções.
