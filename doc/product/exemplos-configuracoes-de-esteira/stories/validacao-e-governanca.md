# Validação da vitrine e governança dos exemplos de configuração da Esteira

Como Apresentador e Responsável pela revisão
Quero um roteiro de teste interno e de apresentação, com registro de execução, ajuda necessária, tempo observado, falhas, resultado, modelo/tokens/custo, e um registro pós-apresentação de compreensão, interesse/objeções e próximo passo
Para assegurar que os dois exemplos (Minimalista e Referência hipotética) estejam prontos para apresentação e transformar a reação do prospect em evidência para decidir manter, ajustar ou expandir a vitrine

## Regras de negócio
- RN-003 (vision RN01/RN06): a validação interna de cada exemplo usa somente a documentação destinada ao usuário final, sem atalhos de quem já conhece a implementação da Esteira.
- RN-005 (vision RN06): o resultado é avaliado contra o objetivo declarado do próprio exemplo, sem meta numérica de conversão/adoção/retorno financeiro.
- RN-006 (vision RN05): toda execução de validação registra modelo, tokens e custo observados, vinculados ao cenário e à versão — nunca como promessa de custo universal.
- RN-007 (vision resultado esperado 3): toda apresentação a um prospect registra uma decisão explícita (interesse em próxima avaliação/uso, ou recusa com razões/objeções); visualização ou opinião genérica não substitui essa decisão.
- RN-008 (vision RN08): todo épico futuro que alcançar a etapa de documentação deve avaliar se afeta algum exemplo publicado e atualizá-lo quando necessário — este processo (não sua automação) é parte do escopo desta story.
- RN-009 (vision RN01/RN07): cada exemplo declara responsável pela revisão, versão suportada e gatilho de revisão.
- RN-010 (vision RN09/RN10): ao entrar em produção, um novo épico deve ser solicitado para reavaliar os temas fora de escopo, sem compromisso prévio de construí-los.

## Critérios de aceitação
- Dado um exemplo (Minimalista ou Referência hipotética) executado por um validador, quando a execução termina (com sucesso ou falha), então existe um registro com execução, ajuda necessária, tempo observado, falhas, dúvidas, qualidade avaliada contra o objetivo do exemplo e modelo/tokens/custo observados.
- Dado um registro de validação que menciona custo ou tokens, quando revisado, então identifica o modelo, o cenário e a versão observados, sem generalizar o valor para outros cenários.
- Dado uma apresentação concluída ao prospect, quando o registro é preenchido, então contém compreensão observada, decisão explícita (interesse ou recusa) e, em caso de recusa, ao menos uma razão/objeção.
- Dado um registro de apresentação contendo apenas opinião genérica ou visualização sem decisão explícita, quando avaliado, então não é aceito como prova de interesse.
- Dado um épico futuro que alcança a etapa de documentação, quando essa etapa é concluída, então existe um registro de avaliação de impacto sobre os exemplos publicados (com ou sem necessidade de atualização).
- Dado a entrada em produção desta entrega, quando confirmada, então um novo épico é solicitado para os temas restantes, sem que nenhum deles seja tratado como já aprovado ou priorizado por herança.
- Dado os dois exemplos, quando prontos para publicação, então ambos passaram pelo teste interno e cada um declara responsável pela revisão e versão suportada.

## Não objetivos
- Implementar automação de board ou `target-prompt` para disparar a avaliação de impacto (RN-008 é processo, não automação nesta etapa).
- Definir meta numérica de conversão sem baseline ou amostra adequada.
- Criar telemetria, marketplace ou campanha de aquisição em escala.
- Construir qualquer tema fora de escopo (Kanban, Scrum, Acadêmico, XGH, Gestão, RH, Atendimento) — apenas solicitar o épico de expansão quando a entrada em produção ocorrer.

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-validacao-da-vitrine-e-governanca-dos-exemplos-de-configuracao-da-esteira` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #93 — Exemplo de configurações de Esteira   (o épico que originou esta story)
- **Branch da issue pai**: `epic93-93-exemplo_de_configuracoes_de_esteira`   (branch do épico)

## Rastreabilidade
- Bloco 3 de `doc/product/exemplos-configuracoes-de-esteira/epicos.md`.
- RF-004, RF-006, RF-007, RF-008 de `doc/requirements/exemplos-configuracoes-de-esteira/functional-requirements.md`.
- RN-003, RN-005, RN-006, RN-007, RN-008, RN-009, RN-010 de `doc/requirements/exemplos-configuracoes-de-esteira/business-rules.md`.
- Depende da conclusão das stories "Exemplo Minimalista" e "Exemplo de Referência hipotética" (o teste interno exige os dois exemplos publicados).
- Ordem relativa: 3 — tamanho **M transversal**.
