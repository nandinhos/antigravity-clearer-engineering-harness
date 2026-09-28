# Relatório de Evidências — PR-06f (Handoff 029)

- **Data/Hora**: 2026-09-26T13:00:00Z
- **Escopo**: Resolução definitiva de regressão de uso (AE1), completamento de `awk | sh` (AE2) e `fish --command=` (AE3).
- **Alvo**: Fechamento formal da Onda 1 (G1–G6) do CEH.

---

## 1. Implementação Técnica

### 1.1 AE1: Varredura de Sufixos em um Único Nível por Subcomando (`safety-gate.py`)
- Adicionado parâmetro `scan_suffixes: bool = True` em `evaluate_command` e `evaluate_subcommand`.
- A varredura de sufixos ocorre uma única vez no nível do subcomando. Quando o sufixo é avaliado, recebe `scan_suffixes=False` e mantém o `depth` inalterado (varredura linear não incrementa profundidade).
- O limite de profundidade de recursão (`depth > 3`) passa a vigiar **estritamente desembrulhos reais** (`sh -c`, `eval`, `os.system`, `-exec`).
- Comandos com 4 ou mais nomes de ferramentas (ex.: `brew install git node perl ruby python3`, `which git bash perl python3 node`, `echo git git git git`) retornam `allow` em ambiente de desenvolvimento sem acionar limite de profundidade espúrio.
- Controles garantidos: `echo git git git git find / -delete` e `setsid nice timeout 5 sudo -u x find / -delete` continuam bloqueados como `deny/CATASTROPHIC`.

### 1.2 AE2: Desembrulho de `print ... | "sh"` em `awk` (`ceh_core/interpreters_extra.py`)
- Padrão `AWK_PRINT_PIPE_PATTERNS` adicionado para capturar expressões canalizadas para shells (`print ... | "sh"`, `printf ... | "sh"`).
- O script impresso (`find / -delete`) é extraído e avaliado recursivamente por `eval_fn`.
- Comandos como `gawk 'BEGIN{print "find / -delete" | "sh"}'` são bloqueados como `deny/CATASTROPHIC`.

### 1.3 AE3: Suporte a `fish --command=<script>` com `=` (`safety-gate.py`)
- `extract_shell_c_command` atualizado para capturar `--command=<script>` e `-c<script>` em `fish`.
- `fish --command="find / -delete"` é extraído e bloqueado como `deny/CATASTROPHIC`.

---

## 2. Prova Física de Falsificabilidade da Invariante de Benignidade

Executada via script determinístico `scratch/verify_benign_commands_falsifiability_ae1.py`:
- Amostra: 288 comandos inócuos gerados pela combinação de 9 verbos legítimos (`echo`, `which`, `command -v`, `apt-get install -y`, `brew install`, `pip install`, `npm install -g`, `man`, `ls`) com 1 a 8 nomes de ferramentas.
- **Com Gate Atual (PR-06f, varredura em 1 nível)**: **0 violações** (100% permitidos em DEV).
- **Com Varredura Aninhada reintroduzida (Simulação PR-06e)**: **180 violações** (bloqueados indevidamente como CATASTROPHIC).
- Golden Corpus Snapshot 100% conforme com diff vazio em [pr06f-corpus-diff.md](./pr06f-corpus-diff.md).

---

## 3. Conformidade Documental e Orçamento de Linhas (`doc-audit.sh`)

7/7 checagens aprovadas com todos os componentes dentro do orçamento normativo:
- `safety-gate.py`: 595 linhas (Teto: 650)
- `test-runner.sh`: 193 linhas (Teto: 200)
- `ceh_core/environment.py`: 127 linhas (Teto: 300)
- `ceh_core/find.py`: 200 linhas (Teto: 300)
- `ceh_core/git.py`: 294 linhas (Teto: 300)
- `ceh_core/interpreters.py`: 254 linhas (Teto: 300)
- `ceh_core/interpreters_extra.py`: 263 linhas (Teto: 300)
- `ceh_core/lexer.py`: 286 linhas (Teto: 300)
- `ceh_core/rm.py`: 233 linhas (Teto: 300)
- `ceh_core/rules.py`: 63 linhas (Teto: 300)
