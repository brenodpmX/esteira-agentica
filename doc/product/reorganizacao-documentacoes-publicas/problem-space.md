# Problem Space — Reorganização das documentações públicas

Status: dor plausível, ainda sem validação suficiente  
Owner: product  
Last updated: 2026-08-22

## Contexto

O repositório possui informação para instalação, configuração, operação,
funcionalidades, incidentes e mudanças, mas combina descoberta do produto,
manual de uso, referência, operação e memória de engenharia. O dono relatou que
a organização é confusa, pouco atraente e o obriga a consultar o código para
resolver dúvidas. Também pretende apresentar o sistema externamente até o fim de
agosto de 2026.

O relato é evidência qualitativa de uma pessoa e uma hipótese válida a testar;
não representa frequência, impacto ou comportamento dos públicos citados.

## Fatos observados em `main`

Levantamento em 22/08/2026:

- 51 arquivos Markdown rastreados: 17 em `doc/product`, 9 em
  `doc/changelogs`, 6 em `doc/changes`, 6 em `doc/incidente`, 3 em
  `doc/architecture`, 3 em `doc/requirements`, 2 em `doc/runbook`, 2 em
  `doc/stories` e 3 na raiz;
- README com 733 linhas e 40 títulos, reunindo introdução, instalação,
  configuração, execução local e Docker, funcionalidades, operação e histórico
  de incidentes;
- `CHANGELOG.md`, nove arquivos em `doc/changelogs` e seis em `doc/changes`
  formam camadas paralelas de comunicação de mudanças;
- uma tag está visível, enquanto `main` recebeu 169 commits nos 30 dias
  anteriores ao levantamento; commit não é uma unidade adequada de comunicação
  pública sem regra de elegibilidade;
- `doc/runbook/docker.md` está ligado pelo README e é público na prática. Isso
  conflita com a hipótese do dono de que todo o diretório `doc/` seria interno;
- a documentação atual já cobre grande parte do conteúdo solicitado. A dor
  observável é foco, encontrabilidade, consistência e governança — não ausência
  geral de informação.

Contagem de arquivos e tamanho do README são sinais de complexidade, não prova de
má experiência. Não foram fornecidos analytics, tickets, volume de suporte,
dados de onboarding nem entrevistas adicionais.

## Problema formulado

Pessoas avaliando ou começando a usar a Esteira Agêntica podem não conseguir
identificar rapidamente valor, limites e próximo passo porque a porta de entrada
mistura jornadas públicas com detalhes operacionais e memória interna. Ao mesmo
tempo, mantenedores não têm uma regra única e explícita para selecionar,
produzir, aprovar e manter comunicação pública de versões.

Consequências a validar:

- atraso ou abandono da avaliação e da primeira execução;
- dependência do código ou do mantenedor para dúvidas que deveriam ser
  autoatendidas;
- risco de instruções duplicadas ou divergentes;
- mudanças relevantes invisíveis ou descritas em linguagem de implementação;
- custo editorial crescente sem responsável nem definição de pronto.

## Evidência de mercado

As referências abaixo apoiam princípios, mas não provam retorno para este
produto:

