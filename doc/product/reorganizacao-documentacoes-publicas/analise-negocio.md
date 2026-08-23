# Análise de negócio — reorganização das documentações públicas

**Épico:** #202  
**Data da diligência:** 22/08/2026  
**Status:** aguardando entrevista com o dono; ainda não apto para aprovação  
**Recomendação provisória:** não aprovar nem recusar antes das respostas e da coleta do baseline mínimo.

## Resumo executivo

A oportunidade é plausível: a documentação já contém informação extensa, mas mistura descoberta do produto, instalação, referência, operação, histórico técnico e comunicação de releases. O problema demonstrável hoje é de organização, foco por público e governança, não de ausência geral de conteúdo.

Ainda não há evidência sobre quem é o público prioritário, em quais tarefas ele falha, qual impacto isso causa, nem qual meta de negócio deve mudar. Também é ambíguo o que significa publicar um *change file* "a partir de cada publicação na main": nos últimos 30 dias `main` recebeu 180 commits, enquanto o repositório expõe apenas uma tag. Usar cada commit, merge, versão ou deploy como gatilho produz volumes e custos muito diferentes.

A decisão deve ficar em espera até o dono confirmar público, problema, resultado esperado, gatilho de release, políticas e capacidade. As respostas serão tratadas como hipóteses e validadas por teste de tarefa, dados de suporte/uso e amostra de releases — não como prova por si só.

## Problema e evidências disponíveis

### Fatos observados no repositório

Levantamento reproduzível em 22/08/2026 sobre `origin/main`:

- 51 arquivos Markdown: 17 em `doc/product`, 9 em `doc/changelogs`, 6 em `doc/changes`, 6 em `doc/incidente`, 3 em `doc/architecture`, 3 em `doc/requirements`, 2 em `doc/runbook`, 2 em `doc/stories` e 4 na raiz.
- O README tem 732 linhas e 40 títulos. Ele já cobre resumo, instalação local, Docker, configuração, funcionalidades, troubleshooting e links técnicos; portanto, o pedido original duplica parcialmente conteúdo existente.
- Não foram encontrados links relativos quebrados nos arquivos Markdown. Integridade de links não é, com a evidência atual, a dor central.
- Há dois níveis de comunicação de mudança: `CHANGELOG.md` consolidado e 9 documentos em `doc/changelogs`, além de 6 documentos em `doc/changes`. Os formatos variam e parte do conteúdo enfatiza implementação, branches, testes e incidentes.
- Foram contados 180 commits em `origin/main` nos 30 dias anteriores à análise, mas apenas a tag `v1.5.0` está visível. Falta definir o evento de negócio que caracteriza uma publicação.
- README e runbook Docker repetem partes do quickstart e da operação. Isso pode ajudar públicos distintos, mas hoje não há uma regra explícita de fonte canônica e navegação.

### Dor formulada

**Hipótese de dor:** pessoas avaliando ou começando a usar a Esteira Agêntica precisam percorrer uma documentação longa e orientada também à implementação para entender valor, escolher o caminho correto e chegar à primeira execução; em paralelo, mantenedores não têm um processo único para transformar cada release em comunicação pública útil e documentação interna de publicação.

Essa formulação será considerada validada somente se houver evidência de falha em tarefas reais, recorrência em dúvidas/suporte ou perda observável no funil de adoção. O tamanho do README, isoladamente, não prova baixa qualidade.

## Público e trabalhos a realizar — pendentes de confirmação

A segmentação abaixo é apenas uma hipótese de pesquisa:

1. **Avaliador técnico:** entender em poucos minutos o que o produto resolve, para quem e suas restrições.
2. **Novo operador:** instalar e obter a primeira execução bem-sucedida, localmente ou em container.
3. **Operador recorrente:** configurar funcionalidades, diagnosticar falhas e atualizar com segurança.
4. **Decisor/usuário de release:** entender benefício, impacto, compatibilidade e ação necessária em cada versão.
5. **Mantenedor interno:** executar a publicação com critérios consistentes e produzir os artefatos obrigatórios.

O dono precisa escolher o público primário e os três trabalhos prioritários. Sem isso, reorganizar por arquivos corre o risco de apenas mudar a taxonomia sem melhorar resultados.

## Mercado, padrões e alternativas

Referências de mercado apoiam princípios, não um desenho técnico obrigatório:

