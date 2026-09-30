# Handoff 083 — PR-17 **HOMOLOGADO** (conformidade entre hosts); despacho do **fechamento da Onda 4** (relatório final, PR para a `main`, v2.0.0)

**Data/Hora:** 2026-10-02T14:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — `4acff31` (PR-17), `67d80ea`; relatório do agente "Handoff 082"
**CI:** [run 36762701448](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36762701448) e [run 36763861586](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36763861586) = success (4/4)
**Antecessor:** [Handoff 081](./handoff-081-pr16-homologado-despacho-pr17-conformidade.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. Verificação independente (`OBSERVED`)

| Item | Resultado |
|---|---|
| `test_cross_host_conformance.py` | verde com e sem as variáveis do Claude; decisão e `use_case` iguais nos três hosts e no motor; `render` conforme a tabela do Handoff 081 |
| Fidelidade dos payloads sintéticos | conferida contra as chaves do `recorded.jsonl` de cada host (terminal e escrita) |
| Mutações (`test_mutation_p17.py`, em cópia temporária) | Muse ignorando `workdir`/`cwd` → reprova; Claude mapeando `ask` para allow → reprova |
| `onda4_baseline.py --check` | A1–A3 e A3-muse conferem; A4: 0 referências de host fora de `adapters/` (77 dentro), *shim* com 94 linhas, `cross_host_conformance_tests_count = 1` |
| Guia `docs/adapters/novo-host.md` | cobre IDE × CLI, reserva por host (E1c), isolamento de plugins pré-existentes (E15/E16) e confinamento dos comandos de bloqueio (BH1) |

### Conformidade pelo caminho de produção (desta revisão)

O teste do agente chama `parse → evaluate → render` em processo. O caminho de produção passa pelo *shim* e pelo `handle_hook_lifecycle`, que faz `os.chdir(req.cwd)` antes de avaliar. Para cobrir a diferença:

- rodei **145 comandos do corpus (1 a cada 7) × 3 hosts** pelo `safety-gate.py` em **subprocesso**, a partir de `/`, com repositórios `dev`, `staging` e `main` temporários;
- a distribuição das decisões do motor foi **87 allow, 38 deny e 20 ask**;
- resultado: **0 divergências** entre a resposta de cada host e a tabela esperada para a decisão do motor.

A amostra também confirmou 0 diferenças entre o motor atual e a decisão gravada no corpus.

**PR-17: HOMOLOGADO.**

### Ressalvas baixas (entram no commit do relatório final)

- **BJ1:** acrescente ao `test_cross_host_conformance.py` uma amostra **em subprocesso** pelo *shim* (por exemplo, 1 comando a cada 20 × 3 hosts), para que o caminho de produção fique coberto pela suíte, e não só pela revisão.
- **BJ2:** o corpus tem **1.014** entradas de comando, **2** de integração e **8** de hook. O teste troca as 8 de hook por `git status` e conta tudo como "1.024 avaliações". Tire as de hook (já cobertas pelo A3 e pelas fixtures) e informe os números reais: 1.016 × 3.
- **BJ3:** o `test_mutation_p16.py` (reserva do Muse) **não está** na suíte. Registre-o.
- **BJ4:** o `test_cross_host_conformance.py` e o `test_mutation_p17.py` foram encadeados com `&&` em linhas que já existiam. Assim, uma falha não diz qual teste caiu. Dê a cada um a própria linha `run_test` e atualize a contagem da suíte onde o `doc-audit` a confere.
- **BJ5:** o guia afirma que, na IDE, "a comunicação é mediada por pipes IPC e timeouts estritos". Isso não foi observado. Rotule como hipótese ou remova; o fato observado é só o comportamento dos códigos de saída (E13).

## 2. Despacho — fechamento da Onda 4

### Passo 1 — `docs(onda4): relatório final antes × depois` (em `feature/onda-4`)

`docs/temp_implementation/evidence/onda4-relatorio-final.md`, com números **medidos no próprio commit** (não copiados de relatórios anteriores):

| Medição | Antes (v1.4.0/v1.4.1) | Depois |
|---|---|---|
| A1 decisões | 1.024, `3878d3cc…` | idêntico |
| A3 respostas do hook (agy/Claude) | 93 + 14 | idênticas (só as 7 negações do agy de exit 2 para 0, na v1.4.1) |
| A3-muse | 41 × deny/2 (tudo bloqueado) | 41 × exit 0, conforme o motor |
| A4 formato de host fora de `adapters/` | 53 + 2 (v1.4.0) | 0 |
| Linhas do `safety-gate.py` | 630 | 94 |
| Testes de conformidade entre hosts | 0 | 1.016 comandos × 3 hosts + amostra em subprocesso |
| Hosts com adaptador e fixtures reais | 2 | 3 (Antigravity IDE/CLI, Claude Code, Muse) |
| Integrar um host novo | copiar o núcleo e escrever o adaptador | `detect`/`parse`/`render` + linha na reserva + fixtures + conformidade + manifesto (guia) |

Inclua também, com honestidade:

- **o que a Onda 4 achou fora do escopo:** o fail-open da IDE do Antigravity (v1.4.1) e o fail-open da reserva no Muse (E1c);
- **os limites que continuam** (ADR 007, seções 4 e 5);
- **os incidentes de processo:** o certificado reescrito no negctl (Handoff 066), a evidência montada da E14 (Handoffs 073/074) e o `rm -rf /` real enviado ao Muse (Handoff 077), com as regras que cada um gerou.

Aplique BJ1–BJ5 no mesmo commit.

### Passo 2 — preparar a release (mesma branch)

- `plugin.json` = **2.0.0**.
- `CHANGELOG [2.0.0]`:
  - **Changed (breaking):** API interna de integração (motor + adaptadores + despachante);
  - **Added:** adaptador do Muse, `package.py`, conformidade entre hosts, guia de novo host;
  - **Security:** reserva por host (o Muse não falha aberto quando um módulo do CEH quebra).
- README com a URL fixada em `v2.0.0`.

### Passo 3 — PR `feature/onda-4 → main`

- Abra o PR pela interface ou pelo `gh`, com os **4 jobs `Validate` verdes** no PR.
- A descrição traz o link do relatório final e deste handoff.
- Se houver conflito com a `main`, faça **merge** da `main` na branch (sem rebase) e rode o `--check` de novo.
- **Não** faça o merge: a revisão final (Claude ou Codex) confere o PR, e depois o **desenvolvedor** faz o merge e cria a tag **`v2.0.0`**.

### Critérios de aceite

- [ ] Relatório final com números medidos no commit, achados fora do escopo, limites e incidentes.
- [ ] BJ1–BJ5 resolvidas; suíte com uma linha por teste.
- [ ] `plugin.json`, CHANGELOG e README em 2.0.0.
- [ ] PR para a `main` com 4/4 verdes, sem merge pelo agente.
- [ ] O plano não é editado pelo agente, e a homologação não é declarada pelo agente.
