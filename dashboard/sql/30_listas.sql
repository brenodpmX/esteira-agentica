-- Status atual de uma issue ou árvore (cor das barras). Ordem das regras:
-- concluída > bloqueada (bloqueio mais novo que a última execução) > sem execução
-- > resultado da última execução.
CREATE OR REPLACE FUNCTION esteira_status AS (concluida, ultimo_bloqueio, ultima_exec, n_exec, ultimo_resultado) ->
    multiIf(
        concluida, 'Concluída',
        ultimo_bloqueio > ultima_exec AND ultimo_bloqueio > toDateTime64(0, 9), 'Bloqueada',
        n_exec = 0, 'Sem execução',
        ultimo_resultado = 'concluída', 'Em andamento',
        ultimo_resultado = 'falha terminal', 'Falha',
        ultimo_resultado = 'timeout', 'Timeout',
        ultimo_resultado = 'interrompida', 'Interrompida',
        'Desconhecida');

-- Status de cor de uma execução.
CREATE OR REPLACE FUNCTION esteira_status_execucao AS (resultado) ->
    multiIf(
        resultado = 'concluída', 'Concluída',
        resultado = 'falha terminal', 'Falha',
        resultado = 'timeout', 'Timeout',
        resultado = 'interrompida', 'Interrompida',
        'Desconhecida');

-- G1: lista viva por árvore. Uma linha por (raiz, nível).
-- O custo só soma execuções da unidade pedida; o tempo soma todas.
-- Uso: SELECT * FROM v_lista_arvore(unidade = 'Créditos') WHERE pipe = '...'
CREATE OR REPLACE VIEW v_lista_arvore AS
WITH
ex AS (
    SELECT a.pipe AS pipe, a.raiz AS raiz, a.nivel AS nivel, a.issue AS issue,
           e.execucao_id AS execucao_id, e.fim AS fim, e.resultado AS resultado,
           e.duracao_s AS duracao_s, e.consumo AS consumo, e.unidade AS unidade,
           e.consumo_disponivel AS consumo_disponivel
    FROM v_arvore AS a
    LEFT JOIN v_execucoes AS e ON e.pipe = a.pipe AND e.issue = a.issue
),
por_raiz AS (
    SELECT pipe, raiz,
           maxIf(fim, execucao_id != '') AS ultima_exec,
           argMaxIf(resultado, fim, execucao_id != '') AS ultimo_resultado,
           countIf(execucao_id != '') AS n_exec_total,
           sumIf(consumo, execucao_id != '' AND unidade = {unidade:String}) AS consumo_total,
           sumIf(duracao_s, execucao_id != '') AS tempo_total_s
    FROM ex GROUP BY pipe, raiz
),
bloq AS (
    SELECT a.pipe AS pipe, a.raiz AS raiz, max(b.ultimo_bloqueio) AS ultimo_bloqueio
    FROM v_arvore AS a
    INNER JOIN v_bloqueios AS b ON b.pipe = a.pipe AND b.issue = a.issue
    GROUP BY pipe, raiz
),
por_nivel AS (
    SELECT pipe, raiz, nivel,
           sumIf(consumo, execucao_id != '' AND unidade = {unidade:String}) AS consumo,
           countIf(execucao_id != '') AS n_exec,
           countIf(execucao_id != '' AND NOT consumo_disponivel) AS n_sem_consumo,
           countIf(execucao_id != '' AND consumo_disponivel AND unidade != {unidade:String}) AS n_outra_unidade,
           sumIf(duracao_s, execucao_id != '') AS tempo_s,
           uniqExact(issue) AS n_issues
    FROM ex GROUP BY pipe, raiz, nivel
)
SELECT
    n.pipe AS pipe,
    n.raiz AS raiz,
    no.board AS raiz_board,
    n.nivel AS nivel,
    n.consumo AS consumo,
    n.n_exec AS n_exec,
    n.n_sem_consumo AS n_sem_consumo,
    n.n_outra_unidade AS n_outra_unidade,
    n.tempo_s AS tempo_s,
    n.n_issues AS n_issues,
    r.consumo_total AS consumo_total,
    r.tempo_total_s AS tempo_total_s,
    r.n_exec_total AS n_exec_total,
    no.criada_em AS criada_em,
    if(r.n_exec_total > 0, greatest(r.ultima_exec, no.criada_em), no.criada_em) AS ultima_atividade,
    esteira_status(no.concluida, b.ultimo_bloqueio, r.ultima_exec, r.n_exec_total, r.ultimo_resultado) AS status
FROM por_nivel AS n
INNER JOIN por_raiz AS r ON r.pipe = n.pipe AND r.raiz = n.raiz
INNER JOIN v_nos AS no ON no.pipe = n.pipe AND no.issue = n.raiz
LEFT JOIN bloq AS b ON b.pipe = n.pipe AND b.raiz = n.raiz;

-- G1.1: lista viva por issue (só execuções da própria issue), todos os boards.
CREATE OR REPLACE VIEW v_lista_issue AS
WITH por_issue AS (
    SELECT n.pipe AS pipe, n.issue AS issue,
           maxIf(e.fim, e.execucao_id != '') AS ultima_exec,
           argMaxIf(e.resultado, e.fim, e.execucao_id != '') AS ultimo_resultado,
           countIf(e.execucao_id != '') AS n_exec,
           countIf(e.execucao_id != '' AND NOT e.consumo_disponivel) AS n_sem_consumo,
           sumIf(e.consumo, e.execucao_id != '' AND e.unidade = {unidade:String}) AS consumo,
           sumIf(e.duracao_s, e.execucao_id != '') AS tempo_s
    FROM v_nos AS n
    LEFT JOIN v_execucoes AS e ON e.pipe = n.pipe AND e.issue = n.issue
    GROUP BY pipe, issue
)
SELECT
    p.pipe AS pipe, p.issue AS issue, no.board AS board, no.coluna AS coluna,
    p.consumo AS consumo, p.tempo_s AS tempo_s, p.n_exec AS n_exec,
    p.n_sem_consumo AS n_sem_consumo, no.criada_em AS criada_em,
    if(p.n_exec > 0, greatest(p.ultima_exec, no.criada_em), no.criada_em) AS ultima_atividade,
    esteira_status(no.concluida, b.ultimo_bloqueio, p.ultima_exec, p.n_exec, p.ultimo_resultado) AS status
FROM por_issue AS p
INNER JOIN v_nos AS no ON no.pipe = p.pipe AND no.issue = p.issue
LEFT JOIN v_bloqueios AS b ON b.pipe = p.pipe AND b.issue = p.issue;