- O [GitHub](https://github.blog/developer-skills/documentation-done-right-a-developers-guide/) recomenda documentação clara e concisa, com início rápido, conceitos e orientação para uso; associa facilidade de entender/configurar à adoção e ao autoatendimento.
- O [Diátaxis](https://diataxis.fr/) separa necessidades de aprendizagem, execução de tarefa, consulta e compreensão em tutorial, how-to, referência e explicação. É uma lente útil para inventariar conteúdo, não uma obrigação de criar quatro árvores vazias.
- O [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) propõe uma lista curada de mudanças notáveis para humanos, organizada por versão; isso favorece release/versionamento como unidade, em vez de transcrever commits.
- Pesquisa do [Google Cloud/DORA](https://cloud.google.com/blog/products/devops-sre/deep-dive-into-2022-state-of-devops-report-on-documentation) mede documentação por atributos como clareza, encontrabilidade e confiabilidade e relata associação com desempenho organizacional. A fonte não prova, sozinha, causalidade nem o retorno específico deste produto.
- O [GitHub Octoverse 2021](https://github.blog/news-insights/octoverse/the-2021-state-of-the-octoverse/) relatou produtividade 55% maior em equipes com documentação de boa qualidade. É evidência externa de direção, não baseline nem promessa de ganho para esta iniciativa.

Alternativas de negócio:

| Alternativa | Benefício | Limite/risco | Ordem de esforço |
|---|---|---|---|
| A. Não fazer agora | Evita custo e preserva foco | Mantém navegação, posicionamento e releases sem governança; impacto ainda não quantificado | Nenhum agora; custo recorrente desconhecido |
| B. Ajustar somente README e índice | Melhora descoberta com mudança pequena | Não resolve duplicidade, manutenção, release e manual interno | Pequeno |
| C. Reorganizar por jornadas + governar releases | Ataca descoberta, primeira execução, referência e comunicação | Exige dono, inventário, critérios e manutenção contínua | Médio/grande |
| D. Adotar um portal/canal novo | Pode ampliar busca, analytics e apresentação | Não há evidência de que ferramenta/canal seja o gargalo; adiciona operação | Grande; não recomendado antes do baseline |

**Direção condicionada:** se a dor for validada, preferir C em incrementos, começando pelos caminhos de maior valor; B é fallback se o impacto ou a capacidade forem baixos. Não há base de negócio para D neste momento.

## Resultado esperado e medição

### Resultado de negócio proposto

Reduzir a fricção para avaliar, instalar e operar o produto e tornar cada release relevante compreensível e publicável de forma consistente, sem aumentar material desatualizado ou expor conteúdo interno.

### Baseline obrigatório antes da execução

1. Testar as três tarefas prioritárias com ao menos 5 representantes do público-alvo; registrar sucesso sem ajuda, tempo, pontos de abandono e perguntas.
2. Levantar 60–90 dias de dúvidas, incidentes ou pedidos de ajuda atribuíveis à documentação, se esse canal existir.
3. Auditar uma amostra de 10 publicações/releases: existência, atraso e completude da comunicação pública; esforço manual para publicá-la.
4. Registrar sinais de adoção disponíveis (clones, instalações, primeiras execuções ou outro evento definido pelo dono), com fonte, janela e limitações.

Se o produto ainda não tiver usuários ou telemetria, o teste de tarefa e a auditoria de releases serão o baseline mínimo; não se deve inventar ganho financeiro.

### Indicadores candidatos

- **Primário:** taxa de sucesso sem ajuda nas três tarefas prioritárias.
- **Eficiência:** mediana do tempo até a primeira execução válida.
- **Autoatendimento:** dúvidas/pedidos de ajuda de documentação por novo usuário ou por execução, conforme denominador disponível.
- **Encontrabilidade/confiabilidade:** taxa de respostas corretas e tempo para localizar configuração/operação em teste moderado.
- **Governança de release:** percentual de releases elegíveis com comunicação pública no prazo e checklist interno completo.
- **Qualidade:** incidências confirmadas de instrução desatualizada ou contraditória.

As metas numéricas e a janela de avaliação dependem do baseline e da meta corporativa informada pelo dono. Sem denominador, contagem bruta de pageviews ou tickets não será usada como sucesso.

## Retorno e custo de não fazer

O retorno deve ser calculado depois do baseline:

`horas evitadas de suporte + horas evitadas no onboarding + horas evitadas por publicação + valor de adoções incrementais − custo de criação e manutenção`

Nenhum valor monetário pode ser afirmado hoje. Os custos plausíveis de não fazer são:

- abandono ou atraso na avaliação/instalação;
- repetição de atendimento e onboarding assistido;
- risco operacional por instruções duplicadas ou divergentes;
- mudanças relevantes invisíveis ou comunicadas em linguagem inadequada;
- custo crescente de curadoria numa cadência alta de mudanças.

Esses itens são riscos, não perdas comprovadas. O dono deve fornecer volume, frequência e custo/hora ou escolher proxies mensuráveis.

## Escopo proposto, condicionado à validação

### Dentro

- narrativa pública concisa de proposta de valor, público, capacidades e limites;
- navegação a partir do README para os caminhos prioritários;
- início do zero para os modos de execução que o dono confirmar como suportados;
- documentação das funcionalidades/configurações relevantes ao usuário, organizada pelo trabalho realizado;
- política editorial de comunicação pública por release, com benefício, impacto, compatibilidade, ação requerida e evidência de validação;
- manual interno de publicação, com responsáveis, entradas, aprovações e definição de pronto;
- inventário, destino e fonte canônica do conteúdo atual;
- validação com usuários e rotina de revisão/manutenção.

### Fora nesta etapa

- escolha de tecnologia, arquitetura, gerador de site ou canal de hospedagem;
- criação de novas funcionalidades do produto;
- tradução, múltiplos formatos/canais e tipos documentais futuros sem evidência;
- reescrita indiscriminada de documentos de engenharia que não participam das jornadas prioritárias;
- criação de stories antes da aprovação do épico.

## Ordem de esforço

Estimativa comparativa, não compromisso de prazo:

1. **Descoberta e baseline — pequeno:** confirmar público, tarefas, canais, métricas e amostra de releases.
2. **Inventário e modelo de conteúdo — médio:** classificar, identificar duplicações, definir destino e fonte canônica.
3. **Jornada de descoberta/primeiro sucesso — médio:** proposta de valor, navegação e instrução validada do zero.
4. **Referência e operação prioritárias — grande:** reorganizar o conteúdo necessário às tarefas confirmadas.
5. **Comunicação e manual de release — médio:** regra de elegibilidade, template, responsáveis e definição de pronto.
6. **Teste e ajuste — pequeno/médio:** repetir tarefas, comparar baseline e corrigir falhas.
7. **Demais tipos/canais — posterior:** só com evidência de demanda.

## Aderência a metas e políticas

- **Metas:** não foi fornecido OKR, meta de adoção, redução de custo ou prazo estratégico. A aderência permanece **não demonstrada** até o dono indicar a meta e o indicador relacionado.
- **Versionamento:** o repositório declara versionamento semântico e incremento de versão para alteração de código. A política de comunicação deve distinguir commit, merge, deploy e release versionada.
- **Segurança:** documentação pública não deve conter segredos, credenciais reais, estado da esteira, dados pessoais ou procedimentos internos sensíveis. A fronteira público/interno e o aprovador ainda precisam ser definidos.
- **Manutenção:** conteúdo duplicado só deve permanecer quando houver públicos distintos e fonte canônica/responsável explícitos.
- **Acessibilidade e linguagem:** idioma, nível técnico e requisitos de acessibilidade não foram informados e precisam de decisão do dono.

## Perguntas de decisão ao dono

1. Quem é o público primário e quais são as três tarefas que mais importam?
2. Quais casos reais demonstram falha da documentação, com frequência e impacto?
3. Qual meta/OKR esta iniciativa atende, qual indicador deve mudar e até quando?
4. Que dados existem para adoção, onboarding, suporte e uso da documentação? Quem os fornece?
5. "Publicação na main" significa cada commit, merge, deploy ou versão/release? Quais mudanças merecem comunicação pública?
6. Qual é a cadência atual e quanto tempo é gasto hoje para publicar e responder dúvidas?
7. O que deve ser público e o que deve permanecer interno? Quem aprova conteúdo e responde por mantê-lo?
8. Quais modos de instalação são oficialmente suportados e qual deve ser o caminho recomendado?
9. Qual capacidade/prazo está disponível e o que deve ser sacrificado se a iniciativa entrar agora?
10. Quais metas mínimas tornam o épico aprovável e quais resultados justificariam recusá-lo ou reduzi-lo ao ajuste de README?

## Critério para decisão

O épico fica apto a aprovação quando houver: público e tarefas priorizados; dor comprovada por baseline ou evidência operacional; meta mensurável; regra inequívoca de publicação; fronteira público/interno e responsáveis; capacidade compatível; e escopo aceito. Deve ser recusado ou reduzido se o teste não revelar fricção material, se não houver meta aderente ou manutenção disponível, ou se a alternativa B entregar o resultado necessário com menor custo.

## Referências

- GitHub, *Documentation done right: A developer’s guide*: https://github.blog/developer-skills/documentation-done-right-a-developers-guide/
- Diátaxis, framework de documentação: https://diataxis.fr/
- Keep a Changelog 1.1.0: https://keepachangelog.com/en/1.1.0/
- Google Cloud/DORA, análise sobre documentação: https://cloud.google.com/blog/products/devops-sre/deep-dive-into-2022-state-of-devops-report-on-documentation
- GitHub, *The 2021 State of the Octoverse*: https://github.blog/news-insights/octoverse/the-2021-state-of-the-octoverse/

Conteúdo das fontes externas foi resumido e reformulado para cumprir restrições de licenciamento.
