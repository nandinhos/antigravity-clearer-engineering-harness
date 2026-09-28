# Índice de Registros de Decisões Arquiteturais (ADRs) — CEH

Este diretório contém os Registros de Decisões Arquiteturais (*Architecture Decision Records* — ADRs) que governam o design, a segurança, o determinismo e a governança de execução do **CLEARER Engineering Harness (CEH)**.

---

## Tabela Canônica de Decisões Arquiteturais

| ADR | Título | Status | Documento / Referência |
|:---:|---|:---:|---|
| **001** | *Protocolo CLEARER e Semântica de Evidências v1* | **Consolidado** | *Decisões de bootstrap integradas diretamente em [`docs/clearer_protocol.md`](../clearer_protocol.md) e [`docs/evidence_semantics.md`](../evidence_semantics.md) (ver nota abaixo).* |
| **002** | *Topologia de Ambientes e Safety Gates Estáticos* | **Consolidado** | *Regras seminais de ambientes incorporadas diretamente em [`docs/safety_gate.md`](../safety_gate.md) e regras globais (ver nota abaixo).* |
| **003** | Adoção da Epistemologia System One e Qualificação "Like a Jev" | **Aprovado** | [`system-one-epistemology.md`](./system-one-epistemology.md) |
| **004** | Governança de CI Mandatória e Pre-Push Safety Gate (*Zero-Tolerance Pipeline Red*) | **Aprovado** | [`ci-governance-policy.md`](./ci-governance-policy.md) |
| **005** | Desacoplamento entre Estratégia de CI e Runtime Local (Host Nativo vs. Docker/Sail) | **Aprovado** | [`runtime-and-ci-adapters.md`](./runtime-and-ci-adapters.md) |
| **006** | Separação entre Núcleo Portável (Stdlib-Only) e Adaptadores de Host | **Aceito** | [`adr-006-nucleo-e-adaptadores.md`](./adr-006-nucleo-e-adaptadores.md) |
| **007** | Proteção de Integridade do Certificado de CI e Modelo de Ameaças | **Aprovado** | [`adr-007-protecao-certificado-modelo-ameacas.md`](./adr-007-protecao-certificado-modelo-ameacas.md) |

---

## Nota Histórica sobre as ADRs 001 e 002

As decisões de arquitetura de **ADR 001** (concepção do acrônimo CLEARER, divisão de papéis em 7 etapas e taxonomia tripartite `OBSERVED / INFERRED / UNKNOWN`) e **ADR 002** (matriz de rigores de ambientes `DEV / HOMOLOGACAO / PRODUCAO` e controle inicial de comandos destrutivos) foram consolidadas diretamente nas regras core e guias normativos do repositório antes da adoção formal do processo estruturado de ADRs numeradas, que passou a ser registrado a partir da **ADR 003**.

---

## Princípios Arquiteturais Inegociáveis do CEH

1. **Stdlib-Only no Núcleo**: O núcleo de avaliação de regras opera exclusivamente com a biblioteca padrão (Python 3.9+ stdlib), sem dependências externas via pip. Scripts de instalação suportam Bash 3.2+ (fail-closed); orquestradores avançados requerem Bash 4.3+.
2. **Evidência Física sobre Suposição**: Nenhuma alegação de funcionamento ou compatibilidade é aceita sem prova observada (`OBSERVED`) com comando executado e exit code documentado.
3. **Fail-Closed on Real Hazards**: Diante de ambiguidade, incerteza léxica ou caminhos desconhecidos em ambientes protegidos, o harness sempre assume a postura mais segura (`CATASTROPHIC > DENY > ASK > ALLOW`).
