# Glossário — Registro de execução de agentes

Status: approved
Owner: requirements
Updated: 2026-08-26

## Inputs
- `doc/product/registro-execucao-agentes/vision.md`
- `doc/product/registro-execucao-agentes/problem-space.md`
- `doc/product/registro-execucao-agentes/epicos.md`
- Histórico de entrevista na issue #176 (2026-08-21 a 2026-08-26)

| Termo | Definição | Sinônimos / Evitar |
|-------|-----------|--------------------|
| Registro de execução | Entrada de negócio criada para cada entrega de uma issue a um agente, independente do TTL do log detalhado em Markdown. Contém identidade, tempo, contexto, resultado, avanço e consumo. | Evitar "log": o log detalhado (Markdown, sujeito a TTL) e o registro (estatístico, TTL próprio) são artefatos distintos e não se substituem. |
| Execução | Uma chamada do agente a uma issue, do início ao fim (ou interrupção), no ciclo de vida da esteira. Cada execução gera exatamente um registro. | Evitar confundir com "issue": uma issue pode ter várias execuções ao longo do tempo. |
| Avanço da issue | Indicador booleano e independente do resultado da execução: se a issue mudou de coluna/etapa como consequência daquela execução. | "Issue avançou". Evitar tratar como sinônimo de "concluída". |
| Resultado da execução | Classificação do desfecho técnico da execução, dissociada do avanço da issue. Valores mínimos: `concluída`, `falha terminal`, `timeout`, `interrompida`, `desconhecida`. | Evitar novos valores fora dessa lista sem decisão de negócio explícita. |
| Repetição sem avanço | Nova execução da mesma issue, na mesma etapa (board + coluna), que ocorre após uma execução anterior que não fez a issue avançar. | "Retrabalho" (termo informal usado na entrevista; o termo de negócio fechado é "repetição sem avanço"). |
| Linhagem histórica | Conjunto formado pela issue raiz e todos os seus descendentes já vinculados como filhos em algum momento, mesmo que o vínculo tenha sido removido posteriormente. Sem ciclos e sem dupla contagem. | Evitar confundir com "hierarquia atual" (apenas os filhos vinculados agora); a linhagem é histórica e cumulativa. |
| Issue raiz | Issue a partir da qual uma consulta/exportação de linhagem é solicitada. Normalmente um épico, mas o conceito é aplicável a qualquer issue com descendentes. | — |
| Descendente | Qualquer issue que, em algum momento do histórico, tenha sido registrada como filha (diretamente ou por transitividade) da issue raiz. | "Filho"/"sub-issue" quando o vínculo é atual; "descendente" é o termo que inclui também vínculos removidos. |
| Descendente sem registro | Descendente conhecido pela linhagem que não possui nenhum registro de execução associado. Deve ser sinalizado explicitamente na consulta/exportação, nunca omitido. | Evitar tratar como "zero execuções" sem distinguir de uma issue que teve execuções e cujo registro está indisponível. |
| Tokens | Termo geral de negócio usado no núcleo do produto para se referir a consumo de execução de agente. Cada plataforma/adapter preserva sua unidade nativa de relato (ex.: créditos no Kiro); "Tokens" é o rótulo agregador, não uma conversão de unidade. | Evitar usar "créditos" como sinônimo universal — créditos é a unidade nativa apenas da plataforma Kiro. |
| Créditos | Unidade nativa de consumo reportada pela plataforma Kiro para uma execução. Um dos valores possíveis de "unidade" dentro do conceito geral de Tokens. | Evitar equiparar numericamente a tokens técnicos ou a valor monetário sem fonte auditável. |
| Consumo indisponível | Estado explícito do campo de consumo quando a fonte (plataforma/adapter) não reportou valor para aquela execução. Distinto de consumo igual a zero. | Evitar registrar ausência de dado como `0`; `0` significa consumo relatado e igual a zero. |
| Fonte do consumo | Identificação de qual plataforma/adapter originou o valor de consumo registrado (ex.: Kiro CLI headless). Necessária para auditabilidade e para nunca equiparar unidades de fontes diferentes sem regra explícita. | — |
| Retenção própria | Prazo de vida do registro estatístico, configurável em dias, independente e desvinculado do TTL do log detalhado. | Evitar confundir com o TTL do log (`log.ttl` em `pipe.yml`), que é um mecanismo diferente e já existente. |
| Expurgo | Remoção de um registro de execução após atingir a idade configurada pela retenção própria. Só ocorre quando a retenção foi explicitamente configurada. | Evitar "TTL" isolado sem qualificar "do log" ou "do registro" — os dois TTLs coexistem e são independentes. |
| Etapa | Sinônimo de coluna do board no momento da execução (ex.: `doing`, `desenvolvimento`). Registrado no momento da execução, refletindo o estado da issue naquele instante. | "Coluna". Usar de forma intercambiável com o termo já consolidado em `pipe.yml`. |
| Board | Mesmo conceito já definido na esteira (ver `README.md`): agrupamento de colunas configurado em `boards` no `pipe.yml`. | — |
| Baseline operacional | Conjunto de métricas publicado ao final da primeira janela de 30 dias: falha terminal, repetição sem avanço, cobertura de consumo e consumo/duração por etapa. Não é uma meta corporativa (OKR) nem uma promessa de retorno monetário. | Evitar tratar como "OKR" — a documentação de negócio registra explicitamente a ausência de OKR formal para este épico. |
