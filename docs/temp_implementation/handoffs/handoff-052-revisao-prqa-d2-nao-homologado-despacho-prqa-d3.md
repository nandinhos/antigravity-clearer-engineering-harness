# Handoff 052 — PR-QA-D2 não homologado por D02; despacho do PR-QA-D3

- **Data/Hora:** 2026-09-28T15:20:00Z
- **Instância:** Revisor sênior independente do CEH
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **Commit de implementação revisado:** `c433606`
- **Base de comportamento:** `c247c79`
- **Risco da revisão:** MÉDIO — teste estrutural que guarda o contrato arquitetural do ponto único de normalização/tokenização.

## 1. Veredito

- **D01: corrigido em PR-QA-D2.** A exceção de `shlex.split` está limitada à tupla `("rules.py", "is_cert_tampering")`, com teto de uma chamada; a exceção órfã também reprova.
- **PR-QA-D2: NÃO HOMOLOGADO por D02 (médio).** A nova varredura AST não reconhece aliases de import para `shlex.split`; a checagem de `normpath` continua textual e também não reconhece aliases.
- **PR-20: RETIDO.** A barreira de ponto único segue vulnerável a implementações convencionais fora de `normalize.py` que o teste não detecta. Corrigir D02 antes de avançar.
- **Despacho imediato:** PR-QA-D3 para tornar as duas verificações sensíveis aos aliases de import e falsificáveis.

## 2. D02 — aliases de import escapam do teste estrutural

**OBSERVED — implementação:** em `clearer-engineering/tests/test_normalization_structural.py:139-145`, `ShlexCallVisitor` reconhece apenas `shlex.split(...)` e o nome literal `shlex_split(...)`. Já `test_normpath_usage_restricted_to_normalize_py` procura o texto `os.path.normpath` ou `posixpath.normpath` linha por linha (`:102-109`). Nenhuma verificação associa símbolos importados às funções chamadas.

**OBSERVED — falsificação reproduzida em cópias temporárias da árvore `clearer-engineering/`:**

| Mutação | Resultado do `test_normalization_structural.py` |
|---|---|
| `from shlex import split as shell_lexer; shell_lexer("git status")` em `rules.py` | exit 0; 4 testes passaram — violação não detectada |
| `from os.path import normpath as path_normalizer; path_normalizer("a/../b")` em `find.py` | exit 0; 4 testes passaram — violação não detectada |

Essas mutações mostram que tokenização e normalização de caminho podem ser reintroduzidas fora de `normalize.py` por aliases usuais sem disparar a proteção estrutural.

## 3. Critérios de D01 reproduzidos

Reexecutei em clones temporários os quatro casos documentados em `prqa-d-evidence.md`; todos produziram exit code diferente de zero:

1. chamada extra no escopo de módulo de `rules.py`;
2. segunda chamada no escopo permitido `is_cert_tampering`;
3. nova função `normalize_custom_branch` em `git.py`;
4. chamada direta a `os.path.normpath` em `find.py`.

As mutações provam que D01 foi endereçado. Elas não cobrem os aliases que compõem D02.

## 4. Validação independente e CI

- **OBSERVED:** `bash clearer-engineering/scripts/test-runner.sh` — 62/62, `STATUS: PASS`, certificado vinculado a `c433606`.
- **OBSERVED:** `bash evals/run.sh` — 5/5 critérios, veredito `APROVA`.
- **OBSERVED:** Run [36440671039](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36440671039): jobs Ubuntu Python 3.9 e 3.12 concluídos com `success`; jobs macOS Python 3.9 e 3.12 ainda `in_progress` na consulta desta revisão.
- **OBSERVED:** `git diff c247c79..c433606 --check` sem erro; D2 altera o teste estrutural e seu relatório de evidência, sem alterar o runtime nem o snapshot de decisões.
- **INFERRED:** manter PR-20 retido até D3 fechar D02 porque o teste estrutural é o mecanismo de regressão para a promessa de normalização única.
- **UNKNOWN:** resultado final dos dois jobs macOS da Run 36440671039; confirmar antes da próxima homologação/promoção.

## 5. Despacho — PR-QA-D3

1. Fazer a análise AST resolver os nomes locais importados por `import shlex as ...`, `from shlex import split as ...`, `import os.path as ...`, `from os.path import normpath as ...` e os equivalentes de `posixpath`.
2. Aplicar a política existente a cada call-site resolvido: somente a chamada `shlex.split` em `rules.py:is_cert_tampering`, com limite um, permanece permitida; normalização de caminho fica somente em `normalize.py`, sem exceções fora do módulo.
3. Adicionar testes de regressão permanentes para os dois aliases reproduzidos e para aliases de módulo, cobrindo nomes de alias diferentes dos identificadores usados hoje.
4. Reexecutar os quatro casos D01 e provar que todos falham no clone; provar que os aliases de D02 também falham. As falhas devem citar arquivo, linha e chamada observada.
5. Manter as decisões de runtime e a baseline `c247c79` idênticas. Validar snapshot, fuzz diferencial, environment differential, suíte 62+ e evals 5/5.
6. Aguardar CI remoto 4/4 jobs verdes. Antes de qualquer push: suíte via `test-runner.sh`, evals, `evidence-report.sh --strict` e checagem separada do gate com `decision == allow`.
7. PR-20 só será despachado após revisão independente homologar o contrato estrutural completo.

## 6. Estado de continuidade

- HEAD revisado: `c433606`; a branch remota continha o commit no início desta revisão.
- Nenhum arquivo do runtime foi alterado nesta revisão; a mutação foi confinada a clones temporários.
- Atualizar a seção 0 do plano com D02 e este despacho. Não avançar a baseline de comportamento.
