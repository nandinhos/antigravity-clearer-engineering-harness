# Handoff 037 — PR-08b e PR-09 homologados com ressalvas de processo; despacho do PR-10 (G9)

**Data/Hora:** 2026-09-27T13:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `af9c357` (PR-08b), `2f898d7` (PR-09)
**Antecessor:** [Handoff 036](./handoff-036-revisao-pr08-despacho-pr08b-pr09.md)

---

## 1. Vereditos

### PR-08b: **HOMOLOGADO**

- **AJ1:** `test_pre_push_refspecs.py` está no `run-all-tests.sh` (56 testes). A checagem de teste órfão está no `doc-audit`. Mutação real: tirei `test_hook_context.py` do `run-all-tests.sh` e o `doc-audit` reprovou com `Testes órfãos detectados: ['test_hook_context.py']`.
- **AJ2:** `:main`, `+:main`, `--delete`, `--del` e `-d` = DEV allow / HML ask / PROD deny. `outro:main` segue deny.

### PR-09: **HOMOLOGADO**

Conferido via stdin real (`OBSERVED`):

| Situação | Resultado |
|---|---|
| payload vazio, só espaços, `{}`, `[]`, `nao-json`, `{"toolCall":{}}` | deny, **exit 2** |
| `run_command` sem comando ou só com espaços; `Bash` sem `command` ou com `command` vazio | deny, **exit 2** (Claude: `hookSpecificOutput`) |
| ferramenta desconhecida (`view_file`) | deny, exit 2 (fail-closed, pronto para o PR-10) |
| `run_command` com `git status` | allow / exit 0 (agy) |
| `Bash` com `git status` | `{}` / exit 0 (Claude: o F6 continua respeitado) |

O corpus mudou em 7 linhas `HOOK-*`, todas apertos. Os fixtures "agy" do corpus usam um formato **híbrido e sintético** (`tool_name` + `tool_input.CommandLine`), que o código antigo lia como Claude: `rm -rf /` nesse fixture saía `{}`, ou seja, allow. Agora sai deny.

**Linha de base avançada** para `2f898d7`.

## 2. Ressalvas de processo

| ID | Achado (`OBSERVED`) | Regra daqui em diante |
|---|---|---|
| **AK1** | **O commit intermediário `af9c357` estava vermelho.** O PR-08b mudou a decisão de `git push origin --delete feature/old`, mas o corpus só foi atualizado no commit do PR-09. Em `af9c357`, `snapshot_gate.py --check` reprova (exit 1). O certificado só cobre o HEAD, então os dois commits foram enviados com um deles vermelho no histórico. | **Um push por commit certificado.** Commit 1 → suíte → certificado → push; só então o commit 2. O Pre-Push CI Gate só certifica o HEAD e não vê commits intermediários. |
| **AK2** | **Relaxamento não nomeado.** `CMD-056-sta`: `--delete feature/old` em staging passou de **deny** para **ask**. A regra do AJ2 (que é minha) produz isso, mas as evidências dizem "0 relaxamentos". Os diferenciais não viram o caso porque o fixture do fuzz não tem CI. Só o corpus mostra. | Toda linha alterada no corpus vai para o `prXX-corpus-diff.md`, com o ID do achado e a direção (aperto ou relaxamento), como desde o PR-04. |
| **AK3** (baixo) | Os fixtures `HOOK:agy` do corpus não têm o formato **real** do agy (`toolCall.name` / `toolCall.args.CommandLine`, `OBSERVED` no Handoff 005). | Trocar pelos payloads gravados nos Handoffs 005/006, no PR-10. |

## 3. Despacho — PR-10 `feat(gate): proteger o certificado e registrar o modelo de ameaças` (G9)

**Estado atual (`OBSERVED`, DEV):** `echo x > .ceh/last-ci-run.json`, `cp /tmp/f.json .ceh/last-ci-run.json`, `tee .ceh/last-ci-run.json`, `sed -i s/FAIL/PASS/ .ceh/last-ci-run.json` e `python3 -c "open('.ceh/last-ci-run.json','w')…"` saem **allow**. Qualquer comando forja o certificado que libera o push.

