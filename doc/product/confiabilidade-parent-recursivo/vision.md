# Visão de Produto — Operação Confiável e Recuperável

Status: pronto para aprovação de negócio
Owner: product
Última atualização: 2026-08-03

## Visão

A Esteira Agêntica deve preservar a continuidade e a integridade do trabalho mesmo diante de entradas inconsistentes. Uma falha localizada deve ser contida, explicada e encaminhada para recuperação, sem interromper outros boards e sem alterar dados de uma issue errada.

## Público beneficiado

- Operadores responsáveis por manter a esteira em funcionamento.
- Times que dependem dos boards como fonte confiável do andamento do trabalho.
- Responsáveis por Produto, Engenharia e Operações que acompanham incidentes e riscos.

## Proposta de valor

**Automação confiável por padrão:** problemas deixam de se propagar silenciosamente e passam a ser impedidos ou isolados, com evidência e orientação suficientes para retomada segura.

## Resultados esperados

1. Nenhum artefato ambíguo é associado automaticamente a uma issue.
2. Relações de uma issue consigo mesma são rejeitadas antes de qualquer alteração externa.
3. Uma falha definitiva em um item não paralisa os demais itens ou boards.
4. O sistema não repete indefinidamente uma ação sem possibilidade de sucesso.
5. A memória operacional permanece íntegra durante a execução dos agentes.
6. Uma segunda instância não opera simultaneamente sobre o mesmo estado.
7. Operações e Produto recebem sinalização acionável quando a esteira precisa de intervenção.

## Princípios de Produto

- **Integridade antes de automação:** em caso de dúvida sobre a identidade de um item, não alterar o board.
- **Falha localizada:** o alcance de um erro deve se limitar ao item afetado.
- **Recuperação orientada:** o sistema deve informar o que ocorreu e como retomar, sem exigir manipulação direta de sua memória.
- **Evidência preservada:** decisões automáticas de rejeição ou isolamento devem ser auditáveis.
- **Estado com um único responsável:** somente o núcleo da esteira pode manter sua memória operacional.

## Escopo funcional

### 1. Associação segura de trabalho

- Reconhecer uma issue apenas quando sua identidade e origem forem inequívocas.
- Impedir que um artefato órfão ou ambíguo substitua o conteúdo de uma issue existente.
- Sinalizar a inconsistência para correção humana, sem realizar atualização externa.

### 2. Validação de relações

- Recusar relações nas quais uma issue seja pai, filha, bloqueadora ou bloqueada por ela mesma.
- Registrar a recusa de forma compreensível e manter o processamento dos demais itens.

### 3. Contenção e recuperação de falhas

- Distinguir falhas recuperáveis de rejeições definitivas.
- Limitar novas tentativas e retirar do fluxo normal o item que não pode ser processado.
- Solicitar intervenção humana para o item isolado, preservando contexto e evidências.
- Continuar processando trabalho elegível nos demais boards.

### 4. Proteção da memória operacional

- Impedir que uma execução de agente produza alteração persistente na memória interna da esteira.
- Detectar e registrar qualquer tentativa ou efeito inesperado.
- Permitir recuperação sem orientar o operador a editar diretamente os arquivos internos.

### 5. Exclusividade de instância

- Garantir que apenas uma instância opere sobre o mesmo estado.
- Recusar a inicialização concorrente com mensagem clara e sem alterar o trabalho em andamento.

### 6. Observabilidade para decisão

- Informar item, board, natureza da falha, ação tomada e necessidade de intervenção.
- Diferenciar processo ativo de processamento saudável.
- Disponibilizar evidências suficientes para acompanhar recorrência e tempo de recuperação.

## Regras de negócio

