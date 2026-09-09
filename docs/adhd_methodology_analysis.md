# Avaliação Técnica: Metodologia `i-have-adhd` e Adaptação ao CLEARER Engineering Harness (CEH)

**Referência**: [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)  
**Data**: 2026-09-09  
**Status**: `PROPOSTA APROVADA PARA ADAPTAÇÃO`  
**Autor**: Antigravity CEH (Ponytail Mode)

---

## 1. Resumo Executivo & Diagnóstico de Over-Engineering

A inspeção detalhada do repositório `ayghri/i-have-adhd` respondeu a duas questões fundamentais:

1. **Incorporar o repositório como código/dependência?**
   - **Veredito**: ❌ **OVER-ENGINEERING**.
   - **Motivo**: O repositório contém dezenas de arquivos, adaptadores de runtimes exóticos que não utilizamos (Pi, OMP, Kimi, Qwen, OpenCode) e scripts de hook em múltiplos shells. Incorporar isso traria dependências mortas e violaria o princípio YAGNI da Escada de Decisão Ponytail.

2. **Incorporar a metodologia de comunicação cognitiva no CEH?**
   - **Veredito**: ✅ **ALTAMENTE RECOMENDADO**.
   - **Motivo**: As **10 regras de saída** do `SKILL.md` são o equivalente ao **Ponytail Mode** na camada de UX/comunicação. Elas reduzem dramaticamente a carga cognitiva, eliminam enrolações comuns de LLMs ("Great question!", preâmbulos vazios), exigem o próximo passo imediato (< 2 min) e tratam erros de forma estritamente factual.

---

## 2. As 10 Heurísticas Cognitivas & Sinergia com o CEH

| # | Heurística `i-have-adhd` | Tradução no CEH (Ponytail Mode) | Impacto no Harness |
|---|---|---|---|
| **1** | **Lead with the next action** | A primeira linha é código, diff ou comando executável. Sem papo furado. | Corta ruído e acelera execução contínua. |
| **2** | **Number multi-step tasks** | Lista numerada estrita, sem passos recursivos/aninhados ("e depois"). | Garante determinismo nas etapas do plano. |
| **3** | **End with one concrete next step** | Fechar com 1 ação imediata para o dev validar em < 2 minutos. | Feedback rápido no fechamento do turno. |
| **4** | **Suppress tangents** | Isolar problemas paralelos; tratar 1 escopo por vez. | Reforça *Explicit Boundaries* e blast radius mínimo. |
| **5** | **Restate state every turn** | Explicitar estado do ciclo ("Passo 2 de 4: teste verde"). | Mantém o dev orientado sem sobrecarregar memória. |
| **6** | **Specific effort estimates** | Trocar termos vagos por métrica de blast radius / tempo tangível. | Calibrado para tamanho do diff e criticidade do ambiente. |
| **7** | **Make wins visible** | Mostrar o que passou a funcionar (rota, comando, teste verde). | Cumpre o gate *ENABLE EVIDENCE AND TOOLS*. |
| **8** | **Matter-of-fact errors** | Sem drama ("Ops!"). Causa raiz e correção direta. | Semântica de evidências `OBSERVED` pura. |
| **9** | **Cap lists at 5 items** | Máximo 5 itens decisórios; dividir em "agora" vs. "depois". | Reduz paralisia na revisão de código e débitos. |
| **10** | **No preamble, no recap, no closers** | Zero introduções e encerramentos vazios ("Espero ter ajudado"). | Economia direta de tokens e foco executivo. |

---

## 3. Salvaguarda e Prevalência do Harness ("Break Rules")

A especificação original do `i-have-adhd` define 6 exceções de quebra de regras, plenamente alinhadas aos Safety Gates do CEH:
- **Ações destrutivas**: Confirmação obrigatória (*Segurança supera brevidade*).
- **Explicações profundas**: Permitidas quando solicitadas expressamente pelo usuário.
- **Hierarquia de Harness**: O system prompt do harness de engenharia **prevalece** sobre a concisão cosmética. O contrato técnico e as evidências nunca são sacrificados.

---

## 4. Plano de Implementação (Roadmap para Casa)

1. **Camada de Regras Globais (`clearer-engineering/rules/AGENTS.md`)**:
   - Adicionar diretriz formal de "Comunicação Executiva & Ponytail UX" no Item 6 (Craftsmanship), incorporando as 10 heurísticas no comportamento padrão de todos os agentes.
2. **Skill Dedicada de Hiperfoco (`skills/clearer-adhd/SKILL.md`)**:
   - Criar a skill leve `clearer-adhd` (ou invocável por `/clearer-adhd`) para quem quiser forçar o modo ultra-conciso em qualquer interação.
3. **Validação com Testes e Diff Audit**:
   - Executar suíte de testes do harness (`tests/test_harness.py`, `scripts/diff-audit.sh`).
4. **Sincronização nos Manuais (`README.md`, `README_PT.md`, `docs/`)**:
   - Registrar a nova capacidade no catálogo de skills e boas práticas do CEH.
