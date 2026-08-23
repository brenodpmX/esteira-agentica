# Análise de negócio — exemplos de configurações de Esteira

Status: **aguardando segunda validação do dono**

Responsável pela diligência: Produto

Última atualização: 2026-08-22

## Decisão executiva

**Recomendação atual: não avançar para aprovação ainda.** A resposta do dono
confirma a intenção de usar exemplos como “produtos na vitrine” no lançamento da
Esteira, aceita a aposta inicial com um exemplo minimalista e outro de referência
e pede que, após a entrada em produção, seja aberto outro épico para os escopos
restantes. Isso fecha intenção e recorte inicial, mas não comprova demanda nem
define público, canal, meta, qualidade mínima, pacote distribuído ou governança.

Há um problema factual: o runbook manda montar `pipe.yml` manualmente e afirma
que não existe arquivo de exemplo; o README contém somente um trecho, sem os
contextos necessários para uma experiência completa. O mercado confirma que
scaffolds, exemplos organizados e galerias reutilizáveis são padrões de descoberta
e experimentação. As fontes, porém, não provam que esta iniciativa produzirá
interesse ou adoção para a Esteira; isso deve ser tratado como experimento
mensurável, não como retorno garantido.

O épico estará apto a avançar quando o dono responder à segunda rodada no fim
deste documento. Se não houver baseline por ser um produto novo, a ausência de
histórico não bloqueia por si só: o dono pode aprovar um desenho de experimento
com público, evento de sucesso, meta, prazo e regra de decisão explícitos.

## Entrevista do dono: decisões e hipóteses

Resposta recebida em 2026-08-22:

- concordância com o escopo candidato de **minimalista + referência**;
- posicionamento dos exemplos como vitrine para apresentar um produto novo ao
  mercado e estimular interesse e uso;
- condição de abrir outro épico quando este entrar em produção, cobrindo os
  escopos restantes.

Tratamento de diligência:

| Declaração | Classificação | Validação necessária |
|---|---|---|
| O produto é novo e precisa ser apresentado ao mercado | decisão/contexto do dono | nenhuma para registrar a intenção |
| Exemplos funcionarão como vitrine e aumentarão vontade de usar | hipótese de valor | teste com público-alvo e funil de descoberta → execução → ação de negócio |
| Minimalista + referência são a primeira entrega | decisão de escopo | definir conteúdo, ordem e critérios de aceite |
| O restante deve virar outro épico após produção | decisão de processo incompleta | definir o que é “restante”, gatilho, responsável e se haverá nova priorização por evidência |

A resposta não substitui dados sobre comportamento de clientes. Também não
responde caminhos divergentes, comparação de custo/qualidade, manutenção nem
qual evento representa “interesse”.

## Problema fechado até aqui

### Dor comprovada

Um prospect ou novo usuário não encontra no repositório um pacote completo e
pronto para experimentar. Para chegar ao primeiro ciclo, precisa transformar um
trecho do README em `pipe.yml`, criar os contextos exigidos e interpretar a
documentação. Isso dificulta demonstrar possibilidades concretas do produto e
introduz passos manuais antes do primeiro resultado.

Evidências internas:

- `doc/runbook/docker.md` orienta a criação manual de `pipe.yml` e registra que
  não há arquivo de exemplo;
- `README.md` mostra um trecho de configuração, mas não um pacote completo com
  os contextos correspondentes;
- a estrutura vigente usa `contexts/<plataforma>/<agente>.md`; os caminhos
  mencionados originalmente (`pipe/contexts/kiro-cli` e
  `pipe/contexts/artifacts`) não constam na estrutura atual;
- a visão de Docker busca permitir que um usuário novo opere apenas com a
  documentação, criando aderência potencial entre as iniciativas.

### Dor ainda não quantificada

Não há no repositório nem na resposta do dono volume de prospects, tempo de
configuração, taxa de conclusão, abandono ou chamados. Portanto, é possível
comprovar a fricção documental, mas não sua frequência, severidade econômica ou
impacto atual em conversão.

## Pesquisa de mercado e alternativas

Consulta realizada em 2026-08-22 a fontes oficiais:

- **CrewAI:** mantém exemplos curados por tipo — crews, flows, integrações e
  notebooks — e seu CLI gera o scaffold completo de um projeto. A combinação
  mostra descoberta por caso de uso e um caminho curto para começar.
- **AutoGen Studio:** entrega times padrão numa galeria, permite importar e
  reutilizar coleções e oferece playground com artefatos e métricas como turnos
  e tokens. Isso torna exemplos comparáveis e testáveis, não apenas inspiracionais.
- **LangGraph:** oferece templates selecionáveis pelo CLI e um projeto mínimo
  extensível, reduzindo o trabalho inicial sem esconder que o usuário precisará
  adaptar a aplicação.
