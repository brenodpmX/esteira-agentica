# Visão de Produto — Exemplos de configurações de Esteira

Status: recomendada para aprovação de negócio
Owner: product
Última atualização: 2026-08-22

## Visão

A Esteira Agêntica deve ser apresentada por exemplos completos, compreensíveis e executáveis que funcionem como uma vitrine: em vez de exigir que um prospect imagine o produto a partir de conceitos ou monte a configuração do zero, os exemplos mostram usos possíveis, resultados e limites em condições reproduzíveis.

Esta entrega é uma aposta de descoberta para um produto novo. Ela não promete conversão comercial nem comprova retorno financeiro; cria material demonstrável e evidencia se o público reconhece utilidade suficiente para querer avaliar o produto.

## Entradas consideradas

- Issue #93 e entrevista registrada em seu histórico.
- `README.md` e `doc/runbook/docker.md`.
- Estrutura vigente de contextos em `contexts/<plataforma>/<agente>.md`.
- Pesquisa de práticas de onboarding e descoberta em CrewAI, AutoGen Studio, LangGraph e n8n.

Os templates citados na tarefa (`.kiro/templates/docs/`) não estão presentes na branch `origin/main`; foram usados como referência estrutural os documentos de produto equivalentes já versionados em `doc/product/`.

## Público e momento inicial

O primeiro público externo é uma empresa de tecnologia que desenvolve software próprio e está iniciando desenvolvimento apoiado por IA. Antes da apresentação externa, os exemplos serão exercitados internamente.

O canal inicial é uma apresentação dirigida. Uma biblioteca pública, aquisição em escala e segmentação de outros públicos não fazem parte desta entrega.

## Proposta de valor

**Tornar a Esteira concreta antes da adoção:** oferecer dois pontos de partida completos que permitam demonstrar rapidamente o ciclo e discutir, com evidência, onde o produto ajuda, quais são seus limites e quanto consome no cenário apresentado.

## Resultados esperados

1. O time consegue demonstrar internamente dois exemplos completos sem reconstruir a configuração durante a execução.
2. O prospect entende o objetivo, o fluxo, o resultado e os limites de cada exemplo.
3. A apresentação termina com uma decisão registrada: interesse em uma próxima avaliação do produto ou ausência de interesse acompanhada dos motivos.
4. Fricções, dúvidas, falhas, consumo e qualidade observados tornam-se insumo para decidir se a vitrine deve ser expandida.
5. Mudanças posteriores do produto que afetem os exemplos disparam revisão documental.

## Escopo aprovado para detalhamento

### Exemplo Minimalista

O menor fluxo completo capaz de produzir um resultado demonstrável. Deve privilegiar compreensão e primeira execução, explicando pré-requisitos, objetivo, resultado esperado e limites.

### Exemplo de Referência hipotético

Um cenário plausível para uma empresa que desenvolve software com apoio de IA. Não será cópia de uma instalação real nem utilizará dados reais; deverá ser generalizado, autocontido e suficientemente rico para mostrar como partes da Esteira trabalham em conjunto.

### Validação e governança

- Roteiro de teste interno e de apresentação.
- Registro da execução, fricções, resultado, modelo, consumo de tokens/custo e avaliação de qualidade.
- Identificação da versão suportada e do responsável pela revisão.
- Regra de revisar os exemplos quando um épico que os afete alcançar a etapa de documentação.

## Regras de negócio

| ID | Regra |
|---|---|
| RN01 | Cada exemplo deve informar objetivo, público, pré-requisitos, uso, resultado esperado e limites. |
| RN02 | Cada exemplo deve incluir todos os contextos necessários segundo o padrão vigente do produto. |
| RN03 | Nenhum exemplo pode conter segredo, credencial, identificador real, dado pessoal ou conteúdo confidencial. |
| RN04 | Cenários e dados devem ser explicitamente identificados como hipotéticos. |
| RN05 | Consumo e custo devem ser apresentados como observação do cenário, modelo e versão usados, não como promessa universal. |
| RN06 | A qualidade do resultado deve ser avaliada contra o objetivo declarado do próprio exemplo. |
| RN07 | Um exemplo deve informar versão suportada, responsável e gatilhos de revisão. |
| RN08 | Todo épico que alcance documentação deve avaliar impacto nos exemplos e atualizá-los quando necessário. |
| RN09 | A entrada em produção desta entrega solicita um novo épico para reavaliar os demais temas; não constitui compromisso de construí-los. |
| RN10 | Expansão da vitrine depende da diligência e aprovação próprias do novo épico. |

