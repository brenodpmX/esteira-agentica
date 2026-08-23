# Blocos de Entrega — Exemplos de configurações de Esteira

Status: propostos para aprovação de negócio
Owner: product
Última atualização: 2026-08-22

## Entradas

- Issue #93 — Exemplo de configurações de Esteira.
- `doc/product/exemplos-configuracoes-de-esteira/vision.md`.
- `doc/product/exemplos-configuracoes-de-esteira/problem-space.md`.

## Critério de decomposição

Os blocos separam o aprendizado em uma sequência de risco crescente: primeiro comprovar o caminho mínimo, depois mostrar um cenário mais expressivo e, por fim, preparar e registrar a validação. Eles descrevem resultados de negócio; formato de pacote, componentes e decisões técnicas pertencem às etapas posteriores.

## Bloco 1: Exemplo Minimalista

**Objetivo:** permitir que o público compreenda e execute o menor ciclo completo da Esteira até um resultado observável.

**Escopo:**
- Caso de uso hipotético simples, objetivo e público declarados.
- Configuração e contextos necessários conforme o padrão vigente.
- Pré-requisitos, instruções de uso e pontos de customização.
- Resultado esperado, limites e critérios de avaliação.
- Registro contextualizado de versão, modelo, tokens e custo.

**Critérios de saída:**
- Execução interna completa seguindo somente a documentação.
- Resultado localizado e avaliado contra o objetivo declarado.
- Fricções, ajuda necessária e falhas registradas.
- Nenhum segredo, dado real ou identificador sensível.

**Fora de escopo:**
- Cobrir múltiplos fluxos, equipes ou domínios.
- Otimizar para o menor custo universal.
- Definir tecnologia ou arquitetura de distribuição.

**Ordem relativa:** 1 — tamanho **S**.

## Bloco 2: Exemplo de Referência hipotético

**Objetivo:** demonstrar uma configuração plausível e mais representativa para uma empresa que desenvolve software com apoio de IA, sem copiar ambiente ou dados reais.

**Escopo:**
- Cenário hipotético coerente com o público inicial.
- Objetivo, atores, fluxo, resultado e limites claramente explicados.
- Configuração e contextos completos, com valores customizáveis identificados.
- Resultado demonstrável e avaliação de qualidade adequada ao caso.
- Registro contextualizado de versão, modelo, tokens e custo.

**Critérios de saída:**
- Execução interna reproduzível sem reconstrução improvisada.
- Diferença para o exemplo Minimalista compreensível e justificada.
- Cenário explicitamente hipotético e livre de dados de terceiros.
- Limites de generalização e de produção registrados.

**Fora de escopo:**
- Replicar uma instalação específica.
- Prometer aderência ao processo do prospect antes da entrevista própria.
- Incluir Kanban, Scrum, Acadêmico, XGH, Gestão, RH ou Atendimento como exemplos adicionais.

**Ordem relativa:** 2 — tamanho **M**.

## Bloco 3: Validação da vitrine e governança

**Objetivo:** assegurar que os dois exemplos estejam prontos para apresentação e transformar a reação do público em evidência para uma decisão posterior.

**Escopo:**
- Roteiro de teste interno e apresentação.
- Registro por exemplo de execução, ajuda, tempo observado, falhas, dúvidas, resultado, modelo, tokens e custo.
- Registro após apresentação de compreensão, interesse explícito, objeções e próximo passo.
- Versão suportada, responsável e gatilhos de revisão.
- Regra de avaliação de impacto quando épicos alcançarem documentação.
- Solicitação de novo épico após entrada em produção para reavaliar os demais temas.

**Critérios de saída:**
- Ambos os exemplos passam pelo teste interno antes da apresentação.
- A evidência separa fato observado de opinião ou hipótese.
- A apresentação produz uma decisão registrada, mesmo que seja não avançar.
- O novo épico não nasce pré-aprovado e não assume compromisso com todos os temas.

**Fora de escopo:**
- Implementar automação de board ou `target-prompt` nesta etapa de negócio.
- Definir meta de conversão sem baseline ou amostra adequada.
- Criar telemetria, marketplace ou campanha de aquisição.

**Ordem relativa:** 3 — tamanho **M transversal**.

## Sequência e dependências

1. Validar o formato no Minimalista.
2. Aplicar o aprendizado ao exemplo de Referência hipotético.
3. Executar o teste interno dos dois.
4. Corrigir bloqueios que impeçam compreensão ou reprodução.
5. Realizar a apresentação e registrar evidências.
6. Após entrada em produção, solicitar novo épico para reavaliar a expansão.

O Bloco 2 pode ser preparado em paralelo apenas depois que o contrato de conteúdo do Bloco 1 estiver estável. A apresentação depende da aprovação interna dos dois exemplos.

## Rastreabilidade

| Resultado de negócio | Bloco |
|---|---|
| Primeiro ciclo compreensível e reproduzível | 1 |
| Demonstração de uso plausível para o prospect | 2 |
| Evidência para manter, ajustar ou não expandir | 3 |
| Manutenção alinhada à evolução do produto | 3 |
| Expansão sujeita a novo gate | 3 |

## Estimativa relativa consolidada

A entrega é **M**. O risco principal está na qualidade e manutenção do conteúdo, não no número de exemplos. Qualquer adição de tema antes da primeira validação altera a hipótese e exige nova avaliação de escopo.