1. **Terminal, fail-closed, por lista de leitura** (não por lista de escritas):
   - todo subcomando que **mencione** `.ceh/last-ci-run.json`, `.ceh/last-ci-run.log` ou `.ceh/last-evals-run.json` é **deny** em qualquer ambiente, **exceto** leituras puras: `cat`, `less`, `head`, `tail`, `jq` sem redirecionamento para o arquivo, `grep`, `ls`, `stat`, `wc` e `python3 -m json.tool` sem saída para o arquivo;
   - o `test-runner.sh` e o `evals/run.sh` continuam gravando os certificados **por dentro** do script. O gate só vê `bash …/test-runner.sh`, e isso segue permitido;
   - desembrulho e varredura (G5) já valem: `bash -c "echo x > .ceh/last-ci-run.json"` tem de ser pego.
2. **Ferramentas de escrita de arquivo:**
   - **Grave primeiro os payloads reais** com o `host_probe.py` no agy: `write_to_file` (`OBSERVED` no Handoff 005) e qualquer outra ferramenta de edição que o agy expuser. Registre como E11 nas evidências. No Claude, as ferramentas `Write`, `Edit`, `MultiEdit` e `NotebookEdit` saem da documentação vigente, validada com payload gravado se possível.
   - O matcher do `hooks.json` passa a incluir essas ferramentas, e o `TOOL_DISPATCH` do PR-09 ganha um avaliador de escrita: caminho-alvo que resolve para `.ceh/` do repositório alvo → **deny**; os demais seguem o fluxo normal.
   - **Pergunta que precisa de observação, não suposição (E11):** no agy, responder `{"decision":"allow"}` para `write_to_file` **pula** a confirmação do próprio host, como acontece no Claude (F6)? Se pular, o allow de escrita no agy passa a ser `{}` (ou o equivalente observado). Grave os dois casos.
3. **ADR 007** (`docs/architecture/`): o gate é **defesa em profundidade, não sandbox**. A garantia real vem de branch protection com status check obrigatório no servidor; documente a configuração recomendada. **Decisão Ponytail:** o `tree_hash` e o `runner_version` do plano original **não** entram. O `commit_hash` já determina a árvore, e um certificado forjado pode trazer qualquer versão. A proteção útil é impedir a escrita (itens 1–2) e exigir o CI do servidor (ADR).
4. **AK3:** fixtures `HOOK:agy` do corpus com o formato real (`toolCall`), incluindo um `write_to_file` para `.ceh/last-ci-run.json` (deny) e outro para um arquivo comum.
5. **Testes:**
   - `tests/test_cert_protection.py`, registrado no `run-all-tests.sh`: as 5 escritas acima = deny, as leituras = allow, `bash -c` / `sh -c` / `eval` com escrita = deny, e os payloads de escrita (agy e Claude) para `.ceh/` = deny e para `app/x.php` = fluxo normal;
   - **falsificabilidade:** tire `tee` da lógica num clone (ou a checagem inteira, conforme o desenho) e mostre o teste reprovando.

### Critérios de aceite do PR-10

- [ ] Os comandos de escrita no certificado ficam deny em todos os ambientes; as leituras ficam allow.
- [ ] Payloads reais de escrita gravados (E11), com a resposta de allow definida por observação.
- [ ] ADR 007 publicado.
- [ ] `pr10-corpus-diff.md` com **cada** linha alterada do corpus (AK2).
- [ ] **Um push por commit certificado** (AK1). As duas redes diferenciais contra `2f898d7` registram 0 relaxamentos. Protocolo 7.1. O plano não é editado pelo agente.

## 4. Sequência

PR-10 → Onda 3 (PR-11 instalador honesto, PR-12 SemVer/CHANGELOG) → **tag v1.3.0**.
