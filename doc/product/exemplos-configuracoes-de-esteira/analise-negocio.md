# Análise de negócio — exemplos de configurações de Esteira

Status: aguardando validação do dono  
Owner: product  
Última atualização: 2026-08-21

## Decisão executiva provisória

Existe evidência suficiente de uma oportunidade, mas ainda não para aprovar o
escopo proposto. O produto documenta configuração manual e o runbook afirma
explicitamente que não há arquivo de exemplo. Produtos alternativos reduzem a
barreira com starter templates, aplicações completas, galerias importáveis e
percursos por nível. Porém, a issue não informa baseline, público prioritário,
meta, ordem dos modelos nem se os seis temas são obrigatórios. Também pede
caminhos que não correspondem à estrutura documentada atualmente.

A recomendação provisória é **não avançar para aprovação até o dono responder às
perguntas registradas na issue**. Se as hipóteses forem confirmadas, a menor
aposta coerente é um catálogo progressivo começando por um modelo mínimo e um
modelo de referência, ambos utilizáveis e mensuráveis. Os pacotes de domínio
devem depender de evidência de demanda. Isso é direcionamento de produto, não
decisão de arquitetura.

## Problema e evidências

### Fatos internos

- `doc/runbook/docker.md` orienta o usuário a criar `pipe.yml` manualmente e
  registra: “não há arquivo de exemplo”.
- O `README.md` contém um trecho de configuração, mas não um pacote completo,
  pronto para uso, com os contextos correspondentes.
- A visão já entregue de Docker define como público o analista/desenvolvedor e
  como sucesso um usuário novo conseguir operar seguindo apenas a documentação.
  Um catálogo pode aderir a essa meta, mas o dono ainda precisa confirmar se o
  público desta iniciativa é o mesmo.
- A estrutura vigente documenta `contexts/<plataforma>/<agente>.md`. Não foi
  encontrada ocorrência de `pipe/contexts/kiro-cli` nem de
  `pipe/contexts/artifacts`; portanto, esses caminhos da demanda precisam ser
  corrigidos ou explicados antes da aprovação.

### Evidência de mercado e alternativas

- A documentação oficial do CrewAI oferece configuração declarativa, scaffold
  por CLI e biblioteca de templates. Sua coleção oficial de exemplos organizava
  aplicações completas por nível e domínio, incluindo starter, recrutamento,
  pesquisa e fluxos com humano no loop. A coleção foi arquivada em 20/04/2026,
  o que também evidencia o risco de obsolescência de exemplos sem governança.
- O AutoGen Studio oferece construtor declarativo, playground e galeria para
  descobrir/importar componentes, mas avisa que o Studio é protótipo e não uma
  aplicação pronta para produção. A referência reforça duas expectativas:
  descoberta simples e limites de uso explícitos.
- O template oficial de retrieval do LangGraph oferecia projeto inicial,
  configuração, testes e instruções de customização. Foi arquivado em
  20/08/2026, reforçando que “pronto para baixar” sem política de manutenção
  perde valor rapidamente.

Conclusão de mercado: exemplos prontos são uma prática de onboarding observável,
mas quantidade não é valor por si só. Progressão, executabilidade, limites de
uso, medição de consumo e manutenção são diferenciais necessários.

## Hipóteses a validar

| Hipótese | Evidência atual | Prova que falta |
|---|---|---|
| H1 — configurar do zero impede ou atrasa adoção | Lacuna explícita no runbook | tempo atual até primeiro ciclo, abandono e chamados |
| H2 — pacote mínimo reduz tempo até valor | prática recorrente nas alternativas | teste com novos usuários e meta do dono |
| H3 — há demanda pelos seis temas sugeridos | apenas a solicitação da issue | demanda por tema, público e frequência de uso |
| H4 — modelos reduzem custo de tokens | intenção declarada | baseline, unidade de custo, teto e execução comparável |
| H5 — catálogo melhora a meta de onboarding do Docker | aderência à visão existente | confirmação de que público e jornada são os mesmos |

## Retorno e como medir

O retorno esperado é reduzir esforço e risco de configuração e aumentar a taxa
de ativação. A proposta só deve ser aprovada com baseline e metas para:

1. **tempo até primeiro valor:** mediana entre início do setup e primeiro ciclo
   completo bem-sucedido;
2. **ativação:** percentual de usuários novos que completam um ciclo usando
   apenas um exemplo e sua documentação;
3. **qualidade operacional:** percentual de exemplos que iniciam, validam e
   concluem o cenário prometido na versão suportada;
4. **custo:** tokens e custo monetário por resultado concluído em cenário de
   referência, com modelo e condições registrados;
5. **suporte:** dúvidas/falhas de configuração por nova instalação;
6. **frescor:** exemplos compatíveis com a versão corrente e tempo para corrigir
   incompatibilidades.

Sem telemetria de uso, as métricas podem ser coletadas em testes de onboarding e
execuções controladas. Não se deve prometer “mais baixo custo” sem cenário,
modelo, qualidade mínima e medição reproduzível.

## Alternativas de produto

