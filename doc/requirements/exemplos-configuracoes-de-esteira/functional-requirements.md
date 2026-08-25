# Requisitos Funcionais — Exemplo de configurações de Esteira

Status: draft · Owner: requirements · Updated: 2026-08-24
Inputs: Issue #93 (body e histórico); `doc/product/exemplos-configuracoes-de-esteira/vision.md`; `doc/product/exemplos-configuracoes-de-esteira/epicos.md`; `README.md`; `business-rules.md` e `glossary.md` deste mesmo diretório

## Atores

- **Analista/Engenheiro interno (validador):** pessoa da equipe que executa
  um exemplo do zero seguindo apenas a documentação de usuário, para
  confirmar que o ciclo funciona antes da apresentação externa.
- **Apresentador:** pessoa da equipe que conduz a apresentação dirigida ao
  prospect, usando os exemplos como demonstração.
- **Prospect:** representante da empresa de tecnologia externa que assiste à
  apresentação e manifesta interesse ou recusa.
- **Responsável pela revisão:** pessoa designada para manter cada exemplo
  atualizado quando uma mudança de produto o afetar (RN-008/RN-009).
- **Esteira (sistema):** executa a configuração do exemplo (`pipe.yml`,
  contextos, board) e produz o resultado demonstrável.

## Dados

- **Exemplo:** pacote nomeado (Minimalista | Referência hipotética) contendo:
  objetivo, público, caso de uso, pré-requisitos, resultado esperado, limites,
  `pipe.yml` de exemplo, contextos de agente completos, instruções de uso e
  customização, versão suportada, responsável pela revisão.
- **Cenário hipotético:** narrativa de uso plausível associada ao exemplo,
  sem dado real (RN-002).
- **Registro de validação:** execução, ajuda necessária, tempo observado,
  falhas, dúvidas, qualidade avaliada contra o objetivo, modelo/tokens/custo
  observados — um registro por execução de validação de um exemplo.
- **Registro de apresentação:** compreensão do prospect, interesse explícito
  ou recusa com objeções, próximo passo — um registro por apresentação
  (RN-007).
- **Responsável e versão suportada:** atributos declarados por exemplo
  (RN-009), não um dado de execução.

## Requisitos

### RF-001 — Configuração completa do exemplo Minimalista

- **Descrição:** o sistema (pacote de exemplo) deve fornecer o menor
  `pipe.yml` e o menor conjunto de contextos de agente necessários para
  produzir um resultado demonstrável de ponta a ponta.
- **Ator:** Analista/Engenheiro interno (validador).
- **Pré-condição:** ambiente com os requisitos do README atendidos (Python
  3.12+, `gh` autenticado, chave SSH, ou stack Docker equivalente).
- **Fluxo principal:**
  1. O validador copia/aplica o `pipe.yml` de exemplo e os contextos
     fornecidos.
  2. O validador cria uma issue de exemplo no board configurado, seguindo
     apenas as instruções de uso do exemplo.
  3. A Esteira processa a issue segundo a configuração do exemplo (detecção,
     execução de agente, transição de coluna).
  4. O validador observa o resultado demonstrável (ex.: issue avançou de
     coluna, comentário do agente, PR aberto — conforme definido no próprio
     exemplo).
- **Alternativos/exceções:** se algum pré-requisito do ambiente estiver
  ausente, as instruções de uso do exemplo devem indicar isso antes da
  execução (não é responsabilidade do exemplo suprir pré-requisitos de
  ambiente, mas sim declará-los — ver RF-005).
- **Critérios de aceitação:**
  - Dado o `pipe.yml` e os contextos do exemplo Minimalista aplicados em um
    ambiente com os pré-requisitos atendidos, quando uma issue de exemplo é
    criada na coluna de entrada configurada, então a Esteira produz o
    resultado demonstrável descrito no exemplo sem intervenção manual fora
    da prevista nas instruções.
  - Dado o exemplo Minimalista, quando um validador o executa seguindo
    somente a documentação de usuário, então nenhuma etapa exige
    conhecimento da implementação da Esteira não documentado no próprio
    exemplo (RN-003).
