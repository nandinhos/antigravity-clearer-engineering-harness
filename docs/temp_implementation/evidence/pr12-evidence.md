# Evidência Técnica de Implementação — PR-12

**Data:** 2026-09-27  
**PR:** PR-12 — `build(release): SemVer, CHANGELOG e instalação fixada por versão`  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commit Base:** `74fdd12` (PR-11b — `fix(uninstall): remoção sem efeito colateral no rc do usuário`)  
**Status:** IMPLEMENTADO E SUBMETIDO PARA REVISÃO  

---

## 1. Resumo Executivo da Release v1.3.0

O PR-12 finaliza formalmente a **Onda 3** do CEH, entregando a governança de versão SemVer, padronização de ativos de instalação, auditoria de mudanças históricas e desacoplamento do perfil do agente:

1. **Fonte Única de Versão (SemVer 1.3.0)**:
   - [`clearer-engineering/plugin.json`](../../clearer-engineering/plugin.json) é consolidado como a única autoridade da versão `1.3.0` do harness.
   - As tags Git históricas `v1.0.0`, `v1.1.0` e `v1.2.0` já existem no repositório.
   - **Norma estrita observada:** A tag `v1.3.0` **NÃO** foi criada pelo agente, permanecendo como prerrogativa exclusiva do desenvolvedor após o merge na branch principal.

2. **Extração Canônica do Perfil do Agente e Teste de Identidade**:
   - O perfil completo do orquestrador foi extraído do heredoc inline em `install.sh` (`AGENT_EOF`) para o arquivo canônico versionado [`clearer-engineering/profiles/clearer-harness.agent.md`](../../clearer-engineering/profiles/clearer-harness.agent.md).
   - O instalador agora copia o perfil diretamente da fonte (`cp "$AGENT_PROFILE_SRC" "$TARGET_AGENT_DIR/agent.md"`).
   - Adicionado teste de integridade byte a byte (`cmp -s`) em [`clearer-engineering/tests/run-install-verification.sh`](../../clearer-engineering/tests/run-install-verification.sh), garantindo que o perfil instalado em `~/.gemini/config/agents/clearer-harness/agent.md` é estritamente idêntico ao arquivo canônico.
   - Teste 30 de [`clearer-engineering/tests/run-all-tests.sh`](../../clearer-engineering/tests/run-all-tests.sh) atualizado para inspecionar as ferramentas declaradas diretamente no perfil canônico.

3. **Suporte à Instalação Fixada por Versão (`CEH_VERSION`)**:
   - [`install.sh`](../../install.sh) implementa suporte nativo à variável `CEH_VERSION` no one-liner.
   - Quando informada, clona o repositório com profundidade 1 fixado na tag (`git clone --depth 1 --branch "v${CEH_VERSION#v}" ...`).
   - As instruções de instalação com versão fixada foram devidamente publicadas e documentadas em [`README.md`](../../README.md) e [`README_PT.md`](../../README_PT.md).

4. **CHANGELOG Canônico (Keep a Changelog)**:
   - Criado [`CHANGELOG.md`](../../CHANGELOG.md) na raiz do projeto aderente ao padrão Keep a Changelog.
   - Consolida detalhadamente todas as entregas desde P0, Onda 0, Onda 1 (G1–G6), Onda 2 (G7, Hook Fail-Closed, G9) e Onda 3 (PR-11, PR-11b, PR-12), com hiperlinks para os respectivos handoffs executivos em `docs/temp_implementation/handoffs/`.

---

## 2. Matriz de Verificação de Integridade e Testes (`OBSERVED`)

| Componente | Verificação Executada | Resultado Observado (`OBSERVED`) | Status |
|---|---|---|---|
| **Identidade de Perfil** | `cmp -s $REPO_ROOT/.../clearer-harness.agent.md $TARGET_AGENT_DIR/agent.md` | Hashes e bytes 100% idênticos sem divergência. | **PASS** |
| **Suíte de Instalação** | `bash clearer-engineering/tests/run-install-verification.sh` | 4/4 blocos passaram (Idempotência, Simetria, Seguro AN1/AN2/AN3, Aliases, Honesty). | **PASS** |
| **Suíte Canônica Geral** | `bash clearer-engineering/tests/run-all-tests.sh` | 58/58 testes unitários e de integração passaram. | **PASS** |
| **Redes Diferenciais** | `test_gate_differential_fuzz.py` & `test_environment_differential.py` | 0 relaxamentos detectados contra `d59c943`. | **PASS** |
| **Auditoria Documental** | `bash clearer-engineering/scripts/doc-audit.sh` | 7/7 checagens aprovadas; orçamentos de linhas respeitados. | **PASS** |
| **Smoke Evals** | `bash evals/run-evals.sh` | 5/5 critérios RFC 2119 satisfeitos. | **PASS** |

---

## 3. Próximos Passos
- Conclusão da Onda 3 após aprovação do PR-12 pela revisão sênior.
- Merge na branch principal e criação da tag `v1.3.0` pelo mantenedor.
- Preparação para Onda 5 (Qualidade: PR-QA B–D, AM2, shellcheck, matriz macOS).
