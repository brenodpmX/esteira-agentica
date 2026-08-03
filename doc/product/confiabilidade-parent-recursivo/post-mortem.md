# Post-Mortem de Produto — Incidente Parent Recursivo

Status: mitigado; ações preventivas pendentes
Incidente de origem: #97
Análise de negócio: #104
Owner: product
Data do incidente: 2026-08-01
Última atualização: 2026-08-03

## Resumo executivo

Em 01/08/2026, a Esteira Agêntica associou um artefato local indevido à issue #76, substituiu seu título e conteúdo e tentou estabelecer uma relação impossível da issue consigo mesma. A rejeição dessa operação passou a ser repetida continuamente e impediu o processamento de todos os boards por aproximadamente 2h37.

A intervenção operacional restaurou os dados e retomou o serviço. Não houve perda financeira identificada nem perda permanente de informação. Entretanto, a correção definitiva ainda depende de cinco frentes preventivas. Até que elas sejam entregues e homologadas, o incidente permanece mitigado, com risco residual de recorrência.

## Classificação de Produto

- **Severidade:** Média.
- **Risco de continuidade:** Alto, pois uma única inconsistência interrompeu todos os boards.
- **Risco de integridade:** Médio-alto, pois a alteração indevida de conteúdo se materializou.
- **Alcance:** um ambiente interno e um operador direto; todos os boards desse ambiente foram afetados.
- **Recuperabilidade:** possível por intervenção manual, com dados originais disponíveis.

A severidade considera o alcance interno e a reversibilidade. O risco de continuidade permanece alto independentemente de o processo ter ficado tecnicamente ativo: durante o período, ele não entregou processamento útil.

## Linha do tempo negocial

| Horário aproximado | Evento e consequência |
|---|---|
| 10:33–10:49 | Execuções automatizadas produziram e movimentaram artefatos inconsistentes; uma segunda instância também foi iniciada. |
| 10:52 | A issue #76 recebeu conteúdo incorreto e uma relação inválida foi enviada ao board. |
| 10:52–13:17 | A mesma rejeição foi repetida 225 vezes; nenhum board avançou. |
| 13:28 | A esteira foi reiniciada e o processamento voltou a ocorrer. |
| Após a retomada | O conteúdo original da issue #76 foi restaurado, os artefatos indevidos foram removidos e o estado foi reconciliado. |

## Impacto

### Continuidade do serviço

A função principal ficou indisponível por cerca de 2h37. O processo permanecia em execução, mas não processava novas tarefas. O indicador anterior de “100% de disponibilidade” não representa a experiência real; para Produto, houve indisponibilidade funcional durante todo o intervalo.

### Integridade e confiança

O conteúdo da issue #76 foi substituído indevidamente. Embora restaurável, o evento mostrou que a automação podia alterar o trabalho errado antes de reconhecer a inconsistência. Isso compromete a confiança no board como fonte do estado real.

### Operação

A recuperação exigiu diagnóstico e intervenção manual. Foram registradas 225 ocorrências do mesmo erro e um desperdício estimado de 700 a 900 chamadas de API. Não houve escalonamento automático nem autorrecuperação.

### Usuários e finanças

O ambiente era interno, sem SLA externo e com um operador direto. Não houve perda financeira identificada. O baixo alcance não reduz a importância preventiva, porque o mesmo padrão pode afetar ambientes com maior volume e dependência operacional.

## Causa raiz sob a ótica de Produto

O incidente resultou da combinação de cinco lacunas de proteção:

1. **Identidade ambígua:** um artefato indevido pôde ser tratado como se pertencesse a uma issue existente.
2. **Validação tardia:** uma relação logicamente impossível só foi recusada ao chegar ao serviço externo.
3. **Falha não isolada:** um único item passou a bloquear o fluxo global e a repetir uma ação sem possibilidade de sucesso.
4. **Estado sem barreira efetiva:** uma execução de agente conseguiu interferir na memória operacional reservada à esteira.
5. **Concorrência não controlada:** duas instâncias puderam operar sobre o mesmo estado.

O gatilho foi específico, mas a causa de Produto é sistêmica: faltavam limites de confiança entre entrada, automação, memória e sincronização.

## Por que o incidente alcançou todos os boards

- O processamento compartilhava um único fluxo de mudanças.
- O item com erro permanecia sempre na frente desse fluxo.
- A rejeição era tratada como se uma nova tentativa pudesse funcionar.
- Não havia limite, isolamento ou encaminhamento automático para intervenção humana.
- O sinal apresentado como erro “não fatal” não refletia a paralisação funcional.

## O que funcionou bem

