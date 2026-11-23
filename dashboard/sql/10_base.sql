-- Views de base sobre as tabelas do clickhouseexporter.
-- Contrato de telemetria v1 (demanda de envio de telemetria da Esteira Agêntica).
-- Atributos chegam como texto em Map(String, String): números e booleanos são convertidos aqui.

-- Todos os eventos da esteira, com a identidade da pipe.
CREATE OR REPLACE VIEW v_eventos AS
SELECT
    Timestamp AS ts,
    ResourceAttributes['service.instance.id'] AS pipe,
    if(ResourceAttributes['esteira.pipe.nome'] != '', ResourceAttributes['esteira.pipe.nome'],
       ResourceAttributes['service.instance.id']) AS pipe_nome,
    ResourceAttributes['service.version'] AS versao,
    if(EventName != '', EventName, LogAttributes['event.name']) AS evento,
    LogAttributes AS a,
    TraceId AS trace_id,
    SpanId AS span_id
FROM otel_logs
WHERE ResourceAttributes['service.name'] = 'esteira-agentica';

-- Uma linha por execução de agente (esteira.agente.execucao).
CREATE OR REPLACE VIEW v_execucoes AS
SELECT
    ts AS fim,
    pipe,
    pipe_nome,
    a['esteira.execucao.id'] AS execucao_id,
    a['esteira.board'] AS board,
    a['esteira.coluna'] AS coluna,
    a['esteira.coluna.destino'] AS coluna_destino,
    a['esteira.issue'] AS issue,
    a['esteira.issue.pai'] AS pai,
    a['esteira.ia.plataforma'] AS plataforma,
    a['gen_ai.agent.id'] AS agente_id,
    if(a['gen_ai.agent.name'] != '', a['gen_ai.agent.name'], a['gen_ai.agent.id']) AS agente,
    a['gen_ai.request.model'] AS modelo,
    if(a['esteira.execucao.resultado'] != '', a['esteira.execucao.resultado'], 'desconhecida') AS resultado,
    a['esteira.execucao.avancou'] = 'true' AS avancou,
    a['esteira.execucao.repeticao_sem_avanco'] = 'true' AS repeticao_sem_avanco,
    a['esteira.execucao.classe'] AS classe,
    a['esteira.execucao.origem'] AS origem,
    toUInt32OrZero(a['esteira.execucao.tentativas']) AS tentativas,
    a['esteira.execucao.sessao'] AS sessao,
    toFloat64OrZero(a['esteira.execucao.duracao_s']) AS duracao_s,
    toFloat64OrNull(a['esteira.execucao.timeout_s']) AS timeout_s,
    a['esteira.consumo.disponivel'] = 'true' AS consumo_disponivel,
    if(a['esteira.consumo.disponivel'] = 'true', toFloat64OrNull(a['esteira.consumo.valor']), NULL) AS consumo,
    a['esteira.consumo.unidade'] AS unidade,
    toFloat64OrNull(a['esteira.composicao.tokens_entrada']) AS tokens_entrada,
    trace_id
FROM v_eventos
WHERE evento = 'esteira.agente.execucao';

-- Configuração efetiva por pipe (dashboard.yml); pipe sem bloco herda `padrao`.
CREATE OR REPLACE VIEW v_config AS
SELECT
    p.pipe AS pipe,
    if(c.pipe != '', c.boards_raiz, d.boards_raiz) AS boards_raiz,
    if(c.pipe != '', c.colunas_finais, d.colunas_finais) AS colunas_finais,
    if(c.pipe != '', c.ordem_colunas, d.ordem_colunas) AS ordem_colunas
FROM (SELECT DISTINCT pipe FROM v_eventos) AS p
CROSS JOIN (SELECT * FROM dashboard_config WHERE pipe = '' LIMIT 1) AS d
LEFT JOIN (SELECT * FROM dashboard_config WHERE pipe != '') AS c ON c.pipe = p.pipe;