| Alternativa | Valor | Custo/risco de negócio |
|---|---|---|
| Manter apenas README/runbook | nenhum custo adicional | mantém configuração manual e não fecha a lacuna |
| Um único starter mínimo | valida H1/H2 rapidamente | não atende comparação de abordagens nem domínios |
| Catálogo progressivo mínimo + referência + temas validados | combina ativação e descoberta; recomendação provisória | requer priorização e manutenção contínua |
| Publicar todos os temas de uma vez | cobertura ampla | alto risco de escopo, baixa validação e catálogo obsoleto |
| Construtor/galeria interativa | ótima descoberta em concorrentes | nova iniciativa; fora desta diligência e sem evidência local |

## Ordem de grandeza relativa

Classificação de conteúdo e validação, não estimativa técnica:

1. **Minimalista — S:** menor conjunto e principal candidato a experimento.
2. **Intermediária/referência — M:** precisa ser generalizada e livre de
   credenciais, IDs e convenções específicas do ambiente atual.
3. **Kanban e Scrum — M cada:** exigem fidelidade ao método e critérios claros
   para não vender uma adaptação como modelo canônico.
4. **XGH — M:** simples em volume, mas demanda posicionamento inequívoco como
   sátira para não induzir prática inadequada nem confundir novos usuários.
5. **Acadêmico — L:** mais papéis, revisão, integridade/citação e validação com
   usuário do domínio.
6. **Gestão, RH ou atendimento — L cada:** são linhas de produto separadas;
   envolvem públicos, riscos e resultados próprios e não devem entrar só para
   aumentar o catálogo.

A ordem definitiva depende de demanda e objetivo confirmados pelo dono.

## Custo de não fazer

- continuidade do setup manual e do tempo de suporte associado;
- maior abandono antes do primeiro valor e menor aproveitamento da entrega
  Docker já disponível;
- configurações copiadas de trechos incompletos, com maior risco de erro;
- ausência de referência para consumo eficiente de tokens;
- concorrentes e alternativas seguem oferecendo scaffolds e descoberta guiada.

Não há dados para monetizar esses efeitos. O dono deve fornecer volume de novos
usuários, tempo médio de setup, abandono e suporte; sem isso, o custo de não
fazer permanece qualitativo.

## Aderência a metas e políticas

- **Aderência potencial:** onboarding autônomo e reprodutível definido na visão
  “Rodar no Docker”. Pendente confirmação do dono.
- **Segurança:** exemplos não podem conter segredos, credenciais, IDs reais ou
  dados pessoais; limites de uso devem ser explícitos.
- **Custo:** cada exemplo deve declarar cenário de referência, modelo, resultado
  mínimo e medição de consumo; “baixo custo” sem qualidade comparável não é
  critério aceito.
- **Domínios sensíveis:** RH e atendimento exigem dados fictícios e aviso contra
  decisões automatizadas indevidas. O acadêmico deve preservar integridade e
  rastreabilidade de fontes.
- **Posicionamento:** XGH deve ser rotulado como paródia, não boa prática.
- **Manutenção:** compatibilidade dos exemplos deve ser critério obrigatório de
  mudança do produto, com responsável e versão suportada definidos. O mecanismo
  de implementação será decidido em etapa técnica posterior.

## Critérios de aprovação do épico

O épico estará apto a avançar quando houver:

1. público e jornada prioritários;
2. dor comprovada por baseline ou pesquisa com usuários;
3. lista de modelos obrigatórios e ordem de entrega;
4. definição inequívoca do pacote e dos caminhos esperados;
5. métrica primária, baseline, meta e janela de avaliação;
6. critério comparável de qualidade/custo de tokens;
7. política de suporte, versionamento e manutenção;
8. aceite dos limites para XGH e domínios sensíveis.

## Perguntas ao dono

1. Quem é o usuário prioritário e qual tarefa tenta concluir?
2. Quais dados existem sobre tempo de setup, abandono, erros e suporte?
3. Os seis temas são escopo obrigatório ou ideias? Quais dois têm prioridade?
4. “Intermediária” deve reproduzir qual configuração, e o que precisa ser
   anonimizado/generalizado?
5. `pipe/contexts/...` e `contexts/artifacts` são novos requisitos ou nomes
   desatualizados? Qual pacote exato o usuário deve baixar?
6. Qual evento de negócio define sucesso, com baseline, meta e prazo?
7. Como comparar custo sem sacrificar qualidade: cenário, modelos permitidos,
   teto de tokens/custo e resultado mínimo?
8. Onde os exemplos serão descobertos e qual expectativa de suporte?
9. Quem responde por atualizá-los e quais mudanças obrigam revisão?
10. XGH deve ser publicado oficialmente como paródia? Há restrições para os
    exemplos acadêmico, RH e atendimento?

## Fontes

- Repositório: `README.md`, `doc/runbook/docker.md` e
  `doc/product/rodar-no-docker/vision.md`.
- [CrewAI — Agents](https://docs.crewai.com/en/concepts/agents)
- [CrewAI — coleção oficial de exemplos](https://github.com/crewAIInc/crewAI-examples)
- [Microsoft AutoGen Studio](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/index.html)
- [LangGraph Retrieval Agent Template](https://github.com/langchain-ai/retrieval-agent-template)

Conteúdo externo resumido e reformulado para cumprir restrições de licenciamento.
