# ADR-002 — Destino declarativo e retomada pelo estado remoto

Status: accepted
Owner: architecture
Last updated: 2026-08-25

## Inputs

- `/app/contexts/templates/docs/adr.md`
- `doc/architecture/migracao-segura-colunas/overview.md`
- `doc/requirements/migracao-de-boards/business-rules.md`
- `doc/requirements/migracao-de-boards/non-functional-requirements.md`
- `src/core/config.py`
- `src/core/snapshot.py`
- `src/core/change_queue.py`

## Contexto

Uma coluna removida já não possui um bloco em `columns`, portanto seu destino
não pode ser declarado dentro da própria coluna. A migração também precisa
retomar após crash sem duplicar movimentos e sem depender de arquivos internos
que o operador precise editar.

Persistir progresso por issue criaria duas fontes de verdade: o journal local e
o valor de `Status` do GitHub. Em falhas entre a mutation remota e a gravação
local, os dois poderiam divergir.

## Decisão

Adicionar ao board o mapa opcional:

```yaml
column-migrations:
  <origem-removida>: <destino-configurado>
```

Origem e destino são IDs de coluna do mesmo board. O mapa representa intenção,
não progresso. Pode ser publicado antes da retirada, no mesmo commit ou mantido
depois da conclusão. Só é acionado quando a origem está no schema remoto e
ausente de `columns`.

A validação de configuração verifica apenas forma e valores não vazios. A
validação semântica ocorre no reconciliador, depois da contagem remota:

- coluna vazia não exige destino;
- coluna ocupada exige destino presente em `columns` do mesmo board;
- origem, destino ausente, destino igual à origem ou destino também retirado
  bloqueiam a tentativa antes de qualquer movimento.

A retomada usa exclusivamente o estado remoto atual:

- issues ainda na origem são trabalho pendente;
- issues no destino já estão concluídas e não são movidas nem contadas de novo;
- origem remota ausente significa contração já concluída; e
- origem remota presente e vazia pode ser contraída.

Não é criado journal de migração nem são adicionados eventos estruturais à
`ChangeQueue`. O snapshot guarda a estrutura efetiva depois da reconciliação,
mas não é usado como prova de que a origem está vazia.

Cada invocação do reconciliador gera um `attempt_id` apenas para correlação de
logs. O resultado e as contagens ficam no logging operacional, não em estado de
coordenação.

## Justificativa

- O mapa por board expressa de forma inequívoca “uma origem, um destino” e torna
  destino cross-board impossível sem referência especial.
- Permitir pré-declaração reduz risco de rollout e não exige duas modalidades de
  configuração.
- O valor remoto de `Status` já é a evidência autoritativa de progresso.
- Releitura remota resolve o caso “mutation concluiu, processo caiu antes de
  gravar estado local” sem protocolo adicional.
- Validação semântica em runtime permite registrar contagem e motivo de bloqueio
  e continuar outros boards, em vez de derrubar todo o processo no preflight.

Alternativas rejeitadas:

- **Destino dentro da coluna removida:** a informação desaparece justamente no
  commit que aciona a migração.
- **Destino global fora do board:** permite referência cross-board e exige mais
  validação.
- **Fallback para primeira/próxima coluna:** não é destino explícito e pode
  classificar trabalho incorretamente.
- **Arquivo de journal com IDs:** duplica o estado remoto e amplia a superfície
  protegida da esteira.
- **Comentário/label por issue:** transforma proteção estrutural em regra por
  item e altera dados fora do escopo.

## Consequências

- Positivas: configuração legível, compatível e antecipável; repetição segura;
  nenhum arquivo de estado novo; métricas disponíveis nos logs; remoções vazias
  continuam simples.
- Negativas: mappings antigos podem permanecer sem efeito e precisam ser
  documentados; erros semânticos são observados durante o full sync, não todos
  no `check_config`; a tentativa depende de listagem remota integral.
- Riscos: operadores podem remover o mapping antes de uma origem ocupada
  concluir; nesse caso a próxima tentativa é bloqueada, mas nenhuma issue é
  alterada e a origem permanece ativa. Logs devem indicar a correção exata no
  `pipe.yml`.
