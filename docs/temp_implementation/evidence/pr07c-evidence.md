# Relatório de Evidências — PR-07c (Handoff 032)

- **Data/Hora**: 2026-09-27T00:20:00Z
- **Escopo**: Rede real e hermética da detecção de ambiente em processos separados (B1), eliminação de tautologias e prova física de falsificabilidade via mutação real (B2), arquivo exclusivo de justificativas de detecção com branch na chave (B3), entradas completas com gramática determinística de sinais (B4), e resolução dos achados de contexto de shell AG1 (subshell isolado) e AG2 (`cd` para destino dinâmico/incerto escalando para `production`).
- **Linha de Base Homologada**: `0a51eef` (avançada no Handoff 032).
- **Alvo**: Fechamento formal definitivo da Onda 1 do CEH.

---

## 1. Resumo das Correções e Inovações (Handoff 032)

| Item | Status | Descrição da Implementação |
|---|---|---|
| **B1** | `OBSERVED` | **Isolamento Total em Subprocesso Separado**: `test_environment_differential.py` agora executa tanto a baseline (`0a51eef`) quanto o gate atual através de workers disparados via `subprocess.Popen([sys.executable, "-c", worker_code, scripts_dir], cwd=repo_path)`. O `sys.path` de cada worker aponta exclusivamente para a sua pasta de scripts extraída, eliminando qualquer compartilhamento de módulos `ceh_core` em memória (`sys.modules`). |
| **B2** | `OBSERVED` | **Remoção de Tautologias e Prova Física Real**: Deletado o teste `test_falsifiability_narrow_list_fails`. A falsificabilidade é comprovada exclusivamente por mutação física do código (`ENV_KEY_SEGMENTS = set()`), cuja saída reprovando a rede diferencial e nomeando `terraform destroy -var env=production` está registrada na Seção 3 deste relatório. |
| **B3** | `OBSERVED` | **Arquivo Exclusivo de Justificativas de Detecção**: Criado `clearer-engineering/tests/fixtures/relaxamentos_deteccao.txt` com o formato `branch|comando|de->para|ID`. O arquivo `relaxamentos_justificados.txt` volta a ser 100% exclusivo do fuzzing de ambiente explícito (`test_gate_differential_fuzz.py`). Ambos iniciam zerados contra a baseline `0a51eef`. |
| **B4** | `OBSERVED` | **Entradas Completas da Rede**: Avaliadas nas branches `dev`, `release/qa-1`, `main` e `feature/evaluation`: corpus decodificado, baterias adversariais, tabela do Handoff 031/032 e gramática determinística com semente fixa (`random.Random(42)`) cobrindo `NOME=valor`, `-var`, `--set`, `--env/--stage/--profile`, `cd <caminho>` e subshells `( ... )`. |
| **AG1** | `OBSERVED` | **Subshell Isolado `( ... )`**: `ceh_core/lexer.py` e `safety-gate.py` agora reconhecem subshells reais de forma estrita (`extract_subshell_command`), avaliando os subcomandos internos com seu próprio contexto de diretório/ambiente sem que o `cd` interno vaze para fora dos parênteses. |
| **AG2** | `OBSERVED` | **`cd` para Destino Incerto Escala para Produção**: Invocação de `cd` para destinos não resolvíveis estaticamente (`$VAR`, `${VAR}`, `~`, `-`) escala deterministicamente o contexto dos comandos seguintes para `production` (Invariante 7). Comandos não destrutivos como `npm test` continuam `allow` (custo aceito); comandos destrutivos como `git reset --hard` resultam em `deny / production`. |

---

## 2. Detalhes das Alterações no Código

### 2.1 Suporte a Subshells sem Vazamento de Contexto (AG1)
- Em `ceh_core/lexer.py`, `split_shell_pipeline` agora rastreia `paren_depth` para subshells que iniciam comandos, distinguindo-os de caracteres literais em palavras como `:(`.
- Implementada a função `extract_subshell_command(subcmd: str) -> str | None`.
- Em `safety-gate.py`, comandos envelopados por subshell são desembrulhados e avaliados recursivamente via `evaluate_command` isolado, garantindo que o `current_cwd` e `current_env` da chamada externa permaneçam inalterados.

