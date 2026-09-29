# Handoff 030 — PR-06f homologado (G5 fechado) e despacho do PR-07 (último da Onda 1)

**Data/Hora:** 2026-09-26T14:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `acd257d` (PR-06f)
**Antecessor:** [Handoff 029](./handoff-029-revisao-pr06e.md)

---

## 1. Veredito: **HOMOLOGADO** (G5 fechado)

Reproduzido de forma independente (`OBSERVED`):

| Item | Prova |
|---|---|
| AE1–AE3 | As 7 linhas `PENDENTE:H029` ficaram verdes; o diff da bateria **só remove prefixos**. **Não resta nenhuma pendência na bateria.** |
| Varredura em um nível | O sufixo é avaliado com `scan_suffixes=False` e sem consumir profundidade. O desembrulho interno (`sh -c`, `eval`…) volta a varrer. Prova: `setsid bash -c "setsid find / -delete"` e `setsid timeout 5 setsid find / -delete` = deny. |
| Invariante de benignidade | Num clone, restaurei a varredura aninhada. Com corpus e bateria vazios, a invariante reprova com **180** comandos inofensivos bloqueados, o mesmo número do agente. |
| Diferencial contra `fe171a7` | **0 relaxamentos** nas 120 sondas acumuladas das revisões H025–H030 e no fuzz (11.997 casos). |
| Tempo do fuzz | 4 testes em ~19 s. Fica **registrado**: a meta de 20 s está no limite. Se a próxima gramática passar disso, reduza a amostra das invariantes, não as entradas. |

**Linha de base avançada** para `acd257d`.

**Registro para o backlog** (fora das classes G1–G6, pela regra do Handoff 028 §4; **não** reabrem a Onda 1):

- `ssh host "<comando>"`: execução remota, a mesma classe do `curl | bash`;
- `npx prisma migrate reset --force` e `docker compose … down -v`: comandos destrutivos de banco e infraestrutura que ainda não são detectados (classe de banco/infra, fora da G5).

## 2. Correção do revisor: a Onda 1 **não** fechava com o PR-06f

Nos Handoffs 026 a 029 eu escrevi que o PR-06f fechava a Onda 1. **Estava errado.** O plano (§5, Onda 1) inclui o **PR-07** (detecção de ambiente por token), que nunca foi despachado. Ele sai agora, e **com o PR-07 homologado a Onda 1 fecha**.

## 3. O problema que o PR-07 resolve (`OBSERVED` nesta revisão)

### 3.1 Rebaixamento: um sinal no comando **reduz** o ambiente (viola a Invariante 7)

Em um repositório na branch `main` (produção):

| Comando | Hoje | Correto |
|---|---|---|
| `php artisan migrate:fresh` | deny / production | deny / production |
| `php artisan db:wipe # staging` | **ask / staging** (um **comentário** rebaixa) | deny / production |
| `php artisan migrate:fresh --env=staging` | **ask / staging** | deny / production (nunca rebaixa) |
| `terraform destroy -var env=staging` | **ask / staging** | deny / production |

**Causa:** em `environment.py:75–78`, a busca de `"staging"`/`"production"` **em qualquer lugar do texto** do comando retorna **antes** da checagem da branch.

### 3.2 Casamento por pedaço de palavra

| Entrada | Hoje | Correto |
|---|---|---|
| branch `feature/evaluation` | staging ("uat" dentro de "evaluation"): `git reset --hard` pede confirmação em DEV | development |
| `normalize_env("delivery")` | production ("live" dentro de "delivery") | development |
| `rm -rf build/production-assets` | ambiente production (a decisão sai allow só por causa do atalho seguro) | development |
| `docker compose -f docker-compose.staging.yml …` | staging (nome de arquivo) | o ambiente do contexto |

## 4. Despacho — PR-07 `fix(gate): detecção de ambiente por token, só escalando`

1. **Sinais do comando só escalam.** O ambiente final é o **mais severo** entre o do contexto (variável de ambiente, `.env*` e branch, na ordem atual) e o do comando. Remova o retorno antecipado de `environment.py:75–78`.
2. **Só contam tokens explícitos**, com o lexer existente e nunca por substring do texto:
   - `--env=X` e `--env X`;
   - atribuições `APP_ENV=X`, `NODE_ENV=X`, `RAILS_ENV=X`, `CEH_ENV=X`, na cabeça do comando ou depois de `env`;
   - `--context X` e `--kube-context X`.

   **Não contam:** comentários (`# …`), caminhos, nomes de arquivo, mensagens (`--grep=…`, `-m "…"`) e texto livre.
3. **Casamento por segmento** em `normalize_env` e na checagem da branch: separe o valor por caracteres que não são letras nem números e compare **segmentos inteiros**.
   - production: `prod`, `production`, `prd`, `live`, `preprod`. O `preprod` fica em production para não relaxar o comportamento atual.
   - staging: `stage`, `staging`, `homolog`, `homologacao`, `homologação`, `uat`, `qa`.
   - `evaluation` e `delivery` deixam de casar.
4. **Teste novo** `tests/test_environment_tokens.py`, com fixtures de repositório na branch indicada. Toda linha da tabela da seção 3, mais estas:

| Branch | Comando | Ambiente esperado |
|---|---|---|
| `dev` | `APP_ENV=production php artisan migrate:fresh` | production (escala) |
| `dev` | `kubectl --context prod-cluster delete pod x` | production (escala; hoje sai development) |
| `dev` | `NODE_ENV=staging npm run deploy` | staging (escala) |
| `dev` | `git log --grep=production` | development |
| `dev` | `cat docs/staging-notes.md` | development |
| `release/qa-1` | `git reset --hard` | staging (segmento `qa`) |
| `main` | `APP_ENV=local git reset --hard` | production (nunca rebaixa) |
| `main` | `env CEH_ENV=staging git reset --hard` | production |

5. **Relaxamentos esperados**, que precisam ser nomeados no `pr07-corpus-diff.md`: só `feature/evaluation`, `delivery` e caminhos com "production"/"staging" voltando a development. **Nenhum** caso na `main` pode perder severidade.
6. **Fuzz:** o diferencial avalia com ambiente explícito e, por isso, **não mede a detecção**. O teste novo é a rede do PR-07. Acrescente a ele uma **invariante de não rebaixamento**:
   - para cada branch (`main`, `release/qa-1`, `dev`) e cada comando destrutivo da bateria, acrescentar `# staging`, `--env=staging` ou `APP_ENV=local` **nunca** reduz a severidade;
   - **falsificabilidade:** restaure o retorno antecipado num clone e mostre a invariante reprovando.

### Critérios de aceite do PR-07

- [ ] Todas as linhas das tabelas das seções 3 e 4 no `test_environment_tokens.py`, verdes.
- [ ] A invariante de não rebaixamento está no teste, com a prova de falsificabilidade.
- [ ] O diferencial contra `acd257d` registra 0 relaxamentos; a bateria e os controles seguem verdes.
- [ ] Os relaxamentos de detecção (item 5) estão nomeados no `pr07-corpus-diff.md`. O plano não é editado pelo agente. Protocolo 7.1.

## 5. Sequência

PR-07 → **fechamento da Onda 1** → PR-QA B–E → Onda 2 (PR-08 G7, PR-09, PR-10) → tag v1.3.0.
