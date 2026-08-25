# Blocos de entrega — Reorganização das documentações públicas

Status: proposta apta à aprovação de negócio
Owner: product
Last updated: 2026-08-25

## Inputs

- Issue #202 e entrevista com o dono.
- `vision.md`.
- `problem-space.md`.

## Princípios de execução

- Os blocos descrevem resultados de negócio, não stories nem solução técnica.
- A ordem é obrigatória porque a capacidade até 31/08 é desconhecida.
- Nenhum bloco autoriza decisão de arquitetura, ferramenta ou hospedagem.
- O baseline antecede reorganização ampla; o pós-teste decide continuidade.
- O agente reviewer aprova conteúdo público. O inventário atribui o responsável
  de manutenção de cada fonte.

## Ordem, esforço relativo e dependências

| Ordem | Bloco | Esforço relativo de negócio | Dependência | Regra de parada |
|---|---|---:|---|---|
| 1 | Evidência e fronteira editorial | Médio | Participantes e amostra de mudanças | Sem fricção material: ir ao fallback mínimo |
| 2 | Porta de entrada e jornadas prioritárias | Médio | Baseline e classificação inicial | Não publicar conteúdo sensível ou sem fonte canônica |
| 3 | Comunicação pública de versões | Pequeno a médio | Regra de elegibilidade e aprovação | Sem responsável/gate: manter processo mínimo explícito |
| 4 | Validação e manutenção | Médio e recorrente | Blocos 2 e 3 | Sem melhora ou capacidade de manutenção: não expandir |

“Esforço relativo” serve apenas para ordenar investimento; estimativa técnica e
capacidade são decisões de etapas posteriores.

## Bloco 1 — Evidência e fronteira editorial

**Objetivo:** provar onde o público falha e estabelecer o que pode ser público
antes de mover ou reescrever conteúdo.

**Resultados esperados:**

- baseline das três tarefas com pelo menos cinco representantes;
- auditoria de dez mudanças candidatas a comunicação;
- inventário priorizado com audiência, sensibilidade, fonte canônica,
  responsável, gatilho de atualização e destino proposto;
- classificação público/interno/misto segundo a finalidade confirmada;
- lista de erros críticos e lacunas da jornada que precisam de correção.

**Critérios de conclusão:**

- sucesso sem ajuda, tempo, dúvidas, abandono e consulta ao código registrados
  por tarefa;
- participantes incluem representantes do público primário;
- dez mudanças classificadas por elegibilidade, prazo e qualidade da mensagem;
- nenhum conteúdo misto é publicizado sem decisão explícita;
- agente reviewer valida o recorte público.

**Fallback:** se o baseline não revelar fricção material, seguir apenas com
README/material da apresentação, correções críticas e regra mínima de release.

**Fora de escopo:** produzir arquitetura de informação definitiva ou escolher
ferramenta.

## Bloco 2 — Porta de entrada e jornadas prioritárias

**Objetivo:** permitir avaliação e primeira execução sem ajuda, código ou
conhecimento da estrutura interna do repositório.

**Resultados esperados:**

- narrativa concisa de problema, valor, capacidades, limites e pré-requisitos;
- README atuando como porta de entrada para conteúdo canônico;
- jornada de primeira execução local apresentada primeiro;
- container apresentado como alternativa oficialmente suportada;
- configuração e exemplos localizáveis a partir da porta de entrada;
- conteúdo duplicado removido ou apontado para uma única fonte canônica;
- instruções críticas validadas nos modos suportados que forem tocados.

**Critérios de conclusão:**

- os três caminhos podem ser executados de ponta a ponta por revisão;
- nenhum caminho exige navegar por documentação interna de issues/desenvolvimento;
- nenhum erro crítico de segurança, compatibilidade ou pré-requisito permanece;
- cada página priorizada informa ou possui registro de responsável e gatilho de
  atualização;
- agente reviewer aprova clareza, consistência e fronteira pública.

**Fora de escopo:** reescrita total, tradução, portal, identidade visual ampla,
SEO ou escolha de tecnologia.

## Bloco 3 — Comunicação pública de versões

**Objetivo:** comunicar mudanças elegíveis no mesmo dia da versão, em linguagem
útil para usuários e avaliadores.

**Resultados esperados:**

- definição de versão/mudança elegível para comunicação pública;
- texto curado por versão com melhoria criada, benefício, impacto,
  compatibilidade e ação necessária;
- ausência de referências a issues, épicos, stories e detalhes internos;
- fonte canônica pública e ligação previsível a partir da porta de entrada;
- fluxo interno mínimo com gatilho, autor, agente reviewer, prazo e definição de
  pronto.

**Critérios de conclusão:**

- 100% das versões elegíveis da amostra possuem nota no mesmo dia;
- as notas auditadas permitem entender impacto e ação sem consultar artefatos
  internos;
- responsáveis e exceções estão explícitos;
- conteúdo automático, se usado como insumo, passa por curadoria antes da
  publicação.

**Fora de escopo:** definir pipeline, automação ou plataforma de release.

## Bloco 4 — Validação e manutenção

**Objetivo:** demonstrar retorno comportamental e impedir que a nova organização
se degrade após a apresentação.

**Resultados esperados:**

- pós-teste com participantes e tarefas comparáveis ao baseline;
- comparação de sucesso sem ajuda e tempo mediano;
- registro de dúvidas, erros e consultas ao código;
- verificação de prazo das comunicações elegíveis;
- rotina mínima de revisão de conteúdo e tratamento de conteúdo sem dono;
- decisão documentada de manter, ajustar, expandir ou interromper.

**Critérios de aprovação do resultado:**

- pelo menos 4 de 5 participantes concluem as três tarefas sem ajuda e sem
  consultar o código;
- sucesso aumenta e tempo mediano diminui, ou não há regressão quando o baseline
  já estiver no teto;
- nenhum erro crítico nos caminhos prioritários;
- 100% das versões elegíveis comunicadas no mesmo dia;
- conteúdo público priorizado possui fonte canônica e responsável;
- expansão só ocorre se houver capacidade explícita de manutenção.

**Fora de escopo:** atribuir causalidade a adoção ou retorno financeiro sem
telemetria apropriada.

## Sequenciamento mínimo para o prazo

Até 31/08, priorizar na ordem:

1. baseline e inventário apenas do conteúdo necessário às três tarefas;
2. README/narrativa e correções críticas dos caminhos prioritários;
3. regra e modelo mínimo de comunicação pública de versão;
4. pós-teste e decisão de continuidade.

Itens não essenciais não entram silenciosamente para cumprir uma “reorganização
completa”. Se a capacidade for insuficiente, o resultado mínimo permanece
publicável e mensurável, e o restante volta para decisão de prioridade após a
apresentação.
