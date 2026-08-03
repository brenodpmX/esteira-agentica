# Espaço do Problema — Confiabilidade após o incidente Parent Recursivo

Status: pronto para aprovação de negócio
Owner: product
Última atualização: 2026-08-03

## Entradas consideradas

- Issue #104 — Post Mortem do incidente reportado em 01/08/2026.
- Histórico operacional da issue #104.
- Registro consolidado do incidente #97 em `doc/incidente/parent-recursivo/ticket.md`.
- Orientações de homologação e change file do incidente #97.
- Documentação vigente do produto no `README.md` e em `CONTEXT.md`.

Os registros existentes respondem às perguntas necessárias sobre evento, impacto, recuperação e risco residual. Por isso, não foi necessária nova entrevista nem pesquisa externa nesta etapa.

## Contexto de negócio

A Esteira Agêntica automatiza a movimentação de trabalho, a atualização dos boards e a execução de agentes. Seu valor depende de duas garantias básicas:

1. o trabalho registrado deve continuar sendo processado mesmo quando um item apresenta problema; e
2. o conteúdo de uma issue não pode ser confundido ou substituído pelo conteúdo de outra.

Em 01/08/2026, um item local indevido foi associado à issue #76. A associação incorreta alterou seu conteúdo e produziu uma relação inválida da issue com ela mesma. O item problemático passou a ocupar continuamente o processamento e interrompeu todos os boards durante aproximadamente 2h37, até intervenção manual.

## Problema de Produto

A esteira não possui salvaguardas suficientes para reconhecer, conter e comunicar inconsistências antes que elas atinjam o board. Quando uma inconsistência chega ao processamento:

- a identidade do trabalho pode ser interpretada de forma ambígua;
- uma relação logicamente impossível pode seguir adiante;
- uma única falha pode interromper todo o fluxo;
- o sistema pode repetir uma ação sem possibilidade de sucesso;
- a memória operacional pode sofrer interferência de uma execução de agente; e
- duas instâncias podem disputar o mesmo estado.

O problema não é apenas o erro específico da issue #76. O risco de Produto é permitir que qualquer item inválido comprometa continuidade, integridade e confiança na automação.

## Pessoas e jornadas afetadas

### Operador da esteira

Precisa confiar que a automação continuará trabalhando e que incidentes serão sinalizados com uma orientação clara. Durante o evento, foi necessário interromper a operação, investigar registros e reparar manualmente o caso.

### Times que acompanham os boards

Dependem das movimentações e atualizações automáticas para enxergar o estado real do trabalho. Durante a interrupção, todos os boards deixaram de avançar, embora o processo aparentasse continuar ativo.

### Responsáveis por Produto e Engenharia

Precisam distinguir rapidamente uma falha transitória de uma inconsistência definitiva, preservar evidências e acompanhar ações preventivas até a eliminação do risco.

## Impacto de negócio observado

| Dimensão | Impacto |
|---|---|
| Continuidade | Todos os boards ficaram sem processamento útil por cerca de 2h37. |
| Integridade | O título e o conteúdo da issue #76 foram substituídos indevidamente e precisaram ser restaurados. |
| Operação | Houve intervenção manual para interromper a repetição, reparar os dados e retomar o serviço. |
| Confiança | O sistema permaneceu em execução, mas não entregava sua função principal, reduzindo a capacidade de perceber a indisponibilidade. |
| Financeiro | Não houve perda financeira identificada; houve desperdício estimado de 700 a 900 chamadas de API. |
| Alcance | Um ambiente interno, de instância única, foi afetado; dentro dele, o impacto alcançou todos os boards. |

Para fins de Produto, o período deve ser tratado como indisponibilidade funcional. A permanência do processo em execução não representa disponibilidade quando nenhum trabalho avança.

## Necessidades não atendidas

1. **Identidade confiável:** cada artefato deve pertencer inequivocamente a uma única issue.
2. **Validação antecipada:** relações impossíveis devem ser recusadas antes de alterar dados externos.
3. **Isolamento de falhas:** um item inválido não pode impedir o processamento dos demais.
4. **Recuperação segura:** falhas definitivas precisam sair do fluxo normal, preservar evidências e pedir intervenção humana sem exigir edição da memória interna.
5. **Proteção do estado:** agentes não podem alterar a memória operacional da esteira.
6. **Exclusividade de execução:** somente uma instância pode operar sobre o mesmo estado.
7. **Sinalização acionável:** repetição, bloqueio ou inconsistência devem gerar alerta claro e rastreável.

## Oportunidade

Transformar o incidente em um marco de confiabilidade: a esteira deve falhar de forma contida, compreensível e recuperável. Isso preserva o valor da automação, reduz o tempo de resposta operacional e impede que uma inconsistência local se torne uma paralisação geral ou uma alteração indevida de dados.

## Risco de não agir

A mitigação executada resolveu o caso concreto, mas não elimina o padrão de falha. Sem as salvaguardas planejadas, um novo item ambíguo, uma relação inválida, uma falha definitiva ou uma segunda instância podem provocar nova interrupção e nova perda de confiança. O risco residual permanece relevante até a conclusão e homologação das cinco frentes corretivas.
