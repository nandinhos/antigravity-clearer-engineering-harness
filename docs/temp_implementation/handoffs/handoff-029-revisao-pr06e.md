# Handoff 029 — Revisão do PR-06e e despacho do PR-06f

**Data/Hora:** 2026-09-26T13:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `5f21c12` (PR-06e)
**Antecessor:** [Handoff 028](./handoff-028-revisao-pr06d.md)

---

## 1. Veredito: **NÃO HOMOLOGADO (regressão de uso)**

O que o PR-06e acertou (`OBSERVED`):

- as 19 linhas `PENDENTE:H028` ficaram verdes, e o diff da bateria **só remove prefixos**;
- `KNOWN_PREFIXES` não existe mais; a invariante com prefixo arbitrário (`setsid`, `flock`, `strace -f`, palavra qualquer) está no fuzz;
- diferencial contra `fe171a7`: **0 relaxamentos**;
- as famílias novas funcionam:
  - `php -r` com `shell_exec`, `passthru` e crases;
  - `php -d x=1 -r 'unlink(…)'`;
  - `perl -MFile::Path=rmtree -e 'rmtree "/"'`;
  - `busybox ash -c`;
- os controles seguem allow: `php artisan route:list`, `php -f script.php`, `awk -f prog.awk`, `bun run build` e `deno run main.ts`;
- desempenho: 150 nomes de ferramenta numa linha levam ≤ 0,01 s.

**A linha de base NÃO avança** (segue em `fe171a7`). Assim, a correção do AE1 volta ao comportamento de referência **sem** gerar relaxamento.

## 2. Achados

### AE1 — ALTO (regressão de uso): comandos inofensivos negados como CATASTROPHIC em qualquer ambiente

| Comando (inclusive em DEV) | `fe171a7` | PR-06e |
|---|---|---|
| `brew install git node perl ruby python3` | allow | **deny/CATASTROPHIC** |
| `apt-get install -y git bash perl python3 ruby` | allow | **deny/CATASTROPHIC** |
| `which git bash perl python3 node` | allow | **deny/CATASTROPHIC** |
| `command -v git bash zsh fish` | allow | **deny/CATASTROPHIC** |
| `echo git git git git` | allow | **deny/CATASTROPHIC** (com 3 nomes, allow) |

Motivo registrado pelo gate: *"Limite de profundidade de recursão/desembrulho excedido (depth=4 > 3)"*.

**Causa:** cada sufixo é avaliado com `evaluate_command(depth+1)`, e essa avaliação **reaplica a varredura** nos próprios sufixos. Com 4 nomes de ferramenta, a cadeia chega a `depth=4`, e o limite, que existe contra o aninhamento de **embrulhos**, devolve CATASTROPHIC.

**Por que nada pegou:** o fuzz diferencial só procura **relaxamentos**. Um bloqueio novo (falso positivo) passa despercebido. Um agente com esse gate ficaria impedido de instalar dependências em desenvolvimento.

### AE2 — BAIXO: `awk` com saída canalizada para o shell

`gawk 'BEGIN{print "find / -delete" | "sh"}'` sai allow em DEV, embora o Handoff 028 tenha especificado `print … | "sh"`.

### AE3 — BAIXO: `fish --command=<script>`

`fish --command="find / -delete"` sai allow. Só a forma com espaço é reconhecida.

Todos estão na bateria como `PENDENTE:H029-*` (**7 linhas**), com 5 controles. Dois deles garantem que a correção do AE1 **não** reabre o AD1: `echo git git git git find / -delete` e `setsid nice timeout 5 sudo -u x find / -delete` têm de seguir deny/CATASTROPHIC.

## 3. Despacho — PR-06f `fix(gate): varredura em um nível só, awk | sh e fish --command=`

1. **AE1: a varredura de sufixos roda uma única vez por subcomando.**
   - O sufixo é avaliado **sem** varredura própria (um parâmetro `scan_suffixes=False`, ou equivalente).
   - Os analisadores de cada sufixo (`rm`, `git`, `find`, shells, interpretadores) continuam desembrulhando normalmente, e o desembrulho de um embrulho interno (`sh -c`, `eval`, `-exec`, `os.system`…) volta a ter varredura no **conteúdo** desembrulhado.
   - O limite de profundidade conta **só desembrulhos**, nunca a varredura.
2. **Invariante de benignidade no fuzz**, para que um bloqueio indevido nunca mais passe despercebido:
   - Gere comandos com verbos inócuos (`echo`, `which`, `command -v`, `apt-get install -y`, `brew install`, `pip install`, `npm install -g`, `man`, `ls`) seguidos de **1 a 8** nomes sorteados do conjunto de cabeças analisadas (`git`, `find`, `rm`, `bash`, `python3`, `node`, `perl`, `ruby`, `php`, `awk`…), **sem** nenhum argumento destrutivo.
   - Exija **allow em DEV** para todos.
   - **Falsificabilidade:** reintroduza a varredura aninhada num clone. A invariante tem de reprovar só pela gramática.
3. **AE2:** no programa `awk`, desembrulhe também `print … | "<shell>"` e `printf … | "<shell>"`, avaliando a string impressa como comando.
4. **AE3:** em `fish`, aceite `--command=<script>` e `-c<script>`.

### Critérios de aceite do PR-06f

- [ ] As 7 linhas `PENDENTE:H029-*` ficam verdes, e todos os controles (H017–H029) seguem verdes, inclusive os 2 controles do AE1.
- [ ] O diferencial contra `fe171a7` registra 0 relaxamentos e nenhuma linha nova em justificativas.
- [ ] A invariante de benignidade está no fuzz, com a prova de falsificabilidade.
- [ ] `pr06f-corpus-diff.md` se o corpus mudar. O plano não é editado pelo agente. Protocolo 7.1.

## 4. Encerramento da Onda 1

Continua valendo o compromisso do Handoff 028 §4: com o PR-06f homologado, a Onda 1 fecha. O AE1 não é uma classe nova, e sim uma regressão do PR-06e. AE2 e AE3 são restos do próprio despacho do PR-06e.

## 5. Sequência

PR-06f → **fechamento da Onda 1** → PR-QA B–E → Onda 2 (PR-08 G7, PR-09, PR-10).
