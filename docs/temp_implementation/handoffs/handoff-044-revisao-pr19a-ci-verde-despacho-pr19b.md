# Handoff 044 — PR-19a homologado: **CI do servidor verde em 4/4**; release v1.3.0 desbloqueada; despacho do PR-19b

**Data/Hora:** 2026-09-27T20:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `4f5c935`, `ddddf57`, `1bb0bf6`, `00d8dd6` (PR-19a)
**Antecessor:** [Handoff 043](./handoff-043-revisao-pr19-ci-vermelho-despacho-pr19a.md)

---

## 1. Veredito: **HOMOLOGADO**

**Servidor** (`OBSERVED` via API do GitHub Actions, [run 36331068859](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36331068859), `head_sha` `00d8dd6`):

| Job | Conclusão | Suíte canônica | E2E |
|---|---|---|---|
| ubuntu / 3.9 (108652959052) | **success** | 1 min 15 s | 1 min 16 s |
| ubuntu / 3.12 (108652959060) | **success** | 1 min 3 s | 1 min 4 s |
| macos / 3.9 (108652959042) | **success** | 8 min 13 s | 7 min 55 s |
| macos / 3.12 (108652958977) | **success** | 7 min 58 s | 5 min 44 s |

- Os passos 1–21 estão **success** nos 4 jobs, incluindo "Verify Apple Legacy Bash 3.2 Behavior" nos 2 jobs de macOS.
- A execução do código (`1bb0bf6`, [run 36329793650](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36329793650)) também é **success**.
- As iterações vermelhas (`4f5c935` e `ddddf57`, runs 56–57) estão no histórico, como o Handoff 043 permitia.

**Conferido no diff:**

- **AQ1:** a variável está do lado do `bash`. O `cmp` compara `profiles/clearer-harness.agent.md`, um arquivo que **não existe** na `main`, então só passa se a árvore veio do commit. A execução vermelha 36326581624 é o controle negativo.
- **AQ2:** `/bin/bash` 3.2 **antes** do Homebrew:
  - `bash -n` no install e no uninstall;
  - `cat install.sh | /bin/bash` e `/bin/bash install.sh` saem com exit ≠ 0 **e** com a mensagem `Bash 4.0+ is required`, conferida por `grep -F` (e não só pelo exit).
- **Python 3.9:** `cluster1_acceptance.py` usava `X | None` (PEP 604) sem `from __future__ import annotations`. **A suíte estava quebrada no piso 3.9**, e nenhum CI de servidor tinha rodado para mostrar isso.
- **`chmod +x` só em `*.sh`:** evita sujar a árvore com mudanças de modo, o que reprovaria os evals por "worktree sujo". O `evals/run.sh` agora mostra **quais** arquivos estão sujos.

### O caso do E2E (`run-e2e-simulation.sh`): a troca para `--check` é legítima

O E2E mandava o payload do hook **sem `Cwd`** e esperava que o `CEH_ENV` definisse o ambiente. Reproduzido:

```
hook sem Cwd, CEH_ENV=development, git reset --hard -> rc=2 deny
  "Ambiente detectado: PRODUCTION (Evidência: Explicit parameter (--env production))"
hook com Cwd num repositório em feature/x -> allow (DEV PERMITTED)
```

- Isso é o **fail-closed de projeto** (`hook_context.py:27`: `Cwd` ausente ou inexistente = produção), somado ao exit 2 do PR-09.
- O E2E estava **desatualizado desde então**, e ninguém viu porque ele só roda no CI, que nunca rodava nesta branch.
- Testar os níveis por `--check --env` está certo. No agy, o `ask` vira `deny` (PR-00c), então o nível `ask` só é observável pelo `--check`.
- O caminho real do hook com `Cwd` continua coberto em `test_hook_context.py` (18 testes: main→deny, dev→allow, staging no agy→deny).
- O `|| true` **não** esconde divergência: a decisão continua sendo comparada, e o `log_error` sai com exit 1.

**Linha de base avançada** para `00d8dd6`.

## 2. Ressalvas baixas

