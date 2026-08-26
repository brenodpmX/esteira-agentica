# Requisitos Funcionais — Registro de execução de agentes

Status: approved
Owner: requirements
Updated: 2026-08-26

## Inputs
- `doc/product/registro-execucao-agentes/vision.md`
- `doc/product/registro-execucao-agentes/problem-space.md`
- `doc/product/registro-execucao-agentes/epicos.md`
- `doc/requirements/registro-execucao-agentes/business-rules.md`
- `doc/requirements/registro-execucao-agentes/glossary.md`
- Histórico de entrevista na issue #176 (2026-08-21 a 2026-08-26)

## Atores
- **Operador da esteira**: administra a instância, consulta/exporta registros e governa quem tem acesso a essa consulta/exportação (RN-012).
- **SRE / Monitoramento**: consulta duração, cobertura e comportamento operacional em lote, sem abrir logs individuais.
- **Produto / Responsável por entrega**: consulta o esforço agregado de uma issue raiz e sua linhagem histórica.
- **Sistema (núcleo da esteira)**: único ator que cria e exclui registros de execução (RN-011); dispara o registro ao final de cada execução de agente.

## Dados
- **Registro de execução**: identidade da execução; identidade da issue; board; etapa (coluna) no momento da execução; plataforma; agente; modelo; instante de início; instante de fim; duração; resultado (RN-002); indicador de avanço (RN-001); consumo (valor, unidade, fonte, disponibilidade — RN-004); referência ao log detalhado (sem duplicar prompt/chat — RN-013); repetição sem avanço (derivado, RN-003).
- **Issue**: identidade, board, etapa atual, vínculos de parent/children conhecidos ao longo do tempo (linhagem histórica — RN-006).
- **Linhagem histórica**: conjunto de issues (raiz + descendentes conhecidos, mesmo desvinculados), sem ciclo, sem dupla contagem (RN-007), com sinalização de descendente sem registro (RN-008).
- **Política de retenção**: prazo em dias, configurável por instância da esteira, independente do TTL do log (RN-009).

## Requisitos

### RF-001 — Registrar uma execução de agente
- Descrição: o sistema deve criar um registro de execução ao final de cada execução de agente (concluída, com erro ou interrompida), independentemente do resultado.
- Ator: Sistema (núcleo da esteira).
- Pré-condição: um agente foi chamado para uma issue em uma etapa de um board.
- Fluxo principal: o agente é executado; ao terminar (por qualquer motivo), o sistema grava um registro com identidade da execução e da issue, board, etapa, plataforma, agente, modelo, início, fim, duração, resultado e indicador de avanço.
- Alternativos/exceções: se a execução for interrompida antes de finalizar (ex.: falha de infraestrutura, encerramento do processo), o sistema ainda grava um registro com resultado `interrompida` ou `desconhecida`, preservando início e o que for conhecido de fim/duração.
- Critérios de aceitação:
  - Dado que um agente concluiu uma execução sobre uma issue, quando a execução termina, então um registro é criado com resultado `concluída` e indicador de avanço preenchido de forma independente do resultado.
  - Dado que uma execução falhou de forma definitiva, quando a execução termina, então um registro é criado com resultado `falha terminal`.
  - Dado que uma execução excedeu o tempo limite, quando isso é detectado, então um registro é criado com resultado `timeout`.
  - Dado que o processo da esteira foi interrompido durante uma execução, quando o sistema reinicia, então existe (ou é criado) um registro para aquela execução com resultado `interrompida` ou `desconhecida`, nunca ausente.
- Fonte: `vision.md` ("Disponibilizar um registro de negócio por entrega de uma issue a um agente"); `epicos.md` (Épico "Registro confiável de cada execução"). Regras: RN-001, RN-002.

### RF-002 — Registrar resultado e avanço de forma independente
- Descrição: o sistema deve armazenar, para cada execução, o resultado técnico e o indicador de avanço da issue como dois campos distintos, sem inferir um a partir do outro.
- Ator: Sistema (núcleo da esteira).
- Pré-condição: uma execução terminou e está sendo registrada (RF-001).
- Fluxo principal: o sistema determina o resultado (um dos cinco valores fechados) e, separadamente, se a issue avançou de etapa como consequência daquela execução; grava os dois valores no registro.
- Alternativos/exceções: quando o sistema não conseguir determinar o resultado com segurança, grava `desconhecida` — nunca deixa o campo vazio.
- Critérios de aceitação:
  - Dado uma execução que concluiu mas não moveu a issue de etapa (ex.: sinalizou `/need_human`), quando o registro é criado, então resultado é `concluída` e avanço é `não`.
  - Dado uma execução que foi interrompida mas cuja issue já havia avançado antes da interrupção, quando o registro é criado, então resultado é `interrompida` e avanço é `sim`.
