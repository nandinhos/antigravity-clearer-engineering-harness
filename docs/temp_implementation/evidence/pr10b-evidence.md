# Evidência de Implementação e Validação — PR-10b

## 1. Identificação do PR
- **PR**: PR-10b
- **Título**: fix(gate): diretório .ceh protegido + E11 com controle
- **Data**: 2026-09-27
- **Status**: IMPLEMENTADO E SUBMETIDO PARA REVISÃO (57/57 testes, 5/5 evals, 0 pendências)
- **Artefatos Criados/Modificados**:
  - `clearer-engineering/scripts/ceh_core/rules.py` (função `mentions_ceh_or_certs` e proteção ampliada ao diretório `.ceh/` inteiro)
  - `clearer-engineering/tests/fixtures/review_batteries.txt` (5 linhas de AL1 promovidas de PENDENTE para verde)
  - `clearer-engineering/tests/test_cert_protection.py` (adicionado `test_terminal_ceh_directory_manipulation_denied`, total 8/8)
  - `docs/temp_implementation/scripts/e11_matrix_runner.py` (script automatizado para matriz experimental 3x2x2)
  - `docs/temp_implementation/evidence/host-probe/agy/20260927T034219Z/` (dados brutos, `results.jsonl`, `invocations.jsonl`, `summary.md`)
  - `docs/architecture/adr-007-protecao-certificado-modelo-ameacas.md` (ADR 007 atualizado com Decisões 4 e 5)

---

## 2. Resolução do AL1: Proteção do Diretório `.ceh/` Inteiro

### Análise da Causa Raiz
No PR-10 inicial, a checagem olhava exclusivamente para regex contendo os nomes dos arquivos (`last-ci-run.json`, etc.). Comandos que operavam no diretório `.ceh/` inteiro (como `cp -r /tmp/fake/. .ceh`, `mv /tmp/fake .ceh`, `rsync -a /tmp/fake/ .ceh/` ou `rm -rf .ceh`) passavam desapercebidos pelo filtro inicial e caíam nas regras gerais de filesystem de DEV (`allow`).

### Correção Cirúrgica Aplicada
Em `ceh_core/rules.py`, a função `mentions_ceh_or_certs` foi implementada para inspecionar componentes de caminho:
```python
def mentions_ceh_or_certs(cmd: str) -> bool:
    if CERT_FILES_REGEX.search(cmd):
        return True
    clean = cmd.replace("\"", "").replace("\x27", "").strip()
    if re.search(r"(?:^|[\s/=])(?:[^\s/]+/)*\.ceh(?:[/\s;&|*]|$)", clean, re.I):
        return True
    return False
```
Qualquer comando mencionando `.ceh/` que não pertença a `ALLOWED_READ_CMDS` (`ls .ceh`, `cat`, etc.) ou que contenha operadores de redirecionamento de escrita (`>`, `>>`) é classificado compulsoriamente como `deny` com `use_case: CERTIFICATE_INTEGRITY`.

### Validação das 5 Linhas de `review_batteries.txt`
As 5 linhas `PENDENTE:H038-AL1` passaram a ser atendidas e o prefixo `PENDENTE:` foi removido:
- `cp -r /tmp/fakeceh/. .ceh` -> `deny` (`H038-AL1`)
- `rm -rf .ceh && cp -r /tmp/fakeceh .ceh` -> `deny` (`H038-AL1`)
- `mv /tmp/fakeceh .ceh` -> `deny` (`H038-AL1`)
- `cp -r /tmp/fakeceh/* .ceh/` -> `deny` (`H038-AL1`)
- `rsync -a /tmp/fakeceh/ .ceh/` -> `deny` (`H038-AL1`)
- Leituras de controle (`ls .ceh`, `cat .ceh/last-ci-run.json`, `jq .status .ceh/last-ci-run.json`) seguem `allow`.

---

