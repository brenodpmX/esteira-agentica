# Registro de execução de agentes + linhagem histórica (#307)

Documentação da capacidade entregue pela issue #307. Descreve os campos do
registro, a taxonomia de resultado, a semântica de consumo/unidade, a regra de
repetição sem avanço, a regra de linhagem histórica (resiliente a arquivamento e
expurgo de logs) e a configuração de retenção.

## Visão geral

Ao final de **cada** execução de agente e em **qualquer** desfecho, o motor
grava um **registro de negócio estruturado e persistente**, independente do log
detalhado em Markdown (`logs/<issue_id>/<ts>.md`, sujeito a `log.ttl`). O
registro é a base durável para responder, em lote e sem abrir logs individuais:
quantas execuções uma issue exigiu, quanto tempo/consumo cada etapa demandou,
quais desfechos ocorreram, quanto esforço foi repetido sem a issue progredir, e
qual o esforço agregado de uma issue principal somada a todos os descendentes
históricos conhecidos.

- **Módulo core:** `src/core/execution_record.py`.
- **Armazenamento durável:** `.pipe/executionRecords.json` (estado interno
  protegido — entra em `PROTECTED_PATHS`, nunca exposto a agente/prompt/log).
- **Ponto de gravação:** ao fim de `call_agent` (`src/__main__.py`), após o
  dispatch, em qualquer desfecho (fail-safe: falha de persistência do registro
  não derruba a esteira — a execução já ocorreu).
- **Fonte única de contagem por contexto:** a métrica "quantas execuções houve
  no contexto `(board, coluna, issue)`" continua tendo origem única em
  `src/core/agent_circuit_break.py`. Esta capacidade **não** cria contador
  paralelo de contexto; grava **um registro por execução** (artefato de negócio
  por execução), que não é a métrica de contexto.

## Campos do registro

| Campo | Significado |
|-------|-------------|
| `execucao_id` | Identidade única da execução. |
| `issue_id` | Identidade da issue executada. |
| `issue_parent` | Vínculo de parentesco **observado no momento da execução** (id da mãe, ou ausente se raiz). Base durável da linhagem — não depende de arquivo local/snapshot. |
| `board` | Board no momento da execução. |
| `etapa` | Coluna/etapa no momento da execução. |
| `plataforma` | Plataforma de IA usada. |
| `agente` | Identificação do agente. |
| `modelo` | Modelo utilizado. |
| `inicio` / `fim` | Instantes (epoch) de início e término (quando conhecido). |
| `duracao` | Derivada de `inicio`/`fim` quando ambos conhecidos. |
| `resultado` | Taxonomia fechada (ver abaixo); nunca vazio/nulo. |
| `avancou` | Booleano, **independente** de `resultado` (RN-01). |
| `repeticao_sem_avanco` | Booleano derivado (RN-03). |
| `consumo` | `{ disponibilidade, unidade, origem, valor? }` com proveniência. |
| `log_ref` | Referência lógica ao log detalhado (**sem** copiar prompt/conversa). |

O registro **nunca** replica prompt nem conversa (RN-13/RNF-07): no máximo uma
referência (`log_ref`) ao diretório do log detalhado.

## Taxonomia de `resultado` (fechada, total, determinística)

`resultado` assume exatamente um de: `concluída`, `falha terminal`, `timeout`,
`interrompida`, `desconhecida` (RN-02). Desfecho indeterminado grava
`desconhecida`, nunca vazio.

Mapeamento concreto `ExecutionResult.classe` (+ `origem`) → `resultado`
(`map_resultado`):

| Classe de `ExecutionResult` | Origem estruturada | `resultado` |
|-----------------------------|--------------------|-------------|
| `SUCEDIDO` | — | `concluída` |
| `FALHA` / `falha persistente` | `timeout` | `timeout` |
| `FALHA` / `falha persistente` | demais (`exit-code`, `erro interno`, …) | `falha terminal` |
| `UNKNOWN_OUTCOME` | `timeout` | `timeout` |
| `UNKNOWN_OUTCOME` | `dispatch failure` / `erro interno` | `interrompida` |
| `UNKNOWN_OUTCOME` | ausente/inconclusiva | `desconhecida` |
| `DEFINITE_NOT_STARTED` | — | `falha terminal` |
| qualquer classe desconhecida | — | `desconhecida` |

O mapeamento é **total** (nenhuma classe fica órfã) e **determinístico** (mesma
entrada → mesmo resultado).

## Avanço e repetição sem avanço

- **`avancou` (RN-01):** dimensão independente do resultado técnico. Observado no
  motor pela **ausência** do `-body.md` na coluna de origem após a execução — o
  agente move os 3 arquivos da issue para a coluna de destino ao concluir a
  etapa. Uma falha técnica **não** apaga o fato de a issue ter avançado, e um
  sucesso que não moveu a issue registra `avancou = não`.
- **`repeticao_sem_avanco` (RN-03):** derivado. É `verdadeiro` quando já existe
  ao menos uma execução anterior da **mesma** issue, na **mesma** etapa (mesmo
  board e mesma coluna), que **não** avançou a issue. Mudança de etapa
  descaracteriza (a etapa é parte da identidade).

## Consumo (proveniência)

`consumo` preserva valor, unidade, origem e disponibilidade (RN-04/RN-05):

- **Indisponível** (`disponibilidade = indisponível`): a plataforma não reportou
  consumo; `valor` **não** é definido (nunca zero). É o caso do adapter
  `kiro-cli`, que não expõe contagem de tokens — comportamento **correto**, não
  falha.
