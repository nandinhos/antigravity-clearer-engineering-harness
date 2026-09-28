# Handoff 027 — Revisão do PR-06c e despacho do PR-06d (fechamento da classe de prefixos)

**Data/Hora:** 2026-09-26T11:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `3ac81b0` (PR-06c)
**Antecessor:** [Handoff 026](./handoff-026-revisao-pr06b.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVAS**

Reproduzido de forma independente (`OBSERVED`):

| Item | Prova |
|---|---|
| AB1/AB3 | As 15 linhas `PENDENTE:H026` ficaram verdes; o diff da bateria **só remove prefixos**. `resolve_command_head` e `substitute_positional_args` estão em `lexer.py`, e as listas de prefixo dos analisadores **sumiram** (`grep` só encontra o `lexer.py`). |
| Diferencial contra `75a763a` | 0 relaxamentos. Das 29 sondas da revisão, 20 passaram a negar (`timeout -s KILL 10 find /`, `chrt -f 99 find /`, `sudo -E env X=1 nice timeout 5 find /`, `su - root -c`, `watch -d -n 1`, `nice -n -5 git checkout -- .`…). Os controles (`nice npm test`, `timeout 30 npm run build`, `sudo -u deploy systemctl status nginx`) seguem allow. |
| Falsificabilidade da invariante de prefixos | Num clone, desliguei o ramo `nice`. Com corpus e bateria vazios, o fuzz reprova com **533** violações; o agente registrou 527, e a diferença vem só de como o ramo foi desligado. |
| Tempo | Fuzz completo em 8,5 s (3 testes, 11.850 casos). |
| Processo | O relatório `--strict` **recusou** a afirmação "Suíte canônica 53/53 PASS" na primeira tentativa: o Z1 funcionou em uso real. O agente não editou o plano, e o push só ocorreu depois de `decision: allow`. |

**Linha de base avançada** para `3ac81b0`. As justificativas seguem vazias e o fuzz, verde.

## 2. Achado AC1 — MÉDIO: opção de prefixo que recebe valor vira a "cabeça"

`OBSERVED` em produção. Todos saem **allow**, e o resultado é igual em `75a763a`, então não é regressão:

| Comando | Por quê |
|---|---|
| `sudo --user deploy find / -delete` | `--user` não está na tabela de opções com valor; `deploy` vira a cabeça. |
| `sudo -iu root find / -delete` | Opções agrupadas cuja última letra recebe valor (`-iu root`). |
| `taskset -c 0 find / -delete` | Com `-c`, o `taskset` não tem máscara posicional, mas o código consome mais um token: `find`. |
| `xargs --max-args 1 find / -delete` | Forma longa com valor separado. |
| `env -S 'find / -delete'` | `-S`/`--split-string` é um **executor de string**, não uma opção comum. |

**Causa:** tabelas de opções escritas de memória, por prefixo. É o padrão 3 do Handoff 018 (especificação por memória) e a mesma classe do W2. Continuar completando tabelas não fecha a classe. O próximo contorno seria outra opção esquecida.

## 3. Despacho — PR-06d `fix(gate): varredura de sufixos após prefixo (fail-closed)`

1. **Rede fail-closed, sem depender de tabela de opções.**
   - Quando a cabeça **original** (`tokens[0]`, pelo nome base) é um prefixo conhecido, o gate também avalia **cada sufixo** que começa num token cujo nome base é uma **cabeça analisada**: `rm`, `git`, `find`, `sh|bash|zsh|dash`, `python*`, `node`, `perl`, `ruby`, `eval`, `su`, `watch`.
   - A decisão é a mais severa (regra de composição do PR-06b).
   - Assim, `sudo --user deploy find / -delete` é avaliado também a partir de `find` → CATASTROPHIC, **seja qual for** a opção que o `resolve_command_head` não conhece.
   - **Custo aceito e registrado no PR:** um valor de opção igual ao nome de um comando (`sudo -u git …`) pode gerar falso positivo, sempre na direção fail-closed.
2. **`env -S`/`--split-string`** entra como executor de string em `resolve_command_head`, com a string avaliada recursivamente.
3. **`taskset`:** só consome a máscara posicional se **não** houver `-c`/`--cpu-list`. Os agrupamentos que terminam em opção com valor (`-iu X`) consomem o valor. Mesmo com a rede do item 1, isso é correção de semântica: evita que `taskset` consuma `find` como máscara.
4. **Invariante de prefixo com opções que recebem valor:** acrescente à lista da invariante `sudo --user x`, `sudo -iu x`, `taskset -c 0`, `xargs --max-args 1`, `nice --adjustment 5`, `timeout --signal KILL 5` e `env -S` (forma de string).
   - **Falsificabilidade:** desligue **só a varredura de sufixos** (item 1). A invariante tem de reprovar pela gramática, com corpus e bateria vazios, para `sudo --user x`.

### Critérios de aceite do PR-06d

- [ ] As 6 linhas `PENDENTE:H027-AC1` ficam verdes, e todos os controles (H017–H027) seguem verdes.
- [ ] O diferencial contra `3ac81b0` registra 0 relaxamentos e nenhuma linha nova em `relaxamentos_justificados.txt`.
- [ ] A prova de falsificabilidade da varredura de sufixos está no `pr06d-evidence.md`.
- [ ] `pr06d-corpus-diff.md`, se alguma decisão do corpus mudar. O plano não é editado pelo agente. Protocolo 7.1, com o gate conferido **em passo separado**.

## 4. Critério de encerramento da Onda 1 (fixado agora, para não virar alvo móvel)

A Onda 1 fecha quando o PR-06d for homologado **e** uma rodada completa de revisão não encontrar contorno nas classes G1–G6: `rm`, `git`, `find`, interpretadores, embrulhos e prefixos.

- Achados **fora** dessas classes vão para o backlog, não reabrem a Onda 1. Exemplos: `curl | bash`, código vindo de arquivo ou do stdin.
- Achados **dentro** dessas classes, mas cuja exploração exige construção dinâmica (concatenação de strings em tempo de execução, `getattr`, `eval` de código gerado), também vão para o backlog. Esses entram como **limite documentado** do gate estático.

## 5. Sequência

PR-06d → fechamento da Onda 1 → PR-QA B–E → Onda 2 (PR-08 G7, PR-09, PR-10).
