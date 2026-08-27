# Evidence Policy & Classification Standards

## 1. Classificação de Fatos
Ao coletar dados ou analisar o projeto, marque o status de conhecimento:
- **OBSERVED**: Diretamente lido de um arquivo, schema, log de execução ou comando executado.
- **INFERRED**: Hipótese ou conclusão deduzida a partir de dados observados (deve ser validada).
- **UNKNOWN**: Informação não presente no contexto ou no repositório.

## 2. Proibição de Hallucination Coding
- Nunca invente assinaturas de funções, tipos, módulos ou variáveis que não existam.
- Se uma classe ou arquivo não for encontrado via busca, registre explicitamente como `UNKNOWN` ou `NOT FOUND`.
- Nunca passe de `UNKNOWN` para `OBSERVED` sem ler o arquivo ou executar o comando.

## 3. Classificação de Claims
Ao emitir relatórios ou responder a auditorias:
- **SUPPORTED**: Há arquivo, linha ou comando que prova a afirmação.
- **PARTIALLY_SUPPORTED**: Há indício, mas falta comprovação completa.
- **UNSUPPORTED**: Não há evidência que sustente a alegação.
