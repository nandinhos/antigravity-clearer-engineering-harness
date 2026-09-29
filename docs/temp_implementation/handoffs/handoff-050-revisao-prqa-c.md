# Handoff 050 — PR-QA-C não homologado: contrato de opções sem vínculo executável

**Data:** 2026-09-28  
**Instância:** revisão independente  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commits revisados:** `40f097b`, `c247c79`  
**Baseline de revisão:** `d4bb909`  
**Antecessor:** [Handoff 049](./handoff-049-revisao-pr22b-despacho-prqa-c.md)

## 1. Veredito: **NÃO HOMOLOGADO**

O inventário e as proteções conhecidas estão presentes, mas o aceite central do PR-QA-C não foi atendido: o teste não verifica cada opção do contrato contra o gate nem valida que a citação existe no `--help` registrado.

### C01 — MÉDIO: `write_options.json` não dirige os testes

- **Evidência:** `clearer-engineering/tests/test_help_contract.py:38-70` verifica presença de comandos e existência dos arquivos de help. `:72-149` mantém listas de comandos e flags escritas manualmente; não itera pelas entradas de `write_options`.
- **Reprodução em clone temporário:** acrescentei `--invented-output` como opção de escrita ao contrato de `cat`, sem alterar o gate nem os testes. `python3 clearer-engineering/tests/test_help_contract.py` terminou com exit code 0, `Ran 5 tests`, `OK`.
- **Impacto:** um novo efeito de escrita pode ser documentado no JSON sem teste que comprove seu bloqueio. O contrato não protege contra a mesma classe de omissão que motivou o PR.
- **Precisão da fonte:** `clearer-engineering/config/write_options.json:147-150` atribui `--output-directory` ao help de `git diff`, mas `docs/temp_implementation/evidence/help-contracts/git-diff.txt` não contém essa opção; o snippet registrado é `--output=<file>`. A checagem de existência do arquivo não detecta essa divergência.
- **Correção mínima sugerida:** gerar os casos de gate a partir das opções registradas e validar cada linha/snippet contra o help versionado. Manter casos específicos para formatos de argumentos e aliases que precisem de expansão.

Não reproduzi um bypass de escrita nas opções conhecidas cobertas pelo teste. A falha é de cobertura do contrato e deixa regressões futuras sem detecção automática.

## 2. Verificações executadas

| Verificação | Resultado observado |
|---|---|
| Estado inicial | Branch `claude/code-review-technical-analysis-kfwcdl`, HEAD `c247c79`, worktree limpo |
| `bash clearer-engineering/tests/run-all-tests.sh` | exit 0; 60/60, 0 falhas |
| `bash evals/run.sh` | exit 0; 5/5 critérios, `APROVA` |
| `bash clearer-engineering/scripts/evidence-report.sh --base d4bb909 ... --strict` | exit 0; `VERIFICADO` |
| CI remoto, run `36371154717` | concluído `success`; 4/4 jobs verdes |
| Checagem separada do gate para `git push origin claude/code-review-technical-analysis-kfwcdl` | `decision: allow`, ambiente `development` |
| Push executado nesta revisão | não |

Uma primeira chamada ao relatório estrito foi recusada pelo próprio script porque os critérios declaravam diretamente estado de testes/evals; a chamada seguinte usou critérios documentais e concluiu `VERIFICADO`. A tentativa de falsificação foi isolada em diretório temporário e não alterou o checkout.

## 3. Próximo passo — PR-QA-C2

1. Fazer o teste percorrer todas as entradas `write_options` e exigir `deny/CERTIFICATE_INTEGRITY` para os alvos protegidos nos três ambientes.
2. Validar `help_line` e `help_snippet` contra o arquivo citado; corrigir ou remover `--output-directory` se a fonte não o documentar.
3. Repetir mutações em clone: remover a defesa de uma opção catalogada e corromper uma referência de help; cada mutação deve fazer o teste falhar.
4. Atualizar a baseline somente após nova revisão e zero relaxamentos não justificados.

**Auditoria:** `NEEDS_EVIDENCE` para o critério de vínculo completo inventário → teste → defesa; demais verificações registradas acima estão `SUPPORTED` pelas execuções observadas.
