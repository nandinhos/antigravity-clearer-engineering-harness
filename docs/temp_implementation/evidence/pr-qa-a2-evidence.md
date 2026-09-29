# Evidência Técnica do PR-QA-A2: Gramática Completa, Fuzz Hermético, Y4 Justificado e Certificado de Evals

## 1. Resumo Executivo

O **PR-QA-A2** conclui a elevação do harness de QA diferencial e da política de evidências do Safety Gate, conforme o Handoff 023:

1. **Y1 (Gramática Completa)**: A gramática determinística com semente fixa (`random.Random(42)`) cobre todas as dimensões exigidas:
   - Abreviações de opções longas (`--forc`, `--discard`, `--work`, `--pathspec-from`, `--stage`, `--sourc`, `--force-c`);
   - `checkout -B`, `switch --force-create`, `--pathspec-from-file`, `--pathspec-file-nul`;
   - `$VAR` e `${VAR}` sem aspas e `~/x` como pathspec do git;
   - `find` com `-delete` catastrófico (`/`, `~`, `/etc`, `..`) e seguro;
   - One-liners de interpretador (`python3 -c`, `node -e`, `perl -e`, `ruby -e`, `sh -c`, `bash -c`) inócuos e destrutivos.
   - **Prova de Falsificabilidade**: Comprovado que a gramática SOZINHA (sem corpus e sem bateria) reprova com 232 relaxamentos ao reintroduzir o W2 (igualdade estrita em vez de prefixo em opções longas).
2. **Y2 (Remoção do TimeoutError)**: Removida a asserção por tempo de parede de `setUpClass`. O tempo de preparação e avaliação é impresso como meta de telemetria (`2.23s`, muito abaixo de 20s).
3. **Y3 (Hermeticidade)**: A avaliação da baseline (`7f87ce3`) e do gate atual ocorre em workers isolados com o mesmo repositório temporário (`git init -q -b dev`) e o mesmo `HOME` descartável.
4. **Y4 (Correção do Falso Positivo e Relaxamento Justificado)**:
   - Corrigido `ceh_core/git.py` para avaliar `':app/x'` via `_is_broad_subpath(p[idx:])` (retornando `allow`);
   - Desmarcado `PENDENTE:` na linha 264 de `review_batteries.txt` (`production|allow|H023-Y4|git checkout -- ':app/x'`);
   - Registrado o relaxamento justificado em `tests/fixtures/relaxamentos_justificados.txt`:
     - `production|git checkout -- ':app/x'|deny->allow|H023-Y4`
     - `staging|git checkout -- ':app/x'|ask->allow|H023-Y4`
   - **Prova de Reprovação**: Comprovado que a remoção dessa linha de justificativa faz o fuzz reprovar imediatamente com exit code 1 nomeando `git checkout -- ':app/x'`.
5. **Y5 (Certificado de Evals e Recusa Estrita no Relatório de Evidências)**:
   - `evals/run.sh` grava `.ceh/last-evals-run.json` com `{commit, verdict, passed, total, timestamp}`;
   - `evidence_report.py` lê o certificado e projeta os evals em `## TESTS` como `OBSERVED` (ou `[DESATUALIZADO]` se o commit divergir do HEAD);
   - Sob `--strict`, `evidence_report.py` recusa compulsoriamente afirmações declaradas sobre o estado de execução da suíte ou dos evals;
   - Adicionados 3 novos testes contratuais em `tests/test_evidence_report.py` (13/13 PASS).

---

## 2. Prova 1: Falsificabilidade W2 Apenas com a Gramática (Y1)

Ao reintroduzir o defeito W2 (desativando correspondência por prefixo de opções longas) e avaliando **sem comandos do corpus e sem comandos da bateria**:

```text
[differential-fuzz] Preparação e avaliação (10500 casos) concluídas em 1.98s (meta < 20s)
SUCESSO: Teste reprovou APENAS com a gramática (sem bateria e sem corpus)!

--- MENSAGEM CAPTURADA ---

[REPROVADO - PR-QA-A] 232 relaxamento(s) NÃO autorizados detectados contra a linha de base 7f87ce3!
Para autorizar um relaxamento decorrente de correção homologada, adicione a(s) linha(s) abaixo em tests/fixtures/relaxamentos_justificados.txt com o respectivo ID do achado:

  staging|git --no-pager checkout --pathspec-from=list.txt HEAD~2 docs/**/*.md|ask->allow|<ID-DO-ACHADO>
  production|git --no-pager checkout --pathspec-from=list.txt HEAD~2 docs/**/*.md|deny->allow|<ID-DO-ACHADO>
  staging|git --no-pager restore --staged --work ./|ask->allow|<ID-DO-ACHADO>
  production|git --no-pager restore --staged --work ./|deny->allow|<ID-DO-ACHADO>
  ... e mais 212 relaxamento(s).
```

---

## 3. Prova 2: Reprovação Sem a Linha de Justificativa de Y4

Ao remover temporariamente a autorização de `H023-Y4` de `relaxamentos_justificados.txt`:

```text
[differential-fuzz] Preparação e avaliação (11691 casos) concluídas em 2.38s (meta < 20s)
FAIL: test_differential_fuzz_against_baseline (__main__.TestGateDifferentialFuzz.test_differential_fuzz_against_baseline)

AssertionError: 
[REPROVADO - PR-QA-A] 2 relaxamento(s) NÃO autorizados detectados contra a linha de base 7f87ce3!
Para autorizar um relaxamento decorrente de correção homologada, adicione a(s) linha(s) abaixo em tests/fixtures/relaxamentos_justificados.txt com o respectivo ID do achado:

  staging|git checkout -- ':app/x'|ask->allow|<ID-DO-ACHADO>
  production|git checkout -- ':app/x'|deny->allow|<ID-DO-ACHADO>
```

A autorização em `relaxamentos_justificados.txt` é estritamente necessária e validada pelo harness.