- Fonte: `problem-space.md` ("Regras de negócio fechadas"). Regras: RN-001, RN-002.

### RF-003 — Registrar consumo com proveniência
- Descrição: o sistema deve registrar o consumo de cada execução com valor, unidade, fonte (plataforma/adapter) e disponibilidade, sem estimar valores ausentes.
- Ator: Sistema (núcleo da esteira), adapter de plataforma (ex.: Kiro).
- Pré-condição: uma execução terminou e está sendo registrada (RF-001).
- Fluxo principal: o adapter da plataforma reporta o consumo observado (ex.: créditos no Kiro); o sistema grava valor, unidade, fonte e marca disponibilidade como `disponível`.
- Alternativos/exceções: se a plataforma não reportar consumo para aquela execução, o sistema grava disponibilidade como `indisponível`, sem preencher valor com zero ou estimativa.
- Critérios de aceitação:
  - Dado que o Kiro reportou 5,81 créditos para uma execução, quando o registro é criado, então valor = 5,81, unidade = créditos, fonte = Kiro, disponibilidade = disponível.
  - Dado que a plataforma não reportou consumo para uma execução, quando o registro é criado, então disponibilidade = indisponível e valor não é preenchido com zero.
  - Dado que uma execução consumiu efetivamente zero unidades e a plataforma reportou esse zero, quando o registro é criado, então valor = 0, disponibilidade = disponível (distinto de indisponível).
- Fonte: `vision.md`, `problem-space.md` ("Regras de negócio fechadas"). Regras: RN-004, RN-005.

### RF-004 — Usar "Tokens" como rótulo geral preservando a unidade nativa
- Descrição: o sistema deve expor o consumo sob o rótulo geral "Tokens" no core, preservando a unidade nativa relatada por cada plataforma (ex.: créditos no Kiro) sem conversão.
- Ator: Sistema (núcleo da esteira), adapter de plataforma.
- Pré-condição: RF-003 aplicado.
- Fluxo principal: o core armazena e exibe o consumo com a unidade nativa da plataforma de origem daquela execução.
- Alternativos/exceções: se duas execuções da mesma linhagem usarem plataformas diferentes com unidades diferentes, o sistema não soma nem converte os valores entre si; exibe os totais segmentados por unidade/fonte.
- Critérios de aceitação:
  - Dado um registro de execução da plataforma Kiro, quando consultado, então a unidade exibida é "créditos" e o rótulo geral do campo é "Tokens".
  - Dado um agregado de linhagem com execuções em plataformas de unidades diferentes, quando consultado, então o total é apresentado por unidade/fonte, nunca somado entre unidades distintas.
- Fonte: resposta do dono em 2026-08-24. Regras: RN-005.

### RF-005 — Consultar/exportar execuções de uma issue raiz com linhagem histórica
- Descrição: o sistema deve permitir consultar/exportar todas as execuções de uma issue raiz e de todos os seus descendentes históricos conhecidos, mesmo que o vínculo de parent/children tenha sido removido posteriormente.
- Ator: Operador da esteira, SRE/Monitoramento, Produto.
- Pré-condição: existe ao menos uma issue raiz com histórico de execuções próprias ou de descendentes.
- Fluxo principal: o solicitante informa a issue raiz; o sistema resolve a linhagem histórica completa (RN-006), agrega quantidade, duração, consumo, resultados e repetições, e retorna o conjunto sem duplicar issues ou execuções.
- Alternativos/exceções: se a linhagem contiver um ciclo, o sistema neutraliza o ciclo e retorna resultado consistente (RN-007); se um descendente conhecido não tiver nenhum registro, ele aparece sinalizado como sem registro, não é omitido (RN-008).
- Critérios de aceitação:
  - Dado um épico com três descendentes conhecidos, um deles desvinculado após a execução, quando a linhagem é consultada, então os três descendentes aparecem no resultado.
  - Dado um descendente conhecido sem nenhum registro de execução, quando a linhagem é consultada, então esse descendente aparece sinalizado como "sem registro", e não é omitido do resultado.
  - Dado uma linhagem que contém um ciclo de vínculos, quando consultada, então o resultado é retornado sem repetir a mesma issue/execução mais de uma vez.
