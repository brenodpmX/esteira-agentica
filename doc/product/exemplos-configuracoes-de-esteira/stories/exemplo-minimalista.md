# Exemplo Minimalista de configuração da Esteira

Como Analista/Engenheiro interno (validador)
Quero um pacote de exemplo com o menor `pipe.yml` e o menor conjunto de contextos de agente capaz de produzir um resultado demonstrável de ponta a ponta
Para compreender e executar o ciclo completo da Esteira sem precisar interpretar conceitos abstratos ou montar configuração do zero

## Regras de negócio
- RN-002 (vision RN03/RN04): nenhum dado pessoal, credencial, segredo ou identificador real de pessoa/empresa em qualquer artefato do exemplo; o cenário deve ser explicitamente rotulado como hipotético.
- RN-003 (vision RN01/RN06): a validação interna deste exemplo deve ser possível usando somente a documentação de uso — sem depender de conhecimento não documentado da implementação da Esteira.
- RN-004 (vision RN02): os contextos de agente do exemplo seguem o padrão vigente `contexts/<plataforma>/<agente>.md`, com conteúdo preenchido (não vazio).
- RN-005 (vision RN06): o resultado da validação é avaliado contra o objetivo declarado do próprio exemplo, sem meta numérica de conversão/adoção.
- RN-009 (vision RN01/RN07): o exemplo declara responsável pela revisão, versão suportada e gatilho de revisão.

## Critérios de aceitação
- Dado o `pipe.yml` e os contextos do exemplo Minimalista aplicados em um ambiente com os pré-requisitos do README atendidos, quando uma issue de exemplo é criada na coluna de entrada configurada, então a Esteira produz o resultado demonstrável descrito no exemplo sem intervenção manual fora da prevista nas instruções.
- Dado o exemplo Minimalista, quando um validador o executa seguindo somente a documentação de usuário, então nenhuma etapa exige conhecimento da implementação da Esteira não documentado no próprio exemplo.
- Dado o exemplo publicado, quando revisado contra a lista de campos mínimos (objetivo, público, caso de uso, pré-requisitos, resultado esperado, limites, versão suportada, responsável), então todos os oito campos estão presentes e não vazios.
- Dado o cenário do exemplo, quando revisado antes da publicação, então não há nome, credencial, identificador ou dado reconhecível de pessoa ou empresa real, e o cenário está explicitamente rotulado como hipotético.

## Não objetivos
- Cobrir múltiplos fluxos, equipes, boards ou domínios (fica para o exemplo de Referência hipotética).
- Otimizar para o menor custo universal de tokens/modelo.
- Definir tecnologia, arquitetura ou mecanismo de empacotamento/distribuição.
- Registrar a execução de validação interna ou a apresentação ao prospect (fica para a story de Validação e governança).

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-exemplo-minimalista-de-configuracao-da-esteira` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #93 — Exemplo de configurações de Esteira   (o épico que originou esta story)
- **Branch da issue pai**: `epic93-93-exemplo_de_configuracoes_de_esteira`   (branch do épico)

## Rastreabilidade
- Bloco 1 de `doc/product/exemplos-configuracoes-de-esteira/epicos.md`.
- RF-001, RF-003, RF-005 de `doc/requirements/exemplos-configuracoes-de-esteira/functional-requirements.md`.
- RN-002, RN-003, RN-004, RN-005, RN-009 de `doc/requirements/exemplos-configuracoes-de-esteira/business-rules.md`.
- Ordem relativa: 1 — tamanho **S**.
