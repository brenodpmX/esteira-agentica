# Análise de Negócio — Circuit-break de agente

Status: recomendação de aprovação
Owner: product
Última atualização: 2026-08-22

## Decisão recomendada

**Aprovar o épico para a próxima etapa.** Há evidência de repetição prolongada de
execuções de agente sem avanço útil, o controle atual apenas espaça novas
execuções e o escopo proposto contém o item reincidente sem impedir o andamento
dos demais. A aprovação não depende de estimativa financeira: ainda não existe
telemetria consolidada de tokens e custo, portanto o retorno será medido primeiro
em execuções evitadas, continuidade do fluxo e tempo de recuperação.

## Entradas e diligência

Foram considerados:

- body e histórico do épico #175;
- entrevista assíncrona com o dono, respondida em 22/08/2026;
- issue pública #1, indicada pelo dono como caso real;
- comportamento vigente de `boards.rerun_cooldown`, documentado no README;
- documentação de confiabilidade do incidente Parent Recursivo;
- referências oficiais de Microsoft Azure e AWS sobre circuit breaker,
  tentativas finitas, isolamento e retomada.

As respostas do dono foram tratadas como hipóteses e confrontadas com a fonte
pública. A afirmação de “63 execuções” não pôde ser confirmada literalmente: a
issue #1 possui **63 comentários**, dos quais **51** foram publicados pela conta
do agente. Ainda assim, o próprio histórico registra de modo explícito pelo
menos **32 ciclos repetidos** sobre o mesmo bloqueio, sem decisão humana, em um
intervalo de aproximadamente 11 horas. Essa evidência conservadora é suficiente
para validar a dor; não é suficiente para calcular tokens ou custo monetário.

## Dor e público afetado

Quando uma issue permanece na mesma coluna após a execução, ela volta a ser
elegível depois do cooldown. Como o cooldown não impõe teto, uma falha de
entendimento, sinalização, sincronização ou decisão pode produzir novas
execuções indefinidamente, inclusive quando cada execução termina tecnicamente
com sucesso.

Isso afeta:

- o operador, que precisa detectar e interromper manualmente a repetição;
- os responsáveis pelos boards, que recebem histórico ruidoso e atraso de
  diagnóstico;
- os demais trabalhos, que disputam capacidade com uma issue sem progresso;
- o mantenedor ou pagador do agente, exposto a consumo evitável de tempo,
  quota e tokens.

A necessidade de negócio é conter o **efeito observável** — repetição da mesma
issue no mesmo board e coluna — sem depender de classificar antecipadamente
todas as causas possíveis.

## Resultado de produto

Permitir que o operador defina, de forma geral para a instância, uma quantidade
máxima de execuções por issue, board e coluna dentro de uma janela de tempo.
Quando uma nova execução ultrapassaria esse limite, a esteira deve impedir a
entrega ao agente, marcar a issue como necessitando intervenção humana e
registrar uma explicação acionável. Após o operador corrigir ou redirecionar o
item e liberar o gate humano, a issue volta a ter uma janela completa de
tentativas.

### Regras de negócio

| ID | Regra |
|---|---|
| RN01 | Cada execução iniciada conta, independentemente de terminar com erro ou sucesso. |
| RN02 | A identidade da contagem é a combinação issue + board + coluna; mudar de coluna representa um novo contexto de trabalho. |
| RN03 | Somente execuções dentro da janela configurada participam da decisão; ocorrências mais antigas deixam de contar. |
| RN04 | Ao atingir o máximo configurado, a próxima entrega ao agente não ocorre. |
| RN05 | O bloqueio marca `need_human` e informa, no comentário da issue, motivo, issue, board, coluna, limite e janela. |
| RN06 | Ao bloquear, a contagem ativa daquele contexto é zerada; após correção e remoção do gate humano, a issue recebe nova franquia completa. |
| RN07 | O controle é opt-in: sem configuração, o comportamento de execução atual é preservado e nenhum bloqueio por limite é aplicado. |
| RN08 | Na primeira versão, limite e janela são gerais; diferenciação por board, coluna ou agente fica fora do escopo. |
| RN09 | O bloqueio de uma issue não impede o processamento de outras issues elegíveis. |

## Escopo aprovado

- configuração opcional de máximo de execuções e janela de controle;
- contagem de toda execução iniciada, inclusive as concluídas com sucesso sem
  mudança de coluna;
- avaliação por issue + board + coluna;
- interrupção antes de uma execução excedente;
- gate `need_human` e comentário com razão e contexto do bloqueio;
- reinício da franquia quando o bloqueio é acionado, permitindo retomada após a
  ação humana;
- compatibilidade com instalações que não ativarem o controle.

## Fora de escopo

- diagnosticar ou corrigir automaticamente a causa raiz de cada repetição;
- limites diferentes por board, coluna ou agente;
- dashboard, alertas externos ou definição de SLA para resposta humana;
- orçamento agregado de tokens, coberto separadamente pelo épico #177;
- consolidação de telemetria de execução, tratada pelo épico #176;
- tratamento de loops de sincronização, tratado pelo épico #184;
- decisões de tecnologia, arquitetura, armazenamento ou componentes;
- criação de stories nesta etapa.

## Alternativas avaliadas

