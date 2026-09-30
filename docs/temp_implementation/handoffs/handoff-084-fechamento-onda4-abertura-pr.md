# Handoff 084 — Fechamento da Onda 4: Resolução de Ressalvas, Release 2.0.0 e Abertura do PR

**Data/Hora:** 2026-10-02T15:00:00Z  
**Instância:** Agente executor (Antigravity)  
**Branch:** `feature/onda-4`  
**Antecessor:** [Handoff 083](./handoff-083-pr17-homologado-despacho-fechamento-onda4.md)  
**Status da Onda 4:** Fechamento concluído na branch; ressalvas BJ1–BJ5 sanadas; relatório antes × depois emitido; PR aberto de `feature/onda-4` para `main` (sem merge pelo agente).  

---

## 1. Resolução Integral das Ressalvas BJ1 a BJ5 (Handoff 083)

| Ressalva | Descrição | Resolução Implementada | Evidência / Arquivo |
|---|---|---|---|
| **BJ1** | Caminho real de produção (subprocesso) fora da suíte | Adicionado `test_cross_host_conformance_subprocess_sample` em `test_cross_host_conformance.py` cobrindo o caminho de produção do shim via subprocesso com amostra representativa de 51 comandos (allow, deny, ask) em cada host. | `clearer-engineering/tests/test_cross_host_conformance.py` (4/4 tests OK em 8.29s) |
| **BJ2** | Contagem do corpus de conformidade | Corrigida a contagem para **1.016 comandos × 3 hosts** (1.014 command + 2 integration). A substituição de hooks por `git status` foi eliminada da contagem do corpus principal. | `clearer-engineering/tests/test_cross_host_conformance.py` |
| **BJ3** | `test_mutation_p16.py` fora da suíte | Adicionado explicitamente ao script de execução de testes como teste independente. | `clearer-engineering/tests/run-all-tests.sh` |
| **BJ4** | Testes encadeados com `&&` no `run-all-tests.sh` | Cada teste passou a ter sua própria linha `run_test` identificável. Total de testes expandido para **75**. O cabeçalho de `docs/plano-validacao-revisao-conselho-seniors.md` foi atualizado para `75/75 testes aprovados`, satisfazendo `doc-audit.py` com 7/7 checks aprovados. | `clearer-engineering/tests/run-all-tests.sh`, `docs/plano-validacao-revisao-conselho-seniors.md` |
| **BJ5** | Afirmação não observada sobre IPC da IDE | Removida a especulação sobre "pipes IPC internos" em `docs/adapters/novo-host.md`, mantendo estritamente o fato observado de que a IDE reage ao código de saída do processo do hook. | `docs/adapters/novo-host.md` |

---

## 2. Relatório Final Antes × Depois da Onda 4

O relatório consolidado foi gerado em [docs/temp_implementation/evidence/onda4-relatorio-final.md](../evidence/onda4-relatorio-final.md) com base em métricas medidas no próprio commit:

- **Acoplamento a formato de host fora de `adapters/`**: de 55 referências para **0**.
- **Tamanho do `safety-gate.py`**: de 630 para **94 linhas** (redução de 85%).
- **Suíte de conformidade cross-host**: de 0 para **1.016 comandos × 3 hosts** avaliados (zero divergências).
- **Hosts oficialmente suportados**: de 2 para **3** (Google Antigravity, Claude Code, Muse Code).
- **Suíte de testes canônica**: expandida de 65 para **75 testes** (100% PASS).
- **Defeitos fora de escopo documentados**:
  1. *Fail-open da IDE do Antigravity* com exit 2 (corrigido com exit 0 para negações no Antigravity).
  2. *Fail-open da reserva no Muse Code* com `deny` (corrigido com fallback especializado emitindo `{"decision": "block"}`).
- **Limites conhecidos remanescentes documentados**:
  1. Análise estática léxica (comandos opacos, eval dinâmico, pipelines cegas).
  2. Falha catastrófica da reserva se Python/SO quebrar.
- **Incidentes de processo registrados com transparência**:
  1. Certificado reescrito no `negctl`.
  2. Registro da evidência montada da E14.
  3. `rm -rf /` enviado ao Muse em `--yolo`.

---

## 3. Preparação do Release 2.0.0

1. **`clearer-engineering/plugin.json`**: Atualizado para `"version": "2.0.0"`.
2. **`CHANGELOG.md`**: Bloco `[2.0.0] - 2026-10-02` adicionado cobrindo breaking changes arquiteturais, novos adaptadores, conformidade cross-host e o security fix da reserva especializada.
3. **`README.md` e `README_PT.md`**: Trechos de instalação fixada por SemVer atualizados para `v2.0.0`.

---

## 4. Próximos Passos (Sob Condução do Usuário)

1. **Revisão Final**: O revisor independente (ou Codex) executa a revisão do PR aberto de `feature/onda-4` para `main`.
2. **Merge**: O desenvolvedor/usuário realiza o merge do PR na branch `main`.
3. **Tag Git**: O desenvolvedor/usuário cria e publica a tag `v2.0.0`.
