# Regras de Negócio — Registro de execução de agentes

Status: approved
Owner: requirements
Updated: 2026-08-26

## Inputs
- `doc/product/registro-execucao-agentes/vision.md`
- `doc/product/registro-execucao-agentes/problem-space.md`
- `doc/product/registro-execucao-agentes/epicos.md`
- Histórico de entrevista na issue #176 (2026-08-21 a 2026-08-26)
- `doc/requirements/registro-execucao-agentes/glossary.md`

Este documento refina, para uso de arquitetura/engenharia/QA, as regras já
fechadas em `problem-space.md` ("Regras de negócio fechadas"). Não repete a
redação de negócio; adiciona contexto de aplicação, exceções e comportamento
esperado nas bordas de cada regra.

## RN-001 — Execução e avanço são dimensões independentes

**Regra:** o resultado técnico de uma execução (`concluída`, `falha terminal`,
`timeout`, `interrompida`, `desconhecida`) nunca é inferido a partir do avanço
da issue, e vice-versa. Os dois campos são registrados separadamente para toda
execução.
**Contexto:** aplica-se à criação de todo registro de execução, no momento em
que a execução do agente termina (ou é interrompida).
**Exceções:** nenhuma. Uma execução `concluída` pode não ter avançado a issue
(ex.: o agente concluiu mas sinalizou `/need_human`); uma execução
`interrompida` pode coexistir com avanço se o avanço ocorreu antes da
interrupção.
**Fonte:** `vision.md` ("Cada registro deve identificar (...) o resultado, se
houve avanço"); `problem-space.md` ("Regras de negócio fechadas").

## RN-002 — Taxonomia de resultado é fechada

**Regra:** todo registro de execução armazena exatamente um resultado dentre
os cinco valores aprovados: `concluída`, `falha terminal`, `timeout`,
`interrompida`, `desconhecida`. Nenhum outro valor é aceito sem nova decisão
de negócio.
**Contexto:** aplica-se à classificação do desfecho de cada execução, no
momento do registro.
**Exceções:** quando a esteira não conseguir classificar o desfecho com
segurança (ex.: sinal insuficiente do adapter), o resultado registrado é
`desconhecida` — nunca um campo vazio ou nulo.
**Fonte:** `problem-space.md` ("O dono aceitou como resultados...").

## RN-003 — Repetição sem avanço é uma regra reproduzível, não uma inferência

**Regra:** uma execução é contada como repetição sem avanço quando, e somente
quando, é uma nova execução da mesma issue, na mesma etapa (mesmo board e
mesma coluna), e a execução imediatamente anterior daquela issue naquela etapa
não resultou em avanço.
**Contexto:** aplica-se ao cálculo de repetição no momento em que uma nova
execução da mesma issue é registrada, ou em agregações posteriores sobre o
histórico de execuções.
**Exceções:** se a issue mudou de etapa entre as duas execuções, não é
repetição sem avanço — é execução de uma etapa nova (consistente com o
comportamento já existente de elegibilidade por coluna descrito no
`README.md`, seção de cooldown de reexecução).
**Fonte:** `problem-space.md` ("Regras de negócio fechadas"); resposta do
dono na entrevista de 2026-08-24 ("Concordo" à proposta de Helena Costa em
2026-08-22).

## RN-004 — Consumo preserva valor, unidade, fonte e disponibilidade

**Regra:** todo registro de execução representa o consumo com quatro atributos
explícitos: valor, unidade, fonte (plataforma/adapter) e disponibilidade
(disponível/indisponível). Consumo zero e consumo indisponível são estados
distintos e nunca são representados pelo mesmo valor.
**Contexto:** aplica-se à criação de todo registro de execução e a qualquer
agregação que some ou compare consumo entre execuções.
**Exceções:** nenhuma. Quando a fonte não reportar consumo para a execução, o
registro marca disponibilidade como `indisponível` — nunca estima ou assume
zero.
**Fonte:** `vision.md` e `problem-space.md` ("Valor, unidade, fonte e
disponibilidade devem permanecer explícitos, sem equiparar unidades ou
estimar dados ausentes").

## RN-005 — "Tokens" é rótulo geral; a unidade nativa da plataforma é preservada

**Regra:** o core do produto usa o termo "Tokens" como rótulo geral de
consumo. Cada adapter de plataforma preserva e registra sua própria unidade
nativa (ex.: créditos no Kiro) sem conversão nem equiparação numérica entre
unidades de plataformas diferentes.
**Contexto:** aplica-se ao registro de consumo de cada execução e a qualquer
exibição/exportação que precise mostrar a unidade ao operador.
**Exceções:** moeda só é registrada quando a própria plataforma for a fonte do
valor monetário; não há conversão presumida de créditos ou tokens para moeda.
**Fonte:** resposta do dono em 2026-08-24 ("No core o termo utilizado será
Tokens, cada adapter utilizar o seu próprio termo... Não trataremos de moedas
a menos que este for o medidor da plataforma de IA").

## RN-006 — Linhagem histórica é cumulativa e independente do vínculo atual

**Regra:** a consulta/exportação de uma issue raiz inclui todo descendente que
já tenha sido vinculado como filho em algum momento do histórico, mesmo que o
vínculo tenha sido removido posteriormente. A remoção de um vínculo de
parent/children não remove o descendente da linhagem histórica.
**Contexto:** aplica-se à consulta/exportação de linhagem e a qualquer
agregação de consumo/duração/resultado por issue raiz.
**Exceções:** nenhuma. Esta é a interpretação de negócio explicitamente
fechada para "todos os filhos criados por aquele issue, sem restrição".
**Fonte:** resposta do dono em 2026-08-22 ("A hierarquia será dada a partir de
todos os filhos criados por aquele issue, sem restrição"); confirmação de
Helena Costa em 2026-08-22 ("linhagem histórica: um descendente continua no
total mesmo se o vínculo for removido depois").

## RN-007 — Linhagem não admite ciclo nem dupla contagem

**Regra:** a consulta/exportação de linhagem detecta e neutraliza ciclos na
árvore de descendência, e cada issue (e cada execução) é contada exatamente
uma vez no agregado, mesmo que alcançável por mais de um caminho na linhagem.
**Contexto:** aplica-se à travessia da árvore de descendência histórica para
formar o conjunto de issues de uma consulta por raiz.
**Exceções:** nenhuma.
**Fonte:** `vision.md` ("100% dos descendentes históricos conhecidos
retornados sem ciclo ou dupla contagem"); `epicos.md` ("prevenção de ciclo e
dupla contagem").

## RN-008 — Descendente sem registro é sinalizado, nunca omitido

**Regra:** quando um descendente é conhecido pela linhagem mas não possui
nenhum registro de execução, a consulta/exportação inclui esse descendente
explicitamente marcado como sem registro, em vez de omiti-lo do resultado.
**Contexto:** aplica-se à composição do resultado de qualquer consulta/
exportação por issue raiz.
**Exceções:** nenhuma.
**Fonte:** `vision.md` ("itens sem registro sinalizados"); `problem-space.md`
("Descendentes conhecidos sem registro aparecem sinalizados, não desaparecem
do resultado").

## RN-009 — Registro tem retenção própria, independente do TTL do log

**Regra:** o registro de execução usa uma retenção própria, configurável em
dias, medida a partir da criação do registro. É independente e desacoplada do
TTL do log detalhado (`log.ttl` em `pipe.yml`). Quando a retenção não for
configurada, nenhum expurgo automático ocorre.
**Contexto:** aplica-se ao ciclo de vida de todo registro de execução, desde a
criação até um eventual expurgo.
**Exceções:** nenhuma. A ausência de configuração é o estado seguro por
padrão — sem perda de dado.
**Fonte:** resposta do dono em 2026-08-25 ("expurgo condicional (se o usuário
configurar) com TTL controlados por dias... se não configurar, não
removeremos"); `vision.md` ("retenção própria configurável em dias. Sem
configuração, não haverá expurgo automático").

## RN-010 — Exclusão de issue não afeta seus registros

**Regra:** excluir uma issue não exclui, não anonimiza e não rompe seus
registros de execução associados. Os registros permanecem acessíveis e sujeitos
apenas à política de retenção própria (RN-009).
**Contexto:** aplica-se a qualquer operação de exclusão de issue no board ou
no estado local da esteira.
**Exceções:** nenhuma.
**Fonte:** resposta do dono em 2026-08-25 ("a relação entre a issue e o seu
registro é independente... se houver [exclusão] o registro permanece");
`vision.md` ("A exclusão da issue não elimina seus registros").

## RN-011 — Somente a lógica do produto cria ou exclui registros

**Regra:** registros de execução só são criados ou excluídos pela lógica
interna do produto (na criação de uma execução ou no expurgo por retenção
própria). Não existe operação de exclusão manual de registro por papel de
negócio ou operação.
**Contexto:** aplica-se a toda superfície de acesso ao registro estatístico
(consulta, exportação, administração).
**Exceções:** nenhuma.
**Fonte:** resposta do dono em 2026-08-25 ("somente o código fonte pode criar
e excluir o registro"); `epicos.md` ("exclusão manual de registros por
usuário" listada como fora de escopo).

## RN-012 — Consulta e exportação são governadas pelo operador da esteira

**Regra:** quem pode consultar e exportar registros é uma decisão do operador
que administra a instância da esteira, não do produto. O produto não impõe
uma política de papéis/permissões própria além de expor o mecanismo de
consulta/exportação.
**Contexto:** aplica-se à camada de consulta/exportação do épico "Consulta,
exportação e baseline operacional".
**Exceções:** nenhuma.
**Fonte:** resposta do dono em 2026-08-25 ("a consulta é uma decisão do
operador da esteira"); `vision.md` ("a consulta/exportação será governada pelo
operador da esteira").

## RN-013 — Prompt e chat não são duplicados no registro estatístico

**Regra:** o registro de execução não replica o conteúdo de prompt e chat já
presentes no log detalhado. Esses conteúdos continuam existindo apenas no log,
sujeito ao seu próprio TTL.
**Contexto:** aplica-se à definição de quais campos compõem um registro de
execução.
**Exceções:** o registro pode referenciar o log detalhado (ex.: por
identificador/caminho), mas não copia prompt ou chat.
**Fonte:** `vision.md` e `problem-space.md` ("Prompt e chat permanecem no log
detalhado e não são duplicados no registro estatístico").

## RN-014 — Zero OKR/prazo/responsável não é motivo para estimar retorno monetário

**Regra:** a ausência de OKR formal, prazo externo e responsável nominal não
autoriza a atribuição de ROI monetário ao épico antes da publicação do
baseline de 30 dias e da definição de uma regra auditável de conversão.
**Contexto:** aplica-se a qualquer comunicação de status, aprovação ou
priorização deste épico e de seus derivados (ex.: dashboard futuro).
**Exceções:** nenhuma.
**Fonte:** `vision.md` ("ROI monetário não será prometido antes do baseline e
de uma regra auditável de conversão"); `problem-space.md` ("Critério de
decisão").
