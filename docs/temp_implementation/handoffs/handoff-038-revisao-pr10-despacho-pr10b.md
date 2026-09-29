# Handoff 038 — PR-10 homologado com ressalvas; despacho do PR-10b (diretório .ceh e controle do E11)

**Data/Hora:** 2026-09-27T14:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `2d4af96` (PR-10)
**Antecessor:** [Handoff 037](./handoff-037-revisao-pr08b-pr09-despacho-pr10.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVAS**

Reproduzido de forma independente (`OBSERVED`):

- **Terminal (deny em todos os casos):**
  - leitura com redirecionamento: `cat /tmp/fake.json > .ceh/last-ci-run.json`, `jq … >`, `head … >`, `grep … >>`, `cat >`;
  - caminhos equivalentes: `./.ceh`, `.ceh//`, absoluto, `"$PWD/…"`, `app/../.ceh`, `.c"eh"`, `.CEH`;
  - outras formas: `cd .ceh && echo x > last-ci-run.json`, `ln -sf`, `dd of=`, `rsync`, `install`, `git show … >`, `shutil.copy`, `cp|mv /tmp/x/last-ci-run.json .ceh/`.
- **Leituras (allow):** `cat`, `jq`, `ls .ceh` e o próprio `test-runner.sh`.
- **Ferramentas de escrita** (via stdin real):
  - `write_to_file` e `replace_file_content` (agy), `Write` e `MultiEdit` (Claude), para `.ceh/…` com caminho absoluto, relativo com `Cwd` ou com `..` → deny, exit 2;
  - caminho ausente ou nome de argumento desconhecido → deny (fail-closed);
  - `app/x.php` → agy `{"decision":"allow"}`, Claude `{}`.
- **Falsificabilidade:** num clone, pus `tee` em `ALLOWED_READ_CMDS`, e o `test_cert_protection.py` reprova 2 testes, a mesma saída da evidência.
- ADR 007 publicado. Um único commit certificado e enviado (AK1 cumprido). `pr10-corpus-diff.md` presente (AK2/AK3 cumpridos).

**Linha de base avançada** para `2d4af96`.

**Nota de processo:** o relatório de entrega foi intitulado "PR-10 (G9) Homologado e Enviado". A homologação é da revisão.

## 2. Ressalvas

### AL1 — MÉDIO: substituição do diretório `.ceh` inteiro

O certificado chega com o nome original dentro de um diretório copiado ou movido. Todos saem **allow** (DEV):

- `cp -r /tmp/fakeceh/. .ceh` e `cp -r /tmp/fakeceh/* .ceh/`
- `rm -rf .ceh && cp -r /tmp/fakeceh .ceh`
- `mv /tmp/fakeceh .ceh`
- `rsync -a /tmp/fakeceh/ .ceh/`

A checagem olha o **nome do arquivo** do certificado, e não o **diretório** `.ceh`. Os casos estão na bateria como `PENDENTE:H038-AL1` (5 linhas), com 5 controles.

**Fora do escopo** (backlog, conteúdo opaco): `tar -xf evil.tar`, `unzip`.

### AL2 — ALTO (método): o E11 não tem controle, e a conclusão pode estar invertida

O registro do E11 diz: `{"decision":"allow"}` → o arquivo é gravado; `{}` → "Antigravity CLI did not complete in 30s". A conclusão foi "o agy exige allow explícito". Os mesmos dados admitem a leitura **oposta**:

- `{}` devolve o **fluxo normal de permissão** do agy, que em modo sem interface espera uma confirmação que nunca vem (daí os 30 s);
- `{"decision":"allow"}` **pula** essa confirmação e autoaprova a escrita. É o mesmo F6 do Claude, que nos levou ao PR-00e.

Se essa for a leitura certa, o gate hoje **autoaprova todas as escritas de arquivo** no agy, e talvez os comandos também, contornando a política de permissão do próprio host. A saída é **o controle que faltou**, a mesma lição do Handoff 009 (PR-00d).

Os dados também estão só em prosa. Não há diretório novo em `evidence/host-probe/agy/`.

## 3. Despacho — PR-10b `fix(gate): diretório .ceh protegido + E11 com controle`

1. **AL1:** todo subcomando que **não** seja leitura pura e que tenha um argumento resolvendo para o diretório `.ceh` do repositório alvo, ou para algo dentro dele, → deny. `rm -rf .ceh` sozinho também entra: apagar o certificado bloqueia o push e é o primeiro passo da substituição. As leituras (`ls .ceh`, `cat`, `jq`…) seguem allow. As 5 linhas `PENDENTE:H038-AL1` ficam verdes.
2. **AL2: repetir o E11 com o `host_probe.py`, gravando os artefatos** em `evidence/host-probe/agy/<timestamp>/`: `results.jsonl`, `invocations.jsonl` e a saída do CLI. Três braços, no **mesmo** modo, prompt e `--add-dir`:
   - **E11-controle:** **sem nenhum hook** ativo (CEH e sonda desinstalados). O arquivo é gravado?
   - **E11-allow:** hook respondendo `{"decision":"allow"}`.
   - **E11-vazio:** hook respondendo `{}`.

   Repita o mesmo trio para `run_command` com um comando **não trivial** (por exemplo, `touch <sentinela>`), no modo padrão **e** em YOLO.
3. **Decisão a partir do resultado:**
   - se o controle **não** grava (o agy pede confirmação) e o allow grava → **o allow explícito autoaprova no agy**. Para ferramentas de escrita e comandos, o gate deve devolver no agy o equivalente a "sem decisão": o formato que o controle mostrar que preserva o fluxo nativo. Se nenhum formato preservar esse fluxo, registre como **limite do host** no ADR 007 e decida junto com o desenvolvedor;
   - se o controle **grava** → o allow explícito é neutro, e a implementação atual está correta. Registre como `OBSERVED`.

### Critérios de aceite do PR-10b

- [ ] As 5 linhas `PENDENTE:H038-AL1` ficam verdes, e os controles da bateria seguem verdes.
- [ ] Os artefatos brutos do E11 (controle, allow e vazio, para escrita e comando, em modo padrão e YOLO) estão versionados, com checagem de vazamento. A conclusão cita as linhas dos artefatos.
- [ ] A resposta de allow no agy é ajustada ou confirmada conforme o item 3, com teste.
- [ ] As duas redes diferenciais contra `2d4af96` registram 0 relaxamentos. Um push por commit certificado. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 4. Sequência

PR-10b → Onda 3 (PR-11 instalador honesto, PR-12 SemVer/CHANGELOG) → **tag v1.3.0**.
