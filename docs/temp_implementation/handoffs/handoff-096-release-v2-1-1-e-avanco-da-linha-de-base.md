# Handoff 096 — Release v2.1.1 conferida; patch de avanço da linha de base

**Data/Hora:** 2026-10-02T07:00:00Z
**Instância:** Revisor independente (Claude)
**Antecessor:** [Handoff 095](./handoff-095-pr11-v2-1-1-homologado.md)
**Estado:** release publicada e verificada. Há um achado médio de versionamento (CE1). O patch da linha de base está pronto para aplicar.

---

## 1. Verificação (`OBSERVED`)

| Item | Resultado |
|---|---|
| Merge do PR #11 na `dev` | `fd9faa8` (merge commit) |
| Merge do PR #12 na `main` | `4fe0523` (merge commit) |
| CI da `main` no merge | [run 36968970640](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36968970640) = success |
| Tag `v2.1.1` | tag anotada → `4fe0523` |
| Release no GitHub | `v2.1.1` publicada, não é rascunho |
| `clearer-engineering/scripts` em `fd9faa8`, `9c3c708` (homologado) e `v2.1.1` | **idênticos** |

O código da tag é exatamente o que foi homologado no Handoff 095.

## 2. Achados

### CE1 — A tag `v2.1.1` publica `plugin.json` com `"version": "2.1.0"` e não tem entrada 2.1.1 no CHANGELOG — MÉDIA (versionamento)

`git show v2.1.1:clearer-engineering/plugin.json` → `"version": "2.1.0"`. O primeiro título do `CHANGELOG.md` na tag é `## [2.1.0] - 2026-10-01`.

Quem instalar pela tag `v2.1.1` vê a versão 2.1.0. A descrição do PR #12 afirmava "CA2: atualização de versão canônica para 2.1.1 em `plugin.json` e manifestos", mas o CA2 era o corpus, e essa atualização não existe no diff.

**Opções (decisão do desenvolvedor, como operador do release):**

| Opção | O que fazer | Custo |
|---|---|---|
| **A (recomendada)** | Manter a tag `v2.1.1` como está, que é imutável, e acrescentar uma nota na release ("`plugin.json` reporta 2.1.0; corrigido na 2.1.2"). No próximo PR: `plugin.json` → `2.1.2`, CHANGELOG com as entradas `[2.1.1]` e `[2.1.2]`, e o hash do `plugin.json` atualizado no A2a. Depois, tag `v2.1.2` | uma versão a mais |
| B | Corrigir `plugin.json` e CHANGELOG por PR e recriar a tag e a release `v2.1.1` no novo merge | reescreve uma tag pública. A release tem poucas horas e provavelmente nenhum consumidor, mas isso quebra a regra de que a tag aponta para o commit homologado |

Para evitar que se repita: um teste que, quando o `HEAD` estiver numa tag `vX.Y.Z`, compare a tag com o `version` do `plugin.json`. Outra opção é pôr essa checagem no checklist do operador do release.

### CE2 — Canário da v2.1.1 na IDE: ainda não feito — pendência do desenvolvedor

O relatório traz `./install.sh` e `ceh-doctor.sh --verify` (131/131), executados **pelo agente**, dentro da sessão dele. A D3 e o Handoff 095 pedem outra coisa: o desenvolvedor, no próprio terminal, roda `ceh-doctor.sh --evidence --step-call <N> --step-resp <M>` e registra a resposta bruta da IDE a uma tentativa de escrita no `.ceh/`, como na E17. Uma forma colada do CA1, como `printf x >.ceh/canario`, mostra a correção nova.

### CE3 — Ruleset com `ci-ok`: afirmado, sem a saída bruta — BAIXA

O relatório diz que a consulta autenticada mostra `CI Aggregated Status (ci-ok)` como único check obrigatório, mas não traz a saída. Registre a saída bruta de `gh api repos/nandinhos/antigravity-clearer-engineering-harness/rulesets/24338451` num arquivo de evidência, por PR, como no D1.

Observação: até agora, o merge de cada PR foi feito pelo agente a pedido do desenvolvedor. A D6 reserva o merge ao operador do release. Se essa delegação for intencional, registre-a no guia.

## 3. Patch de avanço da linha de base

**Arquivo:** [`docs/temp_implementation/patches/0001-baseline-v2.1.1-fd9faa8.patch`](../patches/0001-baseline-v2.1.1-fd9faa8.patch)

| Mudança | Detalhe |
|---|---|
| `gate_baseline.txt` | `4a637fe` → **`fd9faa8`** |
| `relaxamentos_justificados.txt` | zerado; cabeçalho "Handoff 096: linha de base fd9faa8, v2.1.1" |
| `relaxamentos_deteccao.txt` | zerado; mesmo cabeçalho (resolve o CD3) |
| `A2_install_manifest.json` | só os 3 hashes desses arquivos no A2a (atualização pontual) |

**Por que `fd9faa8` e não a tag (`4fe0523`):** o código do gate é idêntico nos dois. O `fd9faa8` está na `dev` e na `main`; o `4fe0523` só existe na `main`, e o fuzz extrai o gate da linha de base com `git archive`.

**Validação nesta revisão** (worktree a partir de `origin/dev`, commit local, sem push):

| Verificação | Resultado |
|---|---|
| `onda4_baseline.py --check` | 5/5 |
| `test_gate_differential_fuzz.py` (listas vazias) | OK |
| `test_environment_differential.py` (listas vazias) | OK |
| `run-all-tests.sh` | **77/77** |
| `git am` do patch sobre `fd9faa8` num clone limpo | aplica sem conflito |

**Como aplicar** (na máquina do desenvolvedor ou pelo agente):

```
git fetch origin claude/code-review-technical-analysis-kfwcdl
git checkout -b chore/baseline-v2.1.1 origin/dev
git show origin/claude/code-review-technical-analysis-kfwcdl:docs/temp_implementation/patches/0001-baseline-v2.1.1-fd9faa8.patch | git am
git push -u origin chore/baseline-v2.1.1
```

Depois, abrir o PR para a `dev` e fazer o merge com o CI verde. O commit preserva a autoria da revisão.

## 4. Próximos passos

1. **Desenvolvedor:** decidir o CE1 (opção A ou B).
2. **Desenvolvedor:** canário da v2.1.1 na IDE (CE2) e saída bruta do ruleset (CE3).
3. **Agente ou desenvolvedor:** aplicar o patch da seção 3 por PR na `dev`.
4. **Agente:** PR de documentação com CA6–CA8, CD1 e CD2 e, se escolhida a opção A, o bump para 2.1.2.
