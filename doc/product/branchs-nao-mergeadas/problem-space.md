# Problem Space — Branches não mergeadas

Status: draft
Owner: product
Last updated: 2026-07-24

## Inputs
- Issue #73 "Branches não mergeadas"
- Entrevista com o usuário (histórico e comentários da issue #73)
- Panorama real das branches e das issues do repositório (ver
  `panorama-branches.md`)
- Configuração de fluxo e boards (`pipe.yml`)

## Contexto
A esteira abre uma branch de trabalho para cada tarefa e a integra ao final por
meio de um Pull Request. Com a evolução constante do próprio código da esteira,
o repositório foi acumulando branches que nunca foram encerradas. Hoje existem
**mais de 30 branches** além da linha principal (`main`).

A lista atual mistura, no mesmo lugar:
- **Trabalho vivo** — tarefas ativas, ainda em andamento.
- **Resíduo já entregue** — trabalho que já foi integrado (à linha principal ou
  à branch "guarda-chuva" do épico que o originou) mas cuja branch nunca foi
  apagada.
- **Trabalho de tarefas já encerradas (arquivadas)** cuja branch ficou órfã.
- **Duplicidade** — a mesma tarefa aparece com mais de uma branch, e um padrão
  de nomenclatura antigo convive com o atual.

A própria esteira já prevê o encerramento da branch nas etapas finais do fluxo
(ao publicar/integrar e ao cancelar uma tarefa). O acúmulo indica que, nas
tarefas que geraram essas branches, essas etapas finais não chegaram a rodar —
em boa parte porque eram iterações de melhoria do próprio código da esteira, que
seguiram caminhos fora do fluxo padrão.

## Problemas
- **Não se distingue o vivo do lixo:** olhando a lista, é impossível saber de
  imediato o que é trabalho em andamento e o que é resíduo descartável.
- **Duplicidade e nomenclatura antiga sem dono:** a mesma tarefa com dois nomes
  e um padrão antigo de nome deixam dúvida sobre qual é a versão correta.
- **Risco de perda irreversível:** uma limpeza sem critério pode apagar, de
  forma definitiva, trabalho que ainda não chegou à linha principal ou que
  aguarda revisão/entrega.
- **Percepção de desorganização:** a lista poluída passa a impressão de projeto
  desleixado e dificulta a navegação de quem chega.

## Impacto
- Perda de tempo e insegurança a cada vez que alguém precisa entender o estado
  do repositório.
- Risco operacional de descartar trabalho legítimo por engano.
- Ruído que se renova sozinho: como nada encerra a branch ao fim da tarefa, o
  acúmulo tende a crescer.

## Oportunidade
Fazer uma **faxina pontual, criteriosa e segura**: tratar cada branch conforme
sua situação de negócio, preservando todo o trabalho vivo e removendo apenas o
que for comprovadamente resíduo. Ao final, a lista de branches passa a refletir
apenas tarefas efetivamente ativas — devolvendo clareza e confiança sobre o
estado do repositório.

## Fora de escopo
- Alterar o conteúdo de qualquer entrega (nenhum código de produto é
  modificado).
- Mudar o processo/fluxo da esteira ou criar automação de encerramento de
  branch (o usuário confirmou que **não** é necessário — a demanda é uma limpeza
  pontual do que existe hoje).
- Definir a mecânica técnica da limpeza (etapas de execução).
- Criar user stories (será feito em etapa posterior).
