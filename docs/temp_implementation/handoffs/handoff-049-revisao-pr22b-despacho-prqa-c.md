# Handoff 049 — PR-22b homologado (G9 fechado de novo; PR-22 aceito como um todo); despacho do PR-QA-C (contrato de opções com `--help`)

**Data/Hora:** 2026-09-28T03:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `d4bb909` (PR-22b)
**Antecessor:** [Handoff 048](./handoff-048-revisao-pr22-regressao-g9-despacho-pr22b.md)

---

## 1. Veredito: **HOMOLOGADO** (PR-22 + PR-22b)

Reproduzido de forma independente (`OBSERVED`):

- **AV1 fechado:** `is_git_read_subcommand` desqualifica a leitura pura quando há `-o`, `-O`, `--output`, `--output=…` ou `--output-…`. Em produção:
  - deny: `git diff|log|show --output=.ceh/…`, a forma com espaço (`--output .ceh/…`), `git --git-dir=.git log … --output=…`, `--ext-diff` via `-c diff.external` ou `GIT_EXTERNAL_DIFF`;
  - allow (leituras legítimas): `git status --ignored .ceh`, `git log -n 5 .ceh/…`, `git diff .ceh/…`, `git show HEAD:app.txt`.
- **Abreviações** (`--outp=`, `--outpu=`, `--out=`): o gate responde allow, mas conferi que o **git rejeita** essas abreviações nas opções de diff/log e não grava nada. Não há brecha.
- **AV2 fechado:** `strip_ceh_exclusions` só age em comandos com semântica de exclusão; `python3 … --exclude .ceh` voltou a deny, como na base.
- **Falsificabilidade:** num clone, removi as 7 linhas da correção. A bateria reprova nas linhas `H048-AV1` (453–455) e o `test_cert_protection.py` reprova em `test_e2e_cert_forge_via_git_output_blocked` e `test_git_output_flag_denied_all_envs`.
- **Redes:** `test_gate_differential_fuzz`, `test_environment_differential`, `test_rules_data_infra`, `test_cert_protection` e a bateria verdes. Corpus com 1.024 avaliações conforme; as formas `--output` entraram no corpus (AV3).
- **Servidor:** `d4bb909` → [run 36367128683](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36367128683) = **success** (4/4).

**Com isso, o PR-22 é aceito como um todo:** AT3 (regras de dados e infraestrutura) + AM2 (leituras de `.ceh`), sem a regressão do G9.

**Linha de base avançada** para `d4bb909`. As justificativas de relaxamento foram **zeradas**: os 5 relaxamentos AM2 agora fazem parte da própria linha de base.

### Ressalvas baixas

- **AW1:** `EXCLUDE_SUPPORTED_CMDS` contém `r8sync`, um **erro de digitação do Handoff 048** copiado literalmente. Também contém `find`, que não tem `--exclude` (o `-prune` já é tratado à parte). Os dois são inofensivos; remova no próximo commit que tocar `rules.py`.
- **AW2:** o `pr22b-evidence.md` versionado não traz o link da execução do servidor (a edição foi revertida antes do commit). O link está no relatório de entrega; na próxima evidência, versione-o (regra do AQ3).
- **AW3:** `-O` desqualifica a leitura por conservadorismo (no git, `-O<arquivo>` é ordem de diff, leitura). Aceitável; só registre.

## 2. Lição de método do AV1 (vale para os próximos PRs de regra)

A regressão do PR-22 não veio de um erro de código isolado, e sim de **admitir um comando numa lista de leitura sem enumerar as opções dele que escrevem**. As redes diferenciais não viram porque só comparam o que está no corpus. A defesa sistemática é o **PR-QA-C**, planejado desde o Handoff 018.

## 3. Despacho — PR-QA-C `test(gate): contrato de opções de escrita a partir do --help`

1. **Inventário:** para cada comando em listas de leitura/permissão do gate (`ALLOWED_READ_CMDS`, `ALLOWED_GIT_READ_SUBCMDS` e demais), capture o `--help` (ou `man`) real do ambiente de CI, versionado em `docs/temp_implementation/evidence/help-contracts/<cmd>.txt`, com a versão da ferramenta e a data.
2. **Contrato:** um arquivo `clearer-engineering/config/write_options.json` listando, por comando, as opções que **gravam** ou **executam** (ex.: `git diff/log/show`: `--output`, `--ext-diff`, `--textconv`; `sort`: `-o`; `tee`: tudo). Cada entrada cita a linha do `--help` que a justifica.
3. **Teste `tests/test_help_contract.py`**, registrado na suíte:
   - para cada opção de escrita do contrato, o gate nega quando o alvo é `.ceh/…`, em todos os ambientes;
   - o teste falha se um comando for admitido numa lista de leitura **sem** entrada no contrato (isso fecha a classe do AV1: nenhuma lista de leitura cresce sem o inventário de opções).
4. **Falsificabilidade:** num clone, retire `--output` do tratamento do gate; o teste reprova. Num segundo clone, acrescente um comando à lista de leitura sem contrato; o teste reprova.
5. **Carona:** AW1 (remover `r8sync` e `find` de `EXCLUDE_SUPPORTED_CMDS`).
6. **Evidência:** CI do servidor verde (4/4) com o link versionado (AW2); redes diferenciais contra `d4bb909` com 0 relaxamentos; `git status --porcelain` vazio.

### Critérios de aceite

- [ ] Contrato de opções de escrita versionado, com o `--help` real de cada comando.
- [ ] O teste reprova tanto por opção de escrita não tratada quanto por comando de leitura sem contrato, com prova por mutação.
- [ ] AW1 resolvido. CI do servidor verde (4/4), link versionado. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 4. Sequência

PR-QA-C → PR-QA-B (invariante do motivo) e PR-QA-D (normalização única) → PR-20 (índice de ADRs) → PR-21 (redação de segredos no Conselho + AU1/AU4) → Onda 4 quando houver evidência de um 3º host.

**Lembrete ao desenvolvedor:** a `main` ainda não contém o conteúdo desta branch (Handoff 048 §3). O `install.sh` da `main` segue com a guarda antiga.
