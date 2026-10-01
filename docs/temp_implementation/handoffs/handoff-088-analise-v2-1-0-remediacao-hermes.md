# Handoff 088 — Análise da versão atual (v2.1.0, remediação da auditoria Hermes)

**Data/Hora:** 2026-10-01T12:00:00Z
**Instância:** Revisor independente (Claude)
**Escopo:** só o estado atual da `main` (`08af4e9`), a pedido do desenvolvedor. Tag `v2.1.0` → `63dbe5c` (merge do PR #7); `08af4e9` acrescenta só documentação (PR #8).
**Origem das mudanças:** remediação F01–F16 guiada pelo Codex e pelo Hermes, com a ata do Conselho em `docs/temp_implementation/conselho/20261001_auditoria_hermes/`.

---

## 1. Verificação independente (`OBSERVED`, worktree limpo da `main`)

| Item | Resultado |
|---|---|
| Suíte canônica (sem variáveis do Claude) | **76/76** |
| `onda4_baseline.py --check` | A1–A4 e A3-muse conferem |
| `snapshot_gate.py --check` | 1.024 idênticas |
| CI da `main` | [run 36819868443](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36819868443) (`08af4e9`) e [run 36817505897](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36817505897) (`63dbe5c`, tag) = success |
| `plugin.json` | 2.1.0 |

### Correções do gate, testadas desta revisão com os exemplos "RED" do plano

| Achado | Caso | Resultado |
|---|---|---|
| F02 | `env APP_ENV=production bash -c 'php artisan migrate:fresh'` (repo `dev`) | deny `DATABASE` ✅ (sem o `APP_ENV`: allow) |
| F03 | `/usr/bin/git push origin dev`, `./git push origin dev` | deny `PRE_PUSH_CI` ✅ |
| F04 | `git reset HEAD --hard`, `git push -vf origin main`, `+main`, `--force-with-lease` (repo `main`) | deny `GIT_HISTORY` ✅ |
| F10 | `rm -rf customer.db`, `rm -R logs.old` (repo `main`) | deny ✅; `rm -f customer.db` continua `FILESYSTEM_SAFE` ✅ |
| F01 | `cat f>.ceh/last-ci-run.json`, `bash -c 'echo' > .ceh/cert`, `tee .ceh/last-ci-run.json` | deny ✅ |
| F01 (certificado) | `1>`, `2>`, `&>`, `>|`, colado ou com espaço, para `last-ci-run.json`/`.log` | deny ✅ |

As mudanças do `test-runner.sh` (F06–F08) estão coerentes com o plano:
- troca de comando revoga o selo canônico;
- `pytest` ausente aborta em vez de cair para `unittest`;
- `HEAD` e worktree são revalidados depois da execução, antes de emitir o certificado.

Os testes dedicados estão no `test_hermes_remediation.py`, dentro da suíte.

**A v2.1.0 está sólida.** Nenhuma regressão encontrada.

## 2. Achados

### CA1 — F01 incompleto: escrita em outros arquivos do `.ceh/` — MÉDIA (já existia na v2.0.0)

| Comando (repo `dev`) | v2.0.0 | v2.1.0 |
|---|---|---|
| `echo x >.ceh/a` | allow | **allow** |
| `printf x >.ceh/config.json` | allow | **allow** |
| `echo x 1>.ceh/a`, `echo x &>.ceh/a` | allow | **allow** |
| `echo x>.ceh/x.json` | allow | **allow** |
| `echo x > .ceh/a` (com espaço) | deny | deny |

- O plano (A1.6) diz "menção a `.ceh/` e `>` fora de aspas → G9", mas a implementação só cobre os nomes do certificado e a forma com espaço.
- **Por que importa:** o `.ceh/config.json` define o `canonical_test_command`. Quando ele **não** está versionado, o `test-runner.sh` lê o arquivo local (linhas 57–58). Um agente pode reescrevê-lo com um redirecionamento colado e obter um certificado "canônico" de um comando trivial.
- **Correção sugerida:** identificar o **alvo** de qualquer redirecionamento (com ou sem descritor, colado ou não) e negar se ele resolver para dentro de `.ceh/`, com controles na bateria para cada forma da tabela.

### CA2 — Os apertos F01–F10 não estão no corpus — MÉDIA

- O `snapshot_gate.py` continua com as mesmas 1.024 decisões: **nenhum** dos casos novos entrou no `gate_corpus`.
- Hoje só o `test_hermes_remediation.py` protege essas correções. As redes diferenciais e o A1 não as enxergam.
- Acrescente os casos "RED" (e os controles negativos) ao corpus, com o diff linha a linha, como no PR-22.
- Avance também o `gate_baseline.txt`, que na `main` ainda está em `e608ea7` (v1.4.1).

### CA3 — Proteção da `main` (Fase D) não comprovada — MÉDIA (processo)

- A evidência `ceh-review-branch-protection.json` traz **401 "Requires authentication"** em todas as consultas: a proteção não foi verificada.
- Confirme em **Settings → Rules** (ruleset na `main` exigindo PR e os 4 jobs `Validate`) e registre uma consulta autenticada, ou um print da regra.

### Ressalvas baixas

- **CA4:** `GIT push origin dev` (maiúsculas) dá allow. Em sistema de arquivos sem distinção de maiúsculas (padrão do macOS), isso executa o `git`. Avalie comparar o nome sem distinção de caixa no Darwin, ou registre como limite.
- **CA5:** `cat .ceh/last-ci-run.json > /tmp/copia` dá deny (falso positivo de leitura; já era assim na v2.0.0). É aceitável por ser fail-closed, mas registre como limite conhecido.
- **CA6:** há **8** caminhos `/Users/<nome>` em `docs/audit/…/evidencias/` (`.py` e `.json`). O `doc-audit` não varre `docs/audit/`. Amplie o escopo e mascare.
- **CA7:** na ata do Conselho, a linha do `codex` ficou com os campos-modelo não preenchidos (`[HOMOLOGADO | RESSALVAS | REJEITADO]`, `[número …]`): a extração do veredito falhou. O plano cita "Plenária 6/6", mas a ata registra **1/4** votos de homologação e "HOMOLOGADO COM RESSALVAS". O parecer do Claude, na própria ata, diz que os testes "RED" não foram reproduzidos e que as Fases C e D estavam só no plano. Vale alinhar o cabeçalho do plano ao que a ata registra.
- **CA8:** o CHANGELOG da `v2.1.0` foi consolidado depois da tag (`8f9f663`), então o CHANGELOG da tag é diferente do da `main`. Sem impacto funcional.

## 3. Prioridade sugerida (Ponytail)

1. **CA1** (pequeno e de segurança) + **CA2** (pinar no corpus), no mesmo PR, com o `gate_baseline` avançado.
2. **CA3**: só configuração no GitHub.
3. CA4–CA8 como carona.
