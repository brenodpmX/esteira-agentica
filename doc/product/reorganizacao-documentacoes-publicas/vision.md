# Vision — Reorganização das documentações públicas

Status: aguardando decisões do dono para aprovação de negócio  
Owner: product / mantenedor a confirmar  
Last updated: 2026-08-22

## Resultado pretendido

Até a apresentação prevista para o fim de agosto de 2026, tornar a Esteira
Agêntica compreensível e experimentável sem leitura do código: uma pessoa do
público prioritário deve conseguir entender valor e limites, escolher um modo
suportado e completar a primeira execução usando somente a documentação
pública.

Depois desse primeiro resultado, manter uma comunicação pública consistente
para versões que incluam épicos ou incidentes relevantes, sem publicar material
interno nem criar fontes concorrentes.

A visão é de resultado e governança. Ela não determina tecnologia, arquitetura
documental, gerador de site ou canal adicional.

## Inputs

- Issue #202 "Reorganização das documentações públicas" e entrevista registrada
  no histórico em 22/08/2026.
- `README.md`, `CHANGELOG.md` e os 51 arquivos Markdown rastreados em `main`.
- `doc/runbook/docker.md`, hoje referenciado pelo README público.
- Apresentação externa planejada para o fim de agosto de 2026.
- Issue #93, indicada pelo dono como prioridade a postergar caso este épico seja
  aprovado.
- Referências de mercado listadas em `problem-space.md`.

## Público e trabalhos prioritários — proposta a confirmar

**Público primário proposto para o recorte de agosto:** arquitetos de software
avaliando integração de IA para equipes. Engenheiros de software e
desenvolvedores independentes permanecem públicos secundários até haver dados
que justifiquem outra ordem.

Três trabalhos prioritários propostos:

1. entender em até poucos minutos o problema resolvido, capacidades, limites e
   pré-requisitos da Esteira Agêntica;
2. instalar e concluir uma primeira execução local, com container apresentado
   como alternativa oficialmente suportada;
3. localizar configuração e um exemplo de uso suficiente para avaliar adoção
   pela equipe.

A entrevista confirmou os três grupos, mas não escolheu um público primário nem
as três tarefas. Por isso, essa priorização ainda depende de aceite explícito.

## Proposta de valor

Para avaliadores e novos usuários que hoje encontram uma documentação extensa e
precisam recorrer ao código para esclarecer dúvidas, oferecer uma porta de
entrada curta e caminhos orientados a tarefas, com informação verificável e
fonte canônica. Para mantenedores, oferecer critérios explícitos sobre o que é
público, quando uma mudança merece comunicação e quem responde pela atualização.

## Escopo de resultado

- narrativa pública concisa sobre problema, público, capacidades, limites e
  estágio do produto;
- README como porta de entrada, não como repositório de todo o conteúdo;
- caminho testado do zero para execução local e alternativa por container;
- configuração e exemplos organizados conforme os trabalhos prioritários;
- inventário do conteúdo existente, com destino, audiência, fonte canônica e
  responsável;
- comunicação pública curada para versões elegíveis, cobrindo benefício,
  impacto, compatibilidade e ação necessária;
- manual interno de publicação com gatilho, entradas, aprovação, responsável e
  definição de pronto;
- validação antes/depois e rotina mínima de manutenção.

## Fora de escopo

- escolher tecnologia, arquitetura, gerador, portal ou hospedagem;
- criar funcionalidades do produto ou stories nesta etapa;
- reescrever indiscriminadamente documentação de engenharia;
- tradução, novos canais ou formatos sem evidência de demanda;
- publicar credenciais, estado da esteira, dados pessoais, detalhes de incidentes
  sensíveis ou procedimentos internos de desenvolvimento.

## Retorno e como medir

Não existe baseline de adoção, suporte ou esforço editorial. Portanto, não há
base para prometer retorno financeiro. O retorno será demonstrado por redução de
fricção e de trabalho evitável:

- **sucesso sem ajuda:** proporção de participantes que conclui os três trabalhos
  prioritários usando apenas a documentação;
- **tempo:** mediana por trabalho e tempo até a primeira execução válida;
- **autoatendimento:** dúvidas documentais por novo usuário ou primeira execução,
  se existir denominador confiável;
- **confiabilidade:** contradições ou instruções desatualizadas encontradas nos
  testes e na manutenção;
- **governança:** versões elegíveis com nota pública e checklist interno completos
  dentro do prazo acordado;
- **esforço:** horas para publicar e horas de suporte atribuíveis à documentação.

Baseline mínimo: teste moderado com pelo menos cinco representantes do público
prioritário, auditoria das dez últimas mudanças candidatas a release e registro
do esforço atual. Repetir as mesmas tarefas após a entrega.

Critério mínimo proposto para aprovar o investimento completo: melhora observada
em sucesso sem ajuda e tempo nas tarefas, 100% das versões elegíveis
comunicadas no prazo e nenhum erro crítico no caminho recomendado. As metas
numéricas de melhora serão fixadas após o baseline; antecipá-las seria inventar
precisão. Se o baseline não mostrar fricção material, limitar a entrega ao README
e ao processo de release.

## Aderência estratégica e restrições

- **Meta:** habilitar a demonstração externa prevista para o fim de agosto e
  reduzir a dependência de leitura do código. Não foi informado um OKR formal.
- **Prioridade:** o dono indicou que a issue #93 perde prioridade; falta confirmar
  capacidade disponível até 31/08.
- **Publicação:** somente versões que incluam épicos ou incidentes relevantes são
  candidatas; o evento exato — merge ou release versionada — ainda precisa ser
  confirmado.
- **Segurança:** conteúdo público não contém segredos, credenciais reais, dados
  pessoais, estado interno ou informação sensível de incidentes.
- **Manutenção:** nenhuma duplicação permanece sem fonte canônica, finalidade e
  responsável explícitos.
- **Qualidade:** comandos devem ser testados do zero nos modos oficialmente
  suportados antes da publicação.

## Critério de decisão

Aprovar quando o dono confirmar: público e três tarefas; participantes ou fatos
para validar a dor; fronteira público/interno; gatilho de comunicação; aprovador
e mantenedor; capacidade; e aceite do baseline e do fallback. Recusar ou reduzir
se não houver evidência de fricção, responsável de manutenção ou capacidade
compatível com o prazo.