- **Fonte:** issue #93, "Objetivo" (item 1); `vision.md`, Bloco 1 de
  `epicos.md`. Regras: RN-002, RN-003, RN-004.

### RF-002 — Configuração completa do exemplo Referência hipotética

- **Descrição:** o sistema deve fornecer uma configuração mais completa que
  a do Minimalista (mais de uma coluna e/ou agente), baseada em um cenário
  plausível de empresa que desenvolve software com apoio de IA, sem copiar
  dados ou configuração de uma empresa real.
- **Ator:** Analista/Engenheiro interno (validador).
- **Pré-condição:** mesma do RF-001.
- **Fluxo principal:** mesmo fluxo do RF-001, aplicado à configuração da
  Referência hipotética (que pode incluir mais de um board, coluna ou
  agente, conforme o cenário escolhido).
- **Alternativos/exceções:** se o cenário escolhido para a Referência
  hipotética se aproximar demais de uma configuração real conhecida (de
  qualquer empresa, incluindo a própria mantenedora da Esteira), o cenário
  deve ser generalizado antes da publicação (RN-002). O Bloco 2 de
  `epicos.md` marca como fora de escopo "replicar uma instalação
  específica" e "prometer aderência ao processo do prospect antes da
  entrevista própria".
- **Critérios de aceitação:**
  - Dado o `pipe.yml` e os contextos do exemplo Referência hipotética
    aplicados em um ambiente com os pré-requisitos atendidos, quando o
    ciclo de exemplo é executado conforme as instruções de uso, então a
    Esteira produz o resultado demonstrável descrito no exemplo.
  - Dado o cenário hipotético da Referência, quando revisado antes da
    publicação, então não há nome, credencial, identificador ou dado
    reconhecível de pessoa ou empresa real, e a diferença de conteúdo em
    relação ao Minimalista é compreensível e justificada.
- **Fonte:** issue #93, "Objetivo" (itens 2 e 3); `vision.md`, Bloco 2 de
  `epicos.md`. Regras: RN-001, RN-002, RN-004.

### RF-003 — Documentação de uso e customização por exemplo

- **Descrição:** cada exemplo deve incluir instruções de uso (como aplicar a
  configuração e observar o resultado) e de customização (como adaptar o
  exemplo a outro cenário sem alterar sua estrutura essencial), com os
  valores customizáveis identificados separadamente da configuração
  reutilizável.
- **Ator:** Analista/Engenheiro interno (validador); Apresentador.
- **Pré-condição:** exemplo (RF-001 ou RF-002) definido.
- **Fluxo principal:**
  1. O validador segue as instruções de uso para reproduzir o ciclo
     completo.
  2. Opcionalmente, o apresentador ou o validador segue as instruções de
     customização para adaptar um parâmetro do exemplo (ex.: nome do board,
     nome do agente) sem quebrar o resultado demonstrável.
- **Alternativos/exceções:** se a customização documentada não for testada
  na validação interna, o exemplo não pode declarar suporte a customização
  não verificada.
- **Critérios de aceitação:**
  - Dado um exemplo publicado, quando um validador segue apenas as
    instruções de uso, então ele reproduz o resultado demonstrável sem
    consultar outra fonte além da documentação do próprio exemplo.
  - Dado um exemplo publicado, quando as instruções de customização são
    seguidas para um ajuste coberto pela documentação, então o resultado
    demonstrável continua sendo produzido e os valores substituíveis pelo
    usuário estão claramente distintos da configuração fixa (critério de
    aceite 3 de `vision.md`).
- **Fonte:** issue #93, "Escopo" ("instruções de uso e customização");
  `vision.md`, critério de aceite 3. Regras: RN-003.

### RF-004 — Registro de validação interna por execução

- **Descrição:** o sistema (processo de validação, não o software da
  Esteira) deve produzir um registro por execução de validação de cada
  exemplo, contendo execução (sucesso/falha), ajuda necessária, tempo
  observado, falhas, dúvidas, qualidade avaliada contra o objetivo do
  exemplo, modelo, tokens e custo observados.
