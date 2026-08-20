# Change File — Incidente #97: Parent Recursivo

**Abertura:** 2026-08-01
**Resolução:** 2026-08-20
**Issue:** #97 — Erro reportado dia 01/08/26
**Versão da correção:** 1.10.0
**Status:** resolvido; C1–C5 integradas e homologadas

## Resumo

O incidente interrompeu o processamento útil de todos os boards por 2h37,
repetiu 225 vezes a mesma rejeição e substituiu temporariamente o conteúdo da
issue #76. O reparo operacional de 01/08 restaurou os dados, mas não eliminava
a causa sistêmica.

A entrega final da versão 1.10.0 conclui e homologa as cinco frentes
preventivas. Este arquivo substitui a comunicação histórica de “correções
pendentes”; o histórico completo permanece no ticket do incidente.

## Correções entregues

| Frente | Resultado | Rastreabilidade |
|---|---|---|
| C1 | resolução determinística do body; ambiguidade e órfãos não alteram issues | #140, #146, #147 |
| C2 | auto-referência removida de todas as relações antes do provider | #138, #143 |
| C3 | erro definitivo/tentativas esgotadas isolados em dead-letter, sem bloqueio global | #139, #144, #145 |
| C4 | `SnapshotGuard` restaura conteúdo e modo do snapshot após interferência | #141, #149 |
| C5 | `InstanceLock` recusa concorrência antes de qualquer mutação de startup | #142, #150–#152, #196 |

## Impacto da entrega

- **Continuidade:** um item inválido deixa de bloquear os demais itens e boards.
- **Integridade:** associação ambígua não escolhe arquivo arbitrário e a memória
  de snapshot é restaurada após a execução do agente.
- **Operação:** falhas isoladas preservam motivo, tentativas e próximo passo;
  inicialização concorrente é recusada com metadados acionáveis.
- **Compatibilidade:** sem breaking change ou migração obrigatória de
  `pipe.yml`; bump MINOR de 1.9.1 para 1.10.0.

## Validação

A segunda rodada de pré-produção registrou 1121 testes aprovados, 28 ignorados
e 1 xpassed. As 24 falhas também ocorriam em `origin/main`, portanto não foram
introduzidas pelo épico. A homologação humana autorizou o avanço em 20/08/2026.
A limitação de não haver Docker no sandbox final está registrada no change file
do épico e não foi ocultada.

## Limites conhecidos

- o lock exige filesystem compartilhado;
- a guarda desta versão cobre snapshots, não toda a memória interna;
- dead-letter não possui replay automático; e
- auditoria parcial de chat em timeout permanece melhoria independente.

## Referências

- `doc/incidente/parent-recursivo/ticket.md`
- `doc/incidente/parent-recursivo/homologacao.md`
- `doc/product/confiabilidade-parent-recursivo/post-mortem.md`
- `doc/changelogs/104-pre-producao-c1-c5-integradas.md`