- Fonte: `vision.md`, `epicos.md` (Épico "Consolidação pela linhagem histórica"). Regras: RN-006, RN-007, RN-008.

### RF-006 — Contar repetição sem avanço
- Descrição: o sistema deve identificar e contabilizar, para fins de consulta/exportação e baseline, as execuções que constituem repetição sem avanço (RN-003).
- Ator: Sistema (núcleo da esteira); consumido por Operador da esteira e SRE/Monitoramento na consulta.
- Pré-condição: existem ao menos duas execuções da mesma issue na mesma etapa.
- Fluxo principal: ao registrar uma nova execução (RF-001), o sistema verifica se a execução imediatamente anterior da mesma issue, na mesma etapa, não resultou em avanço; se assim for, marca a nova execução como repetição sem avanço.
- Alternativos/exceções: se a issue mudou de etapa entre as duas execuções, a nova execução não é marcada como repetição sem avanço.
- Critérios de aceitação:
  - Dado que a execução anterior da issue X na etapa "doing" não avançou, quando uma nova execução de X ocorre ainda em "doing", então essa nova execução é marcada como repetição sem avanço.
  - Dado que a issue X avançou de "doing" para "done" e depois voltou a ser executada em "done", quando essa nova execução ocorre, então ela não é marcada como repetição sem avanço (etapa mudou).
- Fonte: `problem-space.md` ("Regras de negócio fechadas"); resposta do dono em 2026-08-24 ("Concordo"). Regras: RN-003.

### RF-007 — Aplicar retenção própria configurável
- Descrição: o sistema deve permitir configurar, por instância da esteira, uma retenção própria em dias para os registros de execução, e expurgar automaticamente apenas quando essa retenção estiver configurada.
- Ator: Operador da esteira (configura); Sistema (aplica o expurgo).
- Pré-condição: existem registros de execução armazenados.
- Fluxo principal: o operador configura a retenção em dias; o sistema, periodicamente, identifica registros com idade maior ou igual à retenção configurada e os expurga.
- Alternativos/exceções: se a retenção não estiver configurada, o sistema nunca expurga registros automaticamente.
- Critérios de aceitação:
  - Dado que a retenção está configurada para 90 dias, quando um registro atinge 90 dias de idade, então ele se torna elegível para expurgo.
  - Dado que a retenção não está configurada, quando o tempo passa, então nenhum registro é expurgado automaticamente.
- Fonte: `vision.md`, `problem-space.md` ("Regras de negócio fechadas"); resposta do dono em 2026-08-25. Regras: RN-009.

### RF-008 — Preservar registros após exclusão da issue
- Descrição: o sistema deve manter os registros de execução acessíveis mesmo após a issue correspondente ser excluída do board ou do estado local.
- Ator: Sistema (núcleo da esteira).
- Pré-condição: uma issue com registros de execução associados é excluída.
- Fluxo principal: a exclusão da issue ocorre normalmente (fluxo já existente na esteira); os registros de execução daquela issue permanecem inalterados e consultáveis, sujeitos apenas à retenção própria (RF-007).
- Alternativos/exceções: nenhuma — não há modo de exclusão de issue que também exclua ou anonimize os registros.
- Critérios de aceitação:
  - Dado uma issue com dois registros de execução, quando a issue é excluída, então os dois registros continuam existindo e consultáveis até a eventual expiração pela retenção própria.
- Fonte: `vision.md`, `problem-space.md`; resposta do dono em 2026-08-25. Regras: RN-010.

### RF-009 — Restringir criação/exclusão de registros à lógica do produto
- Descrição: o sistema não deve expor nenhuma operação de exclusão manual de registro de execução para operador, SRE ou qualquer outro papel de negócio.
- Ator: Sistema (núcleo da esteira).
- Pré-condição: nenhuma — é uma restrição permanente de superfície do sistema.
- Fluxo principal: registros só são criados por RF-001 e só são removidos por RF-007 (expurgo por retenção); não existe endpoint, comando ou ação de UI para exclusão manual.
- Alternativos/exceções: nenhuma.
- Critérios de aceitação:
  - Dado a superfície de consulta/exportação do sistema, quando inspecionada, então não existe nenhuma ação que exclua um registro manualmente.