## Retorno e como medir

Como não existe baseline e o dono optou por não estabelecer metas numéricas nesta descoberta, o retorno não será declarado em receita, conversão ou redução percentual. A medição será event-based e preservará evidências:

1. **Prontidão interna:** para cada exemplo, registrar se uma pessoa do público interno conseguiu prepará-lo, executá-lo e localizar o resultado seguindo somente a documentação; registrar também ajuda necessária, tempo observado, falhas e dúvidas.
2. **Resultado reproduzível:** guardar cenário, versão, modelo, resultado, tokens e custo da execução para permitir comparação honesta dentro das mesmas condições.
3. **Compreensão externa:** após a apresentação, registrar se o prospect conseguiu explicar o uso e os limites sem interpretação corrigida pelo apresentador.
4. **Sinal de interesse:** registrar uma ação ou declaração explícita de interesse em avaliar/usar o produto; se não houver, registrar objeções e razões.
5. **Decisão:** usar esse registro para manter, ajustar ou não expandir a vitrine no novo épico.

Visualização, download ou opinião genérica não serão tratados isoladamente como prova de valor. Os resultados da primeira apresentação não poderão ser generalizados para o mercado, pois a amostra inicial é uma única empresa.

## Critérios de aceite de negócio

1. Os dois exemplos cumprem RN01–RN07 e podem ser encontrados a partir da documentação destinada à apresentação.
2. Uma execução interna completa de cada exemplo é registrada antes da apresentação externa.
3. O material distingue configuração reutilizável de valores que o usuário precisa substituir.
4. O resultado prometido é verificável e seus limites estão explícitos.
5. Tokens e custo estão ligados ao cenário, modelo e versão usados.
6. Não há dado sensível ou específico de uma empresa real.
7. Existe roteiro para registrar compreensão, interesse, objeções e próximo passo na apresentação.
8. A regra de manutenção RN08 está documentada sem antecipar sua implementação técnica.
9. Os temas posteriores só avançam por novo épico, conforme RN09 e RN10.

## Priorização e ordem relativa de esforço

1. Minimalista — **S**: prova o caminho completo com o menor conteúdo.
2. Referência hipotética — **M**: exige cenário coerente, mais configuração e explicação de limites.
3. Validação e governança dos dois exemplos — **M transversal**: teste, evidências de consumo/qualidade e manutenção.

A aposta total é **M relativa**. A sequência reduz retrabalho: validar primeiro o formato mínimo, aplicar o aprendizado ao exemplo de referência e só então realizar a apresentação.

## Fora de escopo

- Kanban, Scrum, Acadêmico, XGH, Gestão, RH e Atendimento.
- Galeria pública, marketplace, telemetria em escala ou campanha de aquisição.
- Compromisso de construir todos os exemplos imaginados.
- Definição de tecnologia, arquitetura, formato de empacotamento ou mecanismo de distribuição.
- Criação de stories nesta etapa.
- Uso de dados de clientes ou de uma configuração real.

## Decisão recomendada

**Aprovar para a próxima etapa**, como experimento qualitativo de descoberta com escopo fechado nos dois exemplos. A ausência de baseline é aceitável porque não há alegação de retorno quantitativo e porque o primeiro ciclo produzirá a evidência hoje inexistente. A aprovação deve ser revista se o escopo passar a prometer conversão, cobertura de mercado ou comparação universal de custos sem novos dados.

## Fontes de mercado

- [CrewAI Quickstart](https://docs.crewai.com/en/quickstart) — usa scaffold, configuração guiada e um resultado final verificável para o primeiro fluxo.
- [AutoGen Studio](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/index.html) — combina prototipação, playground e galeria, e explicita que o ambiente não é uma aplicação pronta para produção.
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) — oferece instalação e exemplo mínimo, além de recomendar abstrações pré-construídas para quem está começando.
- [n8n AI workflow templates](https://n8n.io/workflows/categories/ai/) — usa uma biblioteca categorizada de templates como base customizável e mecanismo de descoberta.

Conteúdo externo resumido e reescrito para conformidade com restrições de licenciamento.
