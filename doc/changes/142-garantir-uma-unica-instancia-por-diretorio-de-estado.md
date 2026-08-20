# Change #142 — Garantir uma única instância por diretório de estado

- **Tipo:** feature / hardening de confiabilidade
- **Versão-alvo:** 1.9.0 (já presente em `main`)
- **Plataforma afetada:** todas (lock é local ao filesystem, independe de board provider)
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`; novo arquivo de
  estado interno `.pipe/pipe.lock`
- **Implementação:** commits `0edb67a` (task #150, PR #161), `545089a` (task
  #151, PR #162) e `de70f75` (task #152, PR #193), já em `main`
- **Story:** #142, épico #104 (post-mortem do incidente #97 — parte da C5)

## Problema

Sem exclusividade de instância, duas execuções da esteira sobre o mesmo
diretório de estado (`.pipe/`) podem correr concorrentemente — cada uma com
sua própria fila em memória e seu próprio ciclo de sync — causando
concorrência, perda de eventos da fila e corrupção da memória operacional
(`snapshot.json`, `changeQueue.json`, `sessions.json`). O épico #104
(post-mortem do incidente #97) previa essa proteção como task técnica C5.

## Mudanças implementadas

- **`InstanceLock`** (`src/core/lock.py`, task #150): primitiva isolada
  baseada em `fcntl.flock(LOCK_EX | LOCK_NB)` sobre `.pipe/pipe.lock`:
  - `acquire()` não bloqueante; em sucesso grava metadados (`pid`,
    `started_at`, `host`) como JSON no arquivo, com `flush()` + `fsync()`.
  - Em caso de disputa, levanta `LockHeldError` com os metadados do
    detentor atual (lidos best-effort do arquivo), produzindo mensagem com
    caminho, pid, horário de início e host — sem exigir edição de arquivos
    internos.
  - `release()` idempotente (chamar sem lock ativo não levanta erro); não
    remove o arquivo, apenas libera o lock do kernel.
  - Reaproveitamento de lock órfão (processo detentor morto sem cleanup, ex.
    `SIGKILL`) não exige código adicional: é propriedade do próprio `flock`
    do kernel — ao morrer o processo, o SO fecha os file descriptors e
    libera o lock automaticamente, mesmo com o arquivo intacto no disco.
  - Suporte a context manager (`__enter__`/`__exit__`) para uso em testes.
  - `.pipe/pipe.lock` adicionado a `PROTECTED_PATHS` (`src/core/agent.py`) e
    ao bloco de restrições do `.pipe/CONTEXT.md` gerado
    (`context_generator.py`) — o agente nunca deve ler/escrever esse arquivo.
- **Integração ao ciclo de vida de `main()`** (`src/__main__.py`, task #151):
  - Lock adquirido logo após `check_config()`, **antes** de `startup()` —
    a exclusividade existe antes de qualquer efeito persistido (clone de
    repositórios, geração de `CONTEXT.md`, limpeza da fila).
  - Em `LockHeldError`, loga erro estruturado (`event="instance_lock_refused"`
    com `lock_path`, `holder_pid`, `holder_started_at`, `holder_host`) e
    encerra com `SystemExit(1)` sem executar `startup()` nem tocar no estado
    da instância detentora.
  - Liberação em `finally` externo ao loop principal — cobre encerramento
    normal, `SIGTERM` (via `_Shutdown`), `KeyboardInterrupt` e qualquer
    exceção não tratada do loop, garantindo que um arquivo remanescente sem
    lock ativo do kernel permita nova inicialização segura.
- **Suíte de testes concorrentes** (tasks #150/#152):
  - `tests/test_instance_lock.py` — testes unitários da primitiva
    (aquisição, disputa, metadados do detentor, idempotência de `release`,
    reaproveitamento de lock órfão).
  - `tests/test_instance_lock_integration.py` + `tests/_lock_holder_helper.py`
    — testes com subprocessos reais: disputa simultânea sobre o mesmo
    diretório de estado, rajada de N instâncias (no máximo uma ativa),
    reinicialização legítima após encerramento/crash sem intervenção manual,
    e o cenário de regressão composta do incidente #97 aplicado à frente de
    instância única.

## Verificação de bloqueios (critério desta etapa)

- Tasks filhas da story (`/blocked_by #150, #151, #152` registrado no body
  pelo planejamento): #150, #151 e #152 estão todas **encerradas** e
  integradas em `main` (commits acima).
- Nenhuma duplicata da C5 encontrada nos boards `story`/`task`.
- Sem `/blocked_by` pendente no body da issue #142 no momento desta etapa.

## Validação

- `tests/test_instance_lock.py` + `tests/test_instance_lock_integration.py`:
  41 testes, todos aprovados nesta etapa.
- Suíte completa executada nesta etapa: `1090 passed, 28 skipped, 1 xfailed`.
  As 4 falhas observadas em `tests/test_epic_merge_ausente_146_147.py` são
  pré-existentes e não relacionadas a esta story — comparam commits de
  `origin/epic` contra `HEAD` para a regressão do incidente #146/#147
  (sincronização `epic`↔`main`), sem qualquer relação com `InstanceLock`.

## Fora de escopo (conforme a story)

Lock distribuído entre hosts sem filesystem compartilhado e coordenação entre
diretórios de estado distintos.
