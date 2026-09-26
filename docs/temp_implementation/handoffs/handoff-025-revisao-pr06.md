# Handoff 025 — Revisão do PR-06 (G5) e despacho do PR-06b

**Data/Hora:** 2026-09-26T09:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `e4515f9` (Z1/Z2), `607d4a0` (PR-06)
**Antecessor:** [Handoff 024](./handoff-024-revisao-prqa-a2-despacho-pr06.md)

---

## 1. Vereditos

| Entrega | Veredito | Base (`OBSERVED`) |
|---|---|---|
| **Z1/Z2** (`e4515f9`) | **HOMOLOGADO** | A regex tem fronteira de palavra (`evidence_report.py:118`), com 2 contratos novos; o `evals/run.sh` apaga o certificado antes de começar. |
| **PR-06** (`607d4a0`) | **NÃO HOMOLOGADO** | Uma regressão (AA1) e o aceite do G5 contornável por embrulho (AA2). |

O que o PR-06 acertou:

- os 15 `PENDENTE` do G5 ficaram verdes, e os 3 RED do G5 também (resta só o G7);
- nenhuma regex nova em `rules.py`;
- `find.py` (188 linhas) e `interpreters.py` (155 linhas) reaproveitam o `is_target_catastrophic`;
- as 15 decisões alteradas no corpus são **todas apertos** (`find /`, `find /var`, `-exec rm`, `shutil.rmtree("/srv")` e `os.remove("/etc/passwd")`).

**A linha de base não avança** (segue em `2820dad`).

## 2. Achados

### AA1 — ALTO (regressão): o analisador libera cedo e esconde o catastrófico

`evaluate_subcommand` chama `evaluate_find_command` **antes** de tudo e devolve o resultado dele. Em DEV, um `find` destrutivo sem caminho inicial catastrófico sai `allow` **sem passar pelas outras regras**. Diferencial contra `2820dad`:

| Comando (DEV) | `2820dad` | PR-06 |
|---|---|---|
| `find . -exec rm -rf / \;` | deny | **allow** |
| `find . -name x -exec rm -rf ~ \;` | deny | **allow** |
| `find build -delete -exec rm -rf / +` | deny | **allow** |

O fuzz não pegou porque a gramática só gera `-exec rm -rf {}`, nunca `-exec rm` com um alvo fixo. **A causa é de arquitetura: um analisador novo pode apertar, mas não pode encerrar a avaliação com `allow`.**

### AA2 — ALTO: embrulhos escondem o G5

| Comando | Decisão hoje |
|---|---|
| `bash -c "find / -delete"` | **allow em produção** |
| `sh -c "python3 -c \"…shutil.rmtree('/')\""` | allow |
| `python3 -c "import os; os.system('find / -delete')"` | allow |
| `python3 -c "…os.remove('x'); os.system('rm -rf /')"` | allow em DEV (antes também) |

Os analisadores novos só enxergam o comando de fora. O critério do G5 ("`find /` = CATASTROPHIC em qualquer ambiente") é contornado com um `bash -c`.

### AA3 — MÉDIO: detecção de interpretador incompleta (padrão 1 de novo: enumerar formas)

Todos saem allow em produção. Conferi no Python real que `-Bc` e `-cCÓDIGO` funcionam.

- **Flags agrupadas:** `python3 -Bc`, `-Ic`, `perl -le`, `-ne`, `node -pe`.
- **API chamada pelo nome, sem o módulo na frente:** `from shutil import rmtree; rmtree('/')`, `__import__('shutil').rmtree`, `require('node:fs')`, `const {rmSync}=require('fs')`.
- **Alvo passado como argumento depois do código:** `python3 -c '…rmtree(sys.argv[1])' /`.

### AA4 — processo

- **Corpus sem justificativa:** as 15 decisões alteradas não estão justificadas linha a linha num `pr06-corpus-diff.md` (regra desde o PR-04). Eram todas apertos, mas o registro é obrigatório.
- **Plano:** o agente escreveu no plano a seção 0.24 declarando o "Fechamento da Onda 1" antes da revisão. As seções de progresso registram o **resultado da revisão**; a 0.24 foi reescrita neste commit. O agente registra a entrega no arquivo de evidência, não no plano.

Todos os achados estão na bateria como `PENDENTE:H025-*` (**17 linhas**), com 7 controles, entre eles `bash -c "rm -rf /"` (já negado), `perl -le 'print 1'` e `cat s.py | python3`.

