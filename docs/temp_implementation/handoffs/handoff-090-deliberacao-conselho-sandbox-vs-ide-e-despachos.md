# Handoff 090 — Deliberação do Conselho: Sandbox × IDE, Barreira no Servidor e Despachos

**Data/Hora:** 2026-10-01T11:05:00Z  
**Origem:** Conselho de Seniores (Sessão `20261001_090830`)  
**Documento Avaliado:** [Handoff 089](./handoff-089-plano-deliberacao-sandbox-vs-ide.md) (commit `bfa3654`)  
**Ata Consolidada:** [`docs/temp_implementation/conselho/20261001_090830/ata_conselho.md`](../conselho/20261001_090830/ata_conselho.md)  
**Quórum Ativo:** 5 conselheiros votantes (`claude`, `codex`, `muse`, `hermes`, `agy`). *(O CLI `agent` finalizou com erro de conexão RPC).*

---

## 1. Resultado Coletivo da Deliberação

### **Veredito da Banca: HOMOLOGADO COM RESSALVAS**
- **Votos Homologado Direto:** 0 / 5
- **Votos com Ressalvas Construtivas:** 5 / 5
- **Votos Desfavoráveis (Rejeição):** 0 / 5
- **Nível Médio de Certeza:** 0.89

A banca de seniores chancelou a premissa fundamental do Handoff 089: **um controle só vale no ambiente em que foi observado**. A fragilidade das camadas exclusivamente locais (hook e certificado) diante de falhas de runtime e manipulação de arquivos foi reconhecida como o motor dos 9 incidentes da trilha.

---

## 2. Quadro Consolidado de Decisões (D1 a D6)

| Decisão | Veredito Consensual | Recomendações e Ressalvas Bloqueantes |
|---|:---:|---|
| **D1: Barreira no Servidor (`main`)** | **Opção A** *(Unânime)* | **Ruleset na `main` com PR obrigatório e 0 aprovações** (com único mantenedor, exigir aprovação trava o merge e força bypass). **Bypass list vazia**. Criar job agregador estável `ci-ok` (`needs: validate`) para desvincular os checks da nomenclatura da matriz de SO/Python. Prova de ativação via consulta autenticada à API e prova negativa com push direto rejeitado. |
| **D2: Matriz Sandbox vs CI vs IDE** | **Aprovada com Adendos** | Adicionar à matriz: (1) **`agy` CLI Headless** (ciclo de processo e exit 2 diferem do webview da IDE); (2) desdobrar **IDE Linux vs IDE macOS** (semântica APFS case-insensitive e symlinks de `/var`). Prova de proteção da `main` no Sandbox só vale como `OBSERVED` se a API retornar o ruleset ativo. |
| **D3: Evidência da IDE via Script** | **Opção A** *(Gravação C descartada)* | **Fundir `ceh-ide-probe` no `ceh-doctor --evidence`** (anti-overengineering: evita 2 scripts com 80% de duplicação). Desenvolver estritamente em **POSIX `sh` puro** (compatível com `/bin/sh` do macOS e bash 3.2), sem GNU-ismos (`readlink -f`, `date --iso`), com Python opcional para não reproduzir o fail-open do ADR 007. |
| **D4: Paridade nos Testes** | **Aprovada com Hardening** | **Casefold incondicional (`lower()`)** no basename do comando invocado e alvos sensíveis (`GIT`, `.CEH`). A banca rejeitou categoricamente tratar o caso do macOS como "limite documentado" — deve ser bloqueado no parser do gate. Substituir teste estático frágil de grep por helper canônico com `realpath/resolve()`. |
| **D5: Fechamento v2.1.0 (CA1/CA2)** | **PR Único (`v2.1.1`)** | Correção e corpus dourado são estritamente acoplados. **Ordem dos commits**: (1) Correção do CA1 cobrindo `realpath`, symlinks e casefold; (2) Casos de teste F01–F10; (3) Avanço do `gate_baseline`. CA5 a CA8 tramitam em PR separado de documentação. |
| **D6: Formalização de Papéis** | **Aprovada Integralmente** | A ata do Conselho registra deliberação de arquitetura e processo; **nunca substitui a evidência física de teste (`OBSERVED`) com comando registrado e exit code 0**. Um "homologado" sem comando reproduzível é inválido. |

---

## 3. Despacho Soberano do Desenvolvedor

Com base na deliberação unânime do Conselho de Seniores e no protocolo CLEARER, ficam determinados os seguintes despachos executivos:

### Despacho 1 — Execução da D1 (Barreira no Servidor)
- **Ação:** Configuração de Ruleset na branch `main` no GitHub via interface web ou API.
- **Parâmetros:**
  - Exigir Pull Request antes do merge;
  - Aprovações obrigatórias: **0**;
  - Bloquear force push e deleção de branch;
  - Lista de bypass: **Vazia** (sem exceção para administradores);
  - Status check obrigatório: `ci-ok` (após PR de D4) ou os 4 jobs `Validate` atuais.
- **Validação:** Tentativa intencional de push direto na `main` rejeitada pelo servidor com stderr capturado.

### Despacho 2 — Abertura do PR de Infraestrutura (D4 + D3 + D2/D6)
- **Escopo:**
  1. Criação do `ceh-doctor` em POSIX `sh` com `--evidence` (unificação de D3 e D4);
  2. Adição do job agregador `ci-ok` no CI e do runner com variáveis `CLAUDE*`;
  3. Implementação do `lower()` incondicional no parser do gate local;
  4. Atualização da matriz de ambientes e papéis no guia de contribuição (D2 e D6).

### Despacho 3 — Abertura do PR v2.1.1 (D5: CA1 e CA2)
- **Escopo:**
  1. Correção cirúrgica de redirecionamento contra `.ceh/` (resolução canônica com `realpath`/symlink/casefold);
  2. Inclusão dos casos F01–F10 no corpus dourado (`gate_corpus.expected.jsonl`);
  3. Atualização do `gate_baseline` para v2.1.1;
  4. Emissão da evidência da IDE selada pelo `ceh-doctor --evidence`.

---

## 4. Registro de Pareceres Individuais

- [Parecer Claude (Revisor Sênior / Ponytail Lead)](../conselho/20261001_090830/parecer_claude.md) — *Certeza: 0.78*
- [Parecer Codex (Arquiteto de Lógica Formal & Algoritmos)](../conselho/20261001_090830/parecer_codex.md) — *Certeza: 0.86*
- [Parecer Muse (Sistemas POSIX & Portabilidade Linux/macOS)](../conselho/20261001_090830/parecer_muse.md) — *Certeza: 0.86*
- [Parecer Hermes (Tooling MCPs & Confiabilidade de Agente)](../conselho/20261001_090830/parecer_hermes.md) — *Certeza: 0.88*
- [Parecer AGY (Guardião do Harness & Safety Gate)](../conselho/20261001_090830/parecer_agy.md) — *Certeza: 0.95*
