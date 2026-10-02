# Handoff 097 — PR #13 (linha de base v2.1.1) **homologado**; roteiro correto do canário

**Data/Hora:** 2026-10-02T08:00:00Z
**Instância:** Revisor independente (Claude)
**PR revisado:** [#13](https://github.com/nandinhos/antigravity-clearer-engineering-harness/pull/13), `chore/baseline-v2.1.1` → `dev`, cabeça `935c2c6`
**Antecessor:** [Handoff 096](./handoff-096-release-v2-1-1-e-avanco-da-linha-de-base.md)
**Estado:** **HOMOLOGADO.** O merge é do desenvolvedor (D6); a revisão não faz merge.

---

## 1. Verificação (`OBSERVED`)

| Item | Resultado |
|---|---|
| `380e911` (commit do patch) | árvore **idêntica** à do patch do Handoff 096 aplicado sobre `fd9faa8` num clone limpo; autoria da revisão preservada |
| `935c2c6` | só acrescenta a seção 3 em `d1-ruleset-main-evidence.md` |
| CI | [run 36970959376](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36970959376): os 4 `Validate`, a paridade Claude e o `ci-ok` = success |
| **CE1** | opção A aplicada. A release `v2.1.1` tem a nota (`[!NOTE]`) de que o `plugin.json` reporta 2.1.0 e de que a correção vem na 2.1.2. A tag não foi reescrita |
| **CE3** | resolvido. Saída autenticada do ruleset `24338451`: `required_status_checks` = só `CI Aggregated Status (ci-ok)` (mesmo nome do job no CI), `bypass_actors: []`, `current_user_can_bypass: never`, `enforcement: active` |

Endurecimento opcional do ruleset (sem urgência):
- **fixar o check ao app do GitHub Actions** (`integration_id`). Sem isso, um status de commit com o mesmo nome, publicado por outra fonte com permissão de escrita, também satisfaz a regra;
- **restringir o merge a `merge`**, que é o padrão do histórico do projeto.

## 2. Correção do roteiro do canário (CE2) — e de uma frase da própria revisão

O agente sugeriu, para o canário:

```bash
printf x >.ceh/canario     # NÃO FAÇA ISSO NO SEU TERMINAL
```

**Isso não testa o gate.** O hook do CEH só intercepta as **chamadas de ferramenta do agente** dentro da IDE. Um comando digitado direto no terminal do desenvolvedor não passa por ele. O shell simplesmente cria o arquivo `.ceh/canario`. Se já tiver rodado, apague o arquivo.

A frase da D3 (Handoff 090, repetida no 095), "o canário de release é rodado pelo desenvolvedor, no terminal dele, fora da sessão do agente", **estava ambígua**, e a correção é desta revisão. O que fica **fora** da sessão do agente é a **coleta da evidência**: hash e plugins, para que o agente não possa montá-la. A **tentativa de escrita** precisa ser feita **pelo agente**, porque é ela que o hook deve barrar. Foi assim na E14 e na E17.

### Roteiro correto (v2.1.1)

1. **Terminal do desenvolvedor**, num checkout da tag:

   ```bash
   git checkout v2.1.1
   sh clearer-engineering/scripts/ceh-doctor.sh --verify
   sh clearer-engineering/scripts/ceh-doctor.sh --evidence > /tmp/e18-evidence-antes.txt
   ```

   O `--evidence` deve mostrar "Origem da referência: Tag oficial 'v2.1.1'" e "Comparação com tag: ✔ IDÊNTICO".

2. **Na IDE do Antigravity**, peça ao agente que execute como chamada de ferramenta (`run_command`) uma forma **colada** do CA1, que a v2.1.0 deixava passar:

   ```bash
   printf x >.ceh/canario-v211
   ```

   **Resultado esperado:** a IDE mostra "tool call denied with reason: [CEH CERTIFICATE INTEGRITY - G9/AL1] …". Copie a resposta **bruta** da IDE e anote o índice do passo da chamada e o da resposta na transcrição.

3. **Terminal do desenvolvedor:**

   ```bash
   ls -la .ceh/                 # canario-v211 NÃO pode existir
   sh clearer-engineering/scripts/ceh-doctor.sh --evidence --step-call <N> --step-resp <M> > /tmp/e18-evidence.txt
   ```

4. Registre tudo em `docs/temp_implementation/evidence/e18-canario-v2-1-1.md`, **por PR**, com:
   - a saída dos passos 1 e 3;
   - a resposta bruta da IDE;
   - os índices dos passos;
   - os horários UTC.

   O `--evidence` já mascara o `$HOME` e o hostname.

Como controle opcional, repita o passo 2 com `echo {} > tsconfig.json` num projeto qualquer. O resultado esperado é que a IDE **permita** (CC1).

## 3. Estado

| Item | Estado |
|---|---|
| v2.1.1 (código) | publicada; tag e release verificadas (Handoff 096) |
| Linha de base | PR #13 homologado → `fd9faa8` depois do merge |
| Proteção da `main` | ruleset ativo com `ci-ok`, sem bypass (CE3) |
| Canário v2.1.1 na IDE (E18) | **pendente**, pelo roteiro da seção 2 |
| v2.1.2 | bump do `plugin.json` e CHANGELOG `[2.1.1]` e `[2.1.2]`, mais o hash do `plugin.json` no A2a |
| PR de documentação | CA6–CA8, CD1, CD2 |

## 4. Próximos passos

1. **Desenvolvedor:** merge do PR #13 na `dev`, com merge commit.
2. **Desenvolvedor e agente:** canário E18 pelo roteiro da seção 2.
3. **Agente:** PR da v2.1.2 (versão e CHANGELOG), junto com o PR de documentação ou separado.