- **Ator:** Analista/Engenheiro interno (validador).
- **Pré-condição:** exemplo (RF-001 ou RF-002) disponível para execução.
- **Fluxo principal:**
  1. O validador executa o exemplo do zero, cronometrando o tempo e
     anotando qualquer ajuda externa necessária (ex.: consulta a alguém da
     equipe).
  2. Ao final, o validador registra o resultado, as fricções encontradas, o
     modelo/tokens/custo observados, e avalia a qualidade do resultado
     contra o objetivo declarado do exemplo.
- **Alternativos/exceções:** se a execução falhar, o registro deve conter a
  falha e o ponto em que ocorreu — a validação não é considerada concluída
  até haver ao menos uma execução com resultado registrado (sucesso ou
  falha documentada). Ambos os exemplos devem passar pelo teste interno
  antes da apresentação (critério de saída do Bloco 3).
- **Critérios de aceitação:**
  - Dado um exemplo executado por um validador, quando a execução termina
    (com sucesso ou falha), então existe um registro com todos os campos
    exigidos por RN-005/RN-006 preenchidos (ou explicitamente marcados como
    não aplicável, com justificativa).
  - Dado um registro de validação, quando ele menciona custo ou tokens,
    então o registro identifica o modelo, o cenário e a versão observados,
    sem generalizar para outros cenários (RN-006).
- **Fonte:** issue #93, "Escopo" (parágrafo sobre a validação); `vision.md`,
  "Retorno e como medir" (itens 1 e 2), Bloco 3 de `epicos.md`. Regras:
  RN-005, RN-006.

### RF-005 — Conteúdo mínimo obrigatório por exemplo

- **Descrição:** o sistema deve garantir que cada exemplo publicado declare,
  no mínimo: objetivo, público, caso de uso, pré-requisitos, resultado
  esperado, limites, versão suportada e responsável pela revisão.
- **Ator:** Responsável pela revisão.
- **Pré-condição:** exemplo em processo de publicação (após validação
  interna aprovada).
- **Fluxo principal:**
  1. Antes de publicar, o responsável confere que os oito campos mínimos
     estão presentes e preenchidos no exemplo.
  2. Um exemplo sem algum campo mínimo não é publicado.
- **Alternativos/exceções:** nenhuma — os oito campos são obrigatórios,
  conforme RN-009 (RN01/RN07 de `vision.md`).
- **Critérios de aceitação:**
  - Dado um exemplo pronto para publicação, quando revisado contra a lista
    de campos mínimos, então todos os oito campos estão presentes e não
    vazios.
- **Fonte:** issue #93, "Escopo" (lista de itens que "cada exemplo deve
  conter"); `vision.md`, RN01/RN07. Regras: RN-009.

### RF-006 — Registro de apresentação e decisão do prospect

- **Descrição:** o sistema (processo de apresentação) deve permitir
  registrar, após cada apresentação dirigida a um prospect, a compreensão
  observada, o interesse explícito ou a recusa com objeções, e o próximo
  passo acordado.
- **Ator:** Apresentador; Prospect (fonte da manifestação).
- **Pré-condição:** exemplos validados internamente (RF-004 concluído com
  aprovação) e apresentação agendada.
- **Fluxo principal:**
  1. O apresentador conduz a apresentação usando os exemplos Minimalista e
     Referência hipotética.
  2. Ao final, o apresentador registra a compreensão do prospect sobre o
     que foi demonstrado — sem interpretação corrigida pelo apresentador
     (item 3 de "Retorno e como medir" em `vision.md`).
  3. O apresentador registra a decisão explícita do prospect — interesse em
     próxima avaliação/uso, ou não interesse — e, no caso de recusa, as
     razões/objeções.
- **Alternativos/exceções:** se o prospect não manifestar uma decisão
  explícita na apresentação, o apresentador deve registrar isso como
  decisão pendente e agendar o acompanhamento — uma apresentação sem
  decisão registrada (nem "interesse" nem "recusa") não satisfaz este
  requisito (RN-007). O critério de saída do Bloco 3 aceita como resultado
  válido "não avançar", desde que registrado.
