# Handoff 092 — PR #9, segunda rodada (correções CB1–CB10)

**Data/Hora:** 2026-10-02T03:00:00Z
**Instância:** Revisor independente (Claude)
**PR revisado:** [#9](https://github.com/nandinhos/antigravity-clearer-engineering-harness/pull/9), cabeça `21df5fa` (sobre `c8d6105`)
**Antecessor:** [Handoff 091](./handoff-091-revisao-pr9-infraestrutura.md)
**Estado:** **AJUSTE PEQUENO ANTES DO MERGE.** Falta só o CB11 (o `--verify` reprova uma instalação limpa) e o teste versionado do `--verify`. CB12–CB16 podem ir no mesmo push.

---

## 1. Verificação independente (`OBSERVED`, worktree limpo de `21df5fa`)

| Item | Resultado |
|---|---|
| CI | [run 36952685963](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36952685963) e [run 36952682452](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36952682452): os 4 `Validate`, a paridade Claude e o `ci-ok` = success |
| Suíte canônica com o ambiente real desta sessão do Claude Code | **76/76**, exit 0 |
| `onda4_baseline.py --check` | 5/5 (A1–A4 e A3-muse) |
| Corpus | 1.024 → 1.051 avaliações; as 1.024 da `dev` preservadas como prefixo |

### Situação de cada achado

| Achado | Situação | Como foi conferido |
|---|---|---|
| **CB1** | **parcial** (ver CB11) | Numa instalação real (`install.sh` em HOME temporário, como o A2), as quatro adulterações agora reprovam com mensagem e exit 1: `hook_context.py` alterado, `hooks.json` com `"enabled": false`, `ceh_core/engine.py` removido e `scripts/extra_hook.py` criado |
| **CB2** | resolvido | `engine.py` ausente → "✖ Ausente no instalado: scripts/ceh_core/engine.py" e o relatório completo |
| **CB3** | resolvido em 4 de 5 pontos (ver CB13) | Mutação com os 5 `.lower()` revertidos: `snapshot_gate.py --check` diverge e `test_git_canonicalization.py` falha. Revertendo cada um isoladamente, são mortos os de `find`, `git_invocation`, `interpreters` e `rm`; **o do `lexer` sobrevive** |
| **CB4** | resolvido | O `gate-normalization.md` separa "vigente" de "planejado (v2.1.1 / CA1)" |
| **CB5** | resolvido, com ressalva (CB15) | Legenda "verificável / não verificável"; papéis com a coluna "não pode" |
| **CB6** | resolvido | Job `claude-env` com os nomes do apêndice A, valores fictícios e `CLAUDE_PROJECT_DIR` |
| **CB7** | resolvido | `REJEITADO COM RESSALVAS` → `REJEITADO`, com teste em `test_conselho_extraction.py` |
| **CB8** | resolvido | `mkdtemp_resolved` adotado em 6 arquivos de teste |
| **CB9** | resolvido | O teste passa por `evaluate_hook_payload` com payloads do Antigravity e do Muse, compara a resposta inteira, e o ambiente tem as variáveis do apêndice A |
| **CB10** | resolvido, com ressalva (CB16) | Hash do instalado comparado ao de referência; `--step-call` e `--step-resp`; hostname e `$HOME` mascarados |

## 2. Achados novos

### CB11 — `--verify` reprova uma instalação limpa e oficial — MÉDIA (bloqueia)

Teste (`OBSERVED`): `install.sh` do próprio PR num HOME temporário, sem nenhuma adulteração, e depois `ceh-doctor.sh --verify <repo>`:

```
  ✖ Ausente no instalado: tools/package.py
  ✖ Arquivo não autorizado / estranho na instalação: evals/CRITERIA.md
  ✖ Arquivo não autorizado / estranho na instalação: evals/run.sh
  • Total de arquivos verificados: 70
✖ Verificação: FALHA (3 arquivo(s) com divergência)
```

**Por que acontece:** a referência é a árvore `clearer-engineering/` do repositório, mas o `install.sh` instala o **pacote** gerado pelo `tools/package.py`, que não leva o `tools/`, e copia o `evals/` da raiz do repositório.

**Por que importa:** na máquina real, o resultado é sempre FALHA. A diferença entre "limpa" e "adulterada" fica só na contagem (3 contra 4), e a evidência da IDE (D3) nunca sai limpa. O teste de mutação do agente usou uma cópia feita com `cp -a`, não o instalador; por isso não pegou o problema.

**Correção:**
1. Gerar a referência do mesmo jeito que o `install.sh` gera: o pacote do `tools/package.py` num diretório temporário, mais o `evals/`. Alternativa: excluir `tools/` do lado da origem e incluir o `evals/` da raiz, com a lista de exceções escrita no script.
2. **Teste versionado na suíte** (o CB1 já pedia; o script de mutação do agente ficou fora do repositório):
   - instalar com o `install.sh` num HOME temporário;
   - exigir que o `--verify` dê SUCESSO na instalação limpa;
   - exigir FALHA, com a mensagem, para cada uma das quatro adulterações acima e para o arquivo extra do CB12.
3. Rodar esse teste no CI. Hoje o CI só roda `--self-check` e `--evidence`, então o `--verify` nunca foi executado lá.

### Ressalvas baixas (podem ir no mesmo push)

**CB12 — O filtro `! -path "*/tests*"` é largo demais.**

Ele esconde qualquer caminho que contenha `/tests`, e não só o diretório `tests/` da raiz. Teste (`OBSERVED`): `scripts/tests_evil.py` e `tests/conftest.py` criados na instalação, e o `--verify` não acusou nenhum dos dois. Ancore a exclusão em `"$_root/tests/*"` ou, melhor, compare o `tests/` também, porque ele é instalado.

**CB13 — O `.lower()` do `lexer.resolve_command_head` não está pinado.**

Com só ele revertido, a suíte e o snapshot passam. O caso que o distingue (`OBSERVED`):

| Comando | PR | Mutante |
|---|---|---|
| `Sudo GIT push origin dev` | deny | **allow** |

Acrescente ao corpus `Sudo GIT push origin dev` e `ENV GIT push origin dev`.

**CB14 — O retrato da Onda 4 foi regenerado inteiro.**

O commit rodou `onda4_baseline.py --generate`, o que reescreveu A1 e A2. Ele descartou à mão as mudanças que o mesmo `--generate` fez em `A3_muse_before` e `A4`. Conferido nesta revisão:

- **nada foi removido ou afrouxado:**
  - no A2a, só os hashes de `gate_corpus.expected.jsonl` e `gate_corpus.txt` mudaram;
  - os outros acréscimos (6 arquivos no A2a e 28 caminhos no A2b) só aumentam o que é verificado;
  - o A1 preserva as 1.024 linhas como prefixo.
- **mas a mudança não foi declarada no commit nem no PR.** O precedente do projeto é a atualização **pontual**: um hash por commit, como o `f07eb93` com o `plugin.json`, e os caminhos novos em `ONDA4_DECLARED_NEW_PATHS`.

Daqui em diante, não rode `--generate` sobre o retrato. Atualize só os hashes que a mudança exige e declare isso na mensagem do commit. Nesta rodada, basta registrar na descrição do PR.

**CB15 — Matriz e papéis (`docs/adapters/novo-host.md`).**

- A linha do bloqueio real marca a IDE-macOS como "não verificável aqui". Ela é verificável; só ainda não foi observada.
- No papel do agente faltam três restrições da D6, do Handoff 089: **não homologa, não edita o plano, não faz merge**. Nesta trilha, o agente editou o plano uma vez (`8a4898e`).

**CB16 — `--evidence`.**

A linha "Comparação com tag/workspace" compara com o `safety-gate.py` do checkout atual. Esse checkout só equivale à tag se estiver nela. Imprima o resultado de `git describe --exact-match` e escreva "workspace (não é tag)" quando não for.

## 3. Próximos passos

1. O agente corrige o CB11 com o teste versionado e, de preferência, CB12–CB16, no PR #9.
2. A revisão confere só esses pontos.
3. Merge na `dev` e na `main`.
4. O desenvolvedor troca o check obrigatório para `ci-ok`, com a consulta autenticada.
5. Depois, o PR `v2.1.1` (CA1 + CA2).
