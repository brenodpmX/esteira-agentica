# Espaço do problema — Reorganização das documentações públicas

Status: diligência concluída; apto à aprovação de negócio
Owner: product
Last updated: 2026-08-25

## Inputs e método

- Issue #202 e respostas do dono em 23 e 25/08/2026.
- Auditoria do repositório `origin/main` em 25/08/2026.
- Pesquisa de alternativas e práticas públicas: GitHub READMEs e release notes,
  Diátaxis e Keep a Changelog.

As respostas do dono foram tratadas como hipóteses. Afirmações sobre escala da
dor, ganho de tempo e adoção permanecem sem prova até o baseline; fatos do
repositório e políticas explicitamente confirmadas são apresentados
separadamente.

## Contexto

A Esteira Agêntica precisa ser apresentada externamente em setembro de 2026. O
dono, que também usa o produto, relata dificuldade para encontrar respostas e
necessidade recorrente de consultar o código. Ele priorizou arquitetos de
software avaliando integração de IA, sem excluir engenheiros, DevOps, QAs e
desenvolvedores independentes.

A documentação cresceu junto com o desenvolvimento. O README passou a acumular
introdução, configuração, operação, conceitos internos, incidentes e detalhes de
sincronização. Em paralelo, documentos especializados surgiram em diversas
áreas e formatos de mudança.

## Fatos observados

Auditoria em `origin/main`, em 25/08/2026:

- 51 arquivos Markdown públicos no repositório: três na raiz e 48 em `doc/`;
- oito áreas de primeiro nível em `doc/`: `architecture`, `changelogs`,
  `changes`, `incidente`, `product`, `requirements`, `runbook` e `stories`;
- `README.md` com 733 linhas e 41 títulos, sendo 13 seções de segundo nível;
- zero links Markdown relativos quebrados na verificação automatizada;
- 151 commits em `main` entre 25/07 e 25/08/2026;
- uma tag Git visível (`v1.5.0`), enquanto o `CHANGELOG.md` declara versões até
  1.11.0;
- nove arquivos em `doc/changelogs`, seis em `doc/changes` e um changelog geral,
  revelando canais paralelos de comunicação de mudança.

Esses fatos sustentam fragmentação, excesso de funções no README e governança
inconsistente de versões. Eles **não** demonstram, isoladamente, que usuários
falham ou quanto tempo/suporte será economizado. A ausência de links quebrados
indica que o problema não é uma simples faxina de links.

## Dor e causas prováveis

### Dor do público

O avaliador não possui um caminho curto e explícito para responder, na ordem:

1. isso resolve um problema relevante para minha equipe?
2. quais são limites, riscos e pré-requisitos?
3. consigo executar pela primeira vez sem interpretar o código?
4. onde encontro configuração e exemplos para uma avaliação real?
5. o que mudou em uma versão e o que preciso fazer?

O único relato direto ainda é do dono. A existência de potenciais participantes
permite validar a dor, mas não substitui os testes.

### Causas sustentadas por evidência

- **Porta de entrada sobrecarregada:** 733 linhas e múltiplos níveis de assunto
  misturam apresentação, operação e referência no README.
- **Organização por origem do trabalho:** diretórios de stories, requirements,
  incidentes e changes refletem o processo de desenvolvimento, não
  necessariamente as tarefas do público externo.
- **Fronteira público/interno implícita:** a localização em `doc/` não informa
  audiência ou sensibilidade; o próprio README liga para um runbook nessa área.
- **Comunicação de versões inconsistente:** tag, changelog geral e documentos de
  mudança não apresentam uma única cadência observável.
- **Governança incompleta:** não há inventário público com fonte canônica,
  responsável e gatilho de atualização.

## Pesquisa de mercado e alternativas

### Práticas relevantes

- O GitHub posiciona o README como lugar para explicar o que o projeto faz, por
  que é útil, como começar, onde obter ajuda e quem o mantém. Isso favorece um
  README-porta de entrada, não uma enciclopédia única.
- Diátaxis separa necessidades de aprendizado, execução, referência e
  explicação. A lição aplicável é organizar por necessidade real sem criar
  categorias vazias ou impor uma ferramenta.
- Keep a Changelog define changelog como lista curada de mudanças notáveis por
  versão. Isso é aderente ao pedido de falar do impacto, não dos artefatos
  internos.
