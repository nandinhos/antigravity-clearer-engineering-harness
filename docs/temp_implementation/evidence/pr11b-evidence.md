# Evidência Técnica de Implementação — PR-11b

**Data:** 2026-09-27  
**PR:** PR-11b — `fix(uninstall): remoção sem efeito colateral no rc do usuário`  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commit Base:** `8230536` (Handoff 040 — Revisão PR-11 e Despacho PR-11b/PR-12)  
**Status:** IMPLEMENTADO E SUBMETIDO PARA REVISÃO  

---

## 1. Resumo Executivo e Correções de Segurança

O PR-11b resolve definitivamente os três modos de falha identificados pelo revisor sênior no Handoff 040 em relação ao desinstalador (`uninstall.sh`):

1. **AN1 (Eliminação de Efeito Colateral por Edição de Prefixo)**:
   - Em vez de remoção cega dos `N` caracteres que antecedem o bloco CEH (`start_idx - prefix_len`), o desinstalador agora inspeciona e conta estritamente as quebras de linha (`\n`) consecutivas imediatamente anteriores ao bloco.
   - Remove **apenas e tão-somente** `min(num_newlines, prefix_len)` quebras de linha.
   - **Garantia incondicional:** Nenhum caractere alfanumérico ou de configuração do usuário (ex: `export A=1`) fora do bloco é removido, mesmo que o usuário ou um formatador de dotfiles tenha apagado a linha em branco antes do bloco.
2. **AN2 (Ancoragem e Assinatura Estrita para Remoção de Órfãos)**:
   - A limpeza de aliases fora do bloco foi reescrita linha a linha com âncora estrita `^alias <nome>=` tanto em `uninstall.sh` quanto em `install.sh`.
   - Um alias fora do bloco só é removido se for comprovadamente uma definição CEH:
     - Ou é idêntica a uma linha de `aliases.sh`,
     - Ou contém a assinatura `--agent clearer-harness`,
     - Ou contém `plugins/clearer-engineering/`.
   - Linhas comentadas (ex: `# alias ceh=antigo`) e aliases do usuário apontando para outros scripts (ex: `alias ceh='meu-script'`) permanecem 100% intocados.
   - Aliases órfãos legítimos do CEH sem bloco delimitado continuam sendo removidos de forma limpa.
3. **AN3 (Fail-Closed e Eliminação de Falso Sucesso)**:
   - Eliminado `2>/dev/null || true` no bloco Python do `uninstall.sh`.
   - Qualquer falha de leitura, parsing ou escrita de arquivo rc levanta exceção e encerra a execução com código de saída ≠ 0, impedindo o anúncio de falso sucesso.

---

## 2. Matriz de Testes Normativos (`run-install-verification.sh`)

| Teste | Cenário Avaliado | Resultado Observado (`OBSERVED`) | Status |
|---|---|---|---|
| **AN1** | Usuário apaga linha em branco antes do bloco em rc sem `\n` final | `export A=1` preservado byte a byte (zero caracteres não-`\n` removidos). | **PASS** |
| **AN2** | Preservação de comentários e aliases customizados | `# alias ceh=antigo`, `alias ceh='meu-script'` e `export B=2` preservados idênticos ao original. | **PASS** |
| **AN2 (órfão)** | Remoção de alias CEH órfão legítimo fora do bloco | `alias ceh-help='...'` removido com sucesso; linhas vizinhas `export X=1` e `export Y=2` intactas. | **PASS** |
| **AN3** | Fail-Closed diante de falha do interpretador | Mock `python3` com exit 1 faz `uninstall.sh` abortar com erro sem anunciar falso sucesso. | **PASS** |

---

## 3. Prova Física de Falsificabilidade (Mutação em `uninstall.sh`)

Para demonstrar a falsificabilidade das asserções, foi introduzida temporariamente a mutação reproduzindo o código anterior:
- Linha 59: `remove_start = max(0, start_idx - prefix_len)` (remoção cega);
- Linha 74: `content = re.sub(rf'alias {re.escape(a)}=.*?\n', '', content)` (regex sem âncora).

**Saída observada do teste com mutação ativa (`OBSERVED`):**
```text
[2b/4] Teste 2b: Uninstall Seguro (AN1: prefixo editado; AN2: comentários/aliases customizados; AN3: fail-closed)...
ERRO AN1: uninstall.sh corrompeu configuração do usuário quando prefixo foi editado!
Esperado: 'export A=1' | Obtido: 'export A='
MUTATION TEST FAILED AS EXPECTED WITH EXIT 1
```

O teste detectou e rejeitou a mutação com exit code 1. Após a restauração do código correto, todos os testes retornaram 100% PASS.

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
SUCESSO: 7/7 checagens estruturais documentais passaram.
```

---

## 5. Redes Diferenciais e Suíte Geral

- **Rede Diferencial de Portões e Fuzzing**:
  `python3 -m unittest clearer-engineering/tests/test_gate_differential_fuzz.py clearer-engineering/tests/test_environment_differential.py`
  12.027 casos avaliados contra `d59c943` com **0 relaxamentos** detectados (`OK`).
- **Suíte Oficial Canônica**:
  `bash clearer-engineering/tests/run-all-tests.sh`
  **58/58 Testes Aprovados (100% PASS)**.
