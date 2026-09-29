# Handoff 047 — PR-18b homologado (T3 resolvido); despacho do PR-22 (cobertura de regras e falsos positivos em `.ceh`)

**Data/Hora:** 2026-09-27T23:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `62208b7`, `d6bf922` (PR-18b)
**Antecessor:** [Handoff 046](./handoff-046-revisao-pr19c-pr18-despacho-pr18b.md)

---

## 1. PR-18b: **HOMOLOGADO**

Reproduzido de forma independente (`OBSERVED`):

- **AT1:** `evidence/host-probe/agy/tools/` foi removido. O catálogo v1.1.0 foi conferido **pelo conteúdo** por um script da revisão, independente do teste do agente:
  - 4 `payload`, todos com a linha correspondente no `.jsonl`: `run_command` (E1-r1 agy), `write_to_file` (E11), `Bash` (E1-r1 Claude) e `Write` (E7-r1 Claude);
  - 1 `host_doc`: `Edit` aparece como nome de ferramenta nos exemplos de `--allowedTools` do `e0_help.txt`;
  - 18 `declared`, rotulados, com origem e motivo, e nenhum aponta para `host-probe/`.
  - **Mutação:** num clone, apontei o `Bash` para o `.jsonl` do E11, que existe mas não contém `Bash`. O `test_content_schema.py` reprova.
- **AT2:** a propriedade de ida e volta `split(join(segs)) == segs` (500 casos, semente 1337, separadores dentro de aspas, subshell) **reprova** com a mutação do `||` num clone. O invariante de decisão do gate foi renomeado com honestidade.
- **AT4:** os `prompt_*.txt` da ata `20260927_171054` foram limpos. O `doc-audit` cobre `.txt` nas atas. O `parecer_claude.md` registra a **ausência** de resposta, sem conteúdo inventado.
- **Servidor:** `62208b7` → [run 36353326429](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36353326429) = **success** (4/4). O gate não foi alterado. A suíte certificada está verde localmente.

**T3 resolvido:** os testes de conteúdo agora validam estrutura (frontmatter, catálogo, skills, links) em vez de procurar texto.

**Linha de base avançada** para `d6bf922`.

### Ressalvas baixas (carona no PR-21)

- **AU1:** o `doc-audit` só casa `/home/<u>/projects/…` (`doc-audit.py:186`). Ficou de fora `docs/temp_implementation/conselho/20260925_151613/parecer_claude.md:54` (`/home/<user>/.claude/plans/…`). Amplie para qualquer `/home/<u>/` ou `/Users/<u>/`.
- **AU2:** 18 das 23 ferramentas estão `declared`. O E12 (captura real) continua sendo o caminho para promovê-las a `payload`, sem urgência.
- **AU3:** a evidência trouxe o `git diff --stat` vazio, mas não o `git status --porcelain` pedido.
- **AU4:** a ausência do conselheiro devia ficar na **ata**. O arquivo de parecer bruto não deveria receber texto que não veio do conselheiro. No PR-21, o `conselho-seniores.sh` passa a registrar isso sozinho.

## 2. Despacho — PR-22 `feat(gate): cobertura de regras de dados e infraestrutura (AT3) e leituras de .ceh (AM2)`

**Primeiro PR da Onda 5 que altera o gate desde o PR-10b.** Valem todas as regras da Onda 1:
- corpus com `pr22-corpus-diff.md` linha a linha (AK2);
- relaxamentos só com justificativa nomeada;
- redes diferenciais contra `d6bf922`;
- um push por commit certificado;
- controles negativos só em `claude/negctl-*`.

**Estado atual (`OBSERVED`), já na bateria:**

