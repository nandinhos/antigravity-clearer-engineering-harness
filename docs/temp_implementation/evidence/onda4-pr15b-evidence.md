# Relatório de Evidência Técnica: PR-15b (Adaptador do Muse a partir de E1/E1b)

**Data:** 2026-09-30  
**Branch:** `feature/onda-4`  
**Referência:** Handoff 075 (seção 0.71 do plano de implementação)  
**Status da Implementação:** Concluído, testado, mutado e validado ponta a ponta no Muse real (E15)  

---

## 1. Contexto e Objetivos

O PR-15b conclui a integração agnóstica de hosts da Onda 4 com o desenvolvimento do **`MuseAdapter`**, integrando formalmente o CLI do **Muse** ao ecossistema do CLEARER Engineering Harness (CEH).
A implementação baseia-se estritamente nas evidências empíricas capturadas nos experimentos controlados E1 e E1b (`docs/temp_implementation/evidence/host-probe/muse/`).

---

## 2. Contrato Técnico do `MuseAdapter`

### 2.1 Detecção Unívoca de Host (`detect`)
O critério de detecção separa os três hosts sem ambiguidade, comprovado matematicamente por contagem exata contra todos os payloads gravados:

| Conjunto de Payloads Gravados | Total de Casos | `AntigravityAdapter` | `MuseAdapter` | `ClaudeCodeAdapter` |
|---|---|---|---|---|
| **Antigravity** (`antigravity/recorded.jsonl`) | **93** | **93** | 0 | 0 |
| **Muse** (`muse/recorded.jsonl`) | **41** | 0 | **41** | 0 (via despachante) |
| **Claude Code** (`claude_code/recorded.jsonl`) | **14** | 0 | 0 | **14** |

**Ordem Canônica no Despachante (`hook_context.py`):**
```python
ADAPTERS: list[HostAdapter] = [
    AntigravityAdapter(),
    MuseAdapter(),
    ClaudeCodeAdapter(),
]
```
O posicionamento do `MuseAdapter` antes do `ClaudeCodeAdapter` garante que os payloads do Muse sejam interceptados pelo adaptador nativo antes de qualquer fallback genérico.

### 2.2 Ferramentas Suportadas e Decisão Explícita de `submit_reminder_decision`
- **Ferramentas de Terminal:** `bash` -> mapeada para `Request(command=..., cwd=...)`.
- **Ferramentas de Escrita:** `write_file`, `edit_file` -> mapeadas para `Request(command="", cwd=..., target_paths=[...])`.
- **Ferramenta Interna (`INTERNAL_ALLOW_TOOLS`):** `submit_reminder_decision`
  - *Justificativa e Decisão Explícita:* Trata-se de ferramenta interna do runtime do Muse usada para coordenação cognitiva de lembretes e skills, sem acionamento de terminal nem alteração do filesystem. Mapeada para `Request(command="", cwd=...)`, sendo avaliada pelo motor como permitida (`allow`) sem efeitos colaterais.
- **Ferramentas Desconhecidas:** Rejeitadas com `ValueError` ativando fail-closed com bloqueio nativo.

### 2.3 Respostas Nativas do Muse (`render` e `render_error`)
Conforme observado no E1b:
- **`allow`:** `{}` (objeto JSON vazio) com **exit code 0**.
- **`deny` / `ask`:** `{"decision": "block", "reason": "<motivo>"}` com **exit code 0**.
- **`render_error`:** `{"decision": "block", "reason": "<erro>"}` com **exit code 0**.
*Invariante:* No Muse, **nunca** é emitido exit code 2.

---

## 3. Matriz de Fixtures e Resolução da Ressalva BG1

Para atender integralmente à ressalva BG1 apontada no Handoff 075, foram consolidadas fixtures duplas (casos manuais + casos gravados reais):

1. **`tests/fixtures/adapters/muse/cases.jsonl` (8 casos manuais):**
   - Cobre cenários funcionais (`bash_safe`, `bash_destructive_prod`, `write_file_safe`, `write_file_protected_ceh`, `edit_file_safe`, `submit_reminder_decision_safe`) e casos de borda/erro (`bash_empty_command`, `unknown_tool`).
2. **`tests/fixtures/adapters/muse/recorded.jsonl` (41 casos reais gravados):**
   - Payloads extraídos diretamente das sessões exploratórias E1/E1b, garantindo 100% de representatividade dos campos reais (`model_provider`, `turn_id`, `workdir`, etc.).
3. **Fixtures reais de Antigravity e Claude Code:**
   - `tests/fixtures/adapters/antigravity/recorded.jsonl` (93 casos reais).
   - `tests/fixtures/adapters/claude_code/recorded.jsonl` (14 casos reais).