- **n8n:** usa uma biblioteca pública categorizada com mais de 10 mil templates
  como superfície de descoberta. O volume demonstra uma estratégia de catálogo,
  mas não prova que quantidade seja a estratégia adequada para um produto novo.

Leitura para a Esteira: há forte evidência de que alternativas usam exemplos,
templates e galerias como parte do onboarding e da descoberta. Não foi encontrada
prova pública comparável de causalidade entre catálogo e conversão que possa ser
transposta diretamente. A aposta deve começar pequena, com instrumentação e
manutenção explícitas.

### Alternativas de produto

| Alternativa | Benefício | Limite/risco | Recomendação |
|---|---|---|---|
| Manter README/runbook | nenhum esforço novo | mantém a lacuna e uma vitrine abstrata | recusar |
| Melhorar apenas o trecho do README | baixo esforço relativo | continua sem experiência completa e reproduzível | insuficiente isoladamente |
| Um starter minimalista | testa redução de fricção rapidamente | demonstra pouca amplitude do produto | útil, mas não atende sozinho ao objetivo de vitrine |
| Minimalista + referência | combina primeiro sucesso e demonstração realista | exige governança e critério de comparação | **menor aposta recomendada** |
| Publicar todos os temas agora | amplia variedade aparente | dilui validação, aumenta manutenção e inclui domínios sem demanda provada | adiar |
| Galeria/construtor interativo | melhora descoberta e reutilização | nova iniciativa, sem evidência local para este investimento | fora deste épico |

## Escopo de negócio proposto

### Dentro da primeira aposta

1. **Exemplo minimalista:** menor fluxo completo capaz de produzir um resultado
   demonstrável, com consumo medido e limites explícitos.
2. **Exemplo de referência:** configuração realista, generalizada e anonimizada,
   que demonstre o valor característico da Esteira sem depender do ambiente do
   autor.
3. Para ambos: objetivo, público, resultado esperado, pré-requisitos, instruções
   de uso e customização, configuração e contextos necessários, versão suportada,
   cenário reproduzível de avaliação, consumo de tokens/custo, critério mínimo
   de qualidade e responsável por revisão.
4. Nenhum segredo, credencial, identificador real ou dado pessoal.

Os caminhos e o meio de distribuição são resultados a esclarecer com o dono;
esta análise não decide tecnologia ou arquitetura.

### Fora desta primeira aposta

Kanban, Scrum, Acadêmico, XGH, Gestão, RH e Atendimento. A resposta do dono pede
um épico posterior para os escopos restantes, mas eles continuam candidatos, não
compromisso automático de construir todos. A recomendação é que o épico futuro
seja aberto no gatilho acordado e reavalie os temas com dados produzidos pela
primeira entrega. XGH deve ser identificado como paródia; Acadêmico, RH e
Atendimento exigem políticas próprias antes de eventual aprovação.

## Retorno esperado e medição

### Cadeia de valor

1. prospect encontra um caso de uso compreensível;
2. escolhe e inicia um exemplo;
3. conclui o resultado prometido com custo e qualidade conhecidos;
4. realiza a ação de negócio desejada — por exemplo, iniciar avaliação, solicitar
   contato ou adotar o produto.

### Métricas candidatas

- **descoberta:** visitantes elegíveis que abrem/baixam/iniciam um exemplo;
- **ativação:** usuários que concluem o primeiro ciclo sem ajuda;
- **tempo até valor:** mediana entre início do setup e primeiro ciclo concluído;
- **resultado de negócio:** usuários ativados que realizam a ação comercial ou
  de adoção definida pelo dono;
- **qualidade:** execuções que atingem o resultado mínimo definido para o cenário;
- **eficiência:** tokens e custo por resultado aprovado, comparados sob o mesmo
  cenário, modelo e patamar de qualidade;
- **suporte:** falhas ou pedidos de ajuda de configuração por participante;
- **frescor:** percentual de exemplos compatíveis com a versão suportada e prazo
  de correção após mudança incompatível.

A métrica primária ainda não está escolhida. Como o objetivo declarado é
“vitrine”, recomenda-se medir o funil inteiro e não usar downloads ou visualizações
isoladamente como prova de valor. Sem tráfego histórico, a baseline pode ser um
teste comparativo com novos usuários: documentação atual versus pacote de
exemplo. O dono ainda precisa definir segmento, tamanho mínimo da avaliação,
meta, janela e ação de negócio final.

## Ordem relativa de esforço de negócio/conteúdo

Não é estimativa técnica:

1. **Minimalista — S:** menor conteúdo; principal instrumento para testar setup e
   ativação.
2. **Referência — M:** exige seleção do caso, generalização, anonimização e
   explicação de limites.
3. **Benchmark e validação transversal — M:** cenário fixo, avaliação de qualidade,
   registro de custo e teste com usuários para os dois exemplos.
4. **Governança transversal — M:** responsável, compatibilidade, revisão e canal
   de descoberta.
