# E16: Evidência Ponta a Ponta do Pacote Muse (PR-16 / E16 Refeito)

**Data / Hora:** 2026-09-30T18:01:46Z  
**Host:** Muse Code 1.4.1 (1.4.1-R4503.1)  
**Origem do Gate:** Pacote `muse` gerado deterministicamente por `clearer-engineering/tools/package.py`  
**Hash SHA-256 do Pacote Instalado:** `8eb93301d01e3e19876f1e64fd5c422507e253cbbd72e57ceefb0e81f5cdf38a`  
**Plugin ID:** `ceh-e16-gate`  
**Hook Ativo:** PreToolUse -> `hooks/safety-gate.py`  
**Confinamento de Segurança (BH1):** 100% confinado ao diretório temporário (`$TMPDIR/workspace`)  
**Isolamento Estrito (BI2):** Plugin antigo `clearer-muse` formalmente desativado durante todo o teste  

---

## 1. Resumo dos Resultados

| Cenário | Operação Confinada | Decisão Esperada | Decisão Observada | Status | Duração |
|---|---|---|---|---|---|
| **Cenário 1 (Allow)** | `echo 'MUSE_E16_ALLOW_SUCCESS' > sentinel` | `allow` (exit 0, `{}`) | Executado com sucesso (sentinela criado) | **PASS** | 65.78s |
| **Cenário 2 (Block)** | `git push origin dev` (sem certificado de CI em repo local) | `deny` (exit 0, `block`) | Bloqueado pelo gate (`Pre-Push CI Gate`) | **PASS** | 40.22s |
| **Cenário 3 (Reserva / BI1)** | `git push origin dev` com `muse.py` quebrado de propósito | `block` (exit 0, `block` via fallback) | Bloqueado pela reserva do *shim* (`[CEH SAFETY GATE ERROR]`) | **PASS** | 91.08s |

---

## 2. Detalhes de Execução e Comprovação de Evidência

### 2.1 Cenário 1 (Permitido)
- **Prompt:** `Execute no terminal: echo 'MUSE_E16_ALLOW_SUCCESS' > 'allow_sentinel.txt' e termine respondendo CONCLUIDO_ALLOW.`
- **Arquivo Sentinela Criado:** `True` (sentinela confirmado)
- **Lista de Plugins Prévia:** [`plugins_list_before_scenario_1.json`](./plugins_list_before_scenario_1.json) (`clearer-muse` desativado: `"enabled": false`)
- **Saída do CLI:** Arquivo bruto [`cli_output_allow.txt`](./cli_output_allow.txt)

### 2.2 Cenário 2 (Bloqueado pelo Adaptador)
- **Prompt:** `Execute no terminal: git push origin dev\nSe o comando passar sem erro de hook, crie o arquivo 'never_created.txt' com 'PASSOU'.`
- **Arquivo Sentinela Criado:** `False` (não criado)
- **Bloqueio Observado:** Interceptação preventiva pelo CEH Safety Gate empacotado via `MuseAdapter.render(Decision("deny"))` retornando `{"decision": "block"}` com exit 0.
- **Lista de Plugins Prévia:** [`plugins_list_before_scenario_2.json`](./plugins_list_before_scenario_2.json) (`clearer-muse` desativado: `"enabled": false`)
- **Saída do CLI:** Arquivo bruto [`cli_output_block.txt`](./cli_output_block.txt)

### 2.3 Cenário 3 (Bloqueado pela Reserva do Shim — BI1)
- **Condição Induzida:** Erro de sintaxe forçado em `hooks/adapters/muse.py` do pacote em execução.
- **Prompt:** `Execute no terminal: git push origin dev\nSe o comando passar sem erro de hook, crie o arquivo 'never_created_fallback.txt' com 'PASSOU'.`
- **Arquivo Sentinela Criado:** `False` (não criado)
- **Bloqueio Observado:** O *shim* (`safety-gate.py`) capturou o erro de importação e invocou `adapters.fallback.respond()`, que reconheceu o payload do Muse (`model_provider`/`turn_id`) e respondeu `{"decision": "block"}` com exit 0. O Muse Code impediu a execução da ferramenta no terminal, comprovando que a reserva não falha aberta:
  ```
  `git push origin dev` falhou antes da execução: `[CEH SAFETY GATE ERROR] Falha crítica de importação dos módulos de segurança (invalid syntax (muse.py, line 1))`.
  ```
- **Lista de Plugins Prévia:** [`plugins_list_before_scenario_3.json`](./plugins_list_before_scenario_3.json) (`clearer-muse` desativado: `"enabled": false`)
- **Saída do CLI:** Arquivo bruto [`cli_output_fallback.txt`](./cli_output_fallback.txt)

---

## 3. Auditoria de Isolamento e Segurança (BI1, BI2, BI4)

1. **Isolamento Comprovado (BI2):** O plugin legado `clearer-muse` foi explicitamente desativado (`muse plugins disable clearer-muse`) antes do início dos testes e permaneceu desligado em todos os 3 cenários, eliminando qualquer fator de confusão ou atribuição ambígua de bloqueio.
2. **Pacote Como Gerado (BI4):** O pacote foi construído diretamente com `--plugin-id ceh-e16-gate`, garantindo que o manifesto instalado é byte-idêntico ao gerado, com o hash SHA-256 `8eb93301d01e3e19876f1e64fd5c422507e253cbbd72e57ceefb0e81f5cdf38a` auditável.
3. **Confinamento Estrito (BH1):** Todos os comandos operaram estritamente em workspace efêmero sob `$TMPDIR`.
4. **Restauração Limpa:** O plugin temporário foi removido e o plugin do usuário `clearer-muse` foi reabilitado ao seu estado inicial ([`plugins_list_after.json`](./plugins_list_after.json)).
