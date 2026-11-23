-- Árvores: cada issue ligada à raiz mais próxima acima dela (ou a si mesma).
-- Raiz = issue de board listado em boards_raiz (dashboard.yml); sem boards_raiz,
-- issues sem pai. Subida limitada a 10 níveis, com proteção contra ciclo.
-- Uma raiz dentro de outra árvore começa a própria árvore (sem dupla contagem).
CREATE OR REPLACE VIEW v_arvore AS
WITH RECURSIVE cadeia AS (
    SELECT pipe, issue, issue AS atual, pai AS pai_atual, e_raiz AS atual_e_raiz,
           toUInt8(0) AS nivel, [issue] AS caminho
    FROM v_nos
    UNION ALL
    SELECT c.pipe, c.issue, n.issue, n.pai, n.e_raiz,
           toUInt8(c.nivel + 1), arrayPushBack(c.caminho, n.issue)
    FROM cadeia AS c
    INNER JOIN v_nos AS n ON n.pipe = c.pipe AND n.issue = c.pai_atual
    WHERE NOT c.atual_e_raiz AND c.pai_atual != '' AND c.nivel < 10
      AND NOT has(c.caminho, n.issue)
)
SELECT pipe, argMin(atual, c_nivel) AS raiz, issue, min(c_nivel) AS nivel
FROM (SELECT *, nivel AS c_nivel FROM cadeia)
WHERE atual_e_raiz
GROUP BY pipe, issue;
