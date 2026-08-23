# Blocos de entrega — Limitador de consumo de IA

Status: proposta pendente de decisão de negócio
Owner: product
Last updated: 2026-08-22

## Inputs

- `doc/product/limitador-consumo-ia/vision.md`
- `doc/product/limitador-consumo-ia/problem-space.md`
- Issues #175, #176 e #177

Estes blocos organizam o resultado de negócio; não são stories nem prescrevem
tecnologia ou arquitetura.

## Bloco 1 — Política e consumo reconhecido por pipe

**Objetivo:** permitir que o cliente associe a uma pipe uma cota na unidade de
consumo que a plataforma reporte de forma autoritativa.

**Escopo candidato:**

- política opcional por pipe;
- cota e ciclo explícitos, definidos pelo cliente;
- consumo acumulado identificado com valor, unidade, fonte e disponibilidade;
- comportamento atual preservado na ausência de política;
- visibilidade da diferença entre zero e consumo indisponível.

**Fora de escopo:**

- escolher orçamento ou prioridade pelo cliente;
- garantir que a soma das cotas corresponda ao saldo da conta;
- converter tokens, créditos e moeda sem regra verificável;
- decidir onde ou como persistir os dados.

**Gate:** unidade, falhas/indisponibilidade, plataforma inicial e política de
retenção precisam ser aceitas. A issue #176 é convergente e pode fornecer a
capacidade de registro, mas a dependência de entrega será decidida na etapa
técnica.

## Bloco 2 — Impedimento e explicação ao atingir a cota

**Objetivo:** não iniciar uma nova execução quando o consumo reconhecido da pipe
já tiver alcançado sua cota vigente.

**Escopo candidato:**

- decisão antes do acionamento do agente;
- tentativa registrada no controle de execuções;
- warning nos logs de terminal e arquivo;
- explicação com pipe, consumo reconhecido, unidade, cota, ciclo e momento de
  retomada;
- outras pipes sem cota atingida continuam elegíveis.

**Fora de escopo:**

- interromper execução já iniciada;
- comprar créditos, alterar plano ou gerir overage;
- escolher automaticamente qual trabalho é prioritário;
- definir a implementação do bloqueio.

**Gate:** o dono precisa aceitar que a execução anterior pode ultrapassar a cota
e decidir o comportamento quando o consumo não estiver disponível. O circuito
#175 pode conter repetidas tentativas sobre uma issue bloqueada, mas não substitui
a explicação deste controle.

## Bloco 3 — Ciclo, retomada e aferição

**Objetivo:** tornar previsível quando a capacidade volta a ficar disponível e
provar se o controle preserva consumo para as pipes desejadas.

**Escopo candidato:**

- regra explícita de início, fim, reset e fuso do ciclo;
- retomada quando o ciclo reiniciar ou o cliente alterar/desativar a política;
- comparação por pipe entre consumo, cota, bloqueios, excedente e execuções
  evitadas;
- acompanhamento de falsos bloqueios, tempo de retomada e atraso de trabalho
  prioritário;
- baseline publicado ao fim da primeira janela de avaliação.

**Fora de escopo:**

- dashboard gráfico;
- recomendação automática de cotas;
- janelas diária/semanal sem evidência;
- reserva global coordenada entre várias instalações;
- SLA imposto ao operador.

**Gate:** ciclo, metas, janela de avaliação e responsável pela aferição precisam
ser confirmados.

## Sequência recomendada

1. Fechar os gates de unidade, teto e ciclo.
2. Assegurar medição confiável antes de prometer contenção.
3. Aplicar impedimento e mensagem acionável.
4. Observar pelo primeiro ciclo e publicar o baseline.
5. Somente então avaliar múltiplas janelas, reservas ou coordenação global.

Essa ordem minimiza o risco de bloquear com uma métrica que não representa a
unidade econômica real.