## 3. Despacho — PR-06b `fix(gate): analisadores só apertam, desembrulho recursivo e interpretadores completos`

1. **AA1: regra de composição.**
   - Um analisador (`find`, interpretadores e, daqui em diante, qualquer outro) devolve **uma severidade candidata**, nunca a decisão final.
   - A decisão final é a **mais severa** entre os analisadores e o restante do fluxo, nesta ordem: CATASTROPHIC > deny > ask > allow.
   - Em DEV, `allow` só sai quando **ninguém** pediu mais que isso.
   - Isso vale também para o `git.py`. Confira se ele tem o mesmo retorno antecipado; se tiver, aplique a mesma regra.
2. **AA1/AA2: desembrulho recursivo com o gate inteiro.** Nos três casos abaixo, avalie a string interna com o **`evaluate_command` completo** (recursão com profundidade máxima de 3; acima disso, fail-closed) e componha pela regra 1:
   - `sh|bash|zsh|dash -c <script>`;
   - o comando do `-exec/-execdir/-ok/-okdir` do `find`, com `{}` trocado por um nome relativo inócuo;
   - os literais passados a APIs que abrem shell: `os.system`, `subprocess.*`, `child_process.exec*/spawn*`, `system()` de Perl/Ruby e crases.
   - Assim, `find . -exec rm -rf {} /etc \;` passa pelo `rm.py` e sai CATASTROPHIC.
3. **AA3: interpretadores sem enumerar formas.**
   - **Flags agrupadas:** um token curto que contém a letra do código (`c` no Python; `e`/`E` no Perl e no Ruby; `e`/`p` no Node) indica que o código é o resto do token ou o próximo token, como faz o parser de cada interpretador.
   - **APIs pelo nome, sem exigir o módulo:** Python `rmtree|removedirs|unlink|rmdir|remove`; Node `rmSync|rmdirSync|unlinkSync|rm|rmdir|unlink|rimraf`; Perl `unlink|rmdir|rmtree|remove_tree`; Ruby `rm_rf|rm_r|rm|remove_dir|remove_entry|unlink|delete`.
     - Um nome ambíguo (`list.remove`, `hash.delete`) pode virar falso positivo em produção. Isso é **aceito e registrado** no PR, na direção fail-closed.
     - O controle `python3 -c "l=[1]; print(len(l))"` tem de seguir allow.
   - **Argumentos depois do código:** trate como literais; se algum for catastrófico, o resultado é CATASTROPHIC.
   - **Fora de escopo, documentado:** código vindo de arquivo ou do stdin (`python3 script.py`, `cat s.py | python3`, heredoc) equivale a rodar um script e segue allow. `curl … | bash` vai para o backlog como item próprio, sem relação com o G5.
4. **Gramática do fuzz e invariante de embrulho.**
   - Gere `-exec` com alvos fixos (`/`, `~`, `/etc`, `{} /etc`), flags agrupadas e APIs chamadas pelo nome.
   - **Invariante nova** no fuzz: para cada comando gerado `X`, a decisão de `bash -c "X"`, `sh -c 'X'` e `python3 -c "import os; os.system('X')"` tem de ser **pelo menos tão severa** quanto a de `X`.
   - **Falsificabilidade:** reintroduza o retorno antecipado do AA1 num clone. A invariante ou o diferencial tem de reprovar **só pela gramática**, com corpus e bateria vazios.

### Critérios de aceite do PR-06b

- [ ] As 17 linhas `PENDENTE:H025-*` ficam verdes, e todos os controles (H017–H025) seguem verdes.
- [ ] O diferencial contra `2820dad` registra **0 relaxamentos** e nenhuma linha nova em `relaxamentos_justificados.txt`.
- [ ] `pr06b-corpus-diff.md` justifica cada decisão alterada (e fica valendo também para o PR-06).
- [ ] A invariante de embrulho está no fuzz, com a prova de falsificabilidade do AA1 sem bateria.
- [ ] O plano **não** é editado pelo agente. Protocolo 7.1 e relatório `--strict`.

## 4. Sequência

PR-06b (fecha a Onda 1) → PR-QA B–E → Onda 2 (PR-08 G7, PR-09, PR-10). `curl | bash` entra no backlog do plano.
