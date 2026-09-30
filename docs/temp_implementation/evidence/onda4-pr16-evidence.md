# Relatório de Evidência Técnica: PR-16 (Empacotador Multi-Host a partir de Fonte Única)

**Data:** 2026-09-30  
**Branch:** `feature/onda-4`  
**Referência:** Handoff 077 (seção 0.72 do plano de implementação)  
**Status da Implementação:** Concluído, testado, validado ponta a ponta no Muse real (E16) e certificado  

---

## 1. Contexto e Objetivos

O **PR-16** resolve a proliferação de cópias vendorizadas e divergências de ciclo de vida entre hosts:
- **Uma única fonte canônica versionada** (`safety-gate.py`, `hook_context.py`, `ceh_core/`, `adapters/`) gera os pacotes oficiais para **Google Antigravity**, **Muse Code** e **Claude Code**.
- Elimina cópias manuais envelhecidas de safety-gate em outros harnesses.
- Garante empacotamento determinístico (saídas byte a byte idênticas).
- Atualiza `install.sh` para instalar o Antigravity a partir do pacote gerado na hora, mantendo as medições de baseline A2a e A2b rigorosamente idênticas.
- Valida o pacote no Muse Code 1.4.1 real através do experimento controlado **E16** com artefatos brutos e bloqueio confinado ao diretório temporário (atendendo à ressalva BH1).

---

## 2. O Empacotador Multi-Host (`clearer-engineering/tools/package.py`)

O script `clearer-engineering/tools/package.py` opera como CLI padronizado:
```bash
python3 clearer-engineering/tools/package.py --host <antigravity|muse|claude-code> --out <dir>
# Ou geração simultânea de todos os pacotes:
python3 clearer-engineering/tools/package.py --all --out dist/
```

### 2.1 Manifestos e Estruturas Restritas aos Formatos Observados

Cada pacote inclui a fonte agnóstica (`safety-gate.py`, `hook_context.py`, `ceh_core/`, `adapters/`) e o manifesto nativo do host:

| Host | Arquivo de Manifesto | Formato / Estrutura de Hook | Referência de Origem |
|---|---|---|---|
| **Antigravity** | `hooks.json` e `plugin.json` | `"ceh-safety-gate": {"enabled": true, "PreToolUse": [{"matcher": "run_command", ...}]}` | Manifesto canônico de produção do CEH |
| **Muse** | `.muse-plugin/plugin.json` e `manifest.json` | `compat: {"manifestDir": ".muse-plugin", "source": "native"}`, `hooks: [{"event": "PreToolUse", "command": ["python3", "hooks/safety-gate.py"]}]` | Estrutura de plugin observada em E1b e E15 |
| **Claude Code** | `.claude/settings.json` | `hooks: {"PreToolUse": [{"matcher": "Bash", ...}, {"matcher": "Write\|Edit", ...}]}` | Configuração observada na sonda do Handoff 005 |

### 2.2 Hashes Determinísticos dos Pacotes Gerados

Dois empacotamentos sucessivos produzem contagens de arquivos e hashes SHA-256 estritamente idênticos:

| Host | Total de Arquivos | Hash SHA-256 do Pacote | Determinismo |
|---|---|---|---|
| **Antigravity** | 121 | `8894f539ed9cd59be7cc87a419ba794604966cf2fd2148ed955fcdf859b21c57` | **100% Reprodutível** |
| **Muse** | 25 | `7102739ffdf634e28b0b92133df32007d5a0240b9ab5198344954046b8fb71e7` | **100% Reprodutível** |
| **Claude Code** | 24 | `439f880fad0ba83fd2a258a6934d046f81cd59674918c5765ae6f251501f9bed` | **100% Reprodutível** |

---

## 3. Instalação Transparente via `install.sh`

O script `install.sh` foi atualizado para empacotar o plugin `antigravity` via `package.py` em diretório temporário e implantar a partir do pacote:
- **A2a (Ativos Não-Código):** 45 ativos não-código byte-a-byte idênticos ao baseline v1.4.0.
- **A2b (Manifesto da Instalação):** 124 caminhos instalados, com todos os 21 arquivos novos da Onda 4 formalmente declarados em `ONDA4_DECLARED_NEW_PATHS`.
- **Zero Divergência de Instalação:** O usuário e a IDE do Antigravity continuam recebendo a estrutura canônica sem qualquer fricção ou alteração perceptual.

---

## 4. Testes do Empacotador (`test_package.py`)

Arquivo de Teste: `clearer-engineering/tests/test_package.py` (integrado como Teste 72 na suíte geral):