- **Critérios de aceitação:**
  - Dado uma apresentação concluída, quando o registro é preenchido, então
    contém compreensão, decisão explícita (interesse ou recusa) e, se
    recusa, ao menos uma razão/objeção.
  - Dado um registro de apresentação com "opinião genérica" ou
    "visualização" sem decisão explícita, quando avaliado, então não é
    aceito como prova de interesse (RN-007).
- **Fonte:** issue #93, "Público e validação inicial" e "Retorno e decisão";
  `vision.md`, resultado esperado 3, "Retorno e como medir" (item 4).
  Regras: RN-005, RN-007.

### RF-007 — Avaliação de impacto de épicos futuros sobre os exemplos publicados

- **Descrição:** o processo de qualquer épico futuro da Esteira que alcance
  a etapa de documentação deve avaliar se a mudança entregue afeta algum
  exemplo publicado, e atualizar o exemplo quando necessário.
- **Ator:** Responsável pela revisão (do exemplo); agente/processo do épico
  em curso (que dispara a avaliação).
- **Pré-condição:** ao menos um exemplo desta entrega está publicado; um
  novo épico chega à etapa de documentação.
- **Fluxo principal:**
  1. Ao entrar na etapa de documentação, o épico em curso avalia se a
     mudança altera algo referenciado por um exemplo publicado
     (comportamento de configuração, estrutura de contexto, comandos
     `@---`, etc.).
  2. Se afetar, o exemplo é atualizado e revalidado (repetindo RF-004 para
     a parte alterada) antes de ser considerado consistente novamente.
  3. Se não afetar, a ausência de impacto é registrada (não é necessário
     alterar o exemplo).
- **Alternativos/exceções:** a implementação técnica dessa avaliação (ex.:
  automação de board ou ajuste de `target-prompt` na coluna de
  documentação) é explicitamente fora de escopo desta entrega (Bloco 3 de
  `epicos.md`) — este requisito especifica o processo, não sua automação.
- **Critérios de aceitação:**
  - Dado um épico que alcança a etapa de documentação, quando essa etapa é
    concluída, então existe um registro de avaliação de impacto sobre os
    exemplos publicados (com ou sem necessidade de atualização).
  - Dado um exemplo desatualizado por uma mudança de produto não avaliada,
    quando detectado, então é tratado como falha de processo, não como
    comportamento aceitável.
- **Fonte:** issue #93, "Critérios de aceite de negócio"; `vision.md`, RN08,
  critério de aceite 8; histórico, resposta do dono, item 7. Regras:
  RN-008.

### RF-008 — Gatilho de épico de expansão ao entrar em produção

- **Descrição:** ao esta entrega (Minimalista + Referência hipotética)
  entrar em produção, um novo épico deve ser solicitado para reavaliar os
  temas hoje fora de escopo, sujeito à mesma diligência e aprovação desta
  entrega.
- **Ator:** Dono do produto (solicitante do novo épico).
- **Pré-condição:** os dois exemplos desta entrega estão publicados e em
  produção.
- **Fluxo principal:**
  1. Ao confirmar a entrada em produção, o dono solicita a abertura de um
     novo épico para os temas restantes (Kanban, Scrum, Acadêmico, XGH,
     Gestão, RH, Atendimento).
  2. O novo épico segue o mesmo ciclo de diligência e aprovação desta
     entrega (requisitos, arquitetura, stories, etc.) — não há
     aproveitamento automático de escopo; o novo épico não nasce
     pré-aprovado (critério de saída do Bloco 3).
- **Alternativos/exceções:** nenhuma. Este requisito não obriga a
  construção de nenhum tema restante — apenas a solicitação do épico de
  avaliação.
- **Critérios de aceitação:**
  - Dado a entrada em produção desta entrega, quando confirmada, então um
    novo épico é solicitado para os temas restantes.
  - Dado o novo épico solicitado, quando avaliado, então nenhum tema
    restante é tratado como já aprovado ou já priorizado por herança desta
    entrega.
- **Fonte:** issue #93, "Critérios de aceite de negócio" e "Fora de
  escopo"; `vision.md`, RN09/RN10, critério de aceite 9; histórico,
  resposta do dono, item 8. Regras: RN-001, RN-010.
