# Homologação final — Incidente Parent Recursivo

**Issue de incidente:** #97
**Épico de Produto:** #104
**Versão:** 1.10.0
**Status:** aprovado para avanço em 20/08/2026

## Resultado

A homologação conjunta das cinco frentes C1–C5 foi aprovada após a conclusão
das stories #138–#142 e sua integração em `main`. O incidente de 01/08/2026,
antes classificado como “mitigado, com risco residual”, passa a **resolvido**.

O roteiro anterior deste arquivo validava apenas a documentação da hotfix #97,
quando as correções ainda não existiam. Ele foi superado pela segunda rodada de
pré-produção do épico #104 e pelo aceite humano registrado em 20/08/2026.

## Escopo homologado

| Frente | Garantia homologada | Evidência principal |
|---|---|---|
| C1 | body associado somente por identidade inequívoca; órfãos são isolados | `src/core/sync.py`, `tests/test_regressao_colisao_76.py` |
| C2 | auto-referências são removidas antes de I/O | `src/core/commands.py`, `tests/test_sanitize_relations.py` |
| C3 | item falho não bloqueia a fila global e rejeições são isoladas | `src/core/sync.py`, `src/core/dead_letter.py`, testes de erro irrecuperável |
| C4 | alterações indevidas no snapshot são restauradas atomicamente | `src/core/snapshot.py`, testes de validação pós-agente |
| C5 | segunda instância é recusada antes de `startup()` | `src/core/lock.py`, testes concorrentes e de integração |

## Evidências da rodada final

- C1–C5 presentes em `main`, sem divergência de runtime entre a branch do épico
  e a branch executada em produção.
- Stories #138–#142 concluídas/encerradas.
- Segunda rodada de pré-produção: 1121 testes aprovados, 28 ignorados e 1
  xpassed. As 24 falhas observadas foram reproduzidas de forma idêntica em
  `origin/main` e classificadas como pré-existentes, fora do escopo de #104.
- Validação estrutural Docker: 213 testes aprovados; os arquivos Compose foram
  parseados com sucesso.
- O sandbox da segunda rodada não possuía Docker, portanto não repetiu build,
  `up` e smoke test reais. A limitação foi explicitada no change file e aceita
  no aceite humano “pode avançar”, em 20/08/2026.

## Critérios de encerramento

- nenhuma associação ambígua escolhe arbitrariamente um body;
- nenhuma auto-referência alcança o provider;
- uma mensagem-veneno não monopoliza os demais boards;
- interferência do agente no snapshot não persiste;
- somente uma instância opera sobre o mesmo estado; e
- logs e registros de isolamento preservam motivo e próximo passo.

## Limites conhecidos

O encerramento não transforma a solução em sandbox completo. Permanecem fora
do escopo desta versão: lock distribuído entre filesystems distintos, proteção
pós-agente de toda a memória interna além dos snapshots, replay automático de
dead-letter e preservação parcial do chat quando o agente excede timeout.

## Referências

- `doc/incidente/parent-recursivo/ticket.md`
- `doc/product/confiabilidade-parent-recursivo/post-mortem.md`
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md`
- `doc/changelogs/104-pre-producao-c1-c5-integradas.md`

— Helena Costa - Product Manager
