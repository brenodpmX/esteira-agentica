# Espaço do Problema — Exemplos de configurações de Esteira

Status: diligência concluída; recomendada para aprovação
Owner: product
Última atualização: 2026-08-22

## Entradas e evidências

- Issue #93 e duas rodadas de entrevista com o dono.
- `README.md`, que apresenta um trecho de `pipe.yml` e exige contextos em `contexts/<plataforma>/<agente>.md`.
- `doc/runbook/docker.md`, que orienta criar o `pipe.yml` manualmente e registra que não há arquivo de exemplo.
- Pesquisa em documentação oficial de CrewAI, AutoGen Studio, LangGraph e n8n.

## Contexto de negócio

A Esteira é um produto novo que será apresentado inicialmente a uma empresa de tecnologia que desenvolve software próprio e começa a adotar desenvolvimento apoiado por IA. O dono quer usar exemplos de uso como “produtos na vitrine”: artefatos concretos que despertem interesse e deem base para experimentar ou discutir adoção.

Não existem dados históricos de ativação, abandono, suporte, conversão ou tempo até o primeiro resultado. O primeiro uso será um teste interno seguido de uma apresentação dirigida; portanto, esta entrega deve ser tratada como descoberta qualitativa, e não como canal já validado de aquisição.

## Problema

Hoje não existe uma experiência completa de exemplo. O prospect encontra um trecho de configuração no README, mas ainda precisa compor o `pipe.yml`, fornecer os contextos obrigatórios e interpretar como alcançar um resultado. Isso cria três lacunas:

- **Compreensão:** conceitos e configuração não mostram sozinhos o que a Esteira entrega em um caso concreto.
- **Experimentação:** não há ponto de partida completo e reproduzível.
- **Aprendizado comercial:** sem uma vitrine e um registro da reação do público, a equipe não distingue interesse real de entusiasmo interno.

A dor documental é comprovada pelo repositório. Sua magnitude e seu efeito sobre adoção ainda não são conhecidos.

## Hipóteses a validar

| Hipótese | Evidência atual | Como validar |
|---|---|---|
| Exemplos tornam o produto mais compreensível. | Intenção do dono e prática observada em produtos adjacentes. | Teste interno e verificação de compreensão na apresentação. |
| Um exemplo completo reduz a fricção do primeiro ciclo. | Hoje a configuração é manual e incompleta como pacote. | Registrar execução seguindo somente o material do exemplo. |
| A vitrine gera vontade de usar. | Nenhuma evidência de mercado da Esteira. | Registrar ação ou declaração explícita do prospect e suas objeções. |
| Dois exemplos bastam para a primeira apresentação. | Recorte aceito pelo dono. | Observar lacunas durante teste e apresentação antes de ampliar. |
| A manutenção por impacto de épicos evita defasagem. | Regra proposta pelo dono; ainda não exercitada. | Revisar exemplos em cada épico que alcançar documentação e auditar a decisão. |

## Pesquisa de mercado e alternativas

A pesquisa não prova demanda pela Esteira, mas mostra que produtos adjacentes usam exemplos como parte do onboarding e da descoberta:

- CrewAI conduz o usuário de um scaffold a um fluxo executável e a um artefato de saída.
- AutoGen Studio oferece playground e galeria para descobrir/importar componentes, ao mesmo tempo em que declara limites de produção.
- LangGraph combina um exemplo mínimo com caminhos de abstração mais alta para iniciantes.
- n8n mantém uma biblioteca categorizada de templates customizáveis.

Isso sustenta o padrão “exemplo executável + resultado + limites”, mas também evidencia o custo de curadoria e a necessidade de não confundir demonstração com prontidão universal.

### Alternativas consideradas