- Fonte: resposta do dono em 2026-08-25; `epicos.md` (fora de escopo: "exclusão manual de registros por usuário"). Regras: RN-011.

### RF-010 — Governar acesso à consulta/exportação pelo operador da esteira
- Descrição: o sistema deve permitir que o operador da esteira controle quem pode consultar e exportar registros, sem impor uma política própria de papéis.
- Ator: Operador da esteira.
- Pré-condição: a instância da esteira está operacional e possui registros.
- Fluxo principal: o operador define, pelos mecanismos de administração/infraestrutura de sua operação, quem acessa a consulta/exportação exposta pelo sistema.
- Alternativos/exceções: nenhuma — a definição de identidade/autenticação de quem acessa é responsabilidade do operador, não do produto.
- Critérios de aceitação:
  - Dado que o operador restringiu o acesso à consulta/exportação a um subconjunto de usuários de sua operação, quando um usuário fora desse subconjunto tenta acessar, então o controle de acesso do operador (fora do escopo deste produto) é o mecanismo responsável por bloquear — o sistema não impõe uma segunda política conflitante.
- Fonte: resposta do dono em 2026-08-25; `vision.md`. Regras: RN-012.

### RF-011 — Responder consulta de raiz em até 5 minutos sem abrir logs
- Descrição: o sistema deve permitir que o operador obtenha quantidade de execuções, duração, consumo, resultados e repetições de uma issue raiz e sua linhagem em até 5 minutos, sem precisar abrir logs individuais.
- Ator: Operador da esteira, SRE/Monitoramento.
- Pré-condição: a issue raiz e sua linhagem possuem registros de execução.
- Fluxo principal: o solicitante consulta a issue raiz; o sistema retorna quantidade de execuções, duração total/segmentada, consumo (por unidade/fonte), distribuição de resultados e contagem de repetições sem avanço.
- Alternativos/exceções: se a linhagem tiver descendentes sem registro, eles aparecem sinalizados (RF-005) e não impedem a resposta agregada dos demais.
- Critérios de aceitação:
  - Dado uma issue raiz com histórico conhecido, quando consultada, então o operador obtém quantidade, duração, consumo, resultados e repetições sem precisar abrir nenhum log individual.
- Fonte: `vision.md` ("responder (...) em até 5 minutos sem abrir logs individuais"); `epicos.md` (Épico "Consulta, exportação e baseline operacional"). Regras: RN-006, RN-007, RN-008.

### RF-012 — Publicar baseline operacional da primeira janela de 30 dias
- Descrição: o sistema deve fornecer os dados necessários para que o operador designado publique, ao final da primeira janela de 30 dias, o baseline de falha terminal, repetição sem avanço, cobertura de consumo e consumo/duração por etapa.
- Ator: Operador designado pela organização usuária.
- Pré-condição: a capacidade de registro está disponível e em uso há até 30 dias.
- Fluxo principal: o operador consulta/exporta os agregados necessários (RF-005, RF-011) e compõe o baseline com os quatro indicadores.
- Alternativos/exceções: a ausência de OKR/prazo/responsável nominal (RN-014) não bloqueia a publicação do baseline — apenas impede alegar ROI monetário atrelado a ele.
- Critérios de aceitação:
  - Dado 30 dias de operação com registros, quando o operador designado consulta os agregados do sistema, então consegue compor falha terminal, repetição sem avanço, cobertura de consumo e consumo/duração por etapa sem dado ausente não sinalizado.
- Fonte: `vision.md` ("Métricas de sucesso"); `epicos.md` ("Condições de resultado"). Regras: RN-014.

## Fora de escopo (explícito)
Consistente com `epicos.md` e `vision.md`: dashboard, alertas, avaliação
automática de qualidade, recomendação automática de agente/modelo, conversão
monetária sem fonte auditável, exclusão manual de registro por qualquer papel,
e qualquer decisão de arquitetura/tecnologia/armazenamento.
