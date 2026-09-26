# Evidência Técnica do PR-QA-A: Fuzz Diferencial contra a Linha de Base e Prova de Falsificabilidade

## 1. Resumo Executivo

O **PR-QA-A** implementa a infraestrutura canônica de teste de regressão e fuzz diferencial (`test_gate_differential_fuzz.py`) para o Safety Gate do CLEARER Engineering Harness (CEH), conforme especificado no Handoff 022.

- **Linha de base ativa**: `41e665f` (PR-05d), extraída hermeticamente via `git archive <sha> clearer-engineering/scripts | tar -x -C <tmp>`.
- **Regra de controle de linha de base**: o hash em `clearer-engineering/tests/fixtures/gate_baseline.txt` é de controle exclusivo da revisão e não é alterado pelo implementador.
- **Entradas avaliadas**:
  - Corpus de comandos decodificados de `RAW:` e `B64:` (linhas `HOOK:` e `INTEGRATION:` excluídas);
  - Baterias de testes adversariais (`review_batteries.txt`);
  - Mais de 3.500 comandos únicos gerados por gramática determinística com semente fixa (`random.Random(42)`).
  - Total de comandos únicos avaliados: **4.047 comandos** × 3 ambientes (`DEVELOPMENT`, `HOMOLOGACAO`, `PRODUCTION`) = **12.141 avaliações**.
- **Resultado contra a linha de base `41e665f`**:
  - **Zero relaxamentos** (`deny->ask|allow`, `ask->allow`, saída de `CATASTROPHIC`).
  - **Apertos legítimos**: fechamento do achado X1 (`git checkout ':/!x'` e variantes mnemônicas passando de allow para deny/ask).
- **Tempo de execução**: **~2.9s** (teto exigido pela especificação: < 20s).
- **Integração na suíte canônica**: integrado como Teste 53 em `clearer-engineering/tests/run-all-tests.sh` (53/53 PASS).

---

## 2. Prova Física de Falsificabilidade (RFC 2119 / Handoff 022)

Para comprovar que o teste reprova e falsifica qualquer regressão ou relaxamento não autorizado, o defeito **W1** (descarte indevido do primeiro argumento amplo em invocações `git checkout` com múltiplos posicionais sem `--`) foi reintroduzido em uma cópia mutada em runtime.

### Mutação Injetada (Defeito W1):
```python
# W1 Reintroduzido: descarta o primeiro posicional amplo se houver múltiplos argumentos sem '--'
if subcmd == "checkout" and "--" not in args:
    pos = [a for a in args if not a.startswith("-")]
    if len(pos) > 1 and pos[0] in (".", "./", "*"):
        remaining = [a for a in args if a != pos[0]]
        return orig_evaluate_git(subcmd, remaining)
```

### Saída da Reprovação com Nomeação Explícita de `git checkout . app/x`:
```text
[REPROVADO - PR-QA-A] 20 relaxamento(s) NÃO autorizados detectados contra a linha de base 41e665f!
Para autorizar um relaxamento decorrente de correção homologada, adicione a(s) linha(s) abaixo em tests/fixtures/relaxamentos_justificados.txt com o respectivo ID do achado:

  staging|git --no-pager checkout . src/|ask->allow|<ID-DO-ACHADO>
  production|git --no-pager checkout . src/|deny->allow|<ID-DO-ACHADO>
  staging|git -P checkout . config/app.php|ask->allow|<ID-DO-ACHADO>
  production|git -P checkout . config/app.php|deny->allow|<ID-DO-ACHADO>
  staging|git -P checkout . tests/unit/*.py|ask->allow|<ID-DO-ACHADO>
  production|git -P checkout . tests/unit/*.py|deny->allow|<ID-DO-ACHADO>
  staging|git checkout --detach . ':/src'|ask->allow|<ID-DO-ACHADO>
  production|git checkout --detach . ':/src'|deny->allow|<ID-DO-ACHADO>
  staging|git checkout --detach . docs/**/*.md|ask->allow|<ID-DO-ACHADO>
  production|git checkout --detach . docs/**/*.md|deny->allow|<ID-DO-ACHADO>
  staging|git checkout . app/x|ask->allow|<ID-DO-ACHADO>
  production|git checkout . app/x|deny->allow|<ID-DO-ACHADO>
  staging|git checkout . config/app.php src/|ask->allow|<ID-DO-ACHADO>
  production|git checkout . config/app.php src/|deny->allow|<ID-DO-ACHADO>
  staging|rtk git checkout "*" ':/:app/x'|ask->allow|<ID-DO-ACHADO>
  production|rtk git checkout "*" ':/:app/x'|deny->allow|<ID-DO-ACHADO>
  staging|rtk git checkout . ':/:app/x'|ask->allow|<ID-DO-ACHADO>
  production|rtk git checkout . ':/:app/x'|deny->allow|<ID-DO-ACHADO>
  staging|rtk git checkout . config/app.php|ask->allow|<ID-DO-ACHADO>
  production|rtk git checkout . config/app.php|deny->allow|<ID-DO-ACHADO>
```

A suíte falha com exit code não-zero e lista exatamente a linha pronta para colar caso o relaxamento seja formalmente justificado em `tests/fixtures/relaxamentos_justificados.txt`.
