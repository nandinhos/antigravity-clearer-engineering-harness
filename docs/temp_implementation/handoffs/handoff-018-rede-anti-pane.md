# Handoff 018 — Rede anti-pane: versão do Python, causa raiz das falhas recorrentes e novos testes

**Data/Hora:** 2026-09-26T01:30:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Antecessor:** [Handoff 017](./handoff-017-revisao-pr04d-pr05-e-despacho-pr05b-pr06.md) (seus despachos PR-05b e PR-06 continuam valendo, com os acréscimos da seção 4)
**Pergunta do desenvolvedor:** *"E se atualizarmos a versão do Python para rodar tudo na mesma versão?"*

---

## 1. Resposta com evidência: a versão do Python **não** é a causa das panes

**Experimento (`OBSERVED`):** as 123 linhas da bateria executável (seção 3), cobrindo todos os achados dos Handoffs 014–017, rodadas em Python **3.9, 3.10, 3.11 e 3.12** produzem **o mesmo resultado, byte a byte** (md5 `91af00da51bf` nas quatro).

| Achado recente | Natureza | Mudaria com outra versão de Python? |
|---|---|---|
| R1, S1 (alargar o `allow`) | correção ampla demais | Não |
| R2, T1, U1 (`//`, `build/../src`, `./`) | comparar literais em vez de normalizar | Não |
| R3 (motivo com evidência fixa) | texto fixo no código | Não |
| U2 (`-P`) | lista de opções incompleta (falha de especificação **minha**) | Não |
| U4 (bateria fora do corpus) | processo | Não |
| Q4 (crash em 3.8/3.9) | **o único** relacionado à versão | Já corrigido (`__future__` + piso 3.9 + CI 3.9/3.12) |

**Recomendação: não fixar uma versão única.**
- O hook roda com o `python3` do PATH do **host** (`OBSERVED` no `agy`: 3.12.3 em Linux; o Python do sistema no macOS é 3.9). O plugin não controla isso.
- Fixar uma versão exata faria o hook **não encontrar o interpretador** nas máquinas que não a têm. No `agy`, isso bloquearia tudo (fail-closed). No **Claude, liberaria tudo** (fail-open, `OBSERVED` no Handoff 005).
- O que já existe é o certo, com custo mínimo: **piso 3.9 verificado no `install.sh` e a matriz 3.9 + 3.12 no CI**. Isso pega qualquer diferença de versão antes do merge.
- Melhoria opcional e barata (seção 5, item E): registrar na instalação **qual** interpretador passou no autodiagnóstico e avisar quando o do hook for diferente.

## 2. A causa real das panes (4 padrões recorrentes)

1. **Comparar literais em vez de canonicalizar** (R2, T1, U1). Cada correção enumerava formas conhecidas, e a próxima forma equivalente escapava.
2. **Alargar o `allow` para consertar um falso positivo** (R1 → S1). A correção de DEV liberou **produção**, e ninguém mediu o lado do `allow`.
3. **Especificação por memória** (U2, meu). A lista de opções não foi conferida com a ferramenta real, embora `git --help` liste `-P` explicitamente.
4. **Bateria de revisão que não vira teste** (U4). O que a revisão descobre não fica protegido depois dela.

## 3. Já entregue neste handoff (mitigação do padrão 4)

- **`tests/fixtures/review_batteries.txt`**: as baterias dos Handoffs 014–017 com o **resultado esperado** de cada linha (`env|esperado|referência|comando`).
- **`tests/test_review_batteries.py`**, na suíte canônica (52 testes):
  - linhas normais têm de passar;
  - linhas `PENDENTE:<ID>` (hoje: U1, U2 ×2, U3 ×2 e 8 do G5) têm de **continuar falhando**. Se uma passar, o teste falha pedindo a remoção do prefixo, para que a correção fique registrada no mesmo PR.
- O mecanismo já provou valor na criação: eu tinha marcado `find . -exec rm -rf {} +` como pendente, mas ele já é negado. O teste recusou a marcação errada.
- **Regra a partir de agora:** toda revisão entrega a sua bateria **como linhas deste arquivo** no commit do handoff. Nenhuma bateria fica só em texto.

## 4. Acréscimos aos despachos do Handoff 017

- **PR-05b:** fecha U1, U2 e U3 **removendo o prefixo `PENDENTE`** das 5 linhas correspondentes. Sem isso, o teste de baterias reprova.
- **PR-06:** fecha o G5 removendo o `PENDENTE` das 7 linhas G5 restantes; os controles G5 já estão no arquivo e têm de seguir verdes.

## 5. Despacho — PR-QA `test(gate): rede anti-pane` (depois do PR-06, antes da Onda 2)

- **A — Fuzz diferencial contra a linha de base (padrão 2).**
  - Novo `tests/tools/diff_gate.py`: extrai o gate de um commit de referência (`tests/fixtures/gate_baseline.txt`, com o sha homologado mais recente) para um diretório temporário.
  - Gera ≥ 3000 comandos por gramática com semente fixa: `rm` com flags e caminhos (relativos, absolutos, `..`, globs, variáveis), `git` com opções globais e pathspecs, `find` com ações, one-liners.
  - Avalia cada comando no gate **antigo e no novo**, nos 3 ambientes.
  - **Regra:** qualquer transição que **relaxa** (`deny→ask|allow`, `ask→allow`, ou saída de `CATASTROPHIC`) tem de constar em `tests/fixtures/relaxamentos_justificados.txt`, com o ID do achado. Relaxamento não listado **reprova**.
  - Esse mecanismo teria pegado o S1 **sem que ninguém imaginasse o caso**.
- **B — Invariante de integridade do motivo (R3).** No fuzz, para toda decisão, o motivo não pode citar um ambiente diferente do decidido, nem conter uma fonte de evidência fixa.
- **C — Contrato com a ferramenta real (padrão 3).**
  - Teste que lê `git --help`, extrai todas as opções globais da linha `usage:` (hoje, no git 2.43: `-v`, `-h`, `-C`, `-c`, `--exec-path`, `--html-path`, `--man-path`, `--info-path`, `-p`, `--paginate`, `-P`, `--no-pager`, `--no-replace-objects`, `--bare`, `--git-dir`, `--work-tree`, `--namespace`, `--config-env`) e **exige que cada uma esteja classificada** no gate (inócua ou fail-closed). Opção nova não classificada reprova.
  - O mesmo para `rm --help`: todas as flags reconhecidas pelo parser do `rm.py`.
- **D — Canonicalização única (padrão 1).** `rm`, pathspec do `git` e o caminho inicial do `find` passam a usar **uma única função** de normalização de caminho em `ceh_core`, com o fuzz de invariantes do PR-04d estendido a pathspecs do git.
- **E (opcional) — interpretador registrado.** O `install.sh` grava em `~/.gemini/config/plugins/clearer-engineering/.ceh-python` o `sys.executable` e a versão que passaram no autodiagnóstico. O `preflight.sh` avisa se o `python3` do PATH for outro.

## 6. Critérios de aceite do PR-QA

- [ ] A: `diff_gate.py` na suíte; com o S1 reintroduzido numa cópia, a suíte **falha** apontando o relaxamento (prova de falsificabilidade no PR).
- [ ] B: invariante no fuzz; com o texto fixo do R3 reintroduzido, falha.
- [ ] C: com `-P` removido da lista de inócuas, falha nomeando `-P`.
- [ ] D: uma única função de normalização; o fuzz cobre `rm`, pathspec e `find`.
- [ ] Suíte, evals, `doc-audit`, Python 3.9/3.12 e protocolo 7.1.
