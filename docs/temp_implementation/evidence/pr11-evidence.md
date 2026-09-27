# Evidência Técnica de Implementação — PR-11

**Data:** 2026-09-27  
**PR:** PR-11 — `fix(install): resultado honesto e simetria com o uninstall`  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commit Base:** `4b6adab` (Handoff 039 — Encerramento da Onda 2)  
**Status:** IMPLEMENTADO E SUBMETIDO PARA REVISÃO  

---

## 1. Resumo Executivo e Escopo Cirúrgico

O PR-11 cumpre integralmente os requisitos despachados no Handoff 039:
1. **Validação Honesta do Plugin**: Eliminação definitiva do mascaramento `agy plugin validate ... >/dev/null 2>&1 || true` em `install.sh`. O comando agora exibe a saída real e aborta a instalação com código de retorno ≠ 0 em caso de falha de validação, a menos que a flag `--skip-diagnostics` seja explicitamente fornecida.
2. **Autodiagnóstico Pós-Instalação Direto (3 Pontos)**: Executado diretamente a partir de `$TARGET_PLUGIN_DIR/scripts/safety-gate.py`:
   - `safety-gate.py --check "rm -rf /"` → deny/CATASTROPHIC (`OBSERVED`);
   - `safety-gate.py --check "ls"` → allow (`OBSERVED`);
   - hook com stdin vazio → exit code 2 (fail-closed, PR-09, `OBSERVED`).
   Qualquer divergência aborta a instalação com exit ≠ 0 (a menos que `--skip-diagnostics` esteja ativo).
3. **Fonte Única da Verdade para Aliases**: Criado `clearer-engineering/config/aliases.sh`, lido dinamicamente por `install.sh` e `uninstall.sh`. Elimina a duplicação histórica entre `install.sh:212–222`, `:249` e `uninstall.sh:50`.
4. **Simetria Byte a Byte e Idempotência**: O algoritmo de injeção e remoção no `~/.bashrc` e `~/.zshrc` armazena o tamanho exato do separador introduzido (`# CEH_RC_PREFIX_LEN: <N>`), garantindo que uma instalação seguida de desinstalação restaure o arquivo de configuração original byte a byte idêntico (sha256 idêntico, 0 resíduos).
5. **Suíte Oficial 58/58**: O script `run-install-verification.sh` foi integrado à suíte oficial `run-all-tests.sh` como Teste 58.

---

## 2. Matriz dos 4 Testes Normativos (`run-install-verification.sh`)

Executado em ambiente isolado com `TMP_HOME` temporário:

| Teste | Descrição Normativa | Resultado Observado (`OBSERVED`) | Status |
|---|---|---|---|
| **Teste 1** | Idempotência de Instalação | Duas instalações consecutivas mantêm exatamente 1 bloco de aliases delimitado no `.bashrc` e `.zshrc`. | **PASS** |
| **Teste 2** | Simetria Byte a Byte | Instalação seguida de desinstalação restaura `.bashrc` e `.zshrc` com hashes SHA-256 idênticos ao original. Arquivos vazios retornam a 0 bytes. | **PASS** |
| **Teste 3** | Existência de Alvos dos Aliases | Todos os 8 aliases que apontam para scripts (`~/.gemini/config/plugins/clearer-engineering/...`) foram inspecionados na árvore instalada: todos existem e possuem permissão de execução (+x). | **PASS** |
| **Teste 4** | Validação Honesta & Mock de Falha | Mock do binário `agy` que retorna exit 42 e mensagem de erro faz `install.sh` abortar com exit 42 e exibir o erro real no terminal; ao passar `--skip-diagnostics`, a execução é concluída com exit 0 e aviso registrado. | **PASS** |

---

## 3. Prova Física de Falsificabilidade (Mutação Real no `install.sh`)

Para demonstrar que a verificação não é tautológica e que a rede realmente reprova quando o comportamento silencioso/inseguro é reintroduzido, foi realizada a mutação restaurando temporariamente o `|| true`:

```diff
-        local validate_output
-        local validate_status=0
-        validate_output=$(agy plugin validate "$TARGET_PLUGIN_DIR" 2>&1) || validate_status=$?
-        echo "$validate_output"
-        if [[ $validate_status -eq 0 ]]; then
-            log_success "Plugin validated and active in Antigravity."
-        else
-            ...
-            exit "$validate_status"
-        fi
+        agy plugin validate "$TARGET_PLUGIN_DIR" >/dev/null 2>&1 || true
+        log_success "Plugin validated and active in Antigravity."
```

**Saída observada do teste com mutação ativa (`OBSERVED`):**
```text
[4/4] Teste 4: Validação honesta (falha de agy plugin validate sai com exit ≠ 0)...
ERRO: install.sh com agy mock falho deveria retornar exit code 42, mas retornou 0
Output: 
  ╔═══════════════════════════════════════════════════════════════════╗
  ║    🛡️  CLEARER Engineering Harness (CEH) — Global Installer       ║
  ║         Evidence-Driven Engineering for Google Antigravity        ║
  ╚═══════════════════════════════════════════════════════════════════╝
...
[INFO] Validating plugin with Antigravity CLI...
[✔ SUCCESS] Plugin validated and active in Antigravity.
...
MUTATION TEST FAILED AS EXPECTED WITH EXIT 1
```

A rede de testes detectou a mutação e rejeitou com exit 1. Após restaurar a validação estrita, a suíte retornou 100% PASS.

---

## 4. Auditoria Estrutural e de Documentação (`doc-audit.sh`)

```text
=== [CEH Bounded Document Structure Audit] ===
[1/7] Verificando taxonomia de estados permitidos... PASS
[2/7] Verificando consistência da tabela de achados (R1 a R10)... PASS
[3/7] Verificando existência física de arquivos de evidência citados... PASS (20 links válidos)
[4/7] Verificando portabilidade de links e ausência de session IDs... PASS
[5/7] Verificando existência de commits citados no Git local... PASS
[6/7] Verificando consistência em handoffs... PASS
[7/7] Verificando orçamento de linhas dos componentes core... PASS
  • safety-gate.py: 624 linhas (Teto: 650)
  • test-runner.sh: 193 linhas (Teto: 200)
  • ceh_core/environment.py: 281 linhas (Teto: 300)
  • ceh_core/find.py: 200 linhas (Teto: 300)
  • ceh_core/git.py: 294 linhas (Teto: 300)
  • ceh_core/interpreters.py: 254 linhas (Teto: 300)
  • ceh_core/interpreters_extra.py: 263 linhas (Teto: 300)
  • ceh_core/lexer.py: 297 linhas (Teto: 300)
  • ceh_core/push.py: 273 linhas (Teto: 300)
  • ceh_core/rm.py: 233 linhas (Teto: 300)
  • ceh_core/rules.py: 136 linhas (Teto: 300)
SUCESSO: 7/7 checagens estruturais documentais passaram.
```

---

## 5. Redes Diferenciais e Suíte Geral

- **Rede Diferencial de Portões e Fuzzing**:
  `python3 -m unittest clearer-engineering/tests/test_gate_differential_fuzz.py clearer-engineering/tests/test_environment_differential.py`
  12.027 casos avaliados contra `dbeaad5` com **0 relaxamentos** detectados (`OK`).
- **Smoke-Eval Determinístico**:
  `python3 clearer-engineering/tests/cluster2_acceptance.py --clean-eval-smoke`
  **5/5 Critérios Atendidos** (`APROVA`).
- **Suíte Oficial Canônica**:
  `bash clearer-engineering/tests/run-all-tests.sh`
  **58/58 Testes Aprovados (100% PASS)**.
