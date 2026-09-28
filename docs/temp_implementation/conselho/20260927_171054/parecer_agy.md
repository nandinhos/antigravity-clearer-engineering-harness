--- CONTRATO DE SAÍDA MANDATÓRIO ---
VEREDITO: RESSALVAS
CERTEZA: 0.95
ANALISE_ESPECIALIZADA:
Sob a ótica do Guardião do Harness e Safety Gate, o plano do PR-18 é de altíssima qualidade técnica ao trocar verificações heurísticas (`grep -q`) por parsing sintático determinístico e ao vincular ferramentas a evidências físicas auditáveis (`tool_catalog.json`). Contudo, sob a perspectiva de blast radius, segurança estrita e integridade da matriz de ambientes, identifiquei três pontos críticos que exigem blindagem explícita:

1. **Invocação In-Process do Safety Gate no Fuzz (Isolamento Físico e Performance)**:
   O teste de fuzz (`test_lexer_fuzz.py`) sintetizará 2.000 comandos com vetores de ataque reais (`rm -rf`, `git reset --hard`, `git push --force`, `drop database`). É mandatório que o teste importe a API interna (`from ceh_core.safety_gate import evaluate_command` ou equivalente em memória) operando exclusivamente sobre AST e avaliação estática. Proibir qualquer chamada via shell real (`os.system` ou `subprocess.run(shell=True)`) previne qualquer risco de execução acidental no host e reduz o tempo de execução no CI de ~45s (2.000 forks de processo) para < 0.3s.

2. **Expansão dos Invariantes de Fuzz para a Matriz Tríplice (DEV / HML / PRD)**:
   O plano delimitou o invariante apenas para `--env production` (`resultado != 'allow'`). O Safety Gate do CEH possui invariantes igualmente rígidos para os demais ambientes:
   - **Ambiente `homologacao`**: Qualquer composição com segmento destrutivo deve resultar estritamente em `ask` (ou `deny`), **NUNCA `allow`**.
   - **Ambiente `development`**: Padrões catastróficos globais (`rm -rf /`, fork bombs, etc. mapeados em `CATASTROPHIC_PATTERNS`) devem resultar estritamente em `deny` com severidade `CATASTROPHIC`, **NUNCA `allow`**.
   Limitar o fuzz à produção deixa brechas em pipelines que misturam comandos de staging e dev.

3. **Blindagem de Subshells Ocultas e Fail-Closed**:
   Em pipelines complexos (ex: `cmd1; (cmd2; cmd3)` ou comandos com aspas malformadas), o lexer (`split_shell_pipeline`) retorna `parse_err`. O teste de fuzz deve assegurar formalmente que qualquer erro de parsing acione a cláusula `PARSER_FAIL_CLOSED` (`deny`), validando o Invariante 7 (Incerteza é Escalada, Nunca Adivinhada).

RISCOS_IDENTIFICADOS:
1. **Risco de Falso Positivo de Performance / Timeout em CI**: A execução de 2.000 iterações via `subprocess` chamando a CLI `safety-gate.py` gerará sobrecarga de I/O de processos e risco de timeout na esteira do GitHub Actions.
2. **Assimetria de Proteção entre Ambientes**: Fuzzing restrito a `production` pode mascarar vazamento de comandos destrutivos não autorizados em `homologacao` (`ask`) e comandos catastróficos em `development` (`deny`).
3. **Fragilidade de Schema em Caminhos de Evidência**: Apontamentos em `tool_catalog.json` para arquivos de sessão transitórios (`docs/temp_implementation/evidence/...`) correm risco de quebra caso limpezas de arquivos temporários ocorram no futuro sem um teste que trave sua existência.

RECOMENDACAO_FINAL:
Incorporar ao plano (§2.3) a execução in-memory do `evaluate_command`, expandir a asserção do fuzz para verificar a matriz tríplice (`production` -> `deny`, `homologacao` -> `ask`/`deny`, e vetores catastróficos em `development` -> `deny`), e só então prosseguir com a implementação.
------------------------------------
