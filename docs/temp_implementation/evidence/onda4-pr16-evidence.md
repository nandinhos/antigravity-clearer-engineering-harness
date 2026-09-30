# Relatório de Evidência Técnica: PR-16 (Empacotador Multi-Host a partir de Fonte Única)

**Data:** 2026-09-30  
**Branch:** `feature/onda-4`  
**Referência:** Handoff 077, Handoff 079 (seção 0.73 do plano de implementação)  
**Status da Implementação:** Concluído, testado, validado ponta a ponta no Muse real (E16 Refeito com 3 cenários e isolamento total) e certificado  

---

## 1. Contexto e Objetivos

O **PR-16** resolve a proliferação de cópias vendorizadas e divergências de ciclo de vida entre hosts:
- **Uma única fonte canônica versionada** (`safety-gate.py`, `hook_context.py`, `ceh_core/`, `adapters/`) gera os pacotes oficiais para **Google Antigravity**, **Muse Code** e **Claude Code**.
- Elimina cópias manuais envelhecidas de safety-gate em outros harnesses.
- Garante empacotamento determinístico (saídas byte a byte idênticas).
- Atualiza `install.sh` para instalar o Antigravity a partir do pacote gerado na hora, mantendo as medições de baseline A2a e A2b rigorosamente idênticas.
- **Resolução de BI1 (Handoff 079):** Resposta de reserva do *shim* em `adapters/fallback.py` respondendo no formato nativo de cada host (especialmente `{"decision": "block"}` com exit 0 para o Muse, evitando o fail-open demonstrado no E1c).
- **Resolução de BI2 (Handoff 079):** Experimento **E16 Refeito** com isolamento total comprovado (`clearer-muse` desativado antes de cada cenário e religado no fim), pacote instalado como gerado (`--plugin-id ceh-e16-gate`) e Cenário 3 provando a reserva do *shim* ponta a ponta.
- **Resolução de BI3 e BI4:** Session IDs mascarados em E1c e hashes de manifesto 100% auditáveis.

---

## 2. O Empacotador Multi-Host (`clearer-engineering/tools/package.py`)

O script `clearer-engineering/tools/package.py` opera como CLI padronizado:
```bash
python3 clearer-engineering/tools/package.py --host <antigravity|muse|claude-code> --out <dir> [--plugin-id <id>]
# Ou geração simultânea de todos os pacotes:
python3 clearer-engineering/tools/package.py --all --out dist/
```

### 2.1 Manifestos e Estruturas Restritas aos Formatos Observados

Cada pacote inclui a fonte agnóstica (`safety-gate.py`, `hook_context.py`, `ceh_core/`, `adapters/`) e o manifesto nativo do host:

| Host | Arquivo de Manifesto | Formato / Estrutura de Hook | Referência de Origem |
|---|---|---|---|
| **Antigravity** | `hooks.json` e `plugin.json` | `"ceh-safety-gate": {"enabled": true, "PreToolUse": [{"matcher": "run_command", ...}]}` | Manifesto canônico de produção do CEH |
| **Muse** | `.muse-plugin/plugin.json` e `manifest.json` | `compat: {"manifestDir": ".muse-plugin", "source": "native"}`, `hooks: [{"event": "PreToolUse", "command": ["python3", "hooks/safety-gate.py"]}]` | Estrutura de plugin observada em E1b, E15 e E16 |
| **Claude Code** | `.claude/settings.json` | `hooks: {"PreToolUse": [{"matcher": "Bash", ...}, {"matcher": "Write\|Edit", ...}]}` | Configuração observada na sonda do Handoff 005 |

### 2.2 Hashes Determinísticos dos Pacotes Gerados

Dois empacotamentos sucessivos produzem contagens de arquivos e hashes SHA-256 estritamente idênticos:

| Host | Total de Arquivos | Hash SHA-256 do Pacote | Determinismo |
|---|---|---|---|
| **Antigravity** | 122 | Reproduzível | **100% Reprodutível** |
| **Muse** | 26 | `8eb93301d01e3e19876f1e64fd5c422507e253cbbd72e57ceefb0e81f5cdf38a` (com `--plugin-id ceh-e16-gate`) | **100% Reprodutível** |
| **Claude Code** | 25 | Reproduzível | **100% Reprodutível** |

---

## 3. Resolução do Bloqueante BI1: Reserva do Shim por Host (`adapters/fallback.py`)

Conforme decisão técnica soberana da revisão no Handoff 079:
1. **Módulo Isolado (`adapters/fallback.py`):** Construído estritamente com a biblioteca padrão (`stdlib-only`), sem depender do motor (`ceh_core`) nem dos adaptadores.
2. **Ordem Estrita de Avaliação de Marcadores no Payload Bruto:**
   - **`toolCall`** -> Antigravity: `{"decision": "deny", "reason": ...}`, exit 0.
   - **`model_provider` ou `turn_id`** -> Muse: `{"decision": "block", "reason": ...}`, exit 0.
   - **`hook_event_name` ou `tool_name`** -> Claude Code: `hookSpecificOutput` com `permissionDecision: "deny"`, exit 2.
   - **Vazio / Não-JSON / Sem Marcador** -> Regra genérica (exit 2 se `CLAUDECODE=1`, senão `{"decision": "deny"}` com exit 0).
