# Regras de Negócio — Limitador de consumo de IA

Status: draft — RN-002 com pendência de confirmação (ver `need_human` na
issue #177) · Owner: requirements · Updated: 2026-08-25
Inputs: issue #177 e histórico completo da entrevista com o dono (rodadas 1–5),
`doc/product/limitador-consumo-ia/{vision,problem-space,epicos}.md`,
`doc/requirements/limitador-consumo-ia/glossary.md`

## RN-001 — Unidade autoritativa por plataforma, sem conversão

- Regra: o consumo é sempre expresso e comparado na unidade autoritativa que a
  própria plataforma reporta (ex.: créditos fracionários no Kiro). A esteira não
  converte, soma nem compara essa unidade com tokens, moeda ou a unidade de
  outra plataforma. Internamente o core nomeia a grandeza de "tokens" apenas
  como termo de domínio; cada adapter traduz sua unidade nativa para essa
  terminologia interna sem implicar equivalência de valor entre plataformas.
- Contexto: aplica-se a toda captura, exibição, registro e comparação de
  consumo com limite.
- Exceções: nenhuma. Mesmo com múltiplas plataformas configuradas na mesma
  pipe, não há taxa de conversão auditável definida por este épico.
- Fonte: histórico, rodada 4, resposta 1; rodada 4, resposta 4; problem-space,
  seção "Fidelidade da unidade".

## RN-002 — Escopo do limite é a combinação pipe/plataforma

- Regra: toda política de limite (diário, semanal, mensal) é definida e
  aplicada por combinação pipe/plataforma. Um bloqueio nessa combinação nunca
  se estende à pipe inteira, a outra plataforma da mesma pipe ou a outra pipe.
- Contexto: aplica-se à configuração do limite, à decisão de bloqueio e ao
  registro/explicação da tentativa impedida.
- Exceções: nenhuma. Correção explícita do dono: o bloqueio não é "da pipe" —
  é da plataforma dentro da pipe.
- **Pendência de confirmação:** o `pipe.yml` hoje não tem campo de
  identificação de pipe (uma instância = um processo = um `pipe.yml`). A
  interpretação corrente — "pipe" é a própria instância que executa aquele
  `pipe.yml`, tornando `agents.<plataforma>.<limites>` suficiente — está em
  confirmação com o dono (ver RF-006, `need_human` ativo na issue #177). Esta
  regra permanece válida independentemente da resposta; o que pode mudar é
  apenas como o identificador de pipe é derivado para RN-008.
- Fonte: histórico, comentário de correção de 25/08 14:54:56; vision.md, seção
  "Solução"; problem-space.md, seção "Contexto".

## RN-003 — Períodos independentes, combináveis e sem precedência

- Regra: os períodos diário, semanal e mensal são configuráveis de forma
  independente para a mesma combinação pipe/plataforma. Qualquer um deles,
  isolado ou em conjunto com os demais, pode estar configurado. A ordem entre
  eles é irrelevante: quando qualquer período configurado atinge seu limite, a
  combinação é bloqueada.
- Contexto: aplica-se à configuração e à avaliação de bloqueio antes de cada
  tentativa de acionamento.
- Exceções: nenhuma período é obrigatório; a ausência de todos os três para uma
  combinação equivale a não ter política (RN-005).
- Fonte: histórico, rodada 3, resposta 3 ("a ordem não importa, se um recorte
  atingiu seu limite, haverá o bloqueio").

## RN-004 — Condição de bloqueio: maior ou igual ao limite

- Regra: a combinação pipe/plataforma é bloqueada para a próxima tentativa
  quando o consumo reconhecido no período for maior ou igual (`>=`) ao limite
  configurado para aquele período. Não é necessário exceder — atingir já
  bloqueia.
- Contexto: aplica-se à avaliação feita antes de cada tentativa de acionamento
  do agente, para cada período configurado da combinação.
- Exceções: nenhuma.
- Fonte: issue #177, "Resultado esperado"; histórico, rodada 3, resposta 2.

## RN-005 — Ausência de política preserva o comportamento atual

- Regra: se uma combinação pipe/plataforma não tiver nenhum limite configurado
  (diário, semanal ou mensal), a esteira aciona o agente normalmente, sem
  qualquer verificação de consumo.
- Contexto: aplica-se a toda combinação não configurada, inclusive
  combinações novas criadas após a ativação do controle em outras combinações.
- Exceções: nenhuma.
- Fonte: issue #177, "Resultado esperado" ("política opcional e independente
  por combinação pipe/plataforma, sem mudança para combinações não
  configuradas"); epicos.md, "Critérios transversais", item 1.

## RN-006 — Execução em andamento nunca é interrompida

- Regra: o controle nunca interrompe uma execução já iniciada. Uma execução
  iniciada quando a combinação estava abaixo do limite pode terminar consumindo
  acima dele; apenas a tentativa seguinte daquela combinação é impedida.
- Contexto: aplica-se do início ao fim de toda execução de agente, incluindo o
  intervalo entre o início da chamada e a captura do consumo reportado ao
  final.
- Exceções: nenhuma. O controle não promete teto absoluto de consumo.
- Fonte: issue #177, "Contexto" ("uma execução iniciada abaixo do limite pode
  terminá-la acima dele. O controle bloqueia a tentativa seguinte e não promete
  teto absoluto"); histórico, rodada 2, resposta 2; rodada 3 (validado).

## RN-007 — Falha aberta quando o consumo é indisponível

- Regra: se o consumo de uma execução não puder ser medido (a plataforma não
  reportou ou a captura falhou), a execução (a atual e as seguintes daquela
  combinação) continua normalmente. A indisponibilidade não é tratada como
  consumo zero e deve ser registrada separadamente, de forma distinguível de
  zero, em toda evidência (log, registro de execuções, baseline).
- Contexto: aplica-se sempre que a captura de consumo pós-execução falhar ou
  não retornar valor.
- Exceções: nenhuma. Falha aberta é a decisão explícita do dono ("se não
  conseguimos medir o consumo, continuamos, não há como mensurar o que não
  sabemos").
- Fonte: histórico, rodada 4, resposta 1; rodada 5 (fechamento).

## RN-008 — Warning e registro obrigatórios em toda tentativa impedida

- Regra: toda tentativa impedida gera (a) um warning em terminal e em arquivo
  de log e (b) um registro no controle de execuções. Ambos devem conter, no
  mínimo: pipe, plataforma, unidade, consumo reconhecido, limite configurado,
  período(s) que motivou(aram) o bloqueio e a condição de retomada (quando o
  reset ocorre, ou que depende de aumento/desativação manual do limite).
- Contexto: aplica-se a cada tentativa de acionamento impedida por RN-004,
  antes de o agente ser considerado para seleção de tarefa.
- Exceções: nenhuma.
- Fonte: issue #177, "Resultado esperado"; vision.md, "Métricas de sucesso".

## RN-009 — Retomada automática por reset, aumento ou desativação

- Regra: uma combinação bloqueada volta a ficar elegível automaticamente
  quando (a) o período correspondente reinicia (reset), (b) o limite
  configurado é aumentado o suficiente para o consumo reconhecido ficar abaixo
  dele, ou (c) o limite é desativado (removido da configuração). Nenhuma ação
  manual de "desbloqueio" é necessária além dessas.
- Contexto: aplica-se à avaliação de elegibilidade feita a cada tentativa,
  reavaliando os limites vigentes no momento.
- Exceções: se a combinação tiver mais de um período configurado, a retomada
  só ocorre quando nenhum dos períodos configurados estiver em condição de
  bloqueio.
- Fonte: issue #177, "Resultado esperado" ("retomada após reset, aumento ou
  desativação do limite").

## RN-010 — Fuso configurável com padrão local da máquina

- Regra: o cliente pode configurar um fuso horário para determinar a virada do
  dia (reset diário), o início da semana (reset semanal) e o dia de reset
  mensal. Se o fuso não for configurado, a esteira usa o fuso local da máquina
  onde o processo executa.
- Contexto: aplica-se ao cálculo de todas as fronteiras de período de todas as
  combinações pipe/plataforma da instalação, salvo se o requisito permitir
  configuração por combinação (ver gap em RF-005).
- Exceções: nenhuma.
- Fonte: histórico, rodada 5 ("podemos permitir fuso e se não for escolhido,
  usamos o local da máquina"); issue #177, "Resultado esperado".

## RN-011 — Responsável pela aferição é designado pelo implantador, não inferido

- Regra: a esteira não escolhe nem infere automaticamente quem publica e
  revisa o baseline do primeiro ciclo. Essa designação é uma decisão externa de
  quem implanta a esteira.
- Contexto: aplica-se à etapa de aferição/baseline, fora do escopo funcional
  do bloqueio em si.
- Exceções: nenhuma. Este épico não define papel, ferramenta ou processo de
  designação — apenas assume que a designação existe antes da ativação da
  política.
- Fonte: histórico, rodada 5 ("este papel é uma decisão de quem estiver
  implantando a esteira, não podemos inferir").

## RN-012 — Tentativa impedida não é economia observada

- Regra: o consumo que uma tentativa impedida teria gerado é contrafactual e
  desconhecido. Nenhuma métrica, relatório ou baseline deste épico pode
  apresentar tentativas impedidas como economia, redução de custo ou consumo
  evitado.
- Contexto: aplica-se a toda métrica e a todo relatório derivados deste
  controle, incluindo o baseline do primeiro ciclo.
- Exceções: nenhuma, salvo se uma tarifa contratual e uma causalidade
  verificável forem estabelecidas fora deste épico.
- Fonte: issue #177, "Critérios de negócio"; vision.md, "Métricas de sucesso".