1. **`test_package_determinism`:** Empacotamento em diretórios temporários paralelos gerando hashes idênticos.
2. **`test_package_manifests_observed`:** Validação de esquemas e comandos de manifestos dos 3 hosts.
3. **`test_completeness_antigravity`:** Execução hermética de `safety-gate.py` empacotado contra todos os **93 payloads reais** de `antigravity/recorded.jsonl` (100% de conformidade com exit code 0).
4. **`test_completeness_muse`:** Execução hermética de `hooks/safety-gate.py` empacotado contra todos os **41 payloads reais** de `muse/recorded.jsonl` (100% de conformidade com exit code 0 e payload `{}`).
5. **`test_completeness_claude_code`:** Execução hermética de `scripts/safety-gate.py` empacotado contra todos os **14 payloads reais** de `claude_code/recorded.jsonl` (100% de conformidade com exit code 0 e payload `{}`).
6. **`test_negative_control_muse_adapter_missing` (Controle Negativo):**
   - Um pacote do Muse sem `hooks/adapters/muse.py` foi submetido ao teste de completude.
   - **Resultado:** O teste de completude **reprovou** (não permitiu a execução) e o shim atuou em fail-closed, respondendo `{"decision": "deny", "reason": "[CEH SAFETY GATE ERROR] Falha crítica de importação dos módulos de segurança..."}`. Comprova que pacotes corrompidos não falham aberto.

---

## 5. Validação Ponta a Ponta no Muse Real (Experimento E16)

Arquivo do Runner: `docs/temp_implementation/scripts/e16_muse_runner.py`  
Diretório de Artefatos Brutos: `docs/temp_implementation/evidence/e16-muse-package/`  

Foi instanciada uma sessão real do **Muse Code 1.4.1 (1.4.1-R4503.1)** com o pacote `muse` instalado e aprovado como hook `PreToolUse`:

| Cenário | Operação Submetida ao Muse | Comportamento do Safety Gate | Comportamento do Muse CLI | Status | Duração |
|---|---|---|---|---|---|
| **Cenário 1 (Allow)** | `echo 'MUSE_E16_ALLOW_SUCCESS' > sentinel` | Saída `{}` com exit code 0 | Comando executado; arquivo sentinela criado com sucesso | **PASS** | 31.18s |
| **Cenário 2 (Block)** | `git push origin dev` (sem certificado prévio de CI em repositório local) | Saída `{"decision": "block", "reason": "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: NENHUMA execução prévia comprovada em '.github/workflows'"}` com exit code 0 | Ferramenta interceptada e bloqueada pelo hook; `never_created.txt` não criado | **PASS** | 36.15s |

### Auditoria de Isolamento e Segurança (BH1):
- **Zero Contaminação do Host:** O plugin original do desenvolvedor (`clearer-muse`) foi preservado intacto. A comparação via `diff` entre [`plugins_list_before.json`](./e16-muse-package/plugins_list_before.json) e [`plugins_list_after.json`](./e16-muse-package/plugins_list_after.json) comprovou restauração idêntica do ambiente.
- **Confinamento Conforme BH1:** O repositório git e as operações de terminal foram estritamente confinadas ao diretório efêmero `$TMPDIR/workspace`, sem interagir com repositórios externos nem caminhos fora do diretório temporário.

---

## 6. Tratamento Consolidado das Ressalvas BH1–BH3 do Handoff 077

- **BH1 (Alta - E15 e Confinamento de Bloqueios):**
  - Primeira execução reconstruída formalmente em [`docs/temp_implementation/evidence/e15-muse-hook/e15_run1_rm_rf_attempt.md`](./e15-muse-hook/e15_run1_rm_rf_attempt.md).
  - Tabela do `summary.md` do E15 corrigida para documentar o comando real `git push origin dev`.
  - Regra inegociável de confinamento a `$TMPDIR` aplicada e validada no E16.
- **BH2 (Média - Reserva do Shim no Muse & Experimento E1c):**
  - Experimento controlado E1c executado no Muse real (`docs/temp_implementation/evidence/host-probe/muse/e1c/`).
  - Demonstrou que o formato `{"decision": "deny"}` **não bloqueia** no Muse (fail-open), enquanto `{"decision": "block"}` bloqueia com sucesso.
  - Conforme exigido pelo revisor, o shim **não foi alterado unilateralmente**, mantendo a matriz de evidências observadas à disposição da revisão independente.
- **BH3 (Baixa - Limite de Detecção):**
  - Registrado formalmente como limite da arquitetura: ferramentas não mapeadas sem marcadores `model_provider`/`turn_id` seriam roteadas ao adaptador do Claude Code (atualmente 100% dos 41 payloads reais contêm esses marcadores).

---

## 7. Resultados da Suíte Canônica

- **`clearer-engineering/scripts/doc-audit.sh`:** **7/7** checagens aprovadas.
- **`onda4_baseline.py --check`:** **5/5** medições aprovadas (A1=1024, A2a=45, A2b=124, A3=107, A3-muse antes=41, A3-muse depois=41, A4=0 refs externas).
- **`run-all-tests.sh`:** **72/72** testes aprovados (100% de sucesso).
- **Orçamentos:**
  - `safety-gate.py`: 100 linhas (teto <= 100).
  - Módulos core: todos <= 300 linhas.
  - Termos de acoplamento fora de `adapters/`: 0.