- **AR1:** a função do E2E ainda se chama `test_safety_hook`, mas não testa mais o hook. Renomeie para `test_gate_check` **ou** acrescente uma chamada pelo caminho do hook com `Cwd` num repositório-fixture do sandbox, conferindo decisão **e** exit code (2 para deny, 0 para allow).
- **AR2 (evidência):** a tabela do relatório de entrega aponta jobs `1086524941xx`, que não pertencem à execução 36331068859 (os jobs dela são `1086529590xx`). Os links de evidência precisam ser os da execução citada.
- **AR3 (desempenho, informativo):** no macOS, a suíte canônica leva cerca de 8 min, contra cerca de 1 min no Ubuntu. Não bloqueia. Se crescer, investigue (provavelmente `git init`/subprocessos por caso no runner do macOS).
- **AR4 (processo, recorrente):** o commit `00d8dd6` se chama "registrar **homologação** 100% verde". O agente registra a **evidência**. A homologação é da revisão (Handoffs 038 e 043).
- **Shellcheck:** a evidência dá "26 avisos", sem a divisão por código SC tirada do artefato do servidor que o Handoff 043 §3.4 pedia. Isso fica para o PR-19b, que precisa dela como ponto de partida.

## 3. Release v1.3.0: **desbloqueada** (decisão e execução do desenvolvedor)

Agora existe o **primeiro sinal de servidor** para as Ondas 0–3, **mais** o PR-19/19a. O roteiro do [Handoff 042 §3](./handoff-042-encerramento-onda-3-release-despacho-pr19.md) vale, com um ajuste de conteúdo:

- a v1.3.0 passa a incluir o PR-19/19a (CI na branch, matriz macOS e bash ≥ 4), que hoje está em `[Unreleased]` no CHANGELOG. **Antes da tag**, mova esse bloco para a seção `[1.3.0]`, ou deixe-o como `[1.3.1]`. Decisão do desenvolvedor;
- no PR para `main`, o CI roda de novo pelo gatilho `pull_request`. Configure a branch protection exigindo os **4 jobs** `Validate (…)`.

## 4. Despacho — PR-19b `chore(shell): limpeza do shellcheck e shellcheck bloqueante`

1. **Linha de base do servidor:** baixe o artefato `shellcheck-report-ubuntu-latest-py3.12` da execução do seu commit inicial e registre a contagem **por código SC** e **por arquivo** na evidência.
2. **Limpeza:**
   - corrija os avisos um a um. Para cada código, a correção é **semântica**, não só cosmética: `SC2086`, por exemplo, pede aspas, e cada aspa nova é conferida contra o comportamento esperado (arquivos com espaço no nome);
   - `# shellcheck disable=SCxxxx` só com **justificativa na mesma linha** e no máximo por ocorrência, nunca por arquivo.
3. **Bloqueante:** tire o `continue-on-error` e o `|| true` do passo do shellcheck. Qualquer aviso novo reprova o CI.
4. **Carona permitida** (mesmos arquivos, correções pequenas):
   - AR1;
   - AP1: o install remove de novo o cabeçalho legado `# === CLEARER Engineering Harness (CEH) ===`, pelo `rc_aliases.py`;
   - AP2: `pattern.sub(lambda _: block, content)`;
   - AP3: a linha vaga do CHANGELOG.
5. **Testes:** a suíte e o install-verification seguem verdes. Para o AP1: um rc com o cabeçalho legado sai do install sem ele, e o uninstall continua simétrico.
6. **Falsificabilidade:** num commit temporário (ou num `workflow_dispatch` num ref de teste), introduza um `echo $VAR_SEM_ASPAS` num `.sh` e mostre o passo do shellcheck **reprovando no servidor**. Cite o link.
7. **Evidência (AQ3):** só depois da execução do servidor no commit final, com os links dos **4 jobs dessa execução** (AR2).

### Critérios de aceite do PR-19b

- [ ] O shellcheck está **bloqueante** e verde, com a linha de base por código e por arquivo tirada do artefato do servidor.
- [ ] Cada `disable` tem justificativa na linha.
- [ ] O controle negativo do shellcheck reprova no servidor, com link.
- [ ] AR1, AP1, AP2 e AP3 resolvidos, com teste para o AP1.
- [ ] O CI do servidor está verde nos 4 jobs no commit final, com links corretos.
- [ ] As redes diferenciais contra `00d8dd6` registram 0 relaxamentos. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 5. Sequência

Release v1.3.0 (desenvolvedor, em paralelo) ∥ PR-19b → PR-18 (validação de esquema + fuzz do lexer) → PR-QA B–D e AM2 → PR-20/21 → Onda 4 quando houver evidência de um 3º host.
