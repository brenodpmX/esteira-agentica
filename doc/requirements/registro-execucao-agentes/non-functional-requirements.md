# Requisitos Não-Funcionais — Registro de execução de agentes

Status: approved
Owner: requirements
Updated: 2026-08-26

## Inputs
- `doc/product/registro-execucao-agentes/vision.md`
- `doc/product/registro-execucao-agentes/problem-space.md`
- `doc/product/registro-execucao-agentes/epicos.md`
- `doc/requirements/registro-execucao-agentes/functional-requirements.md`
- `doc/requirements/registro-execucao-agentes/business-rules.md`

Este documento explicita atributos de qualidade mensuráveis derivados das
métricas de sucesso definidas em `vision.md`, para uso como critério de
validação por arquitetura e QA. Não redefine escopo funcional — apenas
detalha "quão bem" cada garantia deve se comportar.

| ID | Atributo | Requisito (mensurável) | Como medir |
|----|----------|------------------------|-----------|
| NFR-001 | Completude | Pelo menos 95% das execuções iniciadas na janela de aferição possuem registro com identidade, tempo, resultado e fonte de consumo preenchidos. | Contagem: (execuções com registro completo / total de execuções iniciadas) × 100, apurada na janela de 30 dias. |
| NFR-002 | Corretude de dado ausente | 100% das ausências de consumo são representadas como `indisponível`, nunca como `0` ou campo vazio. | Auditoria: nenhum registro com consumo ausente na fonte deve ter valor numérico preenchido; verificação automatizável por checagem de invariante (disponibilidade = indisponível ⇒ valor não definido). |
| NFR-003 | Integridade de linhagem | 100% dos descendentes históricos conhecidos de uma issue raiz são retornados em cada consulta, sem ciclo e sem dupla contagem (cada issue/execução aparece exatamente uma vez). | Teste de regressão com linhagem contendo vínculo removido e/ou ciclo induzido; contagem de ocorrências de cada id no resultado deve ser exatamente 1. |
| NFR-004 | Completude de sinalização | 100% dos descendentes conhecidos sem registro de execução aparecem sinalizados no resultado da consulta/exportação, nunca omitidos. | Teste com descendente sem nenhuma execução registrada; verificar presença do id no resultado com marcação explícita de "sem registro". |
| NFR-005 | Desempenho de consulta | O tempo entre a solicitação de consulta por issue raiz e a resposta com quantidade, duração, consumo, resultados e repetições é, na prática, suficiente para o operador responder em até 5 minutos sem abrir logs individuais. | Medição do tempo decorrido entre a chamada de consulta e a resposta completa, em ambiente com volume representativo da operação (ver amostra de referência no problem-space: ordem de dezenas de registros por issue/linhagem). |
| NFR-006 | Durabilidade / retenção | Um registro de execução não é removido antes de atingir a idade configurada em `retenção própria (dias)`; quando a retenção não está configurada, nenhum registro é removido automaticamente. | Teste de regressão: registro com idade menor que a retenção configurada não aparece em execução de expurgo; sem configuração, o expurgo automático não executa nenhuma remoção. |
| NFR-007 | Isolamento de dados | O registro de execução nunca contém o conteúdo de prompt ou chat da execução (apenas referência ao log detalhado). | Verificação de schema/estrutura do registro: campos de prompt/chat não existem no registro estatístico. |
| NFR-008 | Auditabilidade de consumo | Todo valor de consumo registrado é rastreável à sua fonte (plataforma/adapter) e à unidade nativa reportada, sem conversão implícita entre unidades ou para moeda. | Verificação de invariante: todo registro com consumo disponível possui fonte e unidade preenchidas; ausência de campo de conversão monetária sem origem auditável. |
| NFR-009 | Preservação após exclusão | 100% dos registros de execução de uma issue excluída permanecem acessíveis após a exclusão, até eventual expurgo pela retenção própria. | Teste de regressão: excluir issue com registros associados; verificar que os registros continuam retornáveis por consulta direta e por consulta de linhagem. |
| NFR-010 | Restrição de superfície | Não existe, em nenhuma superfície exposta pelo sistema (API, comando, UI), uma ação de exclusão manual de registro de execução. | Inspeção da superfície exposta (rotas/comandos/ações) confirmando ausência de operação de exclusão manual de registro. |

## Observações de medição

- A janela de referência para NFR-001, NFR-002, NFR-003, NFR-004 e NFR-005 é
  a primeira janela de 30 dias após a disponibilização, conforme
  `vision.md` ("Métricas de sucesso"). A aferição cabe ao operador designado
  pela organização usuária (RN-014); os valores acima são os mesmos critérios
  de aceitação de negócio, expressos aqui em forma mensurável para uso por
  QA/arquitetura.
- NFR-005 não fixa um número de milissegundos porque a documentação de
  negócio define a meta em termos de experiência do operador ("até 5
  minutos", incluindo tempo humano de leitura do resultado), não como um SLA
  de latência de sistema. Arquitetura pode e deve derivar um orçamento de
  latência técnico a partir desta meta de experiência, mas essa derivação é
  decisão de arquitetura, fora deste documento.
- Volume de referência observado na amostra de negócio (21–22/08/2026): 24
  arquivos em 11 issues, mediana de 5,81 créditos e 3,14 minutos por execução
  (ver `problem-space.md`). Este é um dado de contexto, não uma meta de
  escala — não há meta de volume/throughput fechada com o dono.
