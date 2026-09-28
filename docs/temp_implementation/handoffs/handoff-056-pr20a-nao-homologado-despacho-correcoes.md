# Handoff 056 — PR-20a não homologado; D05 parcial, D06 aberto e D04 bloqueado

- **Data/Hora:** 2026-09-28T19:30:00-03:00
- **Instância:** Revisor sênior independente do CEH
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **HEAD revisado:** `7452b3013b082938eb0d26749aa1cf76d8583576`
- **CI remoto:** Run [36475885529](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36475885529), `success`, 4/4 jobs; SHA observado `c80b8319b23525cf2e0358559107cf96e76c36ec`.
- **Risco da revisão:** MÉDIO — veracidade dos contratos de runtime e validade do teste de regressão; D04 segue como risco separado de política de caminhos.

## 1. Veredito

- **PR-20a: NÃO HOMOLOGADO nesta revisão.** A correção documental de D05 é parcial, e a prova de regressão do diretório do Conselho não testa o código de produção.
- **D05 (médio): PARCIAL.** O ADR delimita adaptadores futuros e remove os claims quantitativos/universais, mas o runtime do Bash permanece incorreto para o Conselho: `conselho-seniores.sh` usa `local -n` e `declare -A`; os testes macOS comuns usam Bash Homebrew 5+, não Apple Bash 3.2. O passo com Apple Bash 3.2 testa somente `install.sh` e `uninstall.sh` e exige que ambos falhem fechados.
- **D06 (médio):** `test_conselho_output_dir.py` reconstrói as expressões de produção em um snippet próprio; não executa `conselho-seniores.sh` nem importa uma função compartilhada. Mudança/regressão na lógica real não necessariamente falha no teste.
- **D04 (médio, INFERRED): NÃO RESOLVIDO.** Uma tentativa de prova com diretórios temporários, symlink e marcador de ambiente não chegou a executar: o PreToolUse bloqueou a chamada com ambiente `unknown` e alerta de ação destrutiva. Nenhum contorno foi tentado.

## 2. Evidências observadas

- `git status` no início: branch limpa e sincronizada com `origin`; HEAD `7452b30`.
- Diff `c80b831`: cinco arquivos alterados; ADR-006 agora marca a decisão como aceita, separa adaptadores futuros e remove `<50ms`/“Portabilidade Total”. Essa parte atende ao despacho anterior.
- `clearer-engineering/tests/test_conselho_output_dir.py`: helper `_extract_output_dir_from_script` monta snippet Bash contendo as expressões copiadas das linhas de produção. Os três cenários exercitam esse snippet, não o script real.
- `.github/workflows/ci.yml`: o passo Apple Legacy Bash 3.2 verifica sintaxe e falha fechada em `install.sh`/`uninstall.sh`; após isso instala Bash Homebrew e adiciona esse Bash ao `PATH` antes da suíte normal. `conselho-seniores.sh` usa `local -n` (linha 82) e arrays associativas (linhas 313–315), recursos não disponíveis em Bash 3.2.
- `bash clearer-engineering/scripts/evidence-report.sh --base 5330e56 --strict` nesta revisão: `NAO_VERIFICADO`; suíte 63/63 certificada em `7452b30`, evals 5/5 ainda certificados em `c80b831` (stale para o HEAD). Portanto o claim do Handoff 055 de relatório estrito verificado no commit final não está demonstrado por esse estado observado.
- CI Run 36475885529 concluiu os quatro jobs com sucesso, mas no commit `c80b831`, não no commit documental `7452b30`.
- A chamada dinâmica de D04 foi bloqueada antes da execução. O resultado não confirma nem refuta a hipótese sobre symlink; mantém D04 como `INFERRED`.

## 3. Despacho PR-20b

1. Corrigir o requisito do Conselho para Bash 4.3+ (ou a versão mínima realmente necessária) e explicitar separadamente os scripts que são suportados em Bash 3.2. Não usar a prova restrita de `install.sh`/`uninstall.sh` para generalizar compatibilidade do pacote.
2. Refatorar a resolução da raiz/saída do Conselho para uma função testável chamada pelo script e importável/executável pelo teste, ou executar o script real com CLI agente falso e diretórios de saída temporários. As mutações na lógica de produção devem reprovar o teste.
3. Reemitir `test-runner.sh`, `evals/run.sh`, auditoria documental e `evidence-report --strict` depois do commit final. Obter CI remoto verde para o SHA final antes de nova homologação.

## 4. Despacho D04

O ensaio pedido precisa demonstrar conjuntamente: (a) a classificação do ambiente configurado no ancestral físico acessado por symlink; (b) a normalização/alvo relativo analisado pelo gate; e (c) o efeito no comando `rm`, sem executar a exclusão. O ensaio proposto usava somente diretórios temporários, mas o hook bloqueou a execução. Solicitar ao responsável pela política uma rota expressamente aprovada para esse caso; não transferir a mesma execução a outro runtime, MCP ou interpreter para contornar o bloqueio. Até existir prova autorizada, D04 permanece aberto e bloqueia homologação geral/merge.