- Os registros permitiram reconstruir a sequência do incidente.
- O conteúdo original estava disponível e pôde ser restaurado.
- A retomada ocorreu após a intervenção operacional.
- Não houve perda permanente nem impacto financeiro identificado.
- As cinco frentes preventivas foram identificadas e decompostas para execução.

## O que precisa melhorar

- Impedir associação ambígua antes de qualquer alteração externa.
- Validar relações impossíveis dentro do próprio produto.
- Conter falhas por item, sem impacto global.
- Encerrar tentativas sem possibilidade de sucesso e pedir intervenção humana.
- Tornar a memória operacional efetivamente protegida.
- Impedir operação concorrente sobre o mesmo estado.
- Medir saúde pelo avanço do trabalho, não apenas pelo processo ativo.
- Preservar a trilha de auditoria também quando uma execução exceder seu limite de tempo.

## Fatores que limitaram o dano

- O uso era interno e de instância única.
- O conteúdo original estava preservado.
- A alteração era reversível.
- A quota externa não foi esgotada.
- A equipe percebeu e interrompeu a repetição no mesmo dia.

Esses fatores reduziram o impacto deste evento, mas não devem ser considerados controles permanentes.

## Decisões de Produto

1. Manter a classificação como incidente produtivo mitigado até a conclusão integral das ações.
2. Priorizar primeiro a prevenção da paralisação, sem confundir isso com resolução do risco de integridade.
3. Exigir a associação segura de artefatos como condição obrigatória para declarar a integridade resolvida.
4. Exigir proteção de estado e exclusividade de instância para encerrar as portas de recorrência.
5. Não criar stories nesta etapa; o trabalho corretivo já foi decomposto em cinco tarefas vinculadas ao incidente #97.
6. Não abrir pesquisa externa; os registros internos fornecem evidência suficiente para o escopo e os critérios.

## Plano de ação orientado a resultado

| Ordem | Resultado esperado | Prioridade | Situação em 03/08/2026 |
|---|---|---|---|
| 1 | Relações de uma issue consigo mesma são rejeitadas antes de alterar o board. | Imediata | Planejado, pendente de entrega. |
| 2 | Uma falha definitiva é isolada e não interrompe outros boards nem se repete indefinidamente. | Imediata | Planejado, pendente de entrega. |
| 3 | Um artefato ambíguo nunca substitui o conteúdo de uma issue. | Obrigatória para integridade | Planejado, pendente de entrega. |
| 4 | A memória operacional não pode ser alterada por execuções de agente. | Alta | Planejado, pendente de entrega. |
| 5 | Uma segunda instância não pode operar sobre o mesmo estado. | Alta | Planejado, pendente de entrega. |

A ordem acordada é **1 → 2 → 3 → 4 → 5**. As duas primeiras ações formam a contenção mínima da indisponibilidade. A terceira é indispensável para a integridade. As cinco são necessárias para o encerramento definitivo.

## Critérios para encerrar o incidente

O incidente somente poderá ser marcado como resolvido quando:

- todos os critérios definidos em `vision.md` estiverem homologados;
- os cenários do incidente não produzirem alteração indevida, paralisação global ou repetição ilimitada;
- itens inconsistentes forem isolados com sinalização acionável;
- a memória operacional permanecer íntegra durante a execução de agentes;
- a inicialização concorrente for recusada com segurança;
- Operações validar a retomada sem edição manual dos arquivos internos; e
- o período de observação definido para a liberação terminar sem recorrência.

Até lá, a comunicação correta é: **caso concreto recuperado; risco sistêmico mitigado apenas operacionalmente; correções preventivas pendentes**.

## Métricas de acompanhamento

- Tempo para detectar uma paralisação funcional.
- Tempo para restaurar o processamento útil.
- Quantidade de itens isolados por inconsistência.
- Quantidade de repetições evitadas por classificação definitiva.
- Percentual de boards que continuam avançando durante falha localizada.
- Ocorrências de alteração indevida de conteúdo.
- Tentativas de inicialização concorrente recusadas.
- Recorrência do padrão do incidente #97.

## Responsabilidades

- **Produto:** manter escopo, critérios, métricas e comunicação do risco residual.
- **Engenharia:** entregar as cinco salvaguardas e evidências de validação.
- **Operações:** validar sinalização, recuperação e continuidade dos demais boards.
- **Homologação:** confirmar os critérios negociais em conjunto, sem considerar apenas a ausência de erro técnico.

## Referências

- `doc/incidente/parent-recursivo/ticket.md`
- `doc/incidente/parent-recursivo/homologacao.md`
- `doc/changelogs/97-erro_reportado_dia_010826.md`
- `doc/product/confiabilidade-parent-recursivo/problem-space.md`
- `doc/product/confiabilidade-parent-recursivo/vision.md`