- **Zero reportado** (`disponibilidade = disponível`, `valor = 0`): estado
  **distinto** de indisponível; nunca compartilham representação.
- **Disponível** (`valor`, `unidade`, `origem`): a **unidade nativa** da
  plataforma é preservada (ex.: `créditos`), sem conversão. "Tokens" é apenas o
  **rótulo geral** do núcleo (`ROTULO_CONSUMO`), nunca uma equiparação entre
  unidades. Moeda só quando a própria plataforma for a fonte.

Invariante (RNF-02): `disponibilidade = indisponível ⇒ valor não definido`.

## Linhagem histórica (consulta por issue raiz)

`consulta_linhagem(issue_raiz)` consolida a issue raiz e todos os seus
descendentes **conhecidos**, reconstruindo a árvore **somente** dos registros
próprios (`issue_id` + `issue_parent`), sem abrir nenhum log individual e sem
depender de arquivos locais.

- **Resiliência à limpeza local (RN-06/CA-9):** arquivar a issue (apaga
  `-body/-history/-addcomment` locais) e expurgar logs por TTL **não** removem a
  existência, o parentesco nem as métricas — eles vivem nos registros próprios.
- **"Descendente conhecido":** issue cuja existência e vínculo de parentesco
  foram capturados por **ao menos um registro de execução**.
- **Descendente sem registro (RN-08):** incluído com `sem_registro = verdadeiro`
  e `execucoes = 0`; nunca omitido nem tratado como "zero execuções" silencioso.
- **Sem ciclo nem dupla contagem (RN-07):** a travessia usa um conjunto
  `visited`; cada issue e cada execução contam **exatamente uma vez**, mesmo com
  ciclo de vínculos ou múltiplos caminhos até o mesmo descendente.

Saída lógica:

```
consulta_linhagem(issue_raiz):
  itens_por_issue:
    - { issue_id, sem_registro, execucoes }
  agregados:
    quantidade_execucoes
    duracao_total
    consumo_por_unidade_origem:         # nunca soma unidades distintas
      - { unidade, origem, total, ha_indisponivel }
    distribuicao_resultados:            # as 5 chaves da taxonomia, sempre presentes
    repeticoes_sem_avanco
```

`consumo_por_unidade_origem` traz **uma entrada por `{unidade, origem}`** com o
`total` por segmento e `ha_indisponivel` sinalizando a presença de execução sem
consumo — **nunca** um total único somando unidades distintas (RN-05/CA-7).

Consulta direta por issue: `records_for_issue(issue_id)` devolve todos os
registros de uma issue, independentemente de ela ainda existir localmente
(preservação após exclusão — CA-13/RNF-09).

## Retenção própria (configuração)

Controlada por `registro.retencao_dias` no `pipe.yml`, **independente** do
`log.ttl`:

```yaml
registro:                 # opcional, na RAIZ; ausente = sem expurgo automático
  retencao_dias: 30       # inteiro > 0 (dias)
```

- **Ausente** ⇒ nenhum expurgo automático (estado seguro por padrão — RN-09).
- **Presente** ⇒ registro com idade `(agora - inicio) >= retencao_dias` fica
  elegível a expurgo. Registros sem `inicio` conhecido são preservados (sem idade
  segura).
- **Validação de forma** (`validate_registro` em `src/core/config.py`): quando
  presente, inteiro `> 0`; `bool` rejeitado antes de `int`; campos desconhecidos
  rejeitados; `ConfigError` citando o caminho, na verificação de configuração,
  antes de qualquer alteração de estado.
- **Expurgo** (`purge_expired`): acionado pela lógica interna do motor no startup
  (após `log.cleanup()`). É o **único** caminho de remoção — não há exclusão
  manual de registro por qualquer papel (RN-11/CA-14/RNF-10).

## Restrições de superfície

- Registros só nascem na **execução** e só saem por **expurgo por retenção**
  (RN-11). Não há operação de exclusão manual de um registro específico.
- O armazenamento (`.pipe/executionRecords.json`) é estado interno protegido:
  consta de `PROTECTED_PATHS` e `build_prompt` rejeita o caminho se ele aparecer
  no prompt. Seu conteúdo nunca é exposto a agente/comentário/log.
- A autorização de **quem consulta/exporta** é decisão do operador da instância
  (RN-12); o produto não impõe segunda política de papéis.

## Cobertura de testes

- `tests/test_execution_record.py` — CT-01..CT-06, CT-13, CT-16, CT-17, CT-18,
  CT-19, CT-20 (registro por execução, taxonomia total).
- `tests/test_execution_lineage.py` — CT-07, CT-08, CT-09, CT-09b, CT-10,
  CT-13b, CT-15, CT-21 (linhagem resiliente, ciclo/caminho duplo, segmentação,
  sem abrir logs, baseline de 30 dias).
- `tests/test_execution_record_retention.py` — CT-11, CT-12 (retenção própria,
  borda `>= N`, desligada por padrão).
- `tests/test_execution_record_config.py` — CT-11b (validação de forma).
- `tests/test_execution_record_surface.py` — CT-14, CT-16 (ausência de exclusão
  manual, `PROTECTED_PATHS`).
- `tests/test_execution_record_integration.py` — gravação ao fim de `call_agent`
  em qualquer desfecho, avanço observado, `issue_parent` capturado, um registro
  por execução.
