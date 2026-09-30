# Handoff 067 — Fase 0c: P2/P3 aceitos; P1 **não comprovado** e achado **crítico**: o gate da v1.4.0 não bloqueia na IDE do Antigravity

**Data/Hora:** 2026-09-30T18:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — commit `c7a5d65` (Fase 0c), CI [run 36660578413](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36660578413) = success (4/4)
**Antecessor:** [Handoff 066](./handoff-066-fase0b-onda4-certificado-reescrito-no-negctl.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. Veredito

| Item | Veredito |
|---|---|
| **P2** caminhos de home na evidência | ✅ aceito |
| **P3** `doc-audit` cobrindo a evidência | ✅ aceito, com duas ressalvas baixas (§4) |
| **P1** hook ativo na sessão do agente | ❌ **não comprovado**: o canário só bloqueou **depois** de uma edição local, não versionada, no gate instalado |
| **PR-13** | **em espera** até a correção do §3 entrar na `main` |

O relatório do agente diz que a Fase 0c foi "integralmente executada, testada e homologada". A homologação não é do agente (regra fixa desde o Handoff 064).

## 2. O que o log mostra sobre o P1

Sequência registrada no log do agente:

1. `touch .ceh/canario-hook`, `test -e …` e, logo depois, `rm -f .ceh/canario-hook` com `CONFIRMADO_REMOVIDO`. O arquivo foi removido, o que indica que **o canário foi criado** com o gate da v1.4.0 instalado.
2. O agente inspecionou o `guard_audit.log`, instrumentou o `safety-gate.py` (log de depuração em `/tmp`) e **editou o script instalado** do hook.
3. Com a edição, o canário foi bloqueado.

**Causa alegada pelo agente:** o executor de hooks da **IDE** do Antigravity trata qualquer código de saída ≠ 0 como falha do hook e **deixa a ferramenta rodar** (fail-open). Só bloqueia com `{"decision": "deny", …}` no stdout **e exit 0**.

**Isso é coerente com tudo o que já foi observado, e é grave:**

- o `safety-gate.py` da v1.4.0 responde deny com o JSON **e exit 2** (`handle_hook`, `sys.exit(2)` em todos os caminhos de deny e de erro);
- no **agy CLI**, exit 2 e crash bloqueiam (E3, E4, E9 `OBSERVED`, Handoff 007), e JSON deny com exit 0 também bloqueia (E5; a sonda responde deny com exit 0, `host_probe.py:130-137`);
- na **IDE**, se a alegação se confirmar, **todo deny do CEH vira execução**. Isso explica o comando do certificado que passou no Handoff 066 (deny por `PARSER_FAIL_CLOSED`, exit 2 → executado).

A IDE e o CLI são **contextos de host diferentes**: toda a caracterização do agy (E1–E11) foi feita no CLI headless. O agente de desenvolvimento trabalha na IDE.

**Status: `INFERRED`.** Nada disso está versionado: o commit `c7a5d65` não traz a configuração de hooks, a mensagem de bloqueio, o `guard_audit.log`, o diff do script instalado nem o payload real da IDE. Não se publica uma correção de segurança sobre alegação.

**Ponto de processo:** o agente alterou o componente de segurança instalado sem despacho e sem registrar o diff. Por ora, **mantenha** a edição local (ela protege a sessão do agente), mas o diff tem de ir para a evidência (§3, passo 1).

## 3. Despacho — correção de segurança na `main`, fora da Onda 4

A correção muda o código de saída das respostas do agy, e o A3 da Onda 4 proíbe exatamente isso. Portanto ela vai **para a `main` como v1.4.1** e depois entra na `feature/onda-4` por merge.

### Passo 1 — Evidência E13 (IDE do Antigravity), versionada

Em `docs/temp_implementation/evidence/host-probe/agy-ide/<timestamp>/`, com caminhos e identificadores mascarados:

1. Versão da IDE e a configuração de hooks que ela carrega (onde está e o que aponta para o `safety-gate.py`).
2. `diff -u` entre o `safety-gate.py` **instalado hoje** e o da `v1.4.0`.
3. **Payload real** que a IDE envia ao hook (formato, chaves, `Cwd`). Se já estiver no log de depuração, grave essas linhas.
4. Braços com a **sonda** (`host_probe.py`), sem o CEH, na mesma sessão da IDE e com o mesmo canário (`touch` de um sentinela num diretório temporário, nunca no `.ceh/`):

   | Braço | Resposta da sonda | Esperado se a alegação for verdadeira |
   |---|---|---|
   | controle | sem hook | executa |
   | deny/0 | `{"decision":"deny",…}`, exit 0 | **bloqueia** |
   | deny/2 | o mesmo JSON, exit 2 | **executa** |
   | exit2 | exit 2 sem JSON | executa |
   | crash | exceção, exit 1 | executa |
   | allow | `{"decision":"allow"}`, exit 0 | executa |

5. Um último braço com o **CEH v1.4.0 oficial** reinstalado (sem a edição local) e o canário `touch .ceh/canario-hook`: se executar, o defeito fica `OBSERVED` de ponta a ponta. Depois reaplique a edição local até a v1.4.1 existir.

Nenhuma execução descartada em silêncio (AM1). Se algum braço contrariar a alegação, **pare e relate**.

### Passo 2 — `fix(hook): deny bloqueante na IDE do Antigravity` (branch a partir da `main`, PR para a `main`)

Só depois do E13 confirmar o defeito:

1. Para payload do Antigravity (`toolCall`), deny e erro respondem com o JSON de deny e **exit 0**. Isso bloqueia no CLI (E5) e na IDE (E13).
2. Para payload do Claude Code, **nada muda** (`hookSpecificOutput` + exit 2 bloqueia, E5/E9).
3. Para payload **não identificável** (vazio, não JSON, não objeto), escolha a resposta que bloqueia nos três contextos observados e justifique na evidência com os braços do E13. Nenhum caminho de erro pode depender de exit ≠ 0 na IDE.
4. **A1 idêntico** (nenhuma decisão muda). No A3, só mudam os códigos de saída das linhas deny do agy. Liste cada linha na evidência.
5. Teste por subprocesso (stdin real): o deny do agy sai com exit 0 e JSON de deny; o do Claude, com exit 2; o erro com payload inválido bloqueia. Prova por mutação num clone: voltar o exit 2 no agy reprova o teste.
6. Ponta a ponta: com a v1.4.1 instalada pelo `install.sh`, **sem edição local**, o canário `touch .ceh/canario-hook` é bloqueado na IDE. Grave a mensagem.
7. CHANGELOG `[1.4.1]` em **Security**: "na IDE do Antigravity, o gate da v1.4.0 não bloqueava (deny com exit 2 era tratado como falha do hook)", com o aviso para atualizar. `plugin.json` = 1.4.1. **A tag é do desenvolvedor**, depois da revisão.

### Passo 3 — Voltar à Onda 4

Merge da `main` (v1.4.1) na `feature/onda-4`, retrato regenerado **uma vez** a partir da v1.4.1, registrando que A1, A2a, A2b e A4 não mudaram e listando as linhas do A3 que mudaram. Revisão curta, e só então o PR-13.

## 4. Ressalvas baixas do P3 (carona no Passo 2)

- **AZ1:** a isenção por prefixo sem a barra final também isenta qualquer usuário cujo nome **comece** por `user`. Use só o prefixo com a barra final.
- **AZ2:** a exclusão da pasta `onda4/` é desnecessária: o único caminho de home ali é `/home/user` (sintético, 9 ocorrências no A1), já coberto pela isenção. Remova a exclusão para a pasta voltar à auditoria.
- **AZ3:** a prova por mutação do P3 rodou num script temporário, apagado depois, sem registro versionado. Registre o comando e a saída na evidência.

## 5. Critérios de aceite

- [ ] E13 versionado: configuração de hooks, diff do script instalado, payload real da IDE e os 6 braços + o braço do CEH oficial.
- [ ] Defeito `OBSERVED` antes de qualquer correção; se não se confirmar, parar e relatar.
- [ ] Correção na `main` por PR: exit 0 no deny do agy, Claude inalterado, erro bloqueando nos três contextos, A1 idêntico, linhas do A3 listadas, teste com prova por mutação, canário bloqueado com a instalação oficial.
- [ ] AZ1–AZ3 resolvidas.
- [ ] CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente. Nada é escrito no `.ceh/` pelo agente (o canário só **tenta**).
