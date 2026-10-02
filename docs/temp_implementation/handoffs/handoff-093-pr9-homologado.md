# Handoff 093 — PR #9 (infraestrutura) **homologado**

**Data/Hora:** 2026-10-02T04:00:00Z
**Instância:** Revisor independente (Claude)
**PR revisado:** [#9](https://github.com/nandinhos/antigravity-clearer-engineering-harness/pull/9), cabeça `286a341` (sobre `21df5fa`)
**Antecessor:** [Handoff 092](./handoff-092-revisao-pr9-rodada-2.md)
**Estado:** **HOMOLOGADO**, com duas ressalvas baixas que podem ficar para o PR `v2.1.1`.

> Observação: o log colado nesta rodada era o da entrega anterior (`21df5fa`). A revisão foi feita sobre o commit novo encontrado na branch, `286a341`.

---

## 1. Verificação independente (`OBSERVED`, worktree limpo de `286a341`)

| Item | Resultado |
|---|---|
| CI | [run 36956135332](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36956135332) e [run 36956130602](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36956130602): os 4 `Validate`, a paridade Claude e o `ci-ok` = success. O CI agora roda o `--verify` sobre uma instalação real (Linux, macOS com bash 3.2 e o job do Claude) |
| Suíte canônica com o ambiente real desta sessão do Claude Code | **77/77**, exit 0 |
| `onda4_baseline.py --check` | 5/5 |

### Situação de cada achado do Handoff 092

| Achado | Situação | Como foi conferido |
|---|---|---|
| **CB11** | resolvido | `install.sh` num HOME temporário, sem alteração → `--verify` = **SUCESSO (131 arquivos)**, exit 0. A referência agora é o pacote do `tools/package.py` mais o `evals/`, igual ao instalador |
| **CB11 (teste)** | resolvido | `test_doctor_verify.py` (7 testes) entrou na suíte. Com o `ceh-doctor.sh` da rodada anterior no lugar, **3 dos 7 falham** (instalação limpa e os dois casos do CB12): o teste protege a correção |
| **CB12** | resolvido | `scripts/tests_evil.py` e `tests/conftest.py` acusados como estranhos, exit 1 |
| **CB13** | resolvido | `Sudo GIT push origin dev` e `ENV GIT push origin dev` no corpus. Com só o `.lower()` do `lexer` revertido, o snapshot diverge e o `test_git_canonicalization.py` falha. **Os 5 pontos do casefold estão pinados** |
| **CB14** | resolvido | O A2 recebeu só a troca dos 2 hashes do corpus; o `test_doctor_verify.py` foi declarado em `ONDA4_DECLARED_NEW_PATHS`; o retrato não foi regerado |
| **CB15** | resolvido | IDE-macOS marcada como "verificável (não observado)"; o papel do agente ganhou "não homologa", "não edita o plano" e "não faz merge" |
| **CB16** | resolvido | O `--evidence` usa `git describe --exact-match` e diz "tag oficial" ou "workspace local (não é tag oficial)" |

As adulterações do Handoff 092 continuam detectadas com mensagem e exit 1: `hook_context.py` alterado, `hooks.json` desligado e `ceh_core/engine.py` ausente.

A troca de "76/76" para "77/77" em `docs/plano-validacao-revisao-conselho-seniors.md` é exigida pelo `doc-audit` (contagem publicada da suíte). Não conta como edição de plano no sentido da D6.

## 2. Ressalvas baixas (podem ir no PR `v2.1.1`)

- **CB17 — O filtro `! -name ".git*"` é largo demais.** Ele esconde qualquer arquivo cujo nome comece por `.git`. Teste (`OBSERVED`): com `scripts/.gitevil.py` criado na instalação, o `--verify` dá SUCESSO. O risco prático é baixo, porque o hook não importa esse arquivo, mas a exclusão deveria cobrir só o diretório `.git/` e nomes exatos (`.gitignore`, `.gitkeep`).
- **CB18 — Queda silenciosa para a árvore crua.** Se o `tools/package.py` falhar, ou se o `python3` não existir, o `--verify` volta a comparar com a árvore `clearer-engineering/` sem avisar, e os falsos positivos do CB11 reaparecem. Imprima qual referência foi usada ("pacote" ou "árvore crua") e, no segundo caso, avise que o resultado não é conclusivo.

## 3. Estado da sequência (Handoff 090, §6)

| # | Despacho | Estado |
|---|---|---|
| 1 | D1 — ruleset na `main` | ✅ feito (Handoff 091) |
| 2 | PR de infraestrutura (#9) | ✅ **homologado** — falta o merge |
| 3 | Check obrigatório → `ci-ok` | pendente (desenvolvedor, depois do merge na `main`) |
| 4 | PR `v2.1.1` (CA1 + CA2) | próximo |
| 5 | PR de documentação (CA5–CA8) | depois |

## 4. Próximos passos

1. **Desenvolvedor:** merge do PR #9 na `dev` e, por PR, na `main`, usando merge commit, como é o histórico do projeto.
2. **Desenvolvedor:** no ruleset, trocar os 4 `Validate` pelo `ci-ok` e registrar a consulta autenticada (`gh api repos/<owner>/<repo>/rulesets/<id>`).
3. **Agente:** PR `v2.1.1` com o CA1 e o CA2 em três commits ordenados (Handoff 090, D5), o diff do corpus restrito aos apertos declarados e, se quiser, CB17 e CB18 juntos.
