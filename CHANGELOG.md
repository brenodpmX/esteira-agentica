# Changelog

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

## [Unreleased] - 2026-08-19

### Adicionado

- Proteção de instância única no ciclo de vida da esteira (US-05, story #142).
  `main()` adquire o `InstanceLock` **antes** de `startup()` — isto é, antes de
  qualquer alteração do estado persistido — e recusa a execução com *fail-fast*
  (`SystemExit(1)`) quando outra instância já detém o lock, registrando
  `instance_lock_refused` com o caminho do lock, o PID e o horário de início do
  detentor. A liberação fica em `finally` externo, cobrindo término normal,
  `SIGTERM`, `KeyboardInterrupt`, falhas de startup e exceções do loop. Fecha a
  lacuna C5 do incidente #97 (duas instâncias sobre o mesmo diretório de
  estado). Tasks #150 (primitiva `InstanceLock`/`LockHeldError`) e #151
  (integração, commit `570e699`).
- Suíte de testes de instância única de ciclo de vida completo (task #152):
  `tests/test_instance_lock_integration.py`,
  `tests/test_instance_lock_concurrent.py` e o helper de subprocesso
  `tests/_main_lock_holder_helper.py`, que exercitam concorrência real via
  processos separados, além dos testes da primitiva isolada já existentes em
  `tests/test_instance_lock.py`.

### Corrigido

- Preservação do modo do arquivo na restauração do `SnapshotGuard`
  (`src/core/snapshot.py`, task #149, PR #194): a verificação de integridade do
  snapshot na execução do agente não altera mais as permissões do arquivo
  restaurado.
- Reconciliação da defasagem `epic` → `main` (bug #196). As entregas das tasks
  #151, #152 e #149 estavam mergeadas apenas em `epic`; `main` — a branch que a
  esteira executa em produção — continha somente a primitiva do lock, sem
  nenhuma proteção efetiva. A promoção foi fast-forward, sem conflito, e
  carrega também o change file da story #140 (declaração de escopo, não
  trabalho novo). O item 5 do ADR
  [`doc/architecture/instance-lock/sequenciamento-epic-main.md`](doc/architecture/instance-lock/sequenciamento-epic-main.md)
  foi registrado como superado nesta entrega.
- Remoção automática de sub-issues propagadas pelo GitHub Projects V2 para
  boards do parent quando o item chega sem `Status`. O pós-hook consulta
  `projectItems`/`fieldValues` via GraphQL e remove por
  `deleteProjectV2Item`; o project de origem é sempre preservado e, se não
  puder ser resolvido, nenhuma remoção é feita.
- Proteção no `create-down` para não criar arquivos locais nem entradas
  duplicadas para itens sem coluna, exigindo prova de propagação: a issue já
  registrada em outro board configurado com coluna conhecida. `parent`
  isolado não autoriza descarte, e snapshots de boards fora do `pipe.yml` não
  servem como prova. A remoção precisa concluir antes de o evento ser
  consumido.
- Detecção de coluna remota vazia como divergência e reconciliação escrevendo a
  coluna conhecida de volta no board, inclusive quando o arquivo local já está
  na coluna correta.
- `create_issue` aplica fallback para a primeira coluna do project, com
  warning, quando a coluna solicitada não existe, em vez de deixar o `Status`
  vazio silenciosamente.
- Nova primitiva `remove_from_board` na porta de board, implementada no adapter
  GitHub com `deleteProjectV2Item`.

### Segurança e compatibilidade

- Itens multi-board com `Status` definido são preservados; a remoção automática
  se restringe a itens de outros projects propagados sem coluna.
- Issues realmente novas, sem prova de presença em outro board configurado,
  usam a primeira coluna local como fallback, inclusive quando possuem
  `parent`.
- Não há mudança de schema nem de `pipe.yml`.
- Resíduos materializados antes desta correção não são apagados automaticamente
  e requerem limpeza manual com a esteira parada.

### Validação e disponibilidade

- Suíte canônica em `tests/test_sub_issue_propagation_fix.py`, exercitando o
  adapter e o core sem `monkeypatch` do método sob teste.
- Implementação final: issue #106, commit `a00ba7c`, no veículo #88/PR #102.
- Homologação aprovada em 19/08/2026. A disponibilidade em produção depende do
  merge do PR #102 e do deploy.

Detalhes: [`doc/changes/88-sub-issues-propagadas-entre-boards.md`](doc/changes/88-sub-issues-propagadas-entre-boards.md).
