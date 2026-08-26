# US — Retirar coluna vazia sem exigir destino

Status: draft
Owner: product
Last updated: 2026-08-26

## Inputs
- `doc/requirements/migracao-de-boards/functional-requirements.md` (F-001, RF-001, RF-002, RF-008)
- `doc/requirements/migracao-de-boards/business-rules.md` (RN-001, RN-004)
- `doc/requirements/migracao-de-boards/non-functional-requirements.md`
- `doc/architecture/migracao-segura-colunas/overview.md`
- `doc/architecture/migracao-segura-colunas/decisions/adr-001-expandir-migrar-contrair-no-core.md`

## Descrição

Como operador da esteira,
Quero que uma coluna sem nenhuma issue classificada seja retirada da
configuração publicada do board imediatamente, sem exigir destino,
Para que mudanças estruturais de baixo risco não fiquem bloqueadas por uma
exigência desnecessária de migração.

## Regras de negócio

- RN-001: coluna vazia pode ser retirada diretamente, sem etapa adicional de
  migração — nenhuma exceção.
- RN-004: a contagem de issues na coluna deve refletir o estado remoto no
  momento da avaliação, não um snapshot desatualizado; a confirmação de
  vazio deve ocorrer por uma leitura remota imediatamente anterior à
  retirada.
- A retirada desta coluna não pode impedir a reconciliação de outras
  colunas/boards no mesmo ciclo (operabilidade — cada origem é tratada
  independentemente).

## Critérios de aceitação

- Dado um board remoto com uma coluna presente no campo `Status` e ausente
  de `boards.<board>.columns`, e nenhuma issue classificada nessa coluna no
  momento da avaliação, quando a reconciliação estrutural é executada, então
  a esteira retira a opção correspondente do campo `Status` sem exigir
  `column-migrations` para essa origem.
- Dado o cenário acima, quando a retirada é confirmada, então a esteira
  realiza uma leitura remota imediatamente antes de retirar a opção, e não
  usa uma contagem obtida antes dessa leitura.
- Dado uma issue que passa a ser classificada na coluna momentos antes da
  leitura de confirmação, quando a esteira verifica novamente antes de
  retirar, então a retirada não ocorre nesse ciclo — a origem permanece
  ativa (este comportamento de borda é o gatilho para a story de coluna
  ocupada; aqui basta que a retirada não prossiga).
- Dado dois boards, um com coluna vazia retirada e outro com uma coluna
  ocupada ainda não tratada, quando a reconciliação é executada, então a
  retirada da coluna vazia conclui independentemente do estado do outro
  board.
- A operação usa exclusivamente a primitiva de contração de estrutura
  (`set_board_columns`/equivalente) já preparada pela story de preparação —
  nenhuma issue é lida ou alterada individualmente neste fluxo, pois não há
  issue na origem.

## Não objetivos

- Migrar issues de uma coluna ocupada (fica para a story seguinte).
- Validar ou aplicar destino declarado em `column-migrations` (não se aplica
  a coluna vazia).
- Produzir evidência estruturada de tentativa com contagens de itens
  movidos/restantes maiores que zero (o resultado aqui é sempre "concluída"
  com contagem inicial zero) — o formato completo do evento de observabilidade
  é definido na story de bloqueio, retomada e observabilidade, reaproveitado
  aqui apenas para o caso trivial.

## Rastreabilidade

- F-001 (functional-requirements.md).
- RF-001, RF-002, RF-008.
- RN-001, RN-004 (business-rules.md).
- ADR-001 — fase "contrair", caso sem migração prévia.
