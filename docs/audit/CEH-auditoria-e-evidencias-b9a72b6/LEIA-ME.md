# Evidências — auditoria CEH b9a72b6

O relatório é `analise-aprofundada.md`. Os resultados são do commit `b9a72b6b6dbd898dd737609bada8036866e56646`, coletados em 30/09/2026 no horário brasileiro; timestamps UTC também aparecem em 01/10.

## Resultados prioritários
- `ceh-review-independent-results.json`: classificações reais de strings e provas isoladas de aliases/empacotamento.
- `ceh-review-probes.json`: três execuções reais do runner em fixtures temporárias.
- `ceh-review-verification-results.json`: exit codes de evals, adversarial e doc-audit.
- `ceh-review-canonical-state.json`: estado PARCIAL da suíte canônica; não é 75/75.
- `ceh-review-api.json` e `ceh-review-branch-protection.json`: respostas públicas do GitHub, sem autenticação.
- `ceh-review-metrics.json`: contagem por escopo, não LOC executáveis.
- `ceh-review-citations.json` e `ceh-review-source-map.json`: fontes primárias conferidas no snapshot.

## Reprodução
Os scripts foram executados em clones isolados em scratch. Eles referenciam caminhos locais de Windows/WSL da máquina de revisão. Para outra máquina, ajuste os caminhos `base`/`repo` para um checkout do MESMO commit antes de executar. Os scripts não instalam globalmente e não executam os payloads destrutivos nem fazem push; somente classificam esses comandos. As provas do runner executam scripts benignos controlados em fixtures Git temporárias. Docker/Sail foram mocks, não containers reais. Certificados sintéticos da prova do validador NÃO são evidência de CI executada.

## Limites
A suíte completa foi interrompida por tempo local elevado durante o grupo 58; não foi declarada aprovada. Não foram executadas integrações com CLIs LLM reais. Os achados estáticos/condicionais são diferenciados dos reproduzidos no relatório. Nenhum código do projeto ou configuração global foi alterado.

`MANIFEST.json` registra tamanho e SHA-256 dos arquivos deste pacote. Os hashes demonstram integridade do pacote de evidências; não são assinatura de origem nem prova automática da correção semântica da análise.

## Resolução & Handoff Formal
Todos os 16 achados técnicos documentados em `analise-aprofundada.md` foram integralmente remediados no commit `63dbe5c` (Release `v2.1.0`).
Consulte o handoff técnico detalhado em [`HANDOFF-HERMES-REMEDIACAO-v2.1.0.md`](./HANDOFF-HERMES-REMEDIACAO-v2.1.0.md) para o mapeamento completo de causas raízes, testes de regressão dedicados (76/76 PASS) e instruções determinísticas de reprodução.