| ID | Regra |
|---|---|
| RN01 | Na dúvida sobre a identidade ou pertinência de um artefato, nenhuma issue deve ser alterada. |
| RN02 | Uma issue nunca pode manter relação de hierarquia ou bloqueio consigo mesma. |
| RN03 | A falha de um item não pode impedir o processamento de outros itens elegíveis. |
| RN04 | Uma rejeição definitiva não pode permanecer em repetição ilimitada. |
| RN05 | Todo item isolado deve manter evidência, motivo e indicação de intervenção humana. |
| RN06 | A memória operacional só pode ser alterada pelo núcleo responsável pela sincronização. |
| RN07 | Apenas uma instância pode operar sobre um mesmo conjunto de estado. |
| RN08 | A recuperação não pode depender de edição manual dos arquivos internos protegidos. |
| RN09 | Mitigação do caso concreto não equivale à resolução definitiva do risco. |

## Critérios de aceite negociais

1. Dado um artefato que possa pertencer a mais de uma issue ou que não tenha associação confiável, quando ele for encontrado, então nenhuma issue externa é alterada, o item é sinalizado para intervenção e os demais trabalhos continuam.
2. Dada uma relação de uma issue com ela mesma, quando a atualização for avaliada, então a relação é rejeitada antes de chegar ao board e a decisão fica registrada.
3. Dada uma rejeição definitiva de um item, quando ela ocorrer, então o item deixa de monopolizar o processamento no mesmo ciclo operacional e os outros boards continuam avançando.
4. Dada uma falha potencialmente recuperável, quando o limite de tentativas for alcançado, então o item é isolado com evidências e indicação de intervenção humana, sem repetição indefinida.
5. Dada uma tentativa de alteração da memória interna por um agente, quando a execução terminar, então nenhuma alteração indevida permanece e o evento fica auditável.
6. Dada uma instância já ativa, quando outra tentar usar o mesmo estado, então a segunda não inicia o processamento e recebe orientação clara.
7. Dado um item isolado, quando o operador consultar o incidente, então consegue identificar o item, o board, o motivo, a ação automática e o próximo passo sem acessar arquivos protegidos.
8. Dado o conjunto de cenários do incidente #97, quando a solução for homologada, então não ocorre substituição de conteúdo entre issues, paralisação global ou repetição ilimitada.

## Métricas de sucesso

- **Integridade:** zero substituições de conteúdo entre issues nos cenários de regressão e após a liberação.
- **Continuidade:** 100% dos cenários com item inválido mantêm o processamento de outros itens elegíveis.
- **Recuperação:** 100% das rejeições definitivas deixam o fluxo normal no primeiro ciclo em que forem classificadas como definitivas.
- **Sinalização:** 100% dos itens isolados apresentam motivo e próximo passo acionável.
- **Exclusividade:** no máximo uma instância ativa por conjunto de estado.
- **Recorrência:** zero repetição do padrão do incidente #97 após a conclusão integral das cinco frentes.

## Priorização e sequência

A sequência acordada permanece:

1. impedir relações de auto-referência;
2. conter falhas definitivas e evitar repetição ilimitada;
3. garantir associação segura entre artefato e issue;
4. proteger a integridade da memória operacional; e
5. impedir instâncias concorrentes.

As duas primeiras frentes reduzem rapidamente o risco de paralisação. A terceira é obrigatória para eliminar o risco de alteração de conteúdo. A resolução do incidente só pode ser declarada após as cinco frentes e seus critérios serem homologados.

## Fora de escopo

- Redesenho dos fluxos, boards ou colunas do produto.
- Criação de novas funcionalidades de gestão de trabalho.
- Alteração dos gates de aprovação humana.
- Criação de stories nesta etapa.
- Definição de solução técnica, componentes ou arquivos de implementação.
- Pesquisa externa; as evidências internas foram suficientes para decidir o escopo.

## Estratégia de validação e liberação

- Validar primeiro os cenários reproduzidos no incidente e, depois, variações de identidade ambígua, relação inválida, falha definitiva, tentativa de alteração de estado e execução concorrente.
- Liberar com acompanhamento de Operações e evidência de que outros boards continuam avançando durante falhas localizadas.
- Manter o incidente como “mitigado, com risco residual” até que todas as frentes estejam concluídas.
- Considerar o incidente “resolvido” somente após homologação integral dos critérios negociais e ausência de recorrência no período de observação definido na liberação.
