# Análise de negócio — exemplos de configurações de Esteira

Status: **diligência concluída; recomendada para aprovação**

Responsável: Helena Costa — Product Manager

Última atualização: 2026-08-22

## Decisão executiva

Recomenda-se aprovar uma primeira vitrine com dois exemplos — **Minimalista** e **Referência hipotética** — acompanhados de teste interno, roteiro de apresentação, registro de evidências e governança de atualização.

A recomendação não presume demanda, conversão ou retorno financeiro. A Esteira é um produto novo, sem baseline, e será apresentada inicialmente a uma única empresa de tecnologia que desenvolve software próprio e começa a adotar IA no desenvolvimento. O retorno desta entrega é reduzir a distância entre explicação e demonstração e produzir evidência qualitativa para a próxima decisão.

A documentação normativa da decisão está em:

- `vision.md` — visão, regras, retorno, medição e critérios de aceite;
- `problem-space.md` — fatos, hipóteses, mercado, alternativas e custo de não fazer;
- `epicos.md` — blocos de entrega e ordem relativa de esforço.

## Trilha da entrevista

### Primeira rodada

Foram apresentados ao dono os fatos internos e dez perguntas sobre público, prioridade, pacote, métrica, qualidade, canal, manutenção e políticas. Não havia respostas anteriores nem dados locais de ativação, abandono, suporte ou consumo.

### Primeira resposta do dono

O dono:

- aceitou em princípio o recorte Minimalista + Referência;
- definiu os exemplos como “produtos na vitrine” para apresentar um produto novo;
- condicionou a entrada em produção à abertura de outro épico para os temas restantes.

A expectativa de despertar interesse permaneceu hipótese, e foi aberta uma segunda rodada para fechar público, canal, medição, natureza do exemplo de referência, padrão de contextos, qualidade, manutenção e regra do épico posterior.

### Segunda resposta do dono

O dono definiu que:

1. a apresentação inicial será feita a uma empresa de tecnologia que desenvolve software próprio e inicia desenvolvimento apoiado por IA;
2. os testes serão internos;
3. não há números ou baseline;
4. os exemplos serão hipotéticos, e não derivados de um caso real;
5. será usado o padrão mais atual do produto;
6. não será exigida comprovação numérica nesta primeira entrega;
7. todo épico que chegar à etapa de documentação deverá avaliar e atualizar os modelos afetados;
8. a entrada em produção solicitará um novo épico, que passará por validação e aprovação próprias.

Essas declarações foram tratadas como decisões de escopo e processo. Elas não foram usadas como prova de demanda.

## Dor comprovada

- O runbook orienta criar `pipe.yml` manualmente e registra que não há arquivo de exemplo.
- O README contém um trecho de configuração, mas não um pacote completo com os contextos necessários.
- O padrão vigente usa `contexts/<plataforma>/<agente>.md`.
- Um prospect precisa montar e interpretar elementos antes de observar um primeiro resultado reproduzível.

Não há evidência para quantificar frequência, severidade econômica, abandono ou receita perdida.

## Hipótese de valor

Se a equipe apresentar exemplos completos, executáveis e transparentes sobre limites, então o prospect poderá compreender melhor o produto e decidir se quer avaliá-lo. Essa hipótese será observada no teste interno e na primeira apresentação, não declarada como validada antecipadamente.

## Pesquisa de mercado

Fontes oficiais mostram práticas adjacentes:

- CrewAI leva o usuário de um scaffold a um fluxo executável e um artefato final.
- AutoGen Studio oferece playground e galeria, além de explicitar limites de produção.
- LangGraph oferece exemplo mínimo e caminhos de maior abstração para iniciantes.
- n8n usa uma biblioteca categorizada de templates customizáveis.

A prática de mercado sustenta “exemplo + resultado + limites” como mecanismo de onboarding e descoberta. Não prova causalidade entre exemplos e conversão para a Esteira.

## Alternativas avaliadas

| Alternativa | Avaliação |
|---|---|
| Manter apenas README/runbook | Menor esforço, mas preserva a lacuna de experiência completa. |
| Melhorar apenas o trecho de configuração | Ajuda o setup, mas não demonstra resultado nem limites. |
| Fazer somente demonstração ao vivo | Útil como apoio, porém não produz ativo reutilizável nem testa autonomia. |
| Publicar muitos exemplos | Amplia variedade aparente, mas aumenta manutenção antes de validar demanda. |
| Minimalista + Referência hipotética | Menor aposta que combina primeiro ciclo e cenário expressivo; escolhida. |
| Galeria/marketplace | Prematura sem demanda, conteúdo e governança validados. |

## Retorno e como será medido

Por decisão explícita do dono, não haverá meta numérica nesta primeira descoberta. Isso impede alegações quantitativas, mas não impede medição. Serão preservados eventos e evidências:

1. conclusão interna de cada exemplo seguindo somente sua documentação;
2. ajuda, tempo observado, falhas e dúvidas durante o teste;
3. cenário, versão, modelo, resultado, tokens e custo da execução;
4. capacidade do prospect de explicar uso e limites;
5. ação ou declaração explícita de interesse em avaliar/usar, ou rejeição com motivos;
6. decisão posterior de manter, ajustar ou não expandir a vitrine.

Uma apresentação a uma empresa não representa validação de mercado. Visualizações, downloads ou elogios genéricos não serão tratados isoladamente como retorno.

## Ordem de esforço

- Minimalista — **S**.
- Referência hipotética — **M**.
- Validação e governança — **M transversal**.
- Primeira aposta consolidada — **M relativa**.

Temas adicionais são M–L cada e dependem de diligência própria.

## Custo de não fazer

- A apresentação continua abstrata ou dependente de preparação improvisada.
- O prospect absorve trabalho de configuração antes de observar valor.
- Falhas de setup podem ser confundidas com incapacidade do produto.
- Produto não registra reação a casos concretos e continua priorizando por opinião.

Não há base para traduzir esse risco em receita perdida.

## Aderência e políticas

- A iniciativa adere ao objetivo declarado pelo dono de apresentar o produto ao mercado.
- Cenários serão hipotéticos e não conterão dados pessoais, segredos, credenciais ou identificadores reais.
- Custos serão vinculados ao cenário, modelo e versão, sem promessa universal.
- Cada exemplo declarará limites, versão suportada, responsável e gatilhos de revisão.
- Épicos em documentação avaliarão impacto nos exemplos.
- O épico posterior reavaliará os temas restantes e não nascerá pré-aprovado.
- Kanban, Scrum, Acadêmico, XGH, Gestão, RH e Atendimento ficam fora desta entrega.

## Critério de decisão

A diligência está apta a avançar porque público, canal inicial, natureza dos exemplos, recorte, padrão vigente, retorno observável, esforço e governança foram fechados. As lacunas de baseline, representatividade e retorno financeiro foram explicitamente aceitas como limites de uma descoberta qualitativa; qualquer promessa comercial ou expansão exigirá nova evidência.

## Fontes

### Internas

- `README.md`
- `doc/runbook/docker.md`
- Histórico da issue #93

### Mercado — fontes oficiais

- [CrewAI Quickstart](https://docs.crewai.com/en/quickstart)
- [AutoGen Studio](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/index.html)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [n8n AI workflow templates](https://n8n.io/workflows/categories/ai/)

Conteúdo externo resumido e reescrito para conformidade com restrições de licenciamento.