---

## 4. Rede de Não-Regressão da Onda 4 (`onda4_baseline.py`)

A execução de `python3 clearer-engineering/tests/tools/onda4_baseline.py --check` validou as 5 medições canônicas:

1. **A1 (Decisões do Gate):** 1.024 avaliações do golden corpus com hash `3878d3cc285f7ab6...` idênticas.
2. **A2a (Ativos Não-Código):** 45 ativos não-código byte-a-byte idênticos, bloco de aliases no shell rc idêntico.
3. **A2b (Manifesto da Instalação):** 123 caminhos instalados, com todos os 20 arquivos novos da Onda 4 formalmente declarados em `ONDA4_DECLARED_NEW_PATHS`.
4. **A3 (Respostas do Hook agy + claude):** 107 respostas do hook preservadas idênticas em exit code e stdout.
5. **A3-muse (Antes × Depois e Controle Cruzado):**
   - *Antes:* 41 respostas preservadas no `A3_muse_before.jsonl` com exit code 2 (comportamento da v1.4.0 sem adaptador).
   - *Depois:* 41 respostas conferidas contra `A3_muse_after.jsonl` com exit code 0 e stdout nativo `{}` ou `block`.
   - *Controle Cruzado:* Todos os 7 comandos de terminal (`bash`) conferidos e confirmados contra `ceh_core.engine.evaluate()`.
6. **A4 (Acoplamento):**
   - `safety-gate.py`: 0 referências de host, 100 linhas (shim fino).
   - `ceh_core/`: 0 referências de host.
   - `hook_context.py`: 0 referências de host.
   - `adapters/`: 69 referências isoladas.

---

## 5. Provas de Falsificabilidade por Mutação (Regra AT5)

Arquivo: `clearer-engineering/tests/tools/test_mutation_p15b.py`  
Executado estritamente em clones temporários descartáveis com caminhos canônicos resolvidos (`Path.resolve()`, convenção BG2):

1. **M1 (Muse após Claude no Despachante):**
   - *Mutação:* Inversão da ordem no `hook_context.py` posicionando `ClaudeCodeAdapter` antes de `MuseAdapter`.
   - *Resultado:* `test_adapters.py` **REPROVOU** com `AssertionError` na detecção e despacho de fixtures do Muse.
2. **M2 (Muse devolvendo exit 2):**
   - *Mutação:* Alteração de `MuseAdapter.render()` para devolver exit code 2 no allow.
   - *Resultado:* `test_adapters.py` **REPROVOU** com `AssertionError` na matriz de fixtures gravadas e unitários de render.

---

## 6. Validação Ponta a Ponta no Muse Real (E15)

Arquivo de Execução: `clearer-engineering/tests/tools/e15_muse_runner.py`  
Diretório de Artefatos Brutos: `docs/temp_implementation/evidence/e15-muse-hook/`

Foi instanciada uma sessão real do **Muse Code 1.4.1 (1.4.1-R4503.1)** com o CEH Safety Gate instalado e aprovado como hook `PreToolUse`:

| Cenário | Operação Submetida ao Muse | Comportamento do Safety Gate | Comportamento do Muse CLI | Status |
|---|---|---|---|---|
| **Cenário 1 (Allow)** | `echo 'MUSE_E15_ALLOW_SUCCESS' > sentinel` | Saída `{}` com exit code 0 | Comando executado; arquivo sentinela criado com sucesso | **PASS** (49.71s) |
| **Cenário 2 (Block)** | `git push origin dev` (sem certificado prévio de CI) | Saída `{"decision": "block", "reason": "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado..."}` com exit code 0 | Ferramenta interceptada e bloqueada pelo hook; `never_created.txt` não criado | **PASS** (28.85s) |

### Artefatos Brutos Preservados:
- `manifest.json`: Manifesto do plugin registrado no Muse.
- `cli_output_allow.txt`: Transcrição bruta da execução permitida.
- `cli_output_block.txt`: Transcrição bruta do bloqueio exibindo a mensagem `[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: NENHUMA execução prévia comprovada em '.github/workflows'`.
- `runner.py`: Cópia versionada do runner experimental.
- `summary.md`: Relatório executivo do teste E15.

---

## 7. Resultados da Suíte Canônica

- **`doc-audit.py`:** **7/7** checagens aprovadas.
- **`run-all-tests.sh`:** **71/71** testes aprovados (100% de sucesso).
- **Sem quebras de orçamento:**
  - `safety-gate.py`: 100 linhas (teto <= 100).
  - Módulos core: todos <= 300 linhas.
  - Termos de acoplamento fora de `adapters/`: 0.