- As release notes automáticas do GitHub oferecem PRs, contribuidores e
  changelog completo. São alternativa de baixo esforço, mas conflitam com a
  política confirmada de não citar issues, épicos ou stories no texto público;
  podem servir apenas como insumo.

### Alternativas avaliadas

| Alternativa | Benefício | Limite/risco | Decisão |
|---|---|---|---|
| Não fazer | Preserva capacidade e a prioridade do épico #93 | Mantém risco para a apresentação, consulta ao código e publicação inconsistente | Recusada |
| Ajustar apenas README/material da palestra | Menor esforço e resposta rápida | Não resolve governança nem comunicação recorrente | Fallback se baseline/capacidade não sustentarem escopo maior |
| Reorganização incremental por jornadas + inventário + regra de versão | Ataca encontrabilidade e manutenção com validação progressiva | Exige classificação e dono por conteúdo | Recomendada |
| Reescrita total | Uniformidade aparente | Alto custo, risco de regressão e pouco vínculo com dor comprovada | Recusada |
| Novo portal/site | Navegação e apresentação potencialmente melhores | Introduz decisão técnica e custo operacional antes de provar necessidade | Fora de escopo |
| Release notes totalmente automáticas | Baixo esforço recorrente | Expõem artefatos internos e não garantem narrativa de impacto | Apenas insumo possível, não solução de negócio |

## Custo de não fazer

- chegar à apresentação de setembro com uma jornada não testada e depender de
  explicação oral para suprir documentação;
- manter a necessidade de consultar código para dúvidas de uso, com risco de
  interpretação incorreta por avaliadores externos;
- continuar criando conteúdo em canais paralelos sem fonte canônica e
  responsável, elevando duplicação e desatualização;
- publicar versões sem mensagem consistente de benefício, compatibilidade e
  ação necessária;
- perder a oportunidade de estabelecer baseline, mantendo futuras decisões sem
  evidência de adoção ou suporte.

Não há dados para monetizar esses custos. A prioridade deve ser justificada por
redução de risco para a apresentação e aprendizado mensurável, não por ROI
financeiro inventado.

## Custo e trade-off de fazer

- o épico #93, “Exemplo de configurações de Esteira”, será postergado;
- pelo menos cinco participantes precisam dedicar tempo ao baseline e pós-teste;
- o agente reviewer assume o gate de aprovação, e responsáveis de manutenção
  ainda precisarão ser atribuídos durante o inventário;
- a capacidade até 31/08 é desconhecida, tornando obrigatório executar por
  ordem de valor e interromper no fallback se necessário.

## Hipóteses e como validá-las

| Hipótese | Evidência atual | Validação |
|---|---|---|
| O público não entende valor/limites rapidamente | Relato do dono; README extenso | Tarefa 1 com pelo menos cinco representantes |
| Primeira execução exige ajuda ou código | Relato do dono; caminhos local e container extensos | Tarefa 2, registrando sucesso, tempo, erros e consulta ao código |
| Configuração e exemplos são difíceis de encontrar | Fragmentação em 51 arquivos | Tarefa 3 e pontos de navegação observados |
| Publicação de mudanças é inconsistente | Tag em 1.5.0 versus changelog em 1.11.0; canais paralelos | Auditoria de dez mudanças/releases candidatas |
| Reorganização reduz esforço | Sem baseline | Comparação antes/depois; não prometer redução antecipadamente |

## Perguntas fechadas na entrevista

- Público primário e três tarefas: confirmados.
- Política público/interno: confirmada por finalidade, com casos mistos avaliados
  individualmente.
- Modos suportados: local primeiro e container como alternativa.
- Comunicação: mesmo dia da versão elegível, em linguagem de melhoria, sem
  artefatos internos.
- Aprovação: agente reviewer.
- Critério mínimo e fallback: aceitos.
- Trade-off: épico #93 postergado.

A quantidade de pessoas/horas até 31/08 segue desconhecida. Isso não bloqueia a
aprovação do problema, mas impede compromisso com todos os blocos no prazo. A
execução deve respeitar a ordem e a regra de parada descritas em `epicos.md`.

## Conclusão

A iniciativa deve avançar para aprovação de negócio com escopo incremental. A
dor tem um relato real e sinais estruturais, mas o tamanho do impacto ainda é
hipótese. O desenho de medição transforma essa incerteza em gate: provar antes,
entregar o mínimo de maior valor e expandir somente se o pós-teste demonstrar
melhora e houver capacidade de manutenção.
