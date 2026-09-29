# Relatório de Evidências — PR-07b (Handoff 031)

- **Data/Hora**: 2026-09-26T23:30:00Z
- **Escopo**: Sinais de ambiente por forma (qualquer `NOME=valor`, `-var env=...`, `--environment`, `--profile`), `cd`/`pushd` como definidor de contexto dos subcomandos seguintes (AF1) e rede diferencial da detecção sem `explicit_env`.
- **Alvo**: Fechamento formal definitivo da Onda 1 do CEH.

---

## 1. Implementação Técnica

### 1.1 Sinais de Ambiente Reconhecidos por Forma (`ceh_core/environment.py`)
- Substituída a lista fixa restrita de nomes por reconhecimento estrito de padrões sintáticos de shell:
  - **Qualquer atribuição `NOME=valor`** na cabeça, após `export` ou após `env`: o valor é avaliado por segmento via `normalize_env(valor)`. Cobre `DJANGO_SETTINGS_MODULE=app.settings.production`, `MIX_ENV=prod`, `STAGE=prod`.
  - **Argumentos `chave=valor` sem hífen ou com `-var`/`--set`**: o valor é avaliado quando algum segmento da chave pertencer a `{"env", "environment", "stage", "profile", "context", "target"}`. Cobre `terraform destroy -var env=production`, `helm upgrade --set env=prod`.
  - **Opções `--X=valor`, `--X valor`, `-X=valor`, `-X valor`**: onde `X` pertence a `{"env", "environment", "stage", "profile", "context", "kube-context", "target"}`. Cobre `--environment=production`, `--profile production`, `--stage=prod`.
  - **Invocação `cd <dir>` ou `pushd <dir>`**: o caminho do diretório de contexto conta como sinal de ambiente que só escala (`normalize_env(dir)`).
- Comentários `# ...`, caminhos em comandos inócuos (`cat docs/staging-notes.md`), argumentos de ferramentas (`rm -rf build/production-assets`), arquivos compose (`docker-compose.staging.yml`) e `--grep=` continuam **não** contando como sinais.

### 1.2 AF1: `cd`/`pushd` Definindo Contexto dos Subcomandos Seguintes (`safety-gate.py`)
- No loop de avaliação de subcomandos em `evaluate_command`, subcomandos `cd <dir>` / `pushd <dir>` atualizam deterministicamente `current_cwd` para os subcomandos seguintes.
- Quando `target_path` for um diretório válido, `detect_environment(target_dir=current_cwd)` redetecta a branch e `.env*` do repositório de destino, escalando `current_env`.
- Comandos como `cd /caminho/repo-na-main && git reset --hard` são avaliados no repositório da `main` como `deny / production`.
- Caminhos com variáveis não resolvidas ou `~` antes de subcomandos destrutivos ativam incerteza / fail-closed (Invariante 7).

---

## 2. Rede Diferencial da Detecção de Ambiente (`test_environment_differential.py`)

Implementada a suíte `clearer-engineering/tests/test_environment_differential.py` conforme Handoff 031 §3.3:
- Extrai a linha de base hermética em `gate_baseline.txt` (`acd257d`) e instancia 4 repositórios-fixture (`dev`, `release/qa-1`, `main`, `feature/evaluation`).
- Avalia todas as decisões **sem `explicit_env`**.
- Compara com a baseline e valida que apenas os relaxamentos justificados em `relaxamentos_justificados.txt` (`H031-PR07`) ocorram.
- **Prova Física de Falsificabilidade**: Simula a lista estreita do PR-07 e comprova que a rede reprova acusando relaxamento não autorizado em `terraform destroy -var env=production`.

---

## 3. Testes Unitários de Tokens e Hermeticidade (`test_environment_tokens.py`)

- Adicionado isolamento estrito de `os.environ` no `setUp` e `tearDown`, removendo variáveis residuais (`CEH_ENV`, `APP_ENV`, `NODE_ENV`, etc.).
- 7/7 cenários unitários aprovados cobrindo:
  - Tabela Seção 1 Handoff 031 (`cd /srv/production && php artisan migrate:fresh`, `php artisan migrate:fresh --environment=production`, `terraform destroy -var env=production`, `DJANGO_SETTINGS_MODULE=app.settings.production ...`).
  - AF1 (`cd <repo-main> && git reset --hard` = `deny / production`).
  - Tabela Seção 3 e 4 Handoff 030 mantidas verdes.

---

## 4. Conformidade da Suíte Canônica (`run-all-tests.sh`) e Documentação (`doc-audit.sh`)

- `run-all-tests.sh`: **55/55 testes aprovados (100% PASS)**.
- `doc-audit.sh`: **7/7 checagens aprovadas** com todos os componentes dentro do orçamento de linhas:
  - `safety-gate.py`: 637 linhas (Teto: 650).
  - `ceh_core/environment.py`: 266 linhas (Teto: 300).
  - `test-runner.sh`: 193 linhas (Teto: 200).
- `test_gate_differential_fuzz.py`: **11.997 casos** avaliados com 0 relaxamentos contra `acd257d`.
- `snapshot_gate.py`: **1012/1012 avaliações conformes** com diff vazio.
