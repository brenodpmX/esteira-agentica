# ADR — Sequenciamento `epic` → `main` para InstanceLock

- **Status:** aceito
- **Data:** 2026-08-05
- **Issues:** #150, #151 e #163
- **PRs relacionados:** #161 e #162

## Contexto

A issue #150 implementa `InstanceLock`/`LockHeldError`, e a #151 integra essa
primitiva ao início e ao encerramento de `main()`. O flow de desenvolvimento
vigente cria e integra branches `feature` em `epic`; por isso #150 já foi
incorporada a `epic` pelo PR #161 e o PR #162 de #151 também aponta para
`epic`.

Isso não torna a funcionalidade disponível em produção: a execução publicada
parte de `main`. Em 2026-08-05, `main` e `epic` possuíam, respectivamente, 27
e 121 commits exclusivos desde o merge-base. O delta `main..epic` abrangia 81
arquivos (18.927 inserções e 2.522 remoções). Uma simulação de merge encontrou
conflitos em `.dockerignore`, `Dockerfile`, `docker-compose.yml`,
`prepare-docker.sh`, `src/__main__.py`, `src/core/sync.py` e
`tests/test_sigterm_shutdown.py`.

Portanto, usar `epic` → `main` como veículo apenas para InstanceLock acoplaria
a correção a uma promoção ampla, introduziria mudanças não relacionadas e
exigiria resolver conflitos sem um escopo de release aprovado.

Há ainda um cuidado específico na #151: seu commit funcional altera um bloco
amplo de `src/__main__.py`. O estado atual da branch remove, entre outras
mudanças, a descoberta local global (`detect_local_all`) já presente em
`epic`/`main`. Esse delta não relacionado não pode entrar no backport.

## Decisão

**InstanceLock será promovido a `main` por backport controlado, na ordem
#150 → #151. Não será feito merge direto de `epic` em `main` como parte desse
trabalho.**

A integração geral de `epic` em `main` continua sendo um evento de release
separado, com escopo, janela, validação e responsável próprios. Esta decisão
não autoriza nem impede essa promoção futura.

O PR #162 continua sendo a integração da #151 no fluxo de desenvolvimento
`feature` → `epic`, mas seu merge isolado **não** satisfaz o critério de
conclusão da #151 em produção. A #151 só estará entregue quando o backport
correspondente for integrado em `main`.

## Sequência obrigatória

1. **Consolidar #150 em `epic`.** Concluído pelo PR #161. A primitiva e seus
   testes constituem a primeira unidade lógica da promoção.
2. **Corrigir e integrar #151 em `epic`.** Antes do merge do PR #162, reduzir o
   delta ao ciclo de vida do lock e preservar integralmente o comportamento
   vigente do loop principal, em especial `detect_local_all`,
   `sync_remote_board`, processamento da fila, rotação de boards e shutdown.
3. **Criar uma branch de promoção a partir do `origin/main` atualizado.** A
   branch deve ser exclusiva para #150/#151; ela não deve nascer de `epic` nem
   conter merge de `epic`.
4. **Aplicar primeiro a unidade da #150.** Reaplicar os commits da primitiva
   (`bc2e6b6`, depois `ba93fe9`) ou um patch semanticamente equivalente,
   resolvendo diferenças contra `main` sem importar mudanças alheias.
5. **Aplicar depois a integração da #151.** Implementar o delta mínimo sobre o
   `main` resultante do passo anterior. Não fazer cherry-pick cego de
   `46948aa`: o commit envolve lógica de sincronização fora do escopo. Os
   testes de #151 podem ser reaproveitados, desde que adaptados ao contrato
   atual de `main`.
6. **Validar a árvore de promoção.** Executar, no mínimo, os testes unitários
   de `InstanceLock`, os testes de integração com `main()`, os testes de
   SIGTERM/startup e a suíte completa. Confirmar também que uma segunda
   instância falha antes de qualquer mutação de estado e que o lock é liberado
   em todas as saídas da primeira instância.
7. **Abrir e integrar PR da branch de promoção para `main`.** O PR deve
   referenciar #150, #151, #161, #162 e este ADR. O merge desse PR é o gate de
   entrega em produção da #151.

## Regras de integridade do backport

- A aquisição ocorre após validação de configuração e antes de `startup()` ou
  de qualquer operação que possa alterar estado persistido.
- `LockHeldError` causa recusa fail-fast com saída não zero e metadados
  observáveis do detentor; não inicia adapters, sync ou agentes.
- A liberação fica em `finally` externo e cobre término normal, SIGTERM,
  `KeyboardInterrupt`, falhas de startup e exceções do loop.
- O backport não pode remover ou substituir comportamentos de sincronização,
  proteção de estado, preflight, logging ou shutdown já existentes em `main`.
- Qualquer diferença além de `InstanceLock`, sua integração e testes exige
  justificativa explícita no PR ou deve ser retirada da branch.

## Consequências

### Positivas

- Entrega #150/#151 em `main` sem transportar 121 commits exclusivos de
  `epic` nem resolver conflitos de uma release ampla dentro de uma correção.
- Torna explícito o gate real de conclusão da #151.
- Preserva a rastreabilidade e a ordem de dependência entre primitiva e
  integração.

### Custos e riscos

- Haverá duas integrações da mesma capacidade (`epic` e `main`) e possível
  resolução de diferenças durante uma promoção futura de `epic`.
- O backport precisa de revisão e testes próprios; os resultados do PR #162
  não são evidência suficiente para `main`.

Esses custos são aceitos porque têm escopo limitado e reversível por PR,
enquanto o merge direto de `epic` mistura a entrega com uma decisão de release
muito mais ampla.