## 3. Resolução Metodológica do AL2: Caracterização Experimental Controlada (E11)

### Matriz 3x2x2 Executada
Executada no ambiente real com Antigravity CLI (`agy` versão 1.2.11) gerando artefatos em `docs/temp_implementation/evidence/host-probe/agy/20260927T034219Z/`.

| Exp ID | Braço de Teste | Ferramenta | Modo CLI | Exit Code | Arquivo Criado? | Hook Acionou? | Tempo |
|---|---|---|---|---|---|---|---|
| `E11-ctrl-write-padrao` | `controle` (sem hook) | `write` | `padrao` | 0 | ✅ SIM | NÃO | 8.38s |
| `E11-allow-write-padrao` | `allow` (`{"decision":"allow"}`) | `write` | `padrao` | 0 | ✅ SIM | SIM | 8.91s |
| `E11-vazio-write-padrao` | `vazio` (`{}`) | `write` | `padrao` | 0 | ❌ NÃO | SIM | 9.91s |
| `E11-ctrl-write-yolo` | `controle` (sem hook) | `write` | `yolo` | 0 | ✅ SIM | NÃO | 12.00s |
| `E11-allow-write-yolo` | `allow` (`{"decision":"allow"}`) | `write` | `yolo` | 0 | ✅ SIM | SIM | 10.80s |
| `E11-vazio-write-yolo` | `vazio` (`{}`) | `write` | `yolo` | 0 | ❌ NÃO | SIM | 9.12s |
| `E11-ctrl-shell-padrao` | `controle` (sem hook) | `shell` | `padrao` | 0 | ✅ SIM | NÃO | 7.94s |
| `E11-allow-shell-padrao` | `allow` (`{"decision":"allow"}`) | `shell` | `padrao` | 0 | ✅ SIM | SIM | 10.31s |
| `E11-vazio-shell-padrao` | `vazio` (`{}`) | `shell` | `padrao` | 0 | ❌ NÃO | SIM | 8.94s |
| `E11-ctrl-shell-yolo` | `controle` (sem hook) | `shell` | `yolo` | 0 | ✅ SIM | NÃO | 10.43s |
| `E11-allow-shell-yolo` | `allow` (`{"decision":"allow"}`) | `shell` | `yolo` | 0 | ✅ SIM | SIM | 11.87s |
| `E11-vazio-shell-yolo` | `vazio` (`{}`) | `shell` | `yolo` | 0 | ❌ NÃO | SIM | 12.72s |

### Fatos Físicos Observados (`OBSERVED`) e Decisão de Engenharia
1. **O controle grava**: Em todos os 4 cenários de controle (**sem nenhum hook instalado**), o CLI `agy` executa a ação e o arquivo sentinela é gravado com sucesso.
2. **O allow é neutro**: O retorno `{"decision": "allow"}` reproduz exatamente o comportamento do controle nativo do host.
3. **O retorno vazio `{}` bloqueia no Antigravity**: Diferente do Claude Code (onde `{}` devolve o fluxo interativo), no Antigravity o retorno `{}` impede a ferramenta de rodar (`file_created=False`), resultando em bloqueio indevido de comandos legítimos.
4. **Alinhamento Normativo**: Conforme estipulado no Handoff 038 §3: *"se o controle grava → o allow explícito é neutro, e a implementação atual está correta. Registre como OBSERVED."*

---

## 4. Auditoria de Linhas e Orçamento
- `clearer-engineering/scripts/ceh_core/rules.py`: 137 linhas (orçamento $\le 300$)
- `clearer-engineering/scripts/safety-gate.py`: 625 linhas (orçamento $\le 650$)
- `clearer-engineering/scripts/hook_context.py`: 294 linhas (orçamento $\le 300$)
- `clearer-engineering/scripts/test-runner.sh`: 193 linhas (orçamento $\le 200$)
- `clearer-engineering/tests/fixtures/review_batteries.txt`: 0 pendências restantes.