### 2.2 Tratamento de Destino Incerto em `cd` (AG2)
- Em `ceh_core/environment.py`, implementada a função `is_unresolved_cd_target(target: str) -> bool`, que identifica alvos dinâmicos com `$VAR`, `~` ou `-`.
- Integrada em `extract_explicit_env_from_tokens` e no loop de subcomandos de `safety-gate.py`.
- Em `safety-gate.py`, na resolução de repositório git (`target_repo`), foi corrigida a regra de escalada monotônica: `target_repo` só atualiza `env` se sua severidade for estritamente superior à já detectada (`if ENV_SEVERITY.get(sub_env, 0) > ENV_SEVERITY.get(env, 0)`), impedindo que um repositório dev local rebaixe um contexto de incerteza ou produção já estabelecido.

---

## 3. Prova Física de Falsificabilidade (B2)

Conforme exigido pelo Critério de Aceite 1 do Handoff 032, a prova de falsificabilidade foi executada aplicando a mutação física `ENV_KEY_SEGMENTS = set()` em `clearer-engineering/scripts/ceh_core/environment.py` e executando a rede diferencial hermética:

```text
======================================================================
FAIL: test_environment_differential_matrix (clearer-engineering.tests.test_environment_differential.TestEnvironmentDifferential.test_environment_differential_matrix)
Avalia baseline vs gate atual sem explicit_env em múltiplos repositórios.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "clearer-engineering/tests/test_environment_differential.py", line 323, in test_environment_differential_matrix
    self.fail(msg)
AssertionError: 
[REPROVADO - Handoff 032 §2] 28 relaxamentos não autorizados de detecção:
  • [dev] terraform destroy -var env=production: old=deny(production) -> cur=allow(development) [deny->allow]
  • [dev] terraform destroy -var env=stage: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [dev] terraform destroy -var env=staging: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [dev] terraform destroy -var environment=production: old=deny(production) -> cur=allow(development) [deny->allow]
  • [dev] terraform destroy -var profile=production: old=deny(production) -> cur=allow(development) [deny->allow]
  • [dev] terraform destroy -var profile=stage: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [dev] terraform destroy -var profile=staging: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [dev] terraform destroy -var stage=prod: old=deny(production) -> cur=allow(development) [deny->allow]
  • [dev] terraform destroy -var stage=production: old=deny(production) -> cur=allow(development) [deny->allow]
  • [dev] terraform destroy -var stage=staging: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [dev] terraform destroy -var target=prod: old=deny(production) -> cur=allow(development) [deny->allow]
  • [release/qa-1] terraform destroy -var env=production: old=deny(production) -> cur=ask(staging) [deny->ask]
  • [release/qa-1] terraform destroy -var environment=production: old=deny(production) -> cur=ask(staging) [deny->ask]
  • [release/qa-1] terraform destroy -var profile=production: old=deny(production) -> cur=ask(staging) [deny->ask]
  • [release/qa-1] terraform destroy -var stage=prod: old=deny(production) -> cur=ask(staging) [deny->ask]
  • [release/qa-1] terraform destroy -var stage=production: old=deny(production) -> cur=ask(staging) [deny->ask]
  • [release/qa-1] terraform destroy -var target=prod: old=deny(production) -> cur=ask(staging) [deny->ask]
  • [feature/evaluation] terraform destroy -var env=production: old=deny(production) -> cur=allow(development) [deny->allow]
  • [feature/evaluation] terraform destroy -var env=stage: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [feature/evaluation] terraform destroy -var env=staging: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [feature/evaluation] terraform destroy -var environment=production: old=deny(production) -> cur=allow(development) [deny->allow]
  • [feature/evaluation] terraform destroy -var profile=production: old=deny(production) -> cur=allow(development) [deny->allow]
  • [feature/evaluation] terraform destroy -var profile=stage: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [feature/evaluation] terraform destroy -var profile=staging: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [feature/evaluation] terraform destroy -var stage=prod: old=deny(production) -> cur=allow(development) [deny->allow]
  • [feature/evaluation] terraform destroy -var stage=production: old=deny(production) -> cur=allow(development) [deny->allow]
  • [feature/evaluation] terraform destroy -var stage=staging: old=ask(staging) -> cur=allow(development) [ask->allow]
  • [feature/evaluation] terraform destroy -var target=prod: old=deny(production) -> cur=allow(development) [deny->allow]

----------------------------------------------------------------------
Ran 1 test in 39.326s

FAILED (failures=1)
```