5. **Temas posteriores — M a L cada:** Kanban/Scrum demandam fidelidade; XGH,
   posicionamento; Acadêmico/RH/Atendimento, validação de domínio e políticas.

A primeira aposta é de ordem **M relativa**, dominada menos pela quantidade de
arquivos e mais pela validação reproduzível e pela manutenção.

## Custo de não fazer

Fatos: permanece a criação manual descrita no runbook, continua inexistente uma
experiência completa de demonstração e prospects seguem sem referência oficial
para comparar resultado, custo e possibilidades.

Riscos plausíveis ainda não quantificados: mais tempo até valor, abandono antes
do primeiro ciclo, suporte evitável e menor capacidade de apresentar o produto.
Não há base para converter esses riscos em receita perdida ou horas de suporte.
A decisão deve usar um experimento de baixo escopo em vez de um business case
financeiro inventado.

## Aderência a metas e políticas

- **Estratégia:** aderência declarada pelo dono ao lançamento e apresentação do
  produto ao mercado; não foi fornecido OKR, meta comercial ou prazo.
- **Onboarding:** aderência potencial à visão de operação autônoma do Docker.
- **Segurança e privacidade:** dados fictícios; ausência de segredos, IDs e dados
  pessoais; credenciais somente por mecanismos já documentados.
- **Transparência de custo:** consumo só pode ser promovido como baixo quando
  medido em condições comparáveis e acompanhado de qualidade mínima.
- **Posicionamento:** não apresentar paródia como prática recomendada nem modelos
  de método como canônicos sem revisão adequada.
- **Domínios sensíveis:** RH não pode induzir decisão automatizada indevida;
  Acadêmico precisa preservar integridade e fontes; Atendimento precisa declarar
  limites e escalonamento humano.
- **Manutenção:** todo exemplo deve declarar compatibilidade, responsável e gatilho
  de revisão; catálogo desatualizado prejudica a confiança que a vitrine busca.

## Critérios para aprovar ou recusar

Aprovar quando houver:

1. público prioritário e ação que se deseja provocar;
2. escopo minimalista + referência definido em termos de resultado;
3. pacote esperado e canal de descoberta esclarecidos;
4. métrica primária, baseline ou desenho de experimento, meta e prazo;
5. cenário comparável de custo com qualidade mínima;
6. responsável e política de compatibilidade/manutenção;
7. regra do épico posterior definida sem prometer temas não validados.

Recusar se o objetivo permanecer apenas “ter boas ideias”, sem público, evento de
sucesso e regra de decisão, ou se for exigido publicar todos os temas sem prova e
sem capacidade de manutenção.

## Segunda rodada de perguntas ao dono

1. Quem é o primeiro público da vitrine (perfil/segmento) e qual ação concreta
   deve demonstrar interesse: executar, solicitar demonstração, iniciar piloto ou
   outra?
2. Onde a vitrine será descoberta? Se o produto ainda não tem tráfego, podemos
   tratar a primeira entrega como teste de onboarding com participantes recrutados?
3. Qual será a métrica primária, meta e prazo? Na ausência de baseline, informe a
   regra para aprovar o experimento (amostra mínima e taxa/tempo esperado).
4. Qual caso real deve originar o exemplo de referência e quais elementos precisam
   ser generalizados ou removidos?
5. Qual pacote o usuário deve receber? Confirme se vale a estrutura atual
   `contexts/<plataforma>/<agente>.md` e se os caminhos `pipe/contexts/...`
   citados originalmente estão desatualizados.
6. Qual resultado mínimo define qualidade e sob quais cenário/modelo compararemos
   tokens e custo?
7. Quem será responsável por manter os exemplos, qual versão será suportada e
   quais mudanças obrigam revisão?
8. No gatilho “quando entrar em produção”, o épico posterior deve apenas registrar
   os temas restantes para nova priorização ou existe compromisso de construir
   todos? Quem confirma o gatilho e abre o épico?

## Fontes

### Internas

- `README.md`
- `doc/runbook/docker.md`
- `doc/product/rodar-no-docker/vision.md`
- histórico da issue #93, resposta do dono em 2026-08-22

### Mercado — fontes oficiais

- [CrewAI — Examples](https://docs.crewai.com/examples/example)
- [CrewAI — Installation e scaffold por CLI](https://docs.crewai.com/en/installation)
- [Microsoft AutoGen Studio — Usage, Gallery e métricas](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/usage.html)
- [LangGraph — servidor local e template inicial](https://docs.langchain.com/oss/python/langgraph/local-server)
- [LangGraph — deployment quickstart e seleção de templates](https://docs.langchain.com/langsmith/deployment-quickstart)
- [n8n — biblioteca de workflow templates](https://n8n.io/workflows/)

Conteúdo externo resumido e reformulado para cumprir restrições de licenciamento.