| Alternativa | Benefício | Limite/risco | Decisão |
|---|---|---|---|
| Manter apenas README e runbook | Menor esforço e manutenção. | Mantém configuração manual e apresentação abstrata. | Rejeitada para a primeira vitrine. |
| Fazer somente demonstração ao vivo | Controle do apresentador e baixo esforço inicial. | Não cria ativo reutilizável nem testa autonomia do material. | Pode apoiar a apresentação, mas não substitui os exemplos. |
| Publicar muitos exemplos de uma vez | Maior variedade aparente. | Dilui aprendizado, aumenta manutenção e inclui domínios sem validação. | Adiada. |
| Criar dois exemplos completos | Compara entrada mínima e cenário mais expressivo com esforço limitado. | Amostra de casos ainda estreita. | Escolhida. |
| Criar galeria/marketplace | Favorece descoberta e escala futura. | Prematura sem demanda, conteúdo e governança validados. | Fora de escopo. |
| Oferecer configuração assistida/consultoria | Reduz fricção para o primeiro prospect. | Não testa se a vitrine é autossuficiente e não escala. | Contingência, não solução principal. |

## Pessoas e jornadas afetadas

### Prospect técnico

Precisa reconhecer rapidamente um caso de uso, compreender os pré-requisitos, observar o resultado e separar capacidade demonstrada de promessa futura.

### Apresentador/time interno

Precisa preparar e repetir a demonstração sem reconstruir configurações, registrar consumo e responder com clareza sobre limites.

### Produto e mantenedores

Precisam aprender quais exemplos merecem investimento e evitar que materiais antigos contradigam o comportamento atual.

## Custo de não fazer

- A apresentação depende de explicação abstrata ou configuração improvisada.
- O primeiro prospect absorve o custo de montar um pacote antes de observar valor.
- Falhas de setup podem ser confundidas com falta de capacidade do produto.
- A equipe perde a oportunidade de registrar objeções e interesse sobre casos concretos.
- A decisão de investir em novos exemplos continua baseada apenas em opinião.

Não há evidência para monetizar esse custo ou afirmar perda de receita.

## Custo e risco de fazer

- Conteúdo e cenários precisam acompanhar mudanças do produto.
- Um exemplo hipotético pode parecer artificial ou não representar a operação do prospect.
- Consumo e qualidade variam por modelo e versão; números sem contexto podem induzir comparação incorreta.
- Uma apresentação a uma empresa não representa o mercado.
- A vitrine pode revelar desinteresse; esse resultado é aprendizado válido, não falha do experimento.

## Políticas e limites

- Usar o padrão vigente de contextos, sem antecipar migração de diretórios.
- Não incluir dados pessoais, segredos, credenciais ou identificadores reais.
- Identificar cenários hipotéticos e limites de produção.
- Vincular qualquer custo ao cenário, modelo e versão observados.
- Não publicar temas sensíveis ou paródicos sem diligência própria.
- Revisar impacto nos exemplos quando um épico alcançar documentação.
- Abrir um novo épico após entrada em produção apenas para reavaliar os demais temas; cada tema mantém seus gates de validação e aprovação.

## Certezas, lacunas aceitas e decisão

### Certezas

- Existe lacuna entre a documentação atual e um exemplo completo.
- O público e o canal da primeira apresentação estão definidos.
- O dono escolheu teste interno e dois exemplos como primeira aposta.
- O padrão atual de contextos deve ser usado.
- Os exemplos serão hipotéticos.
- Não há baseline nem meta numérica, por decisão explícita do dono.

### Lacunas aceitas para descoberta

- Tamanho de mercado, taxa de conversão e retorno financeiro.
- Representatividade de uma única empresa.
- Baseline de tempo, abandono e suporte.

Essas lacunas impedem promessas quantitativas, mas não impedem um experimento de escopo M com critérios qualitativos e registro de evidências.

## Recomendação

Aprovar o recorte Minimalista + Referência hipotética. A etapa seguinte deve preservar a natureza de descoberta, cumprir os critérios de `vision.md` e não ampliar o escopo. Se o teste interno não produzir execuções completas e compreensíveis, a apresentação deve ser adiada e o material corrigido. A expansão da vitrine será decidida apenas no novo épico, com as evidências da primeira apresentação.

## Fontes

- [CrewAI Quickstart](https://docs.crewai.com/en/quickstart)
- [AutoGen Studio](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/index.html)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [n8n AI workflow templates](https://n8n.io/workflows/categories/ai/)

Conteúdo externo resumido e reescrito para conformidade com restrições de licenciamento.