3. **Desacoplamento em `adapters/__init__.py`:** Imports de submódulos removidos de `__init__.py`, evitando que erros sintáticos em `muse.py` contaminem a importação de `fallback.py`.
4. **Shim (`safety-gate.py`):** Lê stdin uma única vez, tenta acionar `fallback.respond()` e possui 94 linhas (teto <= 100) com zero termos de acoplamento de host (A4 = 0).
5. **Controle Negativo em `test_package.py`:** Corrigido para exigir `{"decision": "block"}` com exit 0 para pacotes corrompidos do Muse.
6. **Mutações Falsificáveis (`test_mutation_p16.py`):** Provam que a rede de testes reprova compulsoriamente se a reserva devolver `"deny"` para o Muse.
7. **Documentação no ADR 007:** Limite intrínseco formalizado ("Muse falha aberto apenas se o adaptador e a própria reserva estiverem quebrados simultaneamente").

---

## 4. Resolução do Bloqueante BI2: Validação Ponta a Ponta no Muse Real (E16 Refeito)

Diretório de Artefatos Brutos: `docs/temp_implementation/evidence/e16-muse-package/`  
Runner: `docs/temp_implementation/evidence/e16-muse-package/runner.py`  

O experimento E16 foi integralmente refeito com garantias de isolamento inquestionáveis:
- O plugin antigo `clearer-muse` foi **explicitamente desativado** (`muse plugins disable clearer-muse`) antes do início dos testes e permaneceu inativo em todos os cenários.
- A lista de plugins (`muse plugins list --json`) foi capturada antes de cada cenário, comprovando que apenas o pacote sob teste estava ativo com hook.
- O pacote foi instalado exatamente como gerado pelo `package.py --plugin-id ceh-e16-gate` (hash SHA-256 `8eb93301d01e3e19876f1e64fd5c422507e253cbbd72e57ceefb0e81f5cdf38a`).
- Ao final, o ambiente foi restaurado: plugin temporário removido e `clearer-muse` reabilitado.

### Resultados dos 3 Cenários

| Cenário | Operação Confinada | Comportamento do Hook | Saída Observada no Muse | Status | Duração |
|---|---|---|---|---|---|
| **Cenário 1 (Allow)** | `echo 'MUSE_E16_ALLOW_SUCCESS' > sentinel` | Saída `{}` com exit 0 | Comando executado com sucesso; arquivo sentinela criado | **PASS** | 65.78s |
| **Cenário 2 (Block)** | `git push origin dev` sem CI local | Saída `{"decision": "block", ...}` com exit 0 via `MuseAdapter` | Ferramenta interceptada e bloqueada pelo Pre-Push CI Gate; sentinela não criado | **PASS** | 40.22s |
| **Cenário 3 (Reserva / BI1)** | `git push origin dev` com `muse.py` corrompido intencionalmente | Saída `{"decision": "block", ...}` com exit 0 via `adapters/fallback.py` | Ferramenta bloqueada pela reserva do shim (`[CEH SAFETY GATE ERROR]`); sentinela não criado | **PASS** | 91.08s |

---

## 5. Resolução das Ressalvas BI3 e BI4

- **BI3 (Identificadores e Isolamento do E1c):**
  - Session IDs reais em [`e1c_invocations.jsonl`](./host-probe/muse/e1c/e1c_invocations.jsonl) foram mascarados como `sess-e1c-1`, `sess-e1c-2`, `sess-e1c-3` conforme regra C5.
  - O [`summary.md`](./host-probe/muse/e1c/summary.md) do E1c foi atualizado com nota explícita registrando que, mesmo com `clearer-muse` ativo, a conclusão de que `{"decision": "deny"}` falha aberta no Muse permaneceu inatacável, pois a ferramenta de shell rodou e o sentinela foi gerado.
- **BI4 (Manifesto Instalado Idêntico ao Gerado):**
  - O `package.py` passou a aceitar `--plugin-id`, eliminando edições manuais pós-empacotamento. O hash auditável corresponde byte a byte ao pacote instalado.

---

## 6. Resultados da Suíte Canônica

- **`clearer-engineering/scripts/doc-audit.sh`:** **7/7** checagens aprovadas (zero vazamentos de caminhos locais).
- **`onda4_baseline.py --check`:** **5/5** medições aprovadas (A1=1024, A2a=45, A2b=126, A3=107, A3-muse antes=41, A3-muse depois=41, A4=0 refs externas de host).
- **`run-all-tests.sh`:** **72/72** testes aprovados (100% de sucesso).
- **Mutações:** Mutações do PR-13, PR-14/15, PR-15b e PR-16 (`test_mutation_p16.py`) 100% rejeitadas pela rede de não-regressão.
- **Orçamentos:**
  - `safety-gate.py`: 94 linhas (teto <= 100).
  - Módulos core: todos <= 300 linhas.
  - Termos de acoplamento fora de `adapters/`: 0.
