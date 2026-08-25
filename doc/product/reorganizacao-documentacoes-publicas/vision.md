# Visão — Reorganização das documentações públicas

Status: proposta apta à aprovação de negócio
Owner: product
Last updated: 2026-08-25

## Inputs

- Issue #202 "Reorganização das documentações públicas" e entrevista registrada
  no histórico em 23 e 25/08/2026.
- `README.md`, `CHANGELOG.md` e inventário de `doc/` em `origin/main`.
- Apresentação externa planejada para setembro de 2026.
- [GitHub — About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).
- [Diátaxis](https://diataxis.fr/), referência de organização por necessidade do
  usuário.
- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), referência para
  comunicação curada de mudanças relevantes por versão.
- [GitHub — Automatically generated release notes](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes),
  alternativa avaliada para notas de versão.

## Decisão recomendada

**Aprovar o problema e o recorte incremental descrito nesta visão.** Há
aderência direta à preparação da apresentação externa e evidência objetiva de
fragmentação e inconsistência de publicação. O retorno financeiro não pode ser
estimado porque não há telemetria de adoção, suporte ou tempo gasto. Por isso, a
aprovação deve ser controlada por testes de tarefa e pela capacidade disponível,
com fallback explícito para uma entrega mínima.

A aprovação não autoriza reescrita total, portal novo ou decisão de
tecnologia/arquitetura. Também não cria stories; os blocos de resultado estão em
`epicos.md` para decomposição posterior.

## Visão

Até 31/08/2026, deixar a documentação pública pronta para que um arquiteto de
software avaliando integração de IA consiga, sem consultar o código nem pedir
ajuda:

1. entender valor, capacidades, limites e pré-requisitos da Esteira Agêntica;
2. concluir a primeira execução local, encontrando container como alternativa
   oficialmente suportada;
3. localizar configuração e exemplos suficientes para decidir se vale avaliar
   adoção.

Depois do recorte inicial, toda versão elegível deve ter, no mesmo dia da
publicação, uma comunicação pública curada em linguagem de benefício, impacto,
compatibilidade e ação necessária, sem expor épicos, stories ou detalhes do
processo interno.

## Público

**Primário:** arquitetos de software avaliando tecnologias de integração de IA
para suas equipes.

**Secundários:** engenheiros de software, DevOps, QAs e desenvolvedores
independentes que desejam melhorar entregas ou seus próprios setups.

O dono indicou um diretor de desenvolvimento, dois profissionais de DevOps, um
arquiteto ativo em comunidade e outros engenheiros/QAs como potenciais
participantes. Isso prova disponibilidade plausível para pesquisa, mas não
prova a dor; a hipótese será validada pelo baseline e pós-teste com pelo menos
cinco representantes.

## Proposta de valor

Reduzir o esforço e a incerteza para avaliar e iniciar o produto, ao mesmo tempo
em que se estabelece uma fronteira clara entre conteúdo público e interno e uma
rotina sustentável de comunicação de versões.

O README será a porta de entrada, não o repositório de todo o conteúdo. A
organização seguirá tarefas do público e fonte canônica, sem exigir uma
estrutura ou ferramenta específica.

## Resultados e medição

### Baseline obrigatório

Antes da reorganização ampla:

- testar as três tarefas prioritárias com pelo menos cinco representantes do
  público;
- registrar sucesso sem ajuda, tempo por tarefa, pontos de abandono, dúvidas e
  consultas ao código;
- auditar uma amostra de dez mudanças candidatas a comunicação pública,
  registrando elegibilidade, prazo, duplicação, inconsistências e esforço;
- registrar dúvidas e esforço de suporte/publicação durante o período, quando
  disponíveis.

### Critérios de sucesso

- no pós-teste, pelo menos 4 de 5 participantes concluem as três tarefas sem
  ajuda e sem consultar o código;
- sucesso sem ajuda aumenta e o tempo mediano das tarefas diminui em relação ao
  baseline; se o baseline já atingir o teto, não pode haver regressão;
- nenhum erro crítico de instrução, segurança, pré-requisito ou compatibilidade
  é encontrado nos caminhos priorizados;
- 100% das versões elegíveis auditadas possuem comunicação pública no mesmo dia;
- cada conteúdo público priorizado possui público, fonte canônica, responsável
  e critério de atualização identificados;
- dúvidas recorrentes e esforço de suporte/publicação passam a ser registrados
  para comparação posterior, sem promessa de redução antes do baseline.

### Regra de investimento

Se o baseline não mostrar fricção material, a entrega fica limitada a:

1. README/material da apresentação como porta de entrada;
2. correções críticas encontradas nos caminhos prioritários; e
3. regra mínima de comunicação de versões.

O escopo completo só segue se houver melhora mensurável nos testes, comunicação
no prazo e capacidade de manutenção. Não se atribui ganho financeiro sem dados.

## Políticas confirmadas

- Um documento exclusivamente necessário para desenvolver a aplicação é
  interno; um documento exclusivamente necessário para agentes externos
  entenderem/usarem a aplicação é público.
- Conteúdo de uso misto é avaliado caso a caso por audiência, sensibilidade e
  benefício de publicização; a localização atual não define sua classificação.
- Máquina local e container são modos suportados. A jornada local aparece
  primeiro; container permanece como alternativa, sem alegar inferioridade.
- A comunicação pública nasce no mesmo dia da versão elegível e descreve o que
  melhorou ou foi criado para o usuário, sem citar issues, épicos ou stories.
- O agente reviewer aprova o conteúdo público e é o gate de consistência. Cada
  fonte também precisa de responsável de manutenção explícito no inventário.
- O épico #93 fica postergado enquanto este recorte prioritário é executado.

## Escopo

- narrativa pública concisa sobre problema, valor, limites e pré-requisitos;
- README como porta de entrada para jornadas públicas canônicas;
- caminhos testados de avaliação, primeira execução, configuração e exemplos;
- inventário e classificação de conteúdo por audiência, sensibilidade, fonte
  canônica, responsável e gatilho de atualização;
- notas públicas curadas para versões elegíveis;
- regra interna de publicação, aprovação, manutenção e definição de pronto;
- baseline, pós-teste e rotina mínima de acompanhamento.

## Fora de escopo

- decidir tecnologia, arquitetura, gerador de site ou plataforma de hospedagem;
- reescrever toda a documentação sem evidência de necessidade;
- tradução, SEO, identidade visual ampla ou portal dedicado;
- expor documentação interna de issues e desenvolvimento;
- criar stories nesta etapa;
- prometer aumento de adoção, redução financeira ou economia de suporte antes
  de existir baseline.

## Restrições e riscos

- A capacidade até 31/08 não foi quantificada. Portanto, a ordem dos blocos e o
  fallback mínimo são obrigatórios; prazo não pode ser convertido em expansão
  silenciosa de escopo.
- O relato inicial de confusão é uma amostra única. Os cinco testes evitam
  tratar opinião do dono como comportamento generalizável.
- Há risco de duplicação e desatualização se o inventário não indicar fonte
  canônica e responsável.
- Há risco de conteúdo interno ficar público; classificação e revisão devem
  anteceder publicação.
- Notas automáticas do GitHub listam PRs e contribuidores, mas não atendem
  sozinhas à política de comunicação sem artefatos internos; podem ser insumo,
  não o resultado público.
