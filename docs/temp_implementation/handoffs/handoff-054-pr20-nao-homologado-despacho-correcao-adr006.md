# Handoff 054 — PR-20 não homologado; correção do ADR-006

- **Data/Hora:** 2026-09-28T16:10:00-03:00
- **Instância:** Revisor sênior independente do CEH
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **HEAD revisado:** `5330e562103da19e7ef42805a89694a315063eb9`
- **Risco da revisão:** MÉDIO — fidelidade de decisões arquiteturais e claims de compatibilidade.

## 1. Veredito

- **PR-20: NÃO HOMOLOGADO nesta revisão.** O índice, a mudança do Conselho e as alterações de README estão no escopo despachado, mas o ADR-006 mistura decisão arquitetural aceita com estado implementado e benefícios que não estão sustentados pelas fontes observadas.
- **D05 (médio):** corrigir o status e o alcance factual do ADR-006. É um achado documental; não demonstra falha no núcleo do Safety Gate.
- **D04 permanece aberto** conforme Handoff 053. É uma pendência anterior e independente, necessária para homologação geral/merge da branch; não foi reavaliada nesta revisão.

## 2. Julgamentos das alegações

| Alegação | Julgamento | Evidência observada / lacuna |
|---|---|---|
| O índice enumera ADRs 001–007 e aponta os documentos existentes | **SUPPORTED** | `docs/architecture/README.md` lista as sete entradas; as ADRs 003–007 existem em `docs/architecture/`. A nota histórica explica a ausência de arquivos próprios 001/002. |
| A decisão de núcleo em Python padrão e adaptadores por host foi registrada | **PARTIALLY_SUPPORTED** | ADR-006 explicita a decisão e há núcleo em `clearer-engineering/scripts/ceh_core/`; mas o plano, nas etapas posteriores da Onda 4, ainda prevê criar adaptadores e suíte de conformidade entre hosts. O documento não separa decisão aprovada de implementação concluída. |
| Adaptadores Claude Code/Cursor existem e todos preservam as decisões do núcleo | **UNSUPPORTED** | ADR-006:39–40 afirma que existem e não afrouxam regras. O plano trata `hosts/claude-code/`, payloads e conformidade como entregas futuras; não foi observada prova de conformidade ou implementação desses adaptadores no diff. |
| Portabilidade é total e o comportamento é idêntico entre local, containers e CI | **UNSUPPORTED** | ADR-006:46. Não há no PR-20 matriz de resultados que sustente equivalência universal; a suíte entre hosts está descrita como futura no plano. |
| Núcleo é “Python 3.9+ e Bash POSIX” e opera sem dependências externas | **PARTIALLY_SUPPORTED** | CI exercita Python 3.9/3.12 e há parsers/imports da biblioteca padrão. Porém os scripts usam Bash como requisito, não há evidência de execução POSIX shell, e o workflow instala Bash Homebrew no macOS para os testes normais. Restringir a frase ao que foi efetivamente testado e delimitar “stdlib-only” ao código Python do núcleo, se esse for o contrato. |
| Safety Gate inicia em menos de 50 ms | **UNSUPPORTED** | ADR-006:48 dá um teto quantitativo sem benchmark, comando, ambiente ou amostra no documento/evidências. Remover a cifra ou adicionar medição reproduzível e escopo. |
| Correção da raiz de saída do Conselho | **PARTIALLY_SUPPORTED** | O código em `conselho-seniores.sh:25–26` prefere o repositório do cwd e tenta o repositório do script antes de `pwd`. CI geral passou, mas não foi localizado teste comportamental específico que verifique a raiz criada nas topologias de plugin/repositório previstas pelo PR-20. |
| Suíte, evals e auditoria estrutural local | **SUPPORTED** | `bash clearer-engineering/scripts/test-runner.sh`: exit 0, 62/62; `bash evals/run.sh`: exit 0, 5/5; `bash clearer-engineering/scripts/doc-audit.sh`: exit 0, 7/7 nesta revisão. |
| CI remoto citado | **SUPPORTED** | Run 36468331286: conclusão `success`, quatro jobs verdes, SHA `5330e562103da19e7ef42805a89694a315063eb9`. |

`git diff --check a31a6df..5330e56` passou. O diff do commit contém sete arquivos, 94 inserções e 9 remoções. Nenhum arquivo sob `docs/temp_implementation/` foi alterado pelo commit PR-20; o handoff anterior é ancestral independente.

## 3. D05 — correção solicitada

No PR-20a:

1. Marcar ADR-006 como decisão **aceita**, se essa é a intenção, sem afirmar “Implementado no CEH v1.3.0+” enquanto os adaptadores e a conformidade multi-host estiverem no futuro.
2. Separar o que existe hoje (núcleo Python e adaptador Antigravity observado) dos adaptadores planejados. Não afirmar compatibilidade/comportamento equivalente de hosts sem payloads reais e teste de conformidade.
3. Substituir “Bash POSIX” por requisito compatível com os scripts e a matriz realmente testada, ou acrescentar execução POSIX shell que sustente a alegação.
4. Remover “Portabilidade Total”, “comportamento idêntico” e `<50ms`, ou anexar provas delimitadas e reproduzíveis para esses claims.
5. Acrescentar teste de regressão para o destino das atas do Conselho em: cwd dentro de repo do usuário; execução de uma instalação externa ao repo; e fallback sem raiz Git, mantendo a árvore confinada a diretório temporário.

## 4. Próximo gate

Após PR-20a, revisar o diff do ADR e o teste do Conselho; executar suíte canônica, evals, `doc-audit`, `evidence-report.sh --strict` e CI remoto no commit corrigido. D04 permanece como gate separado para a homologação geral da branch. Não promover merge com base neste handoff.
