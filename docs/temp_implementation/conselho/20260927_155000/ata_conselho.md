# Ata de Deliberação do Conselho de Seniores (CEH)
> *Sessão Extraordinária — Arquitetura do Workbench `temp_implementation` & Protocolo de Destilação de Memória*

**Data/Hora:** 2026-09-27T15:55:00-03:00  
**Repositório:** `clearer-engineering-harness`  
**Documento Avaliado:** `docs/temp_implementation/README.md`  
**Quórum Convocado:** Plenário (6 membros — claude, codex, muse, hermes, agy, agent)  

---

## 1. Parecer Unânime da Banca

O Conselho de Seniores referendou integralmente a modelagem arquitetural apresentada pelo Desenvolvedor: a pasta `docs/temp_implementation/` atua como um **Workbench Efêmero de Engenharia por Feature/Branch**, desacoplando o ruído de experimentação in-flight da documentação canônica definitiva do repositório.

| Conselheiro | Perspectiva Analítica | Veredito | Síntese do Parecer |
|---|---|---|---|
| **`claude`** | Audit & Ponytail Lead | **HOMOLOGADO** | **Anti-Poluição Documental:** Excelente separação de preocupações. Evita que documentações canônicas sejam infladas com 40+ rascunhos de handoff, mantendo apenas a essência destilada pós-homologação. |
| **`agy`** | Harness & Safety Gate | **HOMOLOGADO** | **Isolamento de Blast Radius:** A experimentação e os testes de estresse rodam isolados no workbench. Nenhum contrato canônico é alterado antes da aprovação do CI no servidor. |
| **`codex`** | Lógica Formal & Estrutura | **HOMOLOGADO** | **Protocolo Formal de Destilação:** A transição da Fase 2 (Coleta In-Flight) para a Fase 3 (Destilação) obedece a um algoritmo determinístico de promoção para schemas estruturados (`dev-memory` / KIs). |
| **`muse`** | Sistemas & Runtime | **HOMOLOGADO** | **Scaffold Limpo e Portável:** Scripts transitórios não poluem a suíte canônica de CI enquanto estiverem em rascunho, e o reset ao final da branch garante repetibilidade. |
| **`hermes`** | Tooling & Conectores MCP | **HOMOLOGADO** | **Sincronização com Hubs de Memória:** O processo de destilação é o ponto exato onde a skill `learned-lesson` injeta conhecimento duradouro no MCP `dev-memory`. |
| **`agent`** | Diff Review & Ergonomia | **HOMOLOGADO** | **Higiene Extrema de PRs:** As branches chegam para merge limpas, com o workbench resetado ou arquivado em histórico dedicado de release, facilitando o review cirúrgico. |

---

## 2. O Protocolo Canônico de 3 Fases do Workbench

1. **Fase 1 (Scaffold Inicial):** Na derivação da branch, o workbench inicia vazio com o `README.md` normativo.
2. **Fase 2 (Desenvolvimento & Coleta In-Flight):** Acumula evidências, dry-runs, handoffs e deliberações sem risco de regressão documental.
3. **Fase 3 (Destilação, Consolidação & Reset):**
   - **Promover:** Lições aprendidas para a memória permanente (`docs/lessons/`, `.ceh/`, KIs, MCP `dev-memory`).
   - **Consolidar:** Especificações e decisões na documentação oficial (`docs/architecture/`, `CHANGELOG.md`, ADRs).
   - **Arquivar/Resetar:** Resetar `docs/temp_implementation/` para o scaffold vazio padrão, mantendo o repositório perfeitamente higienizado.