- [GitHub — About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
  descreve o README como lugar para explicar utilidade, possibilidades e uso do
  projeto, reforçando seu papel de porta de entrada;
- [Diátaxis](https://diataxis.fr/) separa necessidades em tutorial, guia de
  tarefa, referência e explicação. É uma lente de classificação por necessidade,
  não uma obrigação de ferramenta ou de quatro árvores documentais;
- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) recomenda uma lista
  curada de mudanças notáveis por versão, para humanos, e diferencia changelog
  de log de commits;
- [Google Cloud/DORA](https://cloud.google.com/blog/products/devops-sre/deep-dive-into-2022-state-of-devops-report-on-documentation)
  mede qualidade por atributos como clareza, encontrabilidade e confiabilidade e
  relata associação com desempenho organizacional. A pesquisa não fornece o
  baseline nem demonstra causalidade específica neste repositório.

Conteúdo das fontes externas foi resumido e reformulado para cumprir restrições
de licenciamento.

## Alternativas

| Alternativa | Retorno possível | Custo/risco | Ordem de esforço |
|---|---|---|---|
| Não fazer agora | Preserva capacidade da issue #93 | Mantém risco para a apresentação, consulta ao código e governança indefinida | Nenhum imediato; recorrência desconhecida |
| Ajustar README e índice | Melhora descoberta rapidamente | Não resolve fonte canônica, validação, release nem manutenção | Pequeno |
| Reorganizar jornadas prioritárias e governar releases | Ataca primeira experiência e manutenção com validação | Exige inventário, dono e disciplina contínua | Médio, expansível |
| Reescrever todo o acervo | Uniformiza formatos | Alto custo e risco de mover conteúdo sem melhorar tarefas | Grande; não recomendado |
| Adotar portal ou canal novo | Pode oferecer busca e analytics | Adiciona operação sem evidência de que tecnologia seja o gargalo | Grande; decisão técnica prematura |

**Recomendação condicionada:** validar e executar a terceira alternativa em
incrementos. Começar pela porta de entrada e pelos três trabalhos prioritários;
usar a segunda como fallback. Não aprovar reescrita total nem canal novo nesta
etapa.

## Custo de não fazer

Até a apresentação externa, o custo mais concreto é reputacional e de
conversão: o público pode não entender ou experimentar o produto sem ajuda. No
longo prazo, permanecem suporte repetido, onboarding assistido, risco de
instrução desatualizada e esforço manual de release.

Não há dados para monetizar esses custos. O cálculo, quando houver baseline, é:

`horas evitadas de suporte + horas evitadas no onboarding + horas evitadas por publicação + valor de adoções incrementais − criação e manutenção`

Sem volume, frequência, custo/hora ou indicador de adoção, qualquer valor seria
especulativo.

## Validação necessária

1. Confirmar um público primário e três tarefas para o recorte de agosto.
2. Recrutar ao menos cinco representantes e registrar sucesso sem ajuda, tempo,
   abandono, dúvidas e recurso consultado.
3. Auditar as dez últimas mudanças candidatas: elegibilidade, existência,
   atraso, completude e esforço da comunicação.
4. Identificar evidências adicionais — pessoas, tickets, comentários ou dúvidas
   recorrentes — sem tratar o relato do dono como amostra suficiente.
5. Classificar conteúdo por audiência e sensibilidade. O diretório não pode ser
   usado sozinho como política, pois hoje contém material público.
6. Repetir o teste após a entrega e comparar o mesmo conjunto de tarefas.

## Riscos e políticas

- **Prazo sem capacidade:** 31/08 é uma data, não uma estimativa; sem pessoas ou
  horas disponíveis, o recorte pode ser inviável.
- **Público amplo:** arquitetos, engenheiros e independentes têm necessidades
  distintas; tentar atender todos no primeiro incremento dilui o resultado.
- **Privacidade por caminho:** mover ou ocultar todo `doc/` quebraria conteúdo
  público atual. Classificar por audiência e sensibilidade, não apenas por pasta.
- **Duplicação:** README, guia e release note só podem repetir conteúdo quando a
  finalidade for explícita e existir uma fonte canônica.
- **Segurança:** nunca publicar segredos, credenciais reais, dados pessoais,
  estado interno ou detalhes de incidentes que elevem risco.
- **Release:** comunicação é curada por versão elegível, salvo decisão explícita
  diferente; não usar cada commit como publicação.
- **Manutenção:** cada artefato público precisa de responsável, gatilho de revisão
  e critério de obsolescência.

## Decisão pendente

A oportunidade tem aderência ao evento de agosto e custo de oportunidade
explícito (#93), mas ainda não está apta à aprovação. Faltam prioridade de
público/tarefas, prova mínima da dor, política público/interno, evento de release,
responsáveis, capacidade e aceite do critério mínimo. Essas lacunas são decisões
de negócio, não de arquitetura.
