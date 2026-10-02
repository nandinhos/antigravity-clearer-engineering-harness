# Handoff 091 — Revisão do PR #9 (infraestrutura: D4 + D3 + docs D2/D6 + H2)

**Data/Hora:** 2026-10-02T00:30:00Z
**Instância:** Revisor independente (Claude)
**PR revisado:** [#9](https://github.com/nandinhos/antigravity-clearer-engineering-harness/pull/9), `feature/infra-d4-d3` → `dev`, cabeça `c8d6105` (sobre `08af4e9`)
**Antecessor:** [Handoff 090](./handoff-090-deliberacao-conselho-sandbox-vs-ide-e-despachos.md)
**Estado:** **AJUSTES NECESSÁRIOS.** CB1–CB4 precisam de correção antes do merge; CB5–CB10 podem entrar no mesmo push.

---

## 1. Verificação independente (`OBSERVED`, worktree limpo de `c8d6105`)

| Item | Resultado |
|---|---|
| CI do PR | [run 36941060014](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36941060014) (`pull_request`) e [run 36941053877](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36941053877) (`push`): os 4 `Validate`, `Claude Code Environment Parity` e `ci-ok` = success |
| Suíte canônica **com o ambiente real desta sessão do Claude Code** (cerca de 55 variáveis `CLAUDE*`) | **76/76**, exit 0 |
| `snapshot_gate.py --check` | 1.024 decisões idênticas: o casefold não mudou nenhuma decisão do corpus atual |
| `ceh-doctor.sh --self-check` sob `dash` (POSIX estrito) | SUCESSO |
| Extrator do Conselho aplicado aos pareceres reais da sessão `20261001_090830` | claude, codex, muse, hermes e agy = RESSALVAS; agent = INDEFINIDO (5/5, como o Handoff 090) |

### O que está correto

- **Casefold restrito**, aplicado só ao basename do executável em `lexer.resolve_command_head`, `git_invocation`, `find`, `interpreters` e `rm`. Os argumentos ficaram intactos.
- **CA4 corrigido.** No repositório real, sem certificado, comparando o gate da `dev` com o do PR:

  | Comando | `dev` | PR #9 |
  |---|---|---|
  | `git push origin dev` | deny | deny |
  | `GIT push origin dev` | **allow** | deny |
  | `Git push origin dev` | **allow** | deny |
  | `/usr/bin/GIT push origin dev` | **allow** | deny |
  | `GIT -C . push origin dev` | **allow** | deny |

  No repositório temporário em `dev`, também passaram a ser negados `RM -rf $HOME`, `PYTHON3 -c "…rm -rf /…"` e `FIND . -delete` (em produção).
- **`ci-ok` bem montado:** `if: always()` com a checagem explícita de `needs.*.result`. Um job pulado não passa como sucesso.
- **Evidência da D1** (`d1-ruleset-main-evidence.md`) coerente:
  - `bypass_actors: []` e `current_user_can_bypass: never`;
  - 0 aprovações, os 4 `Validate`, `non_fast_forward` e `deletion`;
  - push direto recusado com `GH013` em `refs/heads/main`.

  A evidência chegou por PR, o que fecha a ressalva BK2. **CA3/AY2 encerrados.**
- **Extrator do Conselho:** remove os espaços finais (era o que derrubava o voto do Codex), descarta as linhas de modelo e normaliza o `HOMOLOGADO COM RESSALVAS`. O `--trust` foi aplicado ao `agent`.

## 2. Achados

### CB1 — `ceh-doctor --verify` não compara o conjunto de arquivos e ignora o caminho do hook — MÉDIA

A verificação usa uma **lista fixa** mais `ceh_core/*.py` e `adapters/*.py`. Ficam de fora:
- o `scripts/hook_context.py`, que o `safety-gate.py` importa no caminho do hook;
- o `hooks.json`, que é a própria configuração do hook;
- `evidence_report.py`, `doc-audit.py` e outros.

Arquivos **extras** na instalação também não são detectados. O Handoff 090 (D4, item 4) pedia comparar o **conjunto**.

Teste (`OBSERVED`), em uma cópia instalada falsa com `CEH_PLUGIN_DIR`:
- linha acrescentada ao `hook_context.py`;
- arquivo `scripts/extra_hook.py` criado.

Resultado:
```
  • Total de arquivos verificados: 35
✔ Verificação: SUCESSO (todos os 35 arquivos conferem byte-a-byte)
```

Esse é justamente o cenário do incidente 6 (instalação divergente).

**Correção:**
- derivar a lista da árvore de origem (`plugin.json`, `hooks.json`, `scripts/`, `rules/`, `profiles/`, `config/`, sem `__pycache__`);
- comparar nos **dois sentidos** (ausentes e extras) e depois o hash;
- teste de mutação: alterar `hook_context.py`, alterar `hooks.json` e criar um arquivo extra; cada um tem que reprovar.

### CB2 — `--verify` aborta sem relatório quando falta um arquivo do `ceh_core` — MÉDIA

No laço de `ceh_core` e `adapters`, `_tgt_hash=$(calc_sha256 …)` herda o `return 1` de `calc_sha256` quando o arquivo não existe, e o `set -e` encerra o script.

Teste (`OBSERVED`): com `scripts/ceh_core/engine.py` removido da cópia instalada, a saída é só o cabeçalho e `exit=1`, sem dizer qual arquivo falta. A lista fixa testa `[ ! -f ]` antes; o laço não testa.

**Correção:** testar a existência antes do hash, reportar "Ausente no instalado" e incluir o caso no teste de mutação do CB1.

### CB3 — O casefold não está pinado: nenhum teste e nenhum caso no corpus — MÉDIA

Não há comando com maiúsculas no `gate_corpus.txt`, nem nos testes. O Handoff 090 pedia "casefold restrito com controles no corpus".

Mutação (`OBSERVED`, worktree separado): com os 5 `.lower()` revertidos, a suíte passa 76/76 (seção 3). Com o corpus atual, o `snapshot_gate.py --check` não tem como notar a reversão, porque nenhum caso do corpus muda.

**Correção:**
- acrescentar ao corpus as variantes `GIT push origin dev`, `Git push origin dev`, `/usr/bin/GIT push origin dev`, `GIT -C . push origin dev`, `RM -rf $HOME`, `FIND . -delete` e `PYTHON3 -c "import os; os.system('rm -rf /')"`;
- acrescentar também um controle de que os argumentos não mudam: `git checkout -B main` em produção continua deny e `git -C sub status` continua allow;
- regenerar o `gate_corpus.expected.jsonl`, com o diff restrito às linhas novas e listado no PR.

### CB4 — `docs/gate-normalization.md` descreve como vigente o que só vem na v2.1.1 — MÉDIA (documentação)

O §4 ("operadores monitorados `>`, `>>`, `>|`, `&>`, `N>`… unidos ao alvo ou separados por espaço") e o §2.2, item 2 (`.CEH`), descrevem a correção do **CA1**, que ainda não existe. Gate do PR, repositório em `dev` (`OBSERVED`):

| Comando | Decisão |
|---|---|
| `echo x >.ceh/a` | **allow** |
| `printf x >.ceh/config.json` | **allow** |
| `echo x 1>.ceh/a` | **allow** |
| `echo x &>.ceh/a` | **allow** |
| `echo x >.CEH/a` | **allow** |
| `cp`, `mv`, `dd of=`, `install`, `ln -s` para `.ceh/config.json`; `echo x > a/../.ceh/config.json` | deny |

A descrição do PR também diz que o casefold foi aplicado "ao componente `.ceh` em alvos de escrita". O que já negava `.CEH` com espaço era comportamento anterior, não deste PR.

**Correção:** marcar o §4 e o §2.2, item 2, como "alvo da v2.1.1 (CA1)", ou separar "vigente" de "planejado", e corrigir a descrição do PR.

### Ressalvas baixas (podem ir no mesmo push)

**CB5 — Matriz D2 (`docs/adapters/novo-host.md` §6)**

A matriz marca `OBSERVED` como se fosse status, não onde a verificação pode valer:
- `ceh-doctor --verify` aparece como `OBSERVED` no sandbox e no CI, mas nenhum dos dois tem instalação, e o CI nem roda `--verify`;
- o bloqueio real aparece como `OBSERVED` na IDE-macOS, onde nunca foi observado;
- o **agy CLI headless** aparece como `N/A` no bloqueio real, e foi exatamente por essa linha que o Conselho pediu a coluna (código de saída diferente da IDE).

Troque a legenda para "verificável aqui / não verificável aqui". Nos papéis (§7), faltam a coluna "não pode" do Handoff 089, §D6, e a distinção entre gerar o certificado pelo `test-runner.sh` (autorizado) e editar o `.ceh/` à mão (proibido).

**CB6 — Job `claude-env`**

O job usa 3 variáveis escolhidas à mão, mais `USER`. A descrição do PR diz "capturadas de sessão real". Os nomes reais desta sessão (sem os valores, que podem conter credenciais) estão no apêndice A. Use os nomes com valores fictícios, no mínimo os que começam por `CLAUDE_CODE_` e `CLAUDE_PROJECT_DIR`. A paridade com o ambiente completo ficou observada nesta revisão (76/76), mas o CI deve reproduzi-la.

**CB7 — Extrator do Conselho**

`[[ "$verd" == *"RESSALVA"* ]]` transforma `REJEITADO COM RESSALVAS` em `RESSALVAS`, apagando uma rejeição. Teste `REJEITADO` primeiro.

**CB8 — Helper de diretório temporário**

O `mkdtemp_resolved` não é usado por nenhum teste. A D4, item 2, pedia o uso no lugar do `tempfile.mkdtemp()`. Adote-o pelo menos nos testes que comparam caminhos (o incidente 5).

**CB9 — Teste de independência de ambiente**

O teste novo chama `engine.evaluate()`, que nunca consulta a detecção de host, então não pode falhar pelo motivo que pretende cobrir. O caso relevante já existe (`test_antigravity_detect_independent_of_claude_env`). Faça o teste novo passar por `evaluate_hook_payload` com payloads do Antigravity e do Muse, com as variáveis do apêndice A presentes, e compare a decisão e o formato da resposta com o ambiente limpo.

**CB10 — `--evidence`**

- Só imprime o hash do gate instalado; não compara com o da tag.
- O BK1 pega as 3 últimas linhas da transcrição mais recente, não os passos da chamada e da resposta do canário. Aceite os índices como argumento.
- A saída inclui `hostname` e caminhos com `$HOME`. Se o pacote for versionado em `docs/`, o `doc-audit` reprova; mascare-os.

**Observação (sem ação obrigatória):** o ruleset permite `squash` e `rebase`. O histórico do projeto usa merge commit (a linha de base aponta para o commit de merge). Restringir a `merge` evita divergência.

## 3. Mutação do casefold

Worktree separado de `c8d6105`, com o diff do PR em `ceh_core/` revertido por `git apply -R` e commitado localmente (sem push):

| | Gate original do PR | Mutante (sem os 5 `.lower()`) |
|---|---|---|
| `GIT push origin dev` | deny | **allow** |
| `run-all-tests.sh` | 76/76 | **76/76, exit 0** |

**O mutante sobrevive.** A suíte inteira passa sem a correção do CA4, o que confirma o CB3.

## 4. Próximos passos

1. O agente corrige CB1–CB4 (e, de preferência, CB5–CB10) no próprio PR #9.
2. Nova revisão.
3. Merge na `dev` e na `main` (já sob o ruleset).
4. O desenvolvedor troca o check obrigatório para `ci-ok`, com a consulta autenticada (despacho 3 do Handoff 090).
5. Depois disso, o PR `v2.1.1` (CA1 + CA2).

## Apêndice A — Nomes das variáveis `CLAUDE*` desta sessão (sem valores)

```
CLAUDECODE CLAUDE_ADDITIONAL_DIRECTORIES CLAUDE_AFTER_LAST_COMPACT CLAUDE_AUTOCOMPACT_PCT_OVERRIDE
CLAUDE_AUTO_BACKGROUND_TASKS CLAUDE_CODE_ACCOUNT_UUID CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD
CLAUDE_CODE_BASE_REF CLAUDE_CODE_CHILD_SESSION CLAUDE_CODE_CONTAINER_ID CLAUDE_CODE_DEBUG
CLAUDE_CODE_DIAGNOSTICS_FILE CLAUDE_CODE_DISABLE_BACKGROUND_TASKS CLAUDE_CODE_ENTRYPOINT
CLAUDE_CODE_ENVIRONMENT_RUNNER_VERSION CLAUDE_CODE_EXECPATH CLAUDE_CODE_MESSAGING_SOCKET
CLAUDE_CODE_ORGANIZATION_UUID CLAUDE_CODE_REMOTE CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE
CLAUDE_CODE_REMOTE_SESSION_ID CLAUDE_CODE_SESSION_ID CLAUDE_CODE_VERSION CLAUDE_EFFORT CLAUDE_PID
```

Lista parcial dos 55 nomes, sem os que só configuram a interface. Não copie valores: alguns, como os de token e de socket, são credenciais da sessão. Acrescente `CLAUDE_PROJECT_DIR`, que o Claude Code CLI local define e que esteve no incidente 3.
