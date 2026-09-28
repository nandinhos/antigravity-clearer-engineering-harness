# Evidência de Implementação e Validação — PR-10 (G9)

## 1. Identificação do PR
- **PR**: PR-10 (G9)
- **Título**: feat(gate): proteger o certificado e registrar o modelo de ameaças
- **Data**: 2026-09-27
- **Status**: IMPLEMENTADO E VALIDADO (57/57 testes, 5/5 evals)
- **Artefatos Criados/Modificados**:
  - `clearer-engineering/scripts/ceh_core/rules.py` (função `is_cert_tampering`, `ALLOWED_READ_CMDS`, `PROTECTED_CERT_FILES`)
  - `clearer-engineering/scripts/safety-gate.py` (integração de `is_cert_tampering` antes de exclusões de arquivos com caso `CERTIFICATE_INTEGRITY`)
  - `clearer-engineering/scripts/hook_context.py` (suporte a ferramentas de arquivo do Antigravity e Claude com bloqueio de escrita em `.ceh/`)
  - `clearer-engineering/hooks.json` (matchers para `write_to_file`, `replace_file_content`, `multi_replace_file_content`)
  - `clearer-engineering/tests/test_cert_protection.py` (nova suíte com 7 testes comportamentais)
  - `clearer-engineering/tests/run-all-tests.sh` (registrado Teste 24, elevando total para 57 testes)
  - `clearer-engineering/tests/fixtures/gate_corpus.txt` e `gate_corpus.expected.jsonl` (atualização dos payloads reais de agy)
  - `docs/architecture/adr-007-protecao-certificado-modelo-ameacas.md` (ADR 007 documentando modelo de ameaças e decisões)
  - `docs/temp_implementation/evidence/pr10-corpus-diff.md` (auditoria do diff de snapshot)

---

## 2. Evidência E11: Observação do Contrato Real do Antigravity CLI (`agy`)
- **Ambiente**: Linux x86_64, `agy` versão 1.2.11.
- **Procedimento**: Execução de `write_to_file` em sandbox com pre-tool use hook ativo.
- **Payload Recebido pelo Hook**:
  ```json
  {
    "toolCall": {
      "name": "write_to_file",
      "args": {
        "TargetFile": "/tmp/test_eval.txt",
        "CodeContent": "hello world"
      }
    }
  }
  ```
- **Contrato de Resposta Observado (`OBSERVED`)**:
  - Resposta `{"decision": "allow"}`: a ferramenta executa normalmente e o arquivo é gravado no disco com sucesso.
  - Resposta `{}` (objeto vazio): o CLI `agy` não reconhece como aprovação, gerando timeout de 30 segundos com mensagem `Antigravity CLI did not complete in 30s` e bloqueando a execução da ferramenta.
  - **Conclusão**: No Antigravity IDE/CLI, o contrato exige `{"decision": "allow"}` explícito. No Claude Code, o contrato exige `{}` para allow (preservando o fluxo de permissões nativo F6). O `hook_context.py` foi calibrado para respeitar exatamente essa distinção entre os hosts.

---

## 3. Matriz de Comportamento do `safety-gate` para `.ceh/`

| Tipo de Ação | Comando / Chamada | Decisão | Caso de Uso / Motivo |
|---|---|---|---|
| **Escrita Shell (Redirecionamento)** | `echo '...' > .ceh/last-ci-run.json` | `deny` | `CERTIFICATE_INTEGRITY` |
| **Escrita Shell (Redirecionamento Append)** | `echo '...' >> .ceh/last-ci-run.json` | `deny` | `CERTIFICATE_INTEGRITY` |
| **Cópia Shell** | `cp fake.json .ceh/last-ci-run.json` | `deny` | `CERTIFICATE_INTEGRITY` |
| **Tee Shell** | `tee .ceh/last-ci-run.json` | `deny` | `CERTIFICATE_INTEGRITY` |
| **Sed Shell** | `sed -i 's/FAIL/PASS/' .ceh/last-ci-run.json` | `deny` | `CERTIFICATE_INTEGRITY` |
| **Python Inline Shell** | `python3 -c "open('.ceh/last-ci-run.json', 'w').write('{}')"` | `deny` | `CERTIFICATE_INTEGRITY` |
| **Exclusão Shell** | `rm .ceh/last-ci-run.json` | `deny` | `CERTIFICATE_INTEGRITY` (bloqueado em todos os ambientes) |
| **Leitura Segura (`cat`)** | `cat .ceh/last-ci-run.json` | `allow` | Leitura autorizada |
| **Leitura Segura (`head`/`tail`)** | `head -n 5 .ceh/last-ci-run.json` | `allow` | Leitura autorizada |
| **Leitura Segura (`jq`)** | `jq .exit_code .ceh/last-ci-run.json` | `allow` | Leitura autorizada |
| **Leitura Segura (`grep`)** | `grep PASS .ceh/last-ci-run.json` | `allow` | Leitura autorizada |
| **Leitura Segura (`python3 -m json.tool`)** | `python3 -m json.tool .ceh/last-ci-run.json` | `allow` | Leitura autorizada |
| **Ferramenta de Arquivo (Antigravity)** | `write_to_file` alvo `.ceh/last-ci-run.json` | `deny` | Bloqueio de adulteração via hook |
| **Ferramenta de Arquivo (Antigravity)** | `replace_file_content` alvo `.ceh/last-ci-run.json` | `deny` | Bloqueio de adulteração via hook |
| **Ferramenta de Arquivo (Claude Code)** | `Write` alvo `.ceh/last-ci-run.json` | `deny` | Bloqueio de adulteração via hook |
| **Ferramenta de Arquivo (Claude Code)** | `Edit` alvo `.ceh/last-ci-run.json` | `deny` | Bloqueio de adulteração via hook |
| **Ferramenta de Arquivo Legítima** | `write_to_file` alvo `/tmp/test.txt` | `allow` | Arquivo fora de `.ceh/` permitido |

---

## 4. Prova Física de Falsificabilidade
- **Mutação Injetada**: Inclusão de `tee` no conjunto `ALLOWED_READ_CMDS` em `ceh_core/rules.py`.
- **Resultado Comprovado**:
  ```
  FAIL: test_tee_denied (test_cert_protection.TestCertProtection.test_tee_denied)
  AssertionError: 'allow' != 'deny'
  FAIL: test_falsifiability_allowed_reads_not_write (test_cert_protection.TestCertProtection.test_falsifiability_allowed_reads_not_write)
  AssertionError: 'allow' != 'deny'
  FAILED (failures=2)
  ```
- **Conclusão**: A rede de testes é sensível e reprova deterministicamente qualquer relaxamento que admita ferramentas de escrita como leitura.

---

## 5. Auditoria de Linhas e Orçamento de Complexidade
- `clearer-engineering/scripts/safety-gate.py`: 624 linhas (orçamento $\le 650$)
- `clearer-engineering/scripts/ceh_core/rules.py`: 127 linhas (orçamento $\le 300$)
- `clearer-engineering/scripts/ceh_core/push.py`: 273 linhas (orçamento $\le 300$)
- `clearer-engineering/scripts/hook_context.py`: 294 linhas (orçamento $\le 300$)
- `clearer-engineering/scripts/test-runner.sh`: 193 linhas (orçamento $\le 200$)