| Grupo | Comando | Hoje (prod) | Esperado |
|---|---|---|---|
| AT3 | `git stash clear`, `git stash drop` | allow | GIT_HISTORY graduado: DEV allow / HML ask / PROD deny |
| AT3 | `docker volume rm …`, `docker volume prune`, `docker compose down -v` (e `--volumes`) | allow | DATABASE/INFRA graduado |
| AT3 | `redis-cli flushall`, `redis-cli -h db FLUSHDB` (sem distinção de caixa, com opções antes) | allow | DATABASE graduado |
| AT3 | `prisma migrate reset` | allow | DATABASE graduado |
| AT3 | `dd … of=<arquivo do repositório>` | allow | FILESYSTEM graduado; `of=/dev/sd*`/`nvme*` continua CATASTROPHIC |
| AM2 | `find . -path ./.ceh -prune …`, `tar … --exclude=.ceh .`, `du -sh .ceh`, `diff .ceh/… …`, `git status --ignored .ceh` | **deny** | **allow** |

1. **AT3:** regras novas em `ceh_core/rules.py` (ou no módulo do domínio), com o **mesmo mecanismo** das existentes. Nada de caso especial no `safety-gate.py`. Respeite o orçamento de linhas do `doc-audit`.
   - A decisão para `php artisan migrate --force` (hoje allow em produção) fica com vocês, com justificativa na evidência. O `--force` pula a confirmação de produção do próprio Laravel, mas `migrate` é uma ação normal de deploy.
2. **AM2:** **relaxamento consciente**, justificado:
   - `du`, `diff` e `git status|log|diff|show` (sem redirecionamento para `.ceh`) entram na lista de leitura da proteção do `.ceh`;
   - argumentos de exclusão (`--exclude=.ceh`, `--exclude .ceh`, `-path ./.ceh -prune`) **não** tornam o `.ceh` um alvo;
   - cada linha que passar de deny para allow vai para `relaxamentos_justificados.txt` como `env|cmd|deny->allow|H039-AM2`. As redes diferenciais **têm** de acusar esses relaxamentos, e **só** esses.
   - **Controles que continuam deny:** `tar xf evil.tar -C .ceh`, `rsync -a /tmp/fake/ .ceh/`, `cp -r … .ceh`, `diff … > .ceh/last-ci-run.json` e `find .ceh -delete`.
3. **Bateria:** as linhas `PENDENTE:H046-AT3`, `PENDENTE:H047-AT3` e `PENDENTE:H039-AM2` perdem o prefixo `PENDENTE:` **no mesmo commit**, e os controles seguem verdes.
4. **Testes** num `tests/test_rules_data_infra.py`, registrado na suíte (o `doc-audit` checa testes órfãos), com a graduação completa DEV/HML/PROD por comando, variações de caixa e de opções, e composição (`ls && redis-cli flushall`).
5. **Falsificabilidade:**
   - num clone, remova a regra do `redis-cli` e mostre o teste e a bateria reprovando;
   - num clone, restaure o deny do `du` na proteção do `.ceh` e mostre a linha AM2 reprovando.
6. **Evidência:**
   - `pr22-corpus-diff.md` com **cada** linha alterada do corpus, com ID e direção (aperto ou relaxamento);
   - a saída das redes diferenciais listando exatamente os relaxamentos AM2;
   - o CI do servidor verde (4/4) com os links dos jobs **dessa** execução;
   - `git status --porcelain` vazio (AU3).

### Critérios de aceite

- [ ] Nenhuma linha `PENDENTE:H046-AT3`, `PENDENTE:H047-AT3` ou `PENDENTE:H039-AM2` restante. Os controles estão verdes.
- [ ] Os relaxamentos são **exatamente** os AM2 justificados, e o resto do diferencial tem 0 relaxamentos.
- [ ] O corpus diff está linha a linha. Há prova por mutação para AT3 e AM2.
- [ ] O CI do servidor está verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 3. Sequência

PR-22 → PR-QA B–D (invariante do motivo, contrato com `--help`, normalização única) → PR-20 (índice de ADRs e promessas verificáveis) → PR-21 (redação de segredos no Conselho + AU1/AU4) → Onda 4 quando houver evidência de um 3º host.

**Release v1.3.0:** continua com o desenvolvedor. Como o PR-22 muda o gate, faça a tag **antes** do merge do PR-22 (conteúdo já verde no servidor) **ou** depois dele verde. Não no meio.
