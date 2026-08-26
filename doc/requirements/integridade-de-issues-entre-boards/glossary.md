# Glossário — Integridade de issues entre boards

Status: baseline de requisitos
Owner: requirements
Last updated: 2026-08-26

## Inputs
- `doc/product/integridade-de-issues-entre-boards/vision.md`
- `doc/product/integridade-de-issues-entre-boards/problem-space.md`
- `doc/product/integridade-de-issues-entre-boards/epicos.md`
- `doc/incidente/sub-issues-propagadas/ticket.md`
- `doc/changes/88-sub-issues-propagadas-entre-boards.md`
- README.md (seção "Incidente: sub-issues propagadas entre boards")

Este glossário fixa o vocabulário usado nos demais artefatos de requisitos
deste épico (`functional-requirements.md`, `business-rules.md`,
`non-functional-requirements.md`). Termos já definidos no README ou em
requisitos anteriores (`doc/requirements/confiabilidade-parent-recursivo/`)
são reafirmados aqui apenas quando o uso neste épico exige precisão adicional.

| Termo | Definição |
|---|---|
| **Board** | Um GitHub Project V2 configurado em `pipe.yml` (`boards.<id>`). Representa uma fronteira de execução: define o conjunto de colunas, o agente responsável por coluna e o fluxo de trabalho (`flow`) aplicável às issues que nele residem. |
| **Board intencional** (de uma issue) | O board no qual a issue foi criada deliberadamente pelo dono do processo, ou no qual um agente autorizou explicitamente sua presença (ver "participação multi-board autorizada"). É o board cuja coluna determina o agente e o prompt de execução. |
| **Board propagado** | Um board no qual uma issue passou a ter presença como efeito colateral automático do GitHub Projects V2, sem que essa presença tenha sido autorizada explicitamente. Não é um board intencional. |
| **Participação** | O vínculo entre uma issue e um board, materializado como um item de Project V2 (`ProjectV2Item`), com ou sem valor de `Status` preenchido. Uma issue pode ter múltiplas participações simultâneas (multi-board). |
| **Participação intencional** | Participação criada deliberadamente: (a) pela criação original da issue em um board, ou (b) por autorização explícita registrada pelo agente ou pelo dono para presença em mais de um board. |
| **Participação não intencional (propagação)** | Participação adicionada automaticamente pelo GitHub Projects V2 como efeito colateral do estabelecimento de uma relação pai/filho entre issues que pertencem a boards distintos, sem decisão deliberada de quem opera a esteira. |
| **Status executável** | O valor do campo `Status` (coluna) de um item de Project V2 que o torna elegível à seleção de tarefas (`keep_task`) e, portanto, sujeito a despacho de agente. Um item sem `Status` preenchido não é, por definição atual da esteira, elegível a despacho — mas pode se tornar elegível caso receba `Status` antes de ser reconciliado. |
| **Reconciliar** | Levar uma participação não intencional a um estado seguro antes que ela receba `Status` executável ou seja despachada: removendo a participação do board indevido, ou, quando a remoção não for possível a tempo, impedindo o despacho de agente sobre ela. |
| **Despacho indevido** | Execução de agente iniciada sobre uma issue em um board que não é o seu board intencional, resultando em aplicação de prompt, papel e/ou fluxo incompatíveis com o tipo real da issue. |
| **Resíduo** | Participação não intencional, arquivo local duplicado ou item de board que já foi materializado antes da entrega deste épico e que não é eliminado automaticamente pela prevenção/detecção entregue — exige tratamento à parte. |
| **Relação pai/filho** | Vínculo nativo de sub-issue do GitHub (`parent`/`children`), estabelecido pelos comandos `@---` `/parent` e `/children` e refletido na API de sub-issues do GitHub. |
| **Hierarquia** | O conjunto de relações pai/filho de uma issue e seus ancestrais/descendentes, independentemente do board em que cada uma reside. |
| **Fluxo (tipo de trabalho)** | A categoria de trabalho associada a um board — neste épico, os fluxos observados são Epics, User Stories e Tasks. Cada fluxo tem agentes, colunas e prompts próprios; tratar uma issue de um fluxo como se fosse de outro é o efeito de negócio que este épico previne. |
| **Janela do incidente** | O período de 25–26/08/2026 em que as 17 relações entre boards analisadas na diligência de negócio foram observadas, incluindo as 7 execuções indevidas identificadas. |
| **Janela de validação** | O período mínimo de 30 dias corridos após a disponibilização da correção em produção, com pelo menos 17 novas relações entre boards observadas, usado para comprovar a meta de negócio (ver `business-rules.md`, RN-B08). |
| **Evidência de rollout** | Registro verificável (commit/versão, ambiente e data) de que o código corrigido está de fato em execução no ambiente onde o problema é observado — distinta da simples presença do código em `main`. |
| **Board configurado** | Um board presente no `pipe.yml` no momento da verificação. Um diretório de snapshot local (`.pipe/boards/<id>/`) sem entrada correspondente em `pipe.yml` não é um board configurado e não serve como prova de participação intencional nem de propagação. |
| **Prova de propagação** | Evidência de que uma issue sem `Status` em um board já está registrada, com coluna conhecida, em outro board configurado — condição necessária para tratar a participação como não intencional e reconciliá-la sem risco de remover uma sub-issue legítima e nova. |

## Termos já definidos no README (reafirmados por referência)

- **Snapshot**, **fila de mudanças (`change_queue`)**, **`change-up`/`change-down`**,
  **`create-down`**, **`fullsync`**, **`keep_task`**, **`gitevents`**,
  **`agent-hub`**, **`/blocked_by`/`/blocks`**, **`need_human`** — usados neste
  épico com o mesmo significado documentado no README.md (seções "Loop
  Principal", "Seleção de Tarefas" e "Otimização de Sincronização").
