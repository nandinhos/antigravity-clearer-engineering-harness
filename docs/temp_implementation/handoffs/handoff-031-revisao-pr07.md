# Handoff 031 — Revisão do PR-07 e despacho do PR-07b

**Data/Hora:** 2026-09-26T15:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `316505b` (PR-07)
**Antecessor:** [Handoff 030](./handoff-030-revisao-pr06f-despacho-pr07.md)

---

## 1. Veredito: **NÃO HOMOLOGADO (relaxamentos na detecção de ambiente)**

O que o PR-07 acertou (`OBSERVED`):

- o rebaixamento sumiu: na `main`, `php artisan db:wipe # staging`, `--env=staging` e `APP_ENV=local` seguem deny/production;
- casamento por segmento: `feature/evaluation` e `delivery` = development;
- `test_environment_tokens.py` versionado, com as tabelas do Handoff 030 e a invariante de não rebaixamento;
- `kubectl --context=prod` agora escala (antes saía development);
- `export APP_ENV=production && …` e `APP_ENV=production; …` seguem escalando;
- fuzz com ambiente explícito: 0 relaxamentos.

**Mas:** num repositório na branch `dev`, comparei a detecção **sem** ambiente explícito entre `971c56a` e `316505b`:

| Comando (repo em `dev`) | Antes | PR-07 |
|---|---|---|
| `cd /srv/production && php artisan migrate:fresh` | **deny/production** | allow/development |
| `php artisan migrate:fresh --environment=production` | **deny/production** | allow/development |
| `terraform destroy -var env=production` | **deny/production** | allow/development |
| `DJANGO_SETTINGS_MODULE=app.settings.production python manage.py flush --noinput` | production | development |

**Por que o fuzz não pegou:** o diferencial avalia com `explicit_env`, que desliga a detecção. **A detecção de ambiente não tem rede diferencial.**

**Responsabilidade:** a lista de sinais explícitos do Handoff 030 (`--env`, `*_ENV=`, `--context`) foi escrita **por mim, de memória**, estreita demais. É o padrão 3 do Handoff 018 cometido pelo revisor. O agente seguiu a especificação. A correção abaixo troca a lista por **regras de forma**.

**A linha de base NÃO avança** (segue em `acd257d`).

## 2. Achado adicional (G6, preexistente)

**AF1 — `cd` não muda o contexto do alvo.** Num repositório em `dev`, `cd /caminho/repo-na-main && git reset --hard` sai **allow/development**. O `git reset` roda no repositório da `main`, mas o gate avalia o diretório do hook. `git -C /caminho/repo-na-main reset --hard` já sai deny/production. É o mesmo defeito do P0/G6, dentro do próprio comando.

## 3. Despacho — PR-07b `fix(gate): sinais de ambiente por forma, cd como contexto e rede diferencial da detecção`

1. **Sinais por forma, não por lista de nomes.** Todos só escalam:
   - **Atribuição** `NOME=valor` (na cabeça, depois de `env`, ou num `export NOME=valor`/`NOME=valor;` anterior): conta o **valor**, por segmento, **qualquer que seja o nome**. Cobre `DJANGO_SETTINGS_MODULE=app.settings.production`, `MIX_ENV=prod` e `STAGE=prod`.
   - **Argumento `chave=valor`** sem hífen (`-var env=production`, `--set env=prod`): conta o valor quando algum segmento da **chave** for `env|environment|stage|profile|context|target`.
   - **Opção** `--X=valor` ou `--X valor`, com `X` ∈ `env|environment|stage|profile|context|kube-context|target`.
   - **Continua não contando:** comentários, `--grep=`, `-m "…"`, nomes de arquivo e caminhos de **argumentos**.
2. **AF1: `cd`/`pushd` define o contexto dos subcomandos seguintes.**
   - Depois de `cd X &&` / `cd X;`, os subcomandos seguintes são avaliados com `target_dir = X`: branch e `.env*` de `X`, como já faz o `git -C`.
   - Os segmentos do caminho `X` também contam como sinal que só escala. O diretório de trabalho é o **contexto** da execução, não um argumento. É isso que faz `cd /srv/production && …` voltar a produção, enquanto `rm -rf build/production-assets` segue development.
   - `cd` para um caminho com variável ou `~` não resolvido: mantém o contexto atual **e** escala como incerteza (Invariante 7) só se o subcomando seguinte for destrutivo.
3. **Rede diferencial da detecção**, no `test_gate_differential_fuzz.py` ou num teste próprio:
   - avalie a baseline e o gate atual **sem `explicit_env`**, dentro de repositórios-fixture nas branches `dev`, `release/qa-1` e `main`;
   - use os comandos do corpus e da bateria, a tabela da seção 1 e uma gramática de sinais: atribuições, `-var k=v`, `--environment`, `cd <caminho com prod/staging> &&`;
   - todo relaxamento precisa estar em `relaxamentos_justificados.txt`. Os do PR-07 que são **corretos** entram com o ID `H031-PR07`: `build/production-assets`, `docs/staging-notes.md`, `--grep=production`, `feature/evaluation`, `delivery` e `docker-compose.staging.yml`;
   - **falsificabilidade:** restaure a lista estreita do PR-07 num clone e mostre a rede reprovando, nomeando `terraform destroy -var env=production`.
4. **Hermeticidade:** `test_environment_tokens.py` tem de limpar do `os.environ` as variáveis `*_ENV` e `CEH_ENV` (o `environment.py:178` as lê). Hoje, um CI com `APP_ENV=production` definido quebra o teste.

### Critérios de aceite do PR-07b

- [ ] As 4 linhas da tabela da seção 1 e o AF1 (`cd <repo-main> && git reset --hard` = deny/production) estão no `test_environment_tokens.py`, verdes.
- [ ] A tabela do Handoff 030 continua verde, inclusive `rm -rf build/production-assets` = development e `git log --grep=production` = development.
- [ ] A rede diferencial da detecção existe, com a prova de falsificabilidade. Só os relaxamentos `H031-PR07` estão listados.
- [ ] O diferencial com ambiente explícito contra `acd257d` registra 0 relaxamentos. Protocolo 7.1. O plano não é editado pelo agente.

Com o PR-07b homologado, **a Onda 1 fecha**.
