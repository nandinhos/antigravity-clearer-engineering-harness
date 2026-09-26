# Handoff 020 — Revisão da ata do Conselho sobre o PR-05c e ajustes ao despacho

**Data/Hora:** 2026-09-26T04:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Ata revisada:** Conselho `20260925_214340` (codex 0.94, muse 0.82, agy 1.00, todos RESSALVAS)
**Antecessor:** [Handoff 019](./handoff-019-revisao-pr05b.md). O despacho do PR-05c continua valendo, com os ajustes abaixo.

---

## 1. Veredito sobre a ata: **ENDOSSADA COM AJUSTES**

As diretrizes 1, 3, 4 e 5 da ata reproduzem o Handoff 019 corretamente. As notas a seguir decidem os pontos em aberto e corrigem o que a ata deixou de fora.

| Ponto da ata | Decisão | Motivo (`OBSERVED` quando indicado) |
|---|---|---|
| "Função em `rules.py` **ou** `git.py`" | **`ceh_core/git.py`** (novo, ≤ 300 linhas) | O `rules.py` é uma tabela declarativa de regex (70 linhas). Misturar um analisador por tokens nele apaga essa fronteira. |
| Invariante multi-pathspec `any()` | Mantido, mas **não é novo** | Já é o comportamento atual: `git checkout -- ./ app/x.php` = deny (linha H019-U1). O PR tem de preservá-lo, sem apresentá-lo como mudança. |
| Caminho absoluto = amplo (muse) | Aceito (fail-closed) | Descartar arquivo por caminho absoluto é raro. O custo é um falso positivo aceitável; o ganho é não tratar "absoluto dentro do repositório". |
| `normpath` puramente léxico, sem disco (muse) | Aceito | O `rm.py` já segue esse padrão (`os.path.normpath`). Reaproveite a mesma função; não crie uma terceira. |
| Certeza 1.00 (agy) | Não é evidência | A certeza de um conselheiro não substitui a bateria. O que prova o PR-05c são as linhas `PENDENTE` virando verdes. |
| Ata `20260925_214340` | **Fora da branch** | Não está no remoto (`OBSERVED`: só existe `conselho/20260925_151613`). Ela entra no commit do PR-05c, depois da checagem de vazamento. Branch limpa inclui não deixar evidência só local. |

## 2. Achados adicionais desta revisão (a ata não os cobre)

Todos entraram na bateria como `PENDENTE:H020-*` (seção "Handoff 020"), e o teste confirma que hoje falham.

### V1 (formas adicionais): pathspec depois de tree-ish, `-s`/`--source` e magia com `..`

Em produção, `git checkout HEAD src/..`, `git restore -s HEAD src/..`, `git restore --source=HEAD~2 -- src/..` e `git checkout -- ':/app/../..'` saem **allow**. A regra do Handoff 019 só fecha o V1 se o analisador **consumir o valor das opções** (`-s HEAD` é um par) e aplicar a normalização também **depois** da magia `:/`/`:(top)`.

### V4 (falso positivo): a regex de `-f` casa nomes com hífen

`OBSERVED` em produção:

| Comando | Decisão hoje |
|---|---|
| `git checkout feature/add-pdf` | deny |
| `git checkout fix-leaf` | deny |
| `git switch hotfix-ref` | deny |
| `git checkout -- app/self-ref` | deny |

Em staging, esses comandos saem ask. A causa é o padrão `.*-(?:[a-zA-Z]*f…)` em `rules.py:50` e `:53`: ele casa qualquer `-` seguido de letras terminadas em `f`, **inclusive no meio de uma palavra**. É o padrão 1 do Handoff 018 do lado do falso positivo.

### V5 (médio, bypass): `--pathspec-from-file`

`git restore --pathspec-from-file=list.txt` e a mesma opção no `checkout` saem **allow**, embora o conteúdo do arquivo (ou do stdin, com `-`) seja invisível ao gate. **Fail-closed:** trate como amplo.

## 3. Despacho ajustado do PR-05c

Tudo da seção 3 do Handoff 019, e mais:

1. **Um analisador por tokens para `checkout`, `restore` e `switch`** em `ceh_core/git.py`, usando o lexer existente. Ele **substitui** as regex de `rules.py:50–53`. Não pode sobrar regex e analisador decidindo o mesmo comando, porque duas fontes de verdade são como o V4 aconteceu.
   - **Opções curtas:** só um token que começa com **um único** `-` é um agrupamento (`-qf` contém `f`). `--x` é uma opção longa, comparada por inteiro ou por prefixo. Palavras com hífen no meio **nunca** são opções.
   - **Opções que levam valor** (`-s`/`--source`, `-b`/`-c`/`-B`/`-C`, `--orphan`, `--conflict`, `--pathspec-from-file`): consumir o valor, tanto `--x=v` quanto `--x v`.
   - **Posicionais:** depois de `--`, tudo é pathspec. Sem `--` no `checkout`, se houver 2 ou mais posicionais, o primeiro é tree-ish e o resto são pathspecs. Com 1 posicional, avalie-o como pathspec **apenas quanto à amplitude**: um nome de branch como `main` normaliza para ele mesmo e não é amplo. No `restore`, todos os posicionais são pathspecs.
   - **`--pathspec-from-file`** e **`--pathspec-file-nul`** tornam a chamada ampla (V5).
2. **Contrato com a ferramenta real:** o PR cita, de `git checkout --help`, `git restore --help` e `git switch --help` da versão instalada, as linhas que listam as opções que levam valor. Se a lista do código divergir da ajuda, isso tem de ser explicado.
3. **Controles que têm de seguir verdes:**
   - `git checkout -qf main` e `git switch -f hotfix-ref` = deny;
   - todos os controles H017/H019.

### Critérios de aceite (em adição aos do Handoff 019)

- [ ] As 14 linhas `PENDENTE:H019-*` e as 11 linhas `PENDENTE:H020-*` perdem o prefixo, e todas as linhas de controle seguem verdes.
- [ ] `rules.py` não tem mais regex para `checkout`/`restore`/`switch`.
- [ ] O diff do corpus nomeia cada relaxamento. Só são aceitos os do **V3** (`--staged` sozinho) e do **V4** (nomes com hífen).
- [ ] A ata `20260925_214340` está versionada, com a checagem de vazamento registrada.
- [ ] Protocolo 7.1 e `evidence-report --strict` no log de entrega. O status é "pronto para revisão".

## 4. Por que isso importa para os plugins derivados

Essas regex seriam copiadas para todos os hosts. Um analisador por tokens com contrato na `--help` é a mesma peça que o PR-QA (C e D) vai generalizar. Fazer o PR-05c assim evita reescrever a mesma lógica duas vezes.
