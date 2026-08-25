# Requisitos Não-Funcionais — Limitador de consumo de IA

Status: draft
Owner: requirements · Updated: 2026-08-25
Inputs: issue #177 e histórico da entrevista com o dono (rodadas 1–5),
`doc/product/limitador-consumo-ia/{vision,problem-space,epicos}.md`,
`doc/requirements/limitador-consumo-ia/functional-requirements.md`

Este documento detalha "quão bem" cada garantia funcional deve se comportar,
para uso como critério de validação por arquitetura e QA. Não redefine
escopo funcional.

| ID | Atributo | Requisito (mensurável) | Como medir |
|----|----------|------------------------|-----------|
| NFR-001 | Disponibilidade / Continuidade | Um bloqueio em uma combinação pipe/plataforma não pode reduzir, no mesmo ciclo, a disponibilidade de processamento de nenhuma outra combinação elegível (outra plataforma na mesma pipe, ou outra pipe) — 100% das demais combinações elegíveis continuam avançando no ciclo em que o bloqueio ocorre. | Cenário de teste: duas combinações configuradas, uma em condição de bloqueio (RF-002) e outra elegível; verificar que a segunda é processada no mesmo ciclo em que a primeira é impedida. |
| NFR-002 | Correção / Precisão da decisão | Zero falsos bloqueios atribuíveis ao cálculo de período/fronteira — nenhuma combinação pode ser bloqueada com base em consumo de um período diferente do vigente (ex.: consumo do dia anterior contando para o dia seguinte por erro de fronteira). | Cenário de teste: execução próxima ao instante de reset (diário/semanal/mensal), no fuso configurado e no fuso padrão da máquina; o consumo deve ser atribuído ao período correto em 100% dos casos testados. |
| NFR-003 | Correção / Falha aberta | 100% das execuções cujo consumo não pôde ser capturado devem continuar elegíveis (não bloqueadas por causa dessa execução) e 100% delas devem gerar um registro de indisponibilidade distinguível de "consumo zero" na evidência (log e controle de execuções). | Cenário de teste: simular retorno de plataforma sem valor de consumo; verificar que a combinação permanece elegível e que o registro não é indistinguível de zero (ex.: campo `null`/`indisponível` explícito, não `0`). |
| NFR-004 | Observabilidade / Auditabilidade | 100% das tentativas impedidas devem gerar warning em terminal e em arquivo de log, e um registro no controle de execuções, ambos contendo pipe, plataforma, unidade, consumo reconhecido, limite, período(s) e condição de retomada — sem exigir correlação manual entre múltiplos arquivos para reconstruir a decisão. | Cenário de teste: forçar uma tentativa impedida; inspecionar terminal, arquivo de log e controle de execuções; confirmar presença dos seis campos exigidos por RN-008 em cada um. |
| NFR-005 | Desempenho | A avaliação de bloqueio (RF-002) executada antes de cada tentativa de acionamento não deve adicionar latência perceptível ao ciclo de seleção de tarefa — o custo da checagem (comparação de valores já acumulados, sem chamada de rede) deve ser da ordem de milissegundos, não de segundos, independentemente do número de combinações pipe/plataforma configuradas. | Medir o tempo da etapa de avaliação de bloqueio isoladamente (sem incluir a chamada ao agente), com N combinações configuradas, e confirmar que não escala de forma perceptível com N em cenários de uso típico (dezenas de combinações). |
| NFR-006 | Escalabilidade | O acúmulo de consumo reconhecido e a avaliação de limites devem continuar corretos e isolados por combinação pipe/plataforma independentemente do número de plataformas configuradas em `agents` — a garantia de NFR-001 (isolamento de bloqueio) não pode depender do número total de combinações configuradas. | Cenário de teste com múltiplas plataformas e, quando aplicável, múltiplas instâncias (pipes) configuradas; confirmar que o bloqueio de uma combinação não interfere no acúmulo ou na decisão das demais. |
| NFR-007 | Integridade dos dados de consumo | O valor de consumo atribuído a uma combinação pipe/plataforma nunca deve ser somado, comparado ou convertido com o valor de outra plataforma — 100% dos registros de consumo devem preservar a unidade autoritativa de origem, sem conversão implícita para tokens, créditos ou moeda entre plataformas distintas (RN-001). | Cenário de teste com duas plataformas configuradas simultaneamente; inspecionar o consumo acumulado de cada uma e confirmar ausência de qualquer soma, taxa de conversão ou comparação cruzada nos dados armazenados ou exibidos. |
| NFR-008 | Continuidade de execução em andamento | 100% das execuções já iniciadas antes de um bloqueio devem ser concluídas sem interrupção, mesmo que o consumo capturado ao final ultrapasse o limite configurado (RN-006). | Cenário de teste: iniciar uma execução com consumo simulado que, ao final, excede o limite; confirmar que a execução conclui normalmente e que apenas a tentativa seguinte é impedida. |
| NFR-009 | Auditabilidade do baseline | Nenhuma métrica ou relatório derivado do baseline do primeiro ciclo (RF-008) pode apresentar tentativa impedida como economia, redução de custo ou consumo evitado, em 100% das saídas geradas (RN-012). | Revisão do formato/schema do baseline e das saídas geradas; confirmar ausência de qualquer campo ou rótulo que implique economia a partir de tentativa impedida. |

## Critérios de teste de regressão (cenário-chave do épico)

O conjunto de NFRs acima deve ser validado, em conjunto, contra o cenário
central descrito na diligência de negócio: duas plataformas configuradas na
mesma pipe, uma atingindo o limite diário enquanto a outra permanece dentro da
cota, e uma execução em andamento no momento exato em que o limite é
atingido. Nesse cenário:

- a plataforma que atingiu o limite deixa de ser acionada na tentativa
  seguinte (RF-002), mas a execução em andamento no momento do bloqueio
  conclui normalmente (NFR-008);
- a outra plataforma da mesma pipe continua sendo acionada sem qualquer
  degradação perceptível (NFR-001, NFR-005);
- o bloqueio gera registro completo e auditável (NFR-004), sem qualquer
  conversão entre as unidades das duas plataformas (NFR-007);
- se, no mesmo ciclo, uma terceira execução não reportar consumo, ela não
  deve ser confundida com consumo zero nem bloquear a combinação por si só
  (NFR-003).