| Alternativa | Avaliação |
|---|---|
| Manter somente cooldown | Reduz frequência, mas não limita consumo acumulado; rejeitada como solução da dor. |
| Limitar somente falhas técnicas | Não cobre o caso observado de execuções tecnicamente bem-sucedidas sem progresso; rejeitada. |
| Usar somente orçamento agregado de tokens (#177) | Limita exposição total, mas permite que uma issue consuma capacidade destinada a trabalho saudável; complementar. |
| Diagnosticar todas as causas antes de conter | Aumenta tempo e deixa novos modos de falha descobertos; tratamento de causa deve ocorrer depois do isolamento. |
| Limite por contexto + intervenção humana | Contém o efeito conhecido, preserva os demais itens e cria ponto explícito de recuperação; escolhida. |

O mercado reforça a decisão sem determinar a solução técnica. A referência de
Circuit Breaker do Microsoft Azure diferencia retry de interrupção, recomenda
limiar numa janela recente, observabilidade e reset manual. O Azure Service Bus
usa máximo de entregas, registra o motivo do isolamento e permite inspeção,
correção e reenvio. O AWS Step Functions permite máximo de tentativas e aplica
tratamento alternativo quando o limite se esgota. O denominador comum é:
**tentativas finitas, isolamento, motivo e retomada controlada**.

## Custo de não fazer

O caso #1 demonstra que um bloqueio não sinalizado pode continuar por dezenas de
ciclos. Sem o épico, a exposição permanece aberta até uma pessoa perceber e
intervir. O custo mínimo comprovado é capacidade de agente consumida sem avanço,
ruído no histórico e aumento do tempo de recuperação. Também existe exposição a
tokens e atraso de outros trabalhos, mas não há dados para monetizá-la.

Para qualquer limite configurado em `N`, um episódio equivalente aos pelo menos
32 ciclos documentados teria até `32 - N` execuções evitáveis, quando positivo.
Essa fórmula é uma referência de impacto, não uma promessa de economia
financeira.

## Retorno e medição

### Indicadores primários

1. **Execuções excedentes realizadas:** meta de zero após o limite em todo
   contexto com a política ativa.
2. **Execuções evitadas:** quantidade de entregas recusadas pelo controle.
3. **Sinalização completa:** 100% dos bloqueios com `need_human` e comentário
   contendo motivo, contexto, limite e janela.
4. **Isolamento:** 100% dos cenários de aceite mantêm outras issues elegíveis em
   processamento.
5. **Retomada:** 100% das issues liberadas pelo operador recebem nova franquia,
   sem bloqueio imediato causado pela contagem anterior.
6. **Compatibilidade:** zero bloqueios por esse motivo quando a política não
   estiver configurada.

### Indicadores de acompanhamento

- bloqueios por período;
- proporção de bloqueios classificados pelo operador como legítimos ou falso
  positivo;
- tempo entre bloqueio, ação humana e retomada;
- recorrência do mesmo contexto depois da liberação;
- tokens, custo e duração evitados quando o épico #176 disponibilizar a
  telemetria necessária.

Não há OKR quantitativo vigente informado pelo dono. A aderência ocorre às
políticas de confiabilidade já registradas no produto: falha localizada,
recuperação orientada, evidência preservada e continuidade dos demais trabalhos.

## Ordem de esforço negocial

1. **Contrato e compatibilidade:** fechar significado de execução, contexto,
   limite, janela e ausência de configuração.
2. **Contenção:** impedir entrega excedente sem afetar outras issues.
3. **Sinalização e retomada:** comunicar motivo, acionar intervenção humana e
   permitir nova franquia após liberação.
4. **Medição e homologação:** provar execuções evitadas, isolamento,
   compatibilidade e ausência de bloqueio imediato.

Estimativa qualitativa: **esforço médio**. O comportamento é delimitado, mas
exige consistência entre seleção da tarefa, passagem do tempo, mudança de coluna,
sinalização no board e retomada. A decomposição técnica cabe às etapas seguintes.

## Critérios de aceite de negócio

1. Dada uma política válida com máximo `N` e janela `T`, quando uma issue no
   mesmo board e coluna já tiver alcançado `N` execuções dentro de `T`, então
   uma nova execução não é iniciada.
2. Dado o bloqueio pelo limite, quando o operador consultar a issue, então vê
   `need_human` e um comentário que identifica motivo, issue, board, coluna,
   limite e janela.
3. Dada uma execução concluída com sucesso sem mudança de coluna, então ela
   participa da contagem como qualquer outra execução iniciada.
4. Dada uma ocorrência anterior à janela, então ela não contribui para um novo
   bloqueio.
5. Dada uma mudança de coluna, então o novo contexto não herda a contagem da
   coluna anterior.
6. Dado um bloqueio acionado, quando o humano corrige o item e remove
   `need_human`, então a issue pode receber até `N` novas execuções no mesmo
   contexto antes de novo bloqueio.
7. Dada uma instância sem a política configurada, então nenhuma issue é
   bloqueada por limite de reexecução e o comportamento vigente é preservado.
8. Dada uma issue bloqueada pelo limite, então outras issues elegíveis continuam
   sendo processadas.

## Riscos e acompanhamento

- **Falso positivo:** trabalho iterativo legítimo pode atingir o teto. Mitigação
  de produto: política opt-in, valor definido pelo operador, contexto por coluna
  e retomada humana com franquia nova.
- **Configuração permissiva demais:** o controle pode não reduzir exposição.
  Mitigação: documentar exemplos e acompanhar execuções evitadas; não impor um
  valor universal sem baseline.
- **Configuração restritiva demais:** pode aumentar interrupções humanas.
  Mitigação: medir falsos positivos e tempo de recuperação antes de evoluir para
  políticas segmentadas.
- **Retorno financeiro não demonstrável inicialmente:** #176 deve habilitar a
  medição posterior de tokens, duração e custo.

## Referências

- Caso interno: https://github.com/brenodpmX/esteira-agentica/issues/1
- Microsoft Azure, Circuit Breaker pattern:
  https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker
- Microsoft Azure Service Bus, dead-letter queues:
  https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-dead-letter-queues
- AWS Step Functions, tratamento de erros e máximo de tentativas:
  https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html