-- Nós da hierarquia: estado mais recente de cada issue.
-- Prioridade: último esteira.issue.upsert; sem upsert, a execução mais recente.
CREATE OR REPLACE VIEW v_nos AS
WITH fatos AS (
    SELECT pipe, a['esteira.issue'] AS issue, a['esteira.board'] AS board,
           a['esteira.issue.pai'] AS pai, a['esteira.coluna'] AS coluna,
           a['esteira.issue.estado'] AS estado, a['esteira.issue.arquivada'] = 'true' AS arquivada,
           ts, 1 AS fonte
    FROM v_eventos WHERE evento = 'esteira.issue.upsert' AND a['esteira.issue'] != ''
    UNION ALL
    SELECT pipe, issue, board, pai, coluna, '' AS estado, false AS arquivada, fim AS ts, 0 AS fonte
    FROM v_execucoes WHERE issue != ''
)
SELECT
    n.pipe AS pipe,
    n.issue AS issue,
    n.board AS board,
    n.pai AS pai,
    n.coluna AS coluna,
    n.estado AS estado,
    n.arquivada AS arquivada,
    n.criada_em AS criada_em,
    (n.estado = 'closed' OR n.arquivada OR has(cfg.colunas_finais, n.coluna)) AS concluida,
    if(empty(cfg.boards_raiz), n.pai = '', has(cfg.boards_raiz, n.board)) AS e_raiz
FROM (
    SELECT pipe, issue,
           argMax(board, (fonte, ts)) AS board,
           argMax(pai, (fonte, ts)) AS pai,
           argMax(coluna, ts) AS coluna,
           argMaxIf(estado, ts, fonte = 1) AS estado,
           argMaxIf(arquivada, ts, fonte = 1) AS arquivada,
           if(countIf(fonte = 1) > 0, minIf(ts, fonte = 1), min(ts)) AS criada_em
    FROM fatos GROUP BY pipe, issue
) AS n
LEFT JOIN v_config AS cfg ON cfg.pipe = n.pipe;

-- Último bloqueio (trip de circuit break ou admissão negada por limite) por issue.
CREATE OR REPLACE VIEW v_bloqueios AS
SELECT pipe, a['esteira.issue'] AS issue, max(ts) AS ultimo_bloqueio
FROM v_eventos
WHERE evento = 'esteira.agente.circuit_break'
   OR (evento = 'esteira.agente.admissao_negada'
       AND a['esteira.admissao.motivo'] IN ('circuit_break', 'limite_consumo'))
GROUP BY pipe, issue;

-- Transições de coluna, com o tempo que a issue ficou na coluna de destino.
CREATE OR REPLACE VIEW v_transicoes AS
SELECT
    pipe, board, issue, de, para, ts,
    if(prox_ts > ts, dateDiff('second', ts, prox_ts), NULL) AS permanencia_s
FROM (
    SELECT pipe, a['esteira.board'] AS board, a['esteira.issue'] AS issue,
           a['esteira.coluna.de'] AS de, a['esteira.coluna.para'] AS para, ts,
           leadInFrame(ts) OVER (PARTITION BY pipe, a['esteira.issue'] ORDER BY ts
                                 ROWS BETWEEN CURRENT ROW AND 1 FOLLOWING) AS prox_ts
    FROM v_eventos WHERE evento = 'esteira.issue.transicao'
);

-- Métricas de estado (gauges) da esteira.
CREATE OR REPLACE VIEW v_metricas AS
SELECT
    TimeUnix AS ts,
    ResourceAttributes['service.instance.id'] AS pipe,
    MetricName AS metrica,
    Attributes AS a,
    Value AS valor
FROM otel_metrics_gauge
WHERE ResourceAttributes['service.name'] = 'esteira-agentica';

-- Lista de pipes conhecidas (abas).
CREATE OR REPLACE VIEW v_pipes AS
SELECT pipe, argMax(pipe_nome, ts) AS pipe_nome, argMax(versao, ts) AS versao, max(ts) AS ultima_atividade
FROM v_eventos
WHERE pipe != ''
GROUP BY pipe;
