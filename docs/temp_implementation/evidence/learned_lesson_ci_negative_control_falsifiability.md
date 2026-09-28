# Lição Aprendida: Falsificabilidade de Linters de CI e Isolamento de Controles Negativos (AS2)

**Data:** 2026-09-27  
**Status:** RESOLVIDO  
**Tags:** `ci-cd`, `github-actions`, `shellcheck`, `falsifiability`, `negative-control`, `learned-lesson`, `systematic-debugging`

---

## 1. O Problema / Contexto Observado
Durante a evolução do pipeline de integração contínua (PR-19b e PR-19c), surgiu a necessidade de comprovar que o novo portão bloqueante do ShellCheck (`Run ShellCheck (Strict Zero Warnings Gate - Single Job)`) no GitHub Actions é de fato sensível e capaz de falhar de forma determinística diante de uma violação real de sintaxe de shell script (eliminação de "fake pass" ou falso-positivo de sucesso).

No entanto, a realização de provas de falsificabilidade diretamente na branch de trabalho gerou execuções vermelhas no histórico de CI do repositório (ex: execução #67 com erro `SC2086`), causando ruído na interpretação da estabilidade da branch principal e gerando atrito no fluxo de revisão.

---

## 2. Causa Raiz Isolada (Systematic Debugging v2)
1. **Necessidade Epistemológica de Falsificabilidade**:
   - Um teste ou portão de CI só é considerado confiável se for comprovado que ele falha quando a condição avaliada é violada (Invariante Epistemológico do CEH). Sem controle negativo executado no mesmo ambiente de execução (GitHub Actions runner), não há garantia de que o step possui `set -e` / `set -o pipefail` ativo ou de que o exit code é propagado.
2. **Poluição de Histórico de Branch por Falta de Isolamento (Resenha AS2)**:
   - Commits de injeção de erro submetidos na branch de trabalho permanente criam runs vermelhos no painel do Actions associados à branch principal, gerando alertas indevidos e confusão sobre a prontidão da versão.

---

## 3. Solução Canônica & Mitigação em 3 Níveis

### Nível 1: Protocolo de Branch Descartável para Controles Negativos (AS2)
- Toda e qualquer prova de falsificabilidade no CI que exija a falha deliberada do pipeline DEVE ser executada exclusivamente em uma branch temporária isolada com prefixo `claude/negctl-<pr>` (ex: `claude/negctl-19c`).
- O procedimento canônico é:
  1. Criar e alternar para a branch descartável: `git checkout -b claude/negctl-<pr>`.
  2. Injetar a mutação cirúrgica mínima (ex: `sleep $INTERVAL` sem aspas para SC2086).
  3. Comitar e enviar para o repositório remoto: `git push -u origin claude/negctl-<pr>`.
  4. Observar a reprovação estrita (`failed`) no Step exato no GitHub Actions e documentar a URL/ID do run (ex: run 36344146427, job 108689850093).
  5. Retornar à branch de trabalho, excluir a branch local e apagar a branch remota do GitHub:
     ```bash
     git checkout claude/code-review-technical-analysis-kfwcdl
     git branch -D claude/negctl-<pr>
     git push origin --delete claude/negctl-<pr>
     ```

### Nível 2: Isolamento da Violação em Variável Existente (Sem Colaterais)
- A injeção para teste de linter estático deve ser pura e não gerar efeitos colaterais de runtime. Por exemplo, em scripts com `set -u` (`nounset`), referenciar uma variável não declarada causa erro de runtime antes do teste. A injeção correta remove aspas de uma variável já existente (`sleep $INTERVAL` em [task-monitor.sh:97](../../../clearer-engineering/scripts/task-monitor.sh#L97)), violando unicamente o `SC2086` do ShellCheck.

### Nível 3: Verificação Sequencial de 4/4 Verde no Commit de Produção
- O commit limpo de implementação (ex: `3d1812b` do PR-19c) é enviado à branch principal somente após a confirmação do controle negativo, comprovando 100% de sucesso nos 4 jobs remotos da matriz do GitHub Actions antes da emissão do relatório de evidência.

---

## 4. Regra de Ouro (Invariante Preventivo)
> **Invariante AS2:** *Controles negativos de CI nunca tocam a branch de trabalho. Toda prova de falha no pipeline remoto deve nascer, ser comprovada e morrer em branch temporária descartável.*
