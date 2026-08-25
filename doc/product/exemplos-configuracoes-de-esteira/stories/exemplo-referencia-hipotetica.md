# Exemplo de Referência hipotética de configuração da Esteira

Como Analista/Engenheiro interno (validador)
Quero um pacote de exemplo mais completo que o Minimalista, baseado em um cenário plausível de empresa que desenvolve software com apoio de IA, sem copiar configuração ou dados de uma empresa real
Para demonstrar ao prospect uma configuração representativa de como partes da Esteira trabalham em conjunto

## Regras de negócio
- RN-001 (vision RN09/RN10): esta entrega contém exatamente dois exemplos (Minimalista e Referência hipotética); nenhum outro tema (Kanban, Scrum, Acadêmico, XGH, Gestão, RH, Atendimento) é incluído como exemplo adicional.
- RN-002 (vision RN03/RN04): nenhum dado pessoal, credencial, segredo ou identificador real de pessoa/empresa; o cenário deve ser explicitamente rotulado como hipotético e generalizado se se aproximar demais de uma instalação real conhecida.
- RN-003 (vision RN01/RN06): a validação interna deve ser possível usando somente a documentação de uso do exemplo.
- RN-004 (vision RN02): os contextos de agente seguem o padrão vigente `contexts/<plataforma>/<agente>.md`, com conteúdo preenchido.
- RN-009 (vision RN01/RN07): o exemplo declara responsável pela revisão, versão suportada e gatilho de revisão.

## Critérios de aceitação
- Dado o `pipe.yml` e os contextos do exemplo de Referência hipotética aplicados em um ambiente com os pré-requisitos atendidos, quando o ciclo de exemplo é executado conforme as instruções de uso, então a Esteira produz o resultado demonstrável descrito no exemplo.
- Dado o cenário hipotético da Referência, quando revisado antes da publicação, então não há nome, credencial, identificador ou dado reconhecível de pessoa ou empresa real, e a diferença de conteúdo em relação ao Minimalista é compreensível e justificada.
- Dado um exemplo publicado, quando as instruções de customização são seguidas para um ajuste coberto pela documentação, então o resultado demonstrável continua sendo produzido e os valores substituíveis pelo usuário estão claramente distintos da configuração fixa.
- Dado o exemplo pronto para publicação, quando revisado contra a lista de campos mínimos, então todos os oito campos (objetivo, público, caso de uso, pré-requisitos, resultado esperado, limites, versão suportada, responsável) estão presentes e não vazios.

## Não objetivos
- Replicar uma instalação real específica (própria ou de terceiros).
- Prometer aderência ao processo do prospect antes da entrevista própria com ele.
- Incluir Kanban, Scrum, Acadêmico, XGH, Gestão, RH ou Atendimento como exemplos adicionais.
- Registrar a execução de validação interna ou a apresentação ao prospect (fica para a story de Validação e governança).

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-exemplo-de-referencia-hipotetica-de-configuracao-da-esteira` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #93 — Exemplo de configurações de Esteira   (o épico que originou esta story)
- **Branch da issue pai**: `epic93-93-exemplo_de_configuracoes_de_esteira`   (branch do épico)

## Rastreabilidade
- Bloco 2 de `doc/product/exemplos-configuracoes-de-esteira/epicos.md`.
- RF-002, RF-003, RF-005 de `doc/requirements/exemplos-configuracoes-de-esteira/functional-requirements.md`.
- RN-001, RN-002, RN-003, RN-004, RN-009 de `doc/requirements/exemplos-configuracoes-de-esteira/business-rules.md`.
- Depende da conclusão da story "Exemplo Minimalista" (o contrato de conteúdo do Bloco 1 deve estar estável antes de aplicar o aprendizado aqui).
- Ordem relativa: 2 — tamanho **M**.
