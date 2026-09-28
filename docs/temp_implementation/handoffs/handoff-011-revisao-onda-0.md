# Handoff 011 — Revisão da Onda 0 (PR-01 e PR-02) e despacho do PR-02b

**Data/Hora:** 2026-09-25T21:00:00Z
**Instância:** Revisor sênior (auditoria independente em container **sem `agy`**)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `0006c06..9264e6f`
**Antecessor:** [Handoff 010](./handoff-010-encerramento-p0-e-despacho-onda-0.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.10
**Decisão soberana:** do desenvolvedor (`nandodev`).

---

## 1. Veredito (espaço fechado)

| Entrega | Veredito | Base |
|---|---|---|
| **PR-01** (`ff5cad9`, suíte hermética) | **HOMOLOGADO** | Aqui, **sem `agy`**: 48/48, o mesmo total da máquina com `agy` (T1 resolvido). `run-install-verification.sh` passou (instalação, idempotência, desinstalação) **sem tocar o `HOME` real** (`~/.gemini` e `~/.bashrc` conferidos). `doc-audit` com contagem derivada; CI com 3.9/3.12 e `compileall`; e2e sem números fixos. |
| **PR-02** (`9264e6f`, corpus + RED) | **HOMOLOGADO COM RESSALVAS** (O1, O3) | Os 14 casos G1–G5 falham **pela razão certa**: rodados sem `@expectedFailure`, todos dão `AssertionError: 'allow' != 'deny'`, nenhum erro de infraestrutura. Mas o corpus não é hermético (O1) e o teste do G7 codifica o requisito errado (O3). |

## 2. Achados

- **O1 — MEDIUM — o corpus dourado depende do certificado real do repositório.** Os casos `git push` em `development` (`PRE_PUSH_CI`, CMD-043 a CMD-048…) são avaliados **dentro do repositório do CEH**, que tem CI, e por isso leem o `.ceh/last-ci-run.json` real. Reproduzido:

  | Estado do certificado do repositório | `snapshot_gate.py --check` |
  |---|---|
  | Canônico PASS no `HEAD` (logo após o protocolo de saída 7.1) | **FALHA** (as decisões viram `allow`) |
  | Sobrescrito por `test-runner.sh 'true'` (não canônico) | passa |
  | Ausente (CI, checkout novo) | passa |

  Dentro da suíte ele passa **por acoplamento de ordem**: os testes "Test Runner: Success/Failing scenario" rodam antes e sobrescrevem o certificado real (O2). Qualquer reordenação, ou a chamada avulsa documentada, quebra a rede de segurança que o PR-03 vai usar.
- **O2 — LOW (anterior à Onda 0) — a suíte altera o estado que ela certifica.** Os testes do `test-runner.sh` rodam no próprio repositório e gravam `.ceh/last-ci-run.json` no meio da execução. Via `test-runner.sh` a gravação final corrige; chamando `run-all-tests.sh` direto, fica um certificado não canônico e o próximo push é negado (direção segura, mas confusa).
- **O3 — MEDIUM (especificação) — o teste do G7 mede outra coisa.**
  - O G7 (plano, seção 3) é: *o pre-push valida só o `HEAD`, mas um refspec pode enviar **outro commit**, sem certificado*.
  - O teste envia `dev:main` com `dev == HEAD` certificado e exige `deny` por causa do destino. Esse push é legítimo pelo G7 (o commit enviado é o certificado).
  - Uma correção feita para esse teste bloquearia a promoção `dev → main` de um commit testado e deixaria o G7 real aberto.

## 3. Despacho — PR-02b `test(gate): corpus hermético e G7 correto` (antes do PR-03)

1. **O1:** `snapshot_gate.py` avalia os comandos dentro de um **repositório-fixture temporário**: `git init -b dev`, com `.github/workflows/ci.yml`, **sem** `.ceh/`. Nunca no repositório real. O snapshot esperado não muda, porque as decisões atuais equivalem a "sem certificado válido". Aceite: `--check` verde nos 3 estados da tabela O1.
2. **O2:** os testes do `test-runner.sh` em `run-all-tests.sh` (success/failing/runtime adapter) rodam num diretório temporário, como o caso "Runtime Adapter" já faz. Aceite: `git stash list` vazio, e o `.ceh/last-ci-run.json` real **com o mesmo sha256** antes e depois de `run-all-tests.sh`.
3. **O3:** reescrever o G7:
   - **RED** (`expectedFailure`): `HEAD` em `dev` certificado; branch `outro` com um commit **a mais, sem certificado**; `git push origin outro:main` → esperado `deny`.
   - **Controle (verde hoje, tem de continuar verde):** `git push origin dev:main` com `dev == HEAD` certificado → `allow`.
4. O corpus ganha as duas linhas do G7 (RED e controle) como casos de integração no snapshot.

Depois do PR-02b segue o **PR-03** (extração de módulos), com **diff vazio do corpus** como critério de aceite.

## 4. Critérios de aceite do PR-02b

- [ ] `snapshot_gate.py --check` verde com certificado PASS no `HEAD`, com certificado não canônico e sem certificado.
- [ ] `run-all-tests.sh` não altera o `.ceh/last-ci-run.json` real (sha256 antes = depois).
- [ ] G7: RED no caso "outro commit"; controle `dev:main` certificado = `allow`.
- [ ] Protocolo 7.1 completo, com `evidence-report.sh --strict` = VERIFICADO.
