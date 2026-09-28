# Relatório de Evidências — PR-07 (Handoff 030)

- **Data/Hora**: 2026-09-26T23:15:00Z
- **Escopo**: Detecção de ambiente por token explícito, escalonamento univariado (só escala, nunca rebaixa), segmentação estrita em `normalize_env` e branch.
- **Alvo**: Fechamento formal definitivo da Onda 1 do CEH.

---

## 1. Implementação Técnica

### 1.1 Escalonamento Univariado de Ambiente (`ceh_core/environment.py`)
- Removido o retorno antecipado por busca de substring (`environment.py:75-78`), que permitia a comentários (`# staging`) ou substrings em caminhos rebaixarem o ambiente.
- O ambiente do contexto (variáveis de ambiente, `.env*` e Git branch) é determinado com prioridade de evidência.
- Sinais presentes na linha de comando (`cmd_line`) são extraídos estritamente por tokens explícitos via `extract_command_environment_tokens`.
- **Invariante de Não Rebaixamento**: Os sinais do comando **apenas escalam** a severidade (`ENV_SEVERITY: production(2) > staging(1) > development(0)`). Se o sinal do comando tiver severidade menor ou igual ao contexto, o ambiente do contexto prevalece incondicionalmente.

### 1.2 Tokens Explícitos de Comando (`ceh_core/environment.py`)
- Suporte estrito a:
  - `--env=X` e `--env X`;
  - Atribuições `APP_ENV=X`, `NODE_ENV=X`, `RAILS_ENV=X`, `CEH_ENV=X` (na cabeça do comando ou após `env`);
  - `--context=X`, `--context X`, `--kube-context=X` e `--kube-context X`.
- Comentários (`# ...`), caminhos de arquivo, mensagens (`--grep=...`, `-m "..."`) e texto livre são descartados na tokenização léxica (`shlex.split(..., comments=True)`).

### 1.3 Casamento por Segmentos Inteiros em `normalize_env` e Branch (`ceh_core/environment.py`)
- Segmentação via regex `re.split(r'[^\w]+', val_clean)`.
- Comparação por conjuntos finitos:
  - `PROD_SEGMENTS = {"prod", "production", "prd", "live", "preprod"}`
  - `STAGING_SEGMENTS = {"stage", "staging", "homolog", "homologacao", "homologação", "uat", "qa"}`
- Resolução de falsos positivos históricos:
  - `feature/evaluation` deixa de casar com `"uat"` e retorna `development`.
  - `normalize_env("delivery")` deixa de casar com `"live"` e retorna `development`.
  - `rm -rf build/production-assets` em branch `dev` retorna `development`.
  - `docker compose -f docker-compose.staging.yml ps` em branch `dev` retorna `development`.

---

## 2. Testes de Regressão e Invariante de Não Rebaixamento (`test_environment_tokens.py`)

Implementada a suíte `clearer-engineering/tests/test_environment_tokens.py` cobrindo 100% dos requisitos do Handoff 030:
1. `test_normalize_env_segments`: Casamento por segmento estrito e eliminação de falsos positivos (`delivery`, `evaluation`).
2. `test_handoff_030_section_3_table_on_main`: Casos da Seção 3.1 na branch `main` (`migrate:fresh`, `db:wipe # staging`, `migrate:fresh --env=staging`, `terraform destroy -var env=staging`) — 100% `deny / production`.
3. `test_handoff_030_section_3_word_segments`: Casos da Seção 3.2 com branches e argumentos em `dev`.
4. `test_handoff_030_section_4_table`: Casos da Seção 4 (escalonamento com `APP_ENV=production`, `kubectl --context prod-cluster`, `NODE_ENV=staging`, `git log --grep=production`, `release/qa-1`, `APP_ENV=local git reset --hard`).
5. `test_non_downgrade_invariant`: Invariante de não rebaixamento para combinações de branches e comandos destrutivos.

Resultado:
- **5/5 testes aprovados em 0.17s**.
- Integrado como Teste 21 na suíte geral `run-all-tests.sh` (totalizando **54/54 testes aprovados**).

---

## 3. Prova Física de Falsificabilidade da Invariante de Não Rebaixamento

Executada via script determinístico `scratch/verify_environment_falsifiability_pr07.py`:
- Amostra: 45 avaliações cruzando 3 branches (`main`, `release/qa-1`, `dev`), 5 comandos destrutivos e 3 tentativas de downgrade (`# staging`, `--env=staging`, `APP_ENV=local`).
- **Com Gate Atual (PR-07, apenas escalando)**: **0 violações**.
- **Com Retorno Antecipado reintroduzido (Simulação PR-06f)**: **10 violações capturadas** (comandos na `main` rebaixados para staging).
- Falsificabilidade comprovada: a invariante rejeita o defeito com precisão determinística.

---

## 4. Conformidade Documental e Orçamento de Linhas (`doc-audit.sh`)

7/7 checagens aprovadas com todos os componentes dentro do orçamento normativo:
- `safety-gate.py`: 595 linhas (Teto: 650)
- `test-runner.sh`: 193 linhas (Teto: 200)
- `ceh_core/environment.py`: 250 linhas (Teto: 300)
- `ceh_core/find.py`: 200 linhas (Teto: 300)
- `ceh_core/git.py`: 294 linhas (Teto: 300)
- `ceh_core/interpreters.py`: 254 linhas (Teto: 300)
- `ceh_core/interpreters_extra.py`: 263 linhas (Teto: 300)
- `ceh_core/lexer.py`: 286 linhas (Teto: 300)
- `ceh_core/rm.py`: 233 linhas (Teto: 300)
- `ceh_core/rules.py`: 63 linhas (Teto: 300)

## 5. Fuzz Diferencial vs Baseline `acd257d`

Executado via `test_gate_differential_fuzz.py`:
- 11.997 casos avaliados em 3.59s.
- **0 relaxamentos** detectados contra a baseline `acd257d`.
