# Handoff 050 — PR-QA-C homologado (contrato de opções de escrita); despacho do PR-QA-B e do PR-QA-D

**Data/Hora:** 2026-09-28T04:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `40f097b`, `c247c79` (PR-QA-C)
**Antecessor:** [Handoff 049](./handoff-049-revisao-pr22b-despacho-prqa-c.md)

---

## 1. Veredito: **HOMOLOGADO**

Reproduzido de forma independente (`OBSERVED`):

- **Contrato:** `config/write_options.json` cobre os 19 comandos das listas de leitura. Os que gravam ou executam têm as opções registradas com a linha do `--help`:
  - `less` (`-o`, `-O`, `--log-file`, `--LOG-FILE`);
  - `git diff|log|show` (`--output`, `--ext-diff`, `--textconv`);
  - `python3 -m json.tool` (segundo posicional `outfile`).
- **Gate:** as opções do contrato viraram tratamento no `rules.py`, sempre como **aperto** (deny quando o alvo é `.ceh`).
- **AW1 resolvido:** `r8sync` e `find` saíram de `EXCLUDE_SUPPORTED_CMDS`.
- **Falsificabilidade (garantia estrutural):** num clone, acrescentei `nl` à `ALLOWED_READ_CMDS` sem entrada no contrato. O `test_help_contract.py` reprova com `Comandos em ALLOWED_READ_CMDS sem contrato formal em write_options.json: ['nl']`. **Nenhuma lista de leitura cresce mais sem inventário de opções**, que era a classe do AV1.
- **Redes:** `test_help_contract`, `test_cert_protection`, bateria e as duas redes diferenciais verdes, com 0 relaxamentos contra `d4bb909`. Corpus conforme (1.024).
- **Servidor:** `40f097b` → [run 36369910415](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36369910415) = **success** (4/4). O link agora está versionado na evidência (AW2 cumprido).

**Linha de base avançada** para `c247c79`. As justificativas continuam zeradas (só houve apertos).

### Ressalvas baixas

- **AX1:** os `--help` foram capturados no ambiente **local** (git 2.43.0), e não no do CI, como pedido. Os runners usam outras versões (o git do runner era 2.55). Registre no cabeçalho de cada contrato de onde veio, e prefira capturar no job do CI (artefato) na próxima atualização.
- **AX2 (precisão de citação):** duas entradas citam uma linha que não nomeia a opção:
  - `git-diff` → `--output-directory` aponta para a linha do `--output` (170). `--output-directory` é opção do `format-patch`, não do `diff`;
  - `git-log` → `-o` aponta para a linha do `--output`, e o `git log` não documenta `-o`.

  Cada entrada deve citar uma linha que contenha o próprio nome da opção. Um teste simples resolve: o `help_snippet` precisa conter o `flag`.

## 2. Despacho — dois commits, cada um com o CI do servidor verde antes do seguinte

### Commit 1 — PR-QA-B `test(gate): invariante do motivo`

O texto do motivo (`reason`) é o que o agente e o desenvolvedor leem para entender a decisão. Hoje nada garante que ele seja coerente com a decisão.

1. Em `tests/test_reason_invariant.py`, sobre o corpus inteiro (`gate_corpus.txt`) e a bateria, para cada avaliação:
   - `deny` → o motivo contém um **marcador de bloqueio** reconhecido (`[CEH PRODUCTION LOCK]`, `CATASTROPHIC`, `CERTIFICATE INTEGRITY`, `PRE-PUSH CI GATE`, `PARSER_FAIL_CLOSED` etc., numa lista fechada versionada);
   - `allow` → o motivo **não** contém nenhum marcador de bloqueio;
   - `ask` → o motivo contém o marcador de confirmação (`ALERTA`);
   - o `use_case` do resultado aparece de forma consistente com o motivo (por exemplo, `CERTIFICATE_INTEGRITY` com o marcador do G9).
2. Todo motivo menciona o **ambiente detectado** e a **evidência** do ambiente, quando o ambiente influenciou a decisão.
3. **Falsificabilidade:** num clone, troque o texto de um motivo de deny por um texto neutro; o teste reprova, citando o comando.

### Commit 2 — PR-QA-D `refactor(gate): normalização única`

Os achados W1/W2 (Handoffs 019–021) vieram de normalizações duplicadas que divergiam entre os analisadores.

1. Levante **todas** as funções que normalizam comando, caminho ou token (`ceh_core/lexer.py`, `environment.py`, `rm.py`, `git.py`, `find.py`, `push.py`, `rules.py`, `safety-gate.py`) e liste-as na evidência.
2. Consolide numa única API em `ceh_core/` (por exemplo, `normalize.py`), usada por todos os analisadores. Nenhum analisador mantém normalização própria.
3. **Sem mudança de decisão:** o corpus e as redes diferenciais contra `c247c79` precisam ficar **idênticos** (0 apertos e 0 relaxamentos). Qualquer diferença é bug do refactor, não ajuste.
4. **Teste estrutural** no `doc-audit` ou num teste: falha se aparecer uma função de normalização fora do módulo único (por nome ou por padrão de uso de `shlex`/`os.path.normpath` fora dele, com lista de exceções justificada).
5. Respeite os orçamentos de linhas.

### Carona (qualquer um dos commits)

AX2: acrescente ao `test_help_contract.py` a checagem de que o `help_snippet` contém o `flag`, e corrija as duas entradas.

### Critérios de aceite

- [ ] PR-QA-B: o invariante do motivo cobre corpus e bateria, com prova por mutação.
- [ ] PR-QA-D: normalização única, com teste estrutural; corpus e redes **idênticos** à base.
- [ ] AX2 corrigido com teste.
- [ ] Cada commit com o CI do servidor verde (4/4) e o link versionado. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 3. Sequência

PR-QA-B + PR-QA-D → PR-20 (índice de ADRs e promessas verificáveis) → PR-21 (redação de segredos no Conselho + AU1/AU4) → encerramento da Onda 5 → Onda 4 quando houver evidência de um 3º host.

**Lembrete ao desenvolvedor:** a `main` ainda não contém o conteúdo desta branch (Handoff 048 §3).