A rede diferencial reprovou com 28 violações de relaxamento e **nomeou expressamente** `[dev] terraform destroy -var env=production: old=deny(production) -> cur=allow(development) [deny->allow]`.

---

## 4. Resultados dos Testes da Suíte Canônica

### 4.1 Testes Unitários de Ambiente e Tokens (`test_environment_tokens.py`)
Execução de 9/9 testes aprovados (100% OK):
- Handoff 031 §1 (sinais por forma reconhecidos em contexto de dev).
- Handoff 031 AF1 (`cd <repo-main> && git reset --hard` -> `deny / production`).
- Handoff 032 AG1 (`(cd <repo-main> && git reset --hard)` -> `deny / production` sem vazamento de contexto externo).
- Handoff 032 AG2 (`cd "$PROD_DIR" && git reset --hard` -> `deny / production`, `cd - && git reset --hard` -> `deny / production`, `cd "$DIR" && npm test` -> `allow / production` custo aceito).
- Invariante de não rebaixamento de ambiente (Monotonic Escalation).

### 4.2 Rede Diferencial de Ambiente sem `explicit_env` (`test_environment_differential.py`)
- Execução isolada em subprocessos nas branches `dev`, `release/qa-1`, `main` e `feature/evaluation`.
- **0 relaxamentos** detectados contra a baseline `0a51eef`.
- Tempo de execução: ~39 segundos.

### 4.3 Fuzzing Diferencial com Ambiente Explícito (`test_gate_differential_fuzz.py`)
- **11.997 casos avaliados** contra `0a51eef`.
- **0 relaxamentos** detectados.
- Tempo de preparação e avaliação: 3.96s (meta < 20s).

### 4.4 Golden Corpus Snapshot (`snapshot_gate.py --check`)
- **1012/1012 avaliações conformes** com diff vazio (100% conformidade).

### 4.5 Suíte Global (`run-all-tests.sh`)
- **55/55 testes aprovados (100% PASS, 0 falhas)**.

### 4.6 Smoke-Eval (`cluster2_acceptance.py --clean-eval-smoke`)
- **5/5 critérios aprovados**:
  - Critério 1: Baseline 3x consecutivo aprovado.
  - Critério 2: Deriva A (Fail-Closed por Infra Ausente).
  - Critério 3: Deriva B (Detecção de Mutação Semântica).
  - Critério 4: Restauração limpa byte-a-byte.
  - Critério 5: Tempo de parede (< 60s): 1s.

---

## 5. Auditoria de Documentação e Orçamento de Linhas (`doc-audit.sh`)

Resultado: **7/7 checagens aprovadas**:
- `safety-gate.py`: 626 linhas (Teto: 650) — **24 linhas de folga**.
- `test-runner.sh`: 193 linhas (Teto: 200) — **7 linhas de folga**.
- `ceh_core/environment.py`: 278 linhas (Teto: 300) — **22 linhas de folga**.
- `ceh_core/lexer.py`: 297 linhas (Teto: 300) — **3 linhas de folga**.
- `ceh_core/find.py`: 200 linhas (Teto: 300).
- `ceh_core/git.py`: 294 linhas (Teto: 300).
- `ceh_core/interpreters.py`: 254 linhas (Teto: 300).
- `ceh_core/interpreters_extra.py`: 263 linhas (Teto: 300).
- `ceh_core/rm.py`: 233 linhas (Teto: 300).
- `ceh_core/rules.py`: 63 linhas (Teto: 300).

O plano de implementação (`docs/plano-implementacao-elevacao-ceh.md`) foi preservado intacto sem edições pelo agente (Protocolo 7.1).
