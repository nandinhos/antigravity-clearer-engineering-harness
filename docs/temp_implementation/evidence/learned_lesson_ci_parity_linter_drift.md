# Lição Aprendida: Paridade de CI (Local vs GitHub Actions) e Linter Drift Multiplataforma

**Data:** 2026-09-27  
**Status:** RESOLVIDO  
**Tags:** `ci-cd`, `github-actions`, `shellcheck`, `parity`, `linter-drift`, `systematic-debugging`, `learned-lesson`

---

## 1. O Problema / Sintoma Observado
Durante a esteira de CI do PR-19b (`chore(shell): limpeza de avisos do shellcheck e shellcheck bloqueante`), observou-se que a simulação de CI local reportava sucesso funcional completo (58/58 testes passando e emissão do certificado de voo do Safety Gate), mas a esteira remota do GitHub Actions falhou em commits subsequentes:
1. **Falsificabilidade comprovada**: No commit `1893cd6`, o Step 10 da esteira remota barrou o build com exit code 1 devido a um aviso deliberado de ShellCheck.
2. **Drift de Linters no macOS**: No commit `6d565f1`, o job de Ubuntu passou no ShellCheck, mas os dois jobs de macOS falharam no Step 10 com `SC2329` ("Function ... was never invoked directly").

A questão central levantada: *Por que a simulação local não capturou essas falhas antes do push e como mitigar definitivamente essa divergência?*

---

## 2. Causa Raiz Isolada (Systematic Debugging v2)

1. **Step Parity Gap (Lacuna de Paridade de Passos)**:
   - O orquestrador local `test-runner.sh` executava a suíte hermética funcional (`run-all-tests.sh` com 58 testes), emitindo o certificado `.ceh/last-ci-run.json`.
   - No entanto, a checagem estática global de `shellcheck` e `compileall` não fazia parte da pré-condição bloqueante do `test-runner.sh` local, permitindo que alterações com avisos de linter recebessem autorização de voo local.

2. **Linter Drift Multiplataforma (Rolling Release vs Fixed Distribution)**:
   - **Ubuntu Runner**: Instala o ShellCheck via `apt-get` (versão estável 0.8.0 / 0.9.0), onde a regra `SC2329` ainda não existe ou não é disparada em traps.
   - **macOS Runner**: Instala o ShellCheck via `brew install shellcheck` (rolling release contínua, versão 0.11.0), introduzindo a nova regra `SC2329` que analisa o grafo de chamada e sinaliza funções invocadas exclusivamente por `trap ... EXIT` como código morto.
   - **Host Local do Desenvolvedor**: Roda na versão instalada no sistema operacional local, que frequentemente diverge da versão mais recente dos pacotes rolling release dos runners de nuvem.

3. **Heterogeneidade de Sistemas Operacionais**:
   - O ambiente de desenvolvimento local (Linux x86_64) não executa nativamente binários Darwin nem o Apple Legacy Bash 3.2.57 com suas peculiaridades de subshell e tratamento de sinais.

---

## 3. Mitigação em 3 Níveis (Defesa em Profundidade)

### Nível 1: Blindagem de Código contra Linter Drift
- Substituição de funções auxiliares de uma linha declaradas unicamente para cleanup de saída por comandos diretos inline no `trap` (ex: `trap 'rm -rf "$TMP_DIR"' EXIT`).
- Elimina a assunção de visibilidade da função pelo analisador estático, tornando o código imune a regras de "uninvoked function" (`SC2329`) em qualquer versão do ShellCheck (0.8.x até 0.11.x+).

### Nível 2: Paridade de Steps no Orquestrador Local
- O runner local de testes e o hook de pré-push devem validar a cadeia completa de steps estáticos antes de rodar os testes funcionais:
  ```bash
  # 1. Checagem de sintaxe pura
  bash -n scripts/*.sh
  python3 -m compileall -q .
  # 2. Linter estático estrito
  shellcheck -x -e SC1090,SC1091 scripts/*.sh
  # 3. Suíte canônica de testes funcionais
  ./clearer-engineering/tests/run-all-tests.sh
  ```
- O certificado de voo local `.ceh/last-ci-run.json` só deve ser assinado se todos os 3 blocos concluírem com exit code 0.

### Nível 3: Regra Canônica AQ3 (Certificação Remota Inegociável)
- Em projetos com CI multiplataforma matricial (ex: Linux + macOS × múltiplas versões de Python/Node), **a simulação local é condição necessária, mas não suficiente** para homologação definitiva.
- A conclusão formal da tarefa ou feature só ocorre após a observação direta (`OBSERVED`) de 100% de sucesso (`success`) nos 4 jobs remotos da matriz do GitHub Actions.

---

## 4. Resultado Comprovado (`OBSERVED`)

Nos commits `d2b0a26` e `dadcc72`, a esteira remota do GitHub Actions concluiu com **100% VERDE** em todos os 4 jobs da matriz:

| Job | Plataforma | Python | ShellCheck v0.11 | E2E Lifecycle | Veredito |
|---|---|---|---|---|---|
| **Job 108666746897** | `ubuntu-latest` | 3.9 | `success` | `success` | **`success`** |
| **Job 108666746889** | `ubuntu-latest` | 3.12 | `success` | `success` | **`success`** |
| **Job 108666746904** | `macos-latest` | 3.9 | `success` (SC2329 imune) | `success` | **`success`** |
| **Job 108666746900** | `macos-latest` | 3.12 | `success` (SC2329 imune) | `success` | **`success`** |

- Workflow Run ID: [36335965350](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36335965350) — Status: `completed`, Conclusion: `success`.

---

## 5. Invariante Canônico (Regra de Ouro)
> **Invariante de Paridade de CI:** Nunca considere uma alteração multiplataforma concluída baseando-se exclusivamente na aprovação de testes funcionais locais; linters estáticos globais devem rodar localmente com os mesmos parâmetros da esteira, e entregas que afetam múltiplos SOs exigem a verificação remota com 100% verde na matriz completa do CI antes do merge.
