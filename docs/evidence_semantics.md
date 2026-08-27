# Diretrizes: Semântica de Evidência & Auditoria de Claims

O *CLEARER Engineering Harness* adota uma política rigorosa de classificação de conhecimento para erradicar alucinações e asserções infundadas.

---

## 1. As Três Classes Epistêmicas de Fatos

Ao analisar código, logs, arquivos ou requisitos, toda informação deve ser tratada sob uma das três categorias:

| Categoria | Definição | Exemplos de Origem |
|---|---|---|
| **`OBSERVED`** | Fato comprovado diretamente por observação no repositório ou execução de ferramenta. | Leitura de arquivo com `view_file`, linha exata com `grep_search`, saída de comando de teste com exit code 0, schema em migration. |
| **`INFERRED`** | Conclusão razoável ou dedução lógica apoiada em evidências observadas, mas ainda não testada/demonstrada formalmente. | "Como o projeto usa PHP 8.2 e Composer, supõe-se que podemos usar readonly classes, mas precisamos validar se há suporte no PHPStan do projeto." |
| **`UNKNOWN`** | Informação não encontrada no repositório ou não presente no contexto. | Assinatura de um método não localizado, endpoint não implementado, regra de negócio omitida. |

---

## 2. A Regra de Ouro da Evidência

> [!CRITICAL]
> **UNKNOWN nunca pode silenciosamente virar OBSERVED.**
> É terminantemente proibido inventar arquivos, classes, métodos, endpoints, tabelas, campos ou regras de negócio para preencher lacunas de conhecimento.

Se um símbolo ou arquivo não for encontrado via busca:
1. Declare explicitamente como `UNKNOWN` ou `NOT FOUND`.
2. Não gere implementações imaginárias baseadas no nome do símbolo.
3. Solicite esclarecimento ou conduza investigação adicional.

---

## 3. Classificação de Claims (Auditoria de Alegações)

Toda afirmação técnica sobre o funcionamento, estabilidade ou conformidade de uma entrega deve ser auditada:

| Status do Claim | Critério de Classificação |
|---|---|
| **`SUPPORTED`** | Plenamente demonstrado por evidência concreta (comando executado com saída registrada, teste automatizado passando, diff audit sem achados críticos). |
| **`PARTIALLY_SUPPORTED`** | Evidência parcial existe, mas com ressalvas explícitas (ex: testes de unidade passaram, mas testes de integração não puderam rodar por falta de credencial externa). |
| **`UNSUPPORTED`** | Alegação sem sustentação factual ou que contradiz as evidências reais (ex: afirmar "sem regressões" quando nenhuma suíte de regressão foi executada). |

---

## 4. Proibição de Anti-Padrões de Qualidade

### Anti-Padrão 1: Fake Pass
- **Definição**: Reportar um teste como bem-sucedido quando ele falhou (`exit code != 0`), foi ignorado (`skipped`) ou sequer foi executado.
- **Diretriz CEH**: Se o teste falhar, o status registrado é obrigatoriamente `FAIL` e a falha deve ser investigada.

### Anti-Padrão 2: Hallucination Coding
- **Definição**: Codificar contra APIs, contratos ou propriedades inventadas pela IA sem verificar os schemas e tipos reais do projeto.
- **Diretriz CEH**: Sempre consulte o arquivo de definição antes de instanciar ou chamar qualquer dependência.
