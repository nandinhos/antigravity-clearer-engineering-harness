# Handoff 095 — PR #11 (`v2.1.1`) **homologado**

**Data/Hora:** 2026-10-02T06:00:00Z
**Instância:** Revisor independente (Claude)
**PR revisado:** [#11](https://github.com/nandinhos/antigravity-clearer-engineering-harness/pull/11), cabeça `9c3c708` (`c48b55a` + `9c3c708` sobre `49ab3d0`)
**Antecessor:** [Handoff 094](./handoff-094-revisao-pr11-v2-1-1.md)
**Estado:** **HOMOLOGADO**, com três ressalvas baixas.

---

## 1. Verificação independente (`OBSERVED`, worktree limpo de `9c3c708`)

| Item | Resultado |
|---|---|
| CI | [run 36966149434](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36966149434) e [run 36966146782](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36966146782): os 4 `Validate`, a paridade Claude e o `ci-ok` = success |
| Suíte canônica com o ambiente real desta sessão do Claude Code | **77/77**, exit 0. O fuzz diferencial passa contra `4a637fe` |
| `onda4_baseline.py --check` | 5/5 |

### Situação de cada achado do Handoff 094

| Achado | Situação | Como foi conferido |
|---|---|---|
| **CC1** | resolvido | `echo {} > tsconfig.json`, `echo x > src/config.json` e `cat base.json > jsconfig.json` → allow. Payload do Antigravity com `write_to_file` em `tsconfig.json` e `src/config.json` → allow. Com `.ceh/config.json` → deny. `printf x >.ceh/config.json` → deny |
| **CC2** | resolvido | Com `link -> .ceh`: `echo x > link/a`, `echo x >link/a` e `write_to_file link/a` → deny. Com `link2 -> sub/../.ceh`: `echo x > link2/a` → deny. `rules.py` importa `Path`; o `except` ficou restrito a `(OSError, ValueError)` |
| **CC3** | resolvido | Corpus com `.ceh/a` (colado, com espaço, `&>`, `>>`, `2>`, `.CEH`, `sub/..`), `printf x >.ceh/config.json` e os controles `tsconfig.json` e `src/config.json`. Bateria com o caso de symlink |
| **CC4** | resolvido | `gate_baseline.txt` = `4a637fe`. As 6 linhas do CA5 estão em `relaxamentos_justificados.txt` e as 8 equivalentes, por branch, em `relaxamentos_deteccao.txt`: os mesmos 2 comandos nas 4 branches que o teste diferencial de ambiente avalia |
| **CC6** | resolvido | O ADR 007 registra o TOCTOU de symlink e a escrita por interpretador inline; o `gate-normalization.md` trata o CA1 como vigente |

### Mutações (worktree separado, sem push)

| Mutação | Resultado |
|---|---|
| Recolocar `"config.json"` na lista de substrings (CC1) | `test_hermes_remediation.py` e `snapshot_gate.py --check` falham: **morto** |
| Remover o `import Path` e voltar o `except Exception` (CC2) | `test_hermes_remediation.py` falha: **morto** |
| `ceh_core/` inteiro da `dev` (`4a637fe`), ou seja, sem o CA1 | snapshot falha (19 linhas `echo x…` divergem); as 3 baterias do CA1 falham, incluindo a de symlink: **morto** |

**Cobertura do CA1** no gate final, num repositório temporário:
- dão **deny**: todas as formas de escrita no `.ceh/` testadas no Handoff 094 e o redirecionamento via symlink;
- dão **allow**: os controles `2>&1`, `/tmp`, `.cehx/a`, `my.ceh.bak` e `tsconfig.json`.

## 2. Ressalvas baixas

- **CD1 — `cp` e `tee` não resolvem symlink.** Com um `link -> .ceh` que já exista, `cp f link/a` e `tee link/a` dão allow. A resolução só vale para redirecionamentos e para as ferramentas de escrita da IDE. O comportamento é o mesmo da v2.1.0, e criar o symlink (`ln -s .ceh …`) continua barrado. Basta registrar no ADR 007 ou aplicar a mesma resolução aos destinos de `cp`, `mv`, `tee`, `dd of=`, `install` e `ln`.
- **CD2 — Um loop de symlink derruba a avaliação.** Com `loop -> loop`, `echo x > loop/a` levanta `RuntimeError` no `Path.resolve()` (Python 3.11), que fica fora do `except (OSError, ValueError)`. O tratador global fecha corretamente nos três hosts (`OBSERVED`, ambiente limpo):

  | Host | Resposta |
  |---|---|
  | Antigravity | `{"decision":"deny"}`, exit 0 |
  | Muse | `{"decision":"block"}`, exit 0 |
  | Claude | `hookSpecificOutput`, exit 2 |

  Mas isso é bloqueio por exceção, não por regra. No `--check`, sai um traceback no lugar de JSON. Acrescente `RuntimeError` ao `except` e trate o caso como alvo protegido, com motivo explícito.
- **CD3 — Cabeçalho do `relaxamentos_deteccao.txt`.** Continua dizendo "linha de base e608ea7". Será corrigido quando a revisão zerar as listas, depois do merge.

## 3. Depois do merge

1. **Desenvolvedor:** merge do PR #11 na `dev` e, por PR, na `main`, com merge commit.
2. **Operador do release (desenvolvedor):**
   - tag `v2.1.1` no commit de merge da `main`;
   - release;
   - reinstalação pelo `install.sh` da tag;
   - canário na IDE, no próprio terminal, com o `ceh-doctor.sh --evidence --step-call <N> --step-resp <M>`. O registro deve conter o hash do gate e a resposta bruta da IDE para a tentativa de escrita no `.ceh/`.
3. **Revisão:** avançar o `gate_baseline.txt` para o commit de merge da `main`, zerar as duas listas de relaxamentos (com o cabeçalho atualizado) e atualizar os 3 hashes correspondentes no A2a, como no Handoff 086. Essa alteração vai num PR pequeno. Como esta revisão só faz push na própria branch, o patch exato será entregue no handoff seguinte.
4. **Pendente do Handoff 090:** confirmar a troca do check obrigatório para `ci-ok`, com a consulta autenticada do ruleset.
5. **PR de documentação:**
   - CA6: mascarar os caminhos de home em `docs/audit/` e estender o `doc-audit` a esse diretório;
   - CA7: alinhar o plano à ata do Conselho;
   - CA8: nota sobre o CHANGELOG da v2.1.0;
   - CD1 e CD2, se não entrarem no código.
