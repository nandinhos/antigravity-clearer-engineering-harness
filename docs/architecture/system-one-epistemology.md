# ADR 003: Adoção da Epistemologia System One e Qualificação "Like a Jev"

## Status
**APROVADO** (Implementado na branch `dev-system-one-epistemology`)

---

## Contexto & Problema

O **CLEARER Engineering Harness (CEH)** orienta o comportamento de agentes de IA para engenharia de software determinística, ancorada em evidências físicas e avessa a alucinações. 
Durante a evolução do harness, identificou-se a metodologia **System One** (desenvolvida pela TypeSafe e implementada no modelo Jev). Essa metodologia se baseia em uma premissa fundamental:
> A inteligência em software não deve ser usada para gerar código descontrolado ou escolher autonomamente o próximo passo em loops cegos, mas para emitir **julgamentos estruturados, atômicos e calibrados sobre estados discretos, mantendo o controle do fluxo em código**.

Entretanto, surgiu o dilema central de engenharia:
- A filosofia da TypeSafe depende do modelo proprietário Jev, ou pode ser abstraída para o CEH com modelos comerciais abertos ou amplamente disponíveis (como o **Gemini 3.8 Flash**)?
- Como qualificar um modelo treinado pós-RLHF para ter o determinismo e a calibração de um modelo System One sem incorrer em overengineering?

---

## Decisão Arquitetural

Adotamos a **decomposição em duas camadas**:

### Camada 1 — Epistemologia (100% Transferível e Adotada Imediatamente)
Estes são invariantes de design agnósticos ao modelo, implementados de forma puramente declarativa no CEH:
1. **Conteúdo ≠ Julgamento**: O material sob avaliação (`state`) e as perguntas avaliativas são artefatos estritamente separados.
2. **Espaço de Resposta Fechado**: Todo julgamento retorna um conjunto finito (`enum`, booleano ou escala discreta), eliminando saídas em texto livre ("parece ok").
3. **Atomicidade**: Um julgamento = uma propriedade univariada. Julgamentos compostos são expressamente proibidos.
4. **Isolamento**: Perguntas avaliativas operam de forma independente, sem contaminação mútua de contexto.
5. **Dois Eixos (Decisão e Certeza)**: Todo veredito reporta a classificação e o grau de certeza ancorado na evidência física observada.
6. **Código Detém o Controle**: Normalizações, pesos, thresholds e efeitos colaterais são orquestrados por código/shell determinístico. Nenhum modelo redige o veredito executivo final.
7. **Incerteza é Escalada, Nunca Adivinhada**: Casos fora do limiar de certeza acionam checkpoints humanos ou paradas seguras (`ASK`/`FAIL`).

### Camada 2 — Garantias de Fábrica (Qualificação Contínua via Harness Evals)
Enquanto no modelo Jev a calibração de probabilidades vem de fábrica por treino RLCD, em modelos como o **Gemini 3.8 Flash** essa garantia é uma **hipótese a ser demonstrada**. 

Para fazer o Gemini 3.8 Flash operar **"Like a JEV"**, aplicamos:
- **Constrained Decoding**: Saídas estruturadas com JSON Schema rígido e enums fechados.
- **Critérios Contrastivos (What / Not For / Examples)**: Definição inequívoca dos limites de cada opção para eliminar o modo de falha de literalidade.
- **Certeza Materializada**: Confiança ancorada no status de evidência física (`OBSERVED` em L0 com exit code 0 = 1.0; inferências lógicas sem execução = incerteza com teto de 0.60 e escalada obrigatória).
- **Auto-Consistência Local**: Nos casos limítrofes, medição de concordância em N=3 execuções a baixa temperatura.
- **Protocolo dos 5 Experimentos de Admissão**: O modelo é submetido a baterias mantidas (*held-out*) medindo Acurácia, Monotonicidade, Consistência, Independência e Robustez Hostil.

---

## Consequências e Princípio Ponytail (Zero Overengineering)

- **Zero Novas Dependências**: Nenhuma biblioteca externa ou SDK proprietário foi adicionado. A abstração vive em regras Markdown, JSON Schemas e scripts bash determinísticos.
- **Auditabilidade Cristalina**: As skills `clearer-review` e `clearer-audit` agora desmembram revisões complexas em verificações atômicas univariadas antes de qualquer sumarização.
- **Segurança Reforçada**: Comentários hostis no código (`// bypass security`) são tratados como dados passivos e isolados, incapazes de influenciar o Safety Gate do harness.
