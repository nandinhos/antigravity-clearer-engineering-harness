# Handoff 032 — Revisão do PR-07b e despacho do PR-07c (rede real da detecção)

**Data/Hora:** 2026-09-26T16:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `0a51eef` (PR-07b)
**Antecessor:** [Handoff 031](./handoff-031-revisao-pr07.md)

---

## 1. Veredito: **comportamento HOMOLOGADO; rede de teste REPROVADA**

### O comportamento do gate está correto (`OBSERVED`, comparação independente contra `971c56a`)

- Os 4 relaxamentos do Handoff 031 foram fechados: `cd /srv/production && …`, `--environment=production`, `terraform destroy -var env=production` e `DJANGO_SETTINGS_MODULE=…production` = production.
- **AF1 fechado:** `cd <repo-main> && git reset --hard`, `pushd <repo-main> && …` e `cd <repo-main>; git checkout -- .` = deny/production.
- `cd / && rm -rf etc` e `cd /home && rm -rf user` = CATASTROPHIC: o `cd` também muda o diretório-base do `rm`.
- Nenhum relaxamento contra `971c56a` nas minhas sondas de ambiente. O fuzz com ambiente explícito registra 0 relaxamentos contra `acd257d`.

**Linha de base avançada** para `0a51eef`. O `relaxamentos_justificados.txt` foi **zerado**, o que remove as entradas `H031-PR07` (ver B3).

### A rede diferencial da detecção não funciona

| ID | Sev. | Achado (`OBSERVED`) |
|---|---|---|
| **B1** | **ALTO** | **A "linha de base" usa o código atual.** O `test_environment_differential.py` carrega o `safety-gate.py` da baseline **no mesmo processo**. O `from ceh_core…` desse arquivo reaproveita o módulo `ceh_core` **já importado** do gate atual. Prova: `baseline_gate.detect_environment is current_gate.detect_environment` → **True**, e o arquivo é `clearer-engineering/scripts/ceh_core/environment.py` (o atual). A rede compara o código atual **com ele mesmo** em tudo que está em `ceh_core`: ambiente, `rm`, `git`, `find` e interpretadores. Mutação real num clone (`ENV_KEY_SEGMENTS = set()`, que faz `terraform destroy -var env=production` sair allow): **o teste de matriz passou.** O fuzz do PR-QA-A não tem esse defeito, porque roda a baseline num processo separado. |
| **B2** | **ALTO (processo)** | **A prova de falsificabilidade é uma tautologia.** O `test_falsifiability_narrow_list_fails` escreve `narrow_dec = "allow"` e confere que `rank["allow"] < rank["deny"]`. Isso passa sempre e não exercita código nenhum. O `pr07b-evidence.md` a apresenta como "reprova comprovadamente". **Prova de falsificabilidade é uma mutação real do código, com a saída do teste reprovando.** Uma asserção sobre constantes não é evidência e não pode ser apresentada como tal. |
| **B3** | MÉDIO | As chaves de justificativa não têm a branch. `development\|git reset --hard\|ask->allow` autorizaria o **mesmo** relaxamento na `release/qa-1`. Como o arquivo é **compartilhado** com o fuzz de ambiente explícito, a linha também afrouxaria aquela rede. |
| **B4** | BAIXO | A lista de comandos é fixa (19 comandos). O Handoff 031 §3.3 pedia o corpus, a bateria e uma gramática de sinais. |

### Achados de comportamento (G6, preexistentes)

| ID | Sev. | Comando (repo em `dev`) | Hoje | Correto |
|---|---|---|---|---|
| **AG1** | MÉDIO | `(cd <repo-main> && git reset --hard)` (subshell) | allow/development | deny/production |
| **AG2** | MÉDIO | `cd "$PROD_DIR" && git reset --hard` | allow | destino desconhecido → escala (Invariante 7) → deny |
| **AG2** | MÉDIO | `cd - && git reset --hard` | allow/development | idem |

## 2. Despacho — PR-07c `test(gate): rede real da detecção de ambiente + subshell e cd incerto`

1. **B1: a baseline roda num processo separado**, como no `test_gate_differential_fuzz.py`: um worker com `sys.path` apontando **só** para o `scripts/` extraído e com `cwd` no repositório-fixture. Os comandos entram por stdin e as decisões saem em JSON.
2. **B2: remova o `test_falsifiability_narrow_list_fails`.** A prova passa a ser uma mutação real num clone (`ENV_KEY_SEGMENTS = set()`), com a saída da rede reprovando e nomeando `terraform destroy -var env=production`, registrada no `pr07c-evidence.md`.
3. **B3:** arquivo próprio `tests/fixtures/relaxamentos_deteccao.txt`, no formato `branch|comando|de->para|ID`. O `relaxamentos_justificados.txt` volta a ser exclusivo do fuzz de ambiente explícito. Com a linha de base em `0a51eef`, nenhum relaxamento é esperado, e os dois arquivos começam vazios.
4. **B4: entradas da rede**, avaliadas nas branches `dev`, `release/qa-1`, `main` e `feature/evaluation`:
   - todos os comandos do corpus (decodificados) e da bateria;
   - a tabela do Handoff 031;
   - uma gramática de sinais com semente fixa: atribuições `NOME=valor`, `-var k=v`, `--set k=v`, `--env`/`--environment`/`--stage`/`--profile`, `cd <caminho com prod|staging|dev> &&`, `export`, subshell `( … )`.
5. **AG1:** o subshell `( … )` é avaliado com o mesmo contexto de `cd` por dentro. O contexto **não vaza** para fora dos parênteses, como no shell.
6. **AG2:** `cd` para um destino não resolvível (`$VAR`, `~usuário` inexistente, `-`) resulta em contexto **production** para os subcomandos seguintes (Invariante 7, a mesma regra do PR-00 para alvo não resolvível).
   - **Custo aceito:** `cd "$DIR" && npm test` segue allow, porque não é destrutivo.
   - `cd "$DIR" && git reset --hard` = deny.

### Critérios de aceite do PR-07c

- [ ] Num clone com `ENV_KEY_SEGMENTS = set()`, a rede **de matriz** reprova e nomeia `terraform destroy -var env=production`. A saída está colada na evidência.
- [ ] Não resta nenhum teste que confira constantes em vez de exercitar código.
- [ ] As linhas AG1/AG2 estão verdes no `test_environment_tokens.py`, e as tabelas dos Handoffs 030/031 seguem verdes.
- [ ] Os dois diferenciais contra `0a51eef` registram 0 relaxamentos. Protocolo 7.1. O plano não é editado pelo agente.

## 3. Onda 1

A parte de **segurança** da Onda 1 (G1–G6) está entregue e verificada de forma independente. A Onda 1 **fecha formalmente** com o PR-07c, porque a Onda 2 (PR-08/09/10) mexe em push e em hook. Sem uma rede de detecção que funcione, uma regressão de ambiente nessa fase passaria despercebida.
