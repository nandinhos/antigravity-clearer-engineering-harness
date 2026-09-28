# Handoff 051 — PR-QA-B homologado; PR-QA-D pendente; despacho do PR-QA-D2

- **Data/Hora:** 2026-09-28T14:25:32Z
- **Instância:** Revisor sênior independente do CEH
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **HEAD revisado:** `7999273f42755a97d862d6348478a45d0a1832f4`
- **Base diferencial do PR-QA-D:** `c247c79`
**Risco da revisão:** MÉDIO — revisão de mecanismo de teste que controla uma fronteira arquitetural de segurança; nenhuma mudança de runtime feita nesta revisão.

## 1. Veredito

- **PR-QA-B: HOMOLOGADO.** O teste de invariante avalia corpus e bateria, e os testes de mutação internos cobrem motivos incoerentes para `deny`, `allow`, `ask` e `use_case`. A execução focalizada passou 6/6; a suíte geral passou 62/62. O CI remoto 36422792664 terminou `success`, com 4/4 jobs verdes.
- **PR-QA-D: NÃO HOMOLOGADO (D01, médio).** A centralização em `ceh_core/normalize.py`, a comparação comportamental e o CI estão documentados e passam. Porém, o teste estrutural não aplica a exceção de `shlex.split` à ocorrência justificada: libera qualquer ocorrência em todo `rules.py`.
- **PR-20: RETIDO.** A sequência do Handoff 050 só autoriza avançar de B+D para PR-20 quando ambos satisfizerem os critérios. O despacho imediato é PR-QA-D2; PR-20 só começa após sua homologação.

## 2. D01 — exceção estrutural ampla demais

**OBSERVED — código:** `clearer-engineering/tests/test_normalization_structural.py:41-43` registra a exceção por nome de arquivo (`"rules.py"`). Em `:115-125`, qualquer ocorrência de `shlex.split` em um arquivo listado em `SHLEX_EXCEPTIONS` é aceita. A justificativa descreve uma única captura de `ValueError` na função de proteção de certificado. Atualmente há uma chamada autorizada em `clearer-engineering/scripts/ceh_core/rules.py:173`.

**OBSERVED — falsificação reproduzida em clone temporário:** copiei `clearer-engineering/` para um diretório temporário, acrescentei ao final de `rules.py` uma chamada adicional `extra_tokens = shlex.split("git status")` e executei `python3 clearer-engineering/tests/test_normalization_structural.py`. Resultado: exit code `0`, quatro testes aprovados. A mutação adiciona uma segunda normalização/tokenização fora do módulo canônico sem ser detectada.

**Critério não atendido:** Handoff 050, item “Teste estrutural”, permite lista de exceções justificada. O comportamento observado da lista é uma exceção de arquivo inteiro, não restrita à chamada ou contexto justificado. O relatório do PR-QA-D descreve falsificações para `normalize_custom_branch` e `normpath`, mas elas não testam o escopo desta exceção.

**Impacto:** regressões futuras podem adicionar `shlex.split` em `rules.py` e passar pela barreira estrutural, voltando a permitir divergência entre tokenização dos analisadores e o módulo canônico.

## 3. Evidência independente dos critérios restantes

- **OBSERVED:** `test_reason_invariant.py` — 6/6; `test_normalization_structural.py` no HEAD original — 4/4; `test_help_contract.py` — 5/5.
- **OBSERVED:** `bash clearer-engineering/tests/run-all-tests.sh` — 62/62, exit code 0; snapshot dourado, fuzz diferencial e environment differential passaram como parte da suíte.
- **OBSERVED:** `bash evals/run.sh` — 5/5 critérios, veredito `APROVA`.
- **OBSERVED:** CI 36422792664 (PR-QA-B) e CI 36428018017 (PR-QA-D) concluídos `success`, cada um com 4/4 jobs verdes nas matrizes Ubuntu/macOS e Python 3.9/3.12.
- **OBSERVED:** `gate_baseline.txt` contém `c247c79`; a suíte de snapshot/diferencial passou. Não há evidência observada de mudança de decisão em relação a essa base.
- **OBSERVED:** `evidence-report.sh --strict` retornou exit 0 e `VERIFICADO` no HEAD limpo com certificado para `7999273`. A conclusão de homologação deste handoff é separada: a prova concreta de D01 reprova um critério do PR-QA-D, ainda que suíte, CI e relatório estrito estejam verdes.
- **INFERRED:** PR-20 precisa aguardar D2, pois a dependência explícita do Handoff 050 é a conclusão conjunta de PR-QA-B e PR-QA-D.
- **UNKNOWN:** se a exceção de tokenização será modelada por local AST, por função/call-site ou por outra forma precisa. O implementador deve escolher a menor forma que restrinja apenas a captura autorizada e seja testável.

## 4. Despacho — PR-QA-D2

1. Restringir `SHLEX_EXCEPTIONS` à ocorrência/contexto autorizado de `rules.py` em `is_cert_tampering`; não aceitar por nome de arquivo inteiro.
2. Atualizar o teste estrutural para identificar a ocorrência autorizada por contexto AST ou contrato igualmente específico. Evitar depender apenas do número de linha.
3. Incluir prova por mutação em clone: uma segunda chamada de `shlex.split` no mesmo `rules.py` deve fazer o teste estrutural falhar, citando arquivo e linha. Manter também provas para `normalize_*` e `normpath`.
4. Não alterar decisões de runtime nem a linha de base `c247c79`. Confirmar snapshot, fuzz diferencial e environment differential sem diferença; qualquer mudança exige revisão separada e justificativa por linha.
5. Manter AX2 e os critérios de PR-QA-B verdes. Atualizar a evidência com os resultados brutos da mutação e os links de CI.
6. Executar a sequência do protocolo 7.1: suíte via `test-runner.sh`, evals, `evidence-report.sh --strict`; checagem do gate para push em passo separado, exigindo `decision == allow`, antes de qualquer push.
7. **Não iniciar PR-20** até a revisão independente homologar D2. Após D2 homologado, PR-20 pode tratar o índice de ADRs e as promessas verificáveis, conforme o despacho anterior.

## 5. Estado de continuidade

- Branch revisada estava limpa e sincronizada com `origin` em `7999273`.
- Nesta revisão, não foi alterado código do gate nem baseline de comportamento. Este handoff e a seção 0.50 do plano registram a decisão de revisão.
- **OBSERVED — publicação bloqueada:** após `safety-gate.py --check` retornar `decision: allow`, duas tentativas de `git push` foram negadas pelo hook PreToolUse, que informou certificado ausente/inválido e prescreveu `bash profiles/ceh/scripts/test-runner.sh <argv>`. O arquivo prescrito não existe neste checkout. O `.ceh/config.json` local aponta para `bash clearer-engineering/tests/run-all-tests.sh`; os certificados locais emitidos pelo `test-runner.sh` do projeto marcaram PASS para os respectivos HEADs testados. Nenhuma tentativa de contornar o bloqueio foi feita. O commit do Handoff 051 permanece local, um commit à frente de `origin`.
- **UNKNOWN:** causa da divergência entre o gate de domínio, que autorizou a decisão, e o hook PreToolUse, que não reconheceu o certificado local.
- A `main` ainda não contém o conteúdo desta branch; preservar o aviso de fluxo do Handoff 050.
