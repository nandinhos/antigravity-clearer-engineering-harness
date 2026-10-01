--- CONTRATO DE SAÍDA MANDATÓRIO ---
VEREDITO: RESSALVAS
CERTEZA: 0.95 (Fundamentada na auditoria do parser de shell, AST do Git e matriz de ambientes DEV/HML/PRD)
ANALISE_ESPECIALIZADA:
Sob a ótica de Guardião do Harness & Safety Gate, a modelagem abstrata dos 16 achados ataca com precisão as principais brechas de integridade do sistema, com destaque para os seguintes acertos fundamentais:
1. **Monotonicidade de Ambiente (F02 / Invariante 2)**: A imposição de $\text{env}_{\text{efetivo}} = \max(\text{env}_{\text{ancestral}}, \text{env}_{\text{prefixo}}, \text{env}_{\text{interno}})$ fecha em definitivo o vetor de bypass onde `APP_ENV=production bash -c "..."` permitia a execução de comandos destrutivos ao resetar para o `explicit_env` default (`development`). A hierarquia de severidade (`PRODUCAO > HOMOLOGACAO > DEV`) passa a ser inviolável na descida da árvore recursiva (`depth + 1`).
2. **Fechamento de Evasão de Comandos Destrutivos e CI Gate (F03, F04, F05)**: A migração de regex textual frágil (`\bgit\s+reset\s+--hard\b`, `\b-f\b`) para o consumo direto da AST de flags estruturadas (`parse_push_args`, `is_force`, `tokens`) impede que permutações comuns (`git reset HEAD --hard`, agrupamentos como `-vf` ou `/usr/bin/git push`) burlem as salvaguardas de branch e o bloqueio de operações destrutivas em PRODUCAO/HOMOLOGACAO.
3. **Integridade Estrita de Certificação de CI (F06, F07, F08)**: As amarras para invalidar certificados forjados por fallback silencioso (`unittest` em vez de `pytest`), divergência de comando no transporte Sail/Docker e detecção de worktree suja pós-execução garantem que o gate `PRE_PUSH_CI` opere exclusivamente sobre fatos físicos comprovados (`OBSERVED`).

Contudo, há **duas ressalvas técnicas mandatórias** sob as regras do Safety Gate:
- **Ressalva 1 (F10 — Heurística do `rm -rf`)**: A proposta de usar `os.path.isdir(target)` para desambiguar pastas pontuadas (`customer.db/`) é insuficiente e perigosa. Se um comando contiver `-r` ou `-R`, a semântica pretendida pelo emissor é *intrinsecamente recursiva*. O Safety Gate proíbe qualquer atalho de "arquivo único seguro" quando as flags `-r` ou `-R` estiverem presentes na linha de comando, independentemente de o alvo possuir ponto na extensão ou de existir fisicamente no disco no momento do parse estático. Se há flag recursiva, a classificação de risco é destrutiva.
- **Ressalva 2 (F05 — Fail-Closed em Git Config)**: A resolução de refs implícitas via `git config` não pode admitir tolerância a erro. Se a leitura de `push.default` ou `remote.<remote>.push` falhar ou retornar mapeamentos não-determinísticos (`matching`, wildcards), o Safety Gate deve bloquear a operação (`FAIL_CLOSED`) exigindo que o desenvolvedor especifique a ref explicitamente (`git push origin <branch>`).

RISCOS_IDENTIFICADOS:
1. **Falso Negativo no F10**: Depender de `os.path.isdir` em tempo de parse pode classificar um diretório ainda não criado ou caminho expandido por glob como "arquivo inofensivo", permitindo que comandos destrutivos passem sem interceptação em ambientes restritos.
2. **Falsos Positivos em Testes que Geram Caches Não Rastreados (F08)**: Suítes de teste que geram artefatos temporários não cobertos por `.gitignore` podem invalidar sistematicamente o certificado de CI pós-execução, exigindo higienização de `.gitignore` ou isolamento em `/tmp`.
3. **Degradação de Latência no Hook Pre-Push (F05)**: Múltiplas invocações síncronas de `git config` em repositórios corporativos grandes podem onerar a experiência de push se não forem cacheadas durante a avaliação do comando.

RECOMENDACAO_FINAL:
Ajustar a especificação do **F10** para tornar a presença das flags `-r`/`-R` o critério eliminatório absoluto (qualquer `rm` com flag recursiva é destrutivo, sem atalhos para caminhos com ponto) e homologar o início imediato da **Fase A (Bloco A: P1 — F01 a F08)** via ciclo estrito TDD (RED com teste de falha comprovada antes de cada patch).
------------------------------------
