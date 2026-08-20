# Change #142 — Garantir uma única instância por diretório de estado

- **Tipo:** feature / hardening de confiabilidade
- **Versão-alvo:** 1.9.0
- **Plataforma afetada:** todas (lock é local ao filesystem, independe de board provider)
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`; novo arquivo de
  estado interno `.pipe/pipe.lock`
- **Implementação:** commits `0edb67a` (task #150, PR #161), `570e699` (task
  #151, PR #162) e `de70f75` (task #152, PR #193)
- **Story:** #142, épico #104 (post-mortem do incidente #97 — parte da C5)

> **Retificação (2026-08-19, bug #196).** A versão original deste arquivo
> afirmava que as três tasks já estavam "em `main`" e citava `545089a` como
> commit da task #151. Ambas as afirmações eram incorretas:
>
> - `545089a` **não é ancestral de `main` nem de `epic`** (é um commit órfão da
>   branch original da task #151, substituído na integração). O commit real da
>   integração é `570e699`.
> - Apenas `0edb67a` (task #150, a primitiva `InstanceLock`) estava em `main`.
>   `570e699` (task #151, integração ao ciclo de vida) e `de70f75` (task #152,
>   testes concorrentes) existiam **somente em `epic`**. Nenhuma instância da
>   esteira executando a partir de `main` tinha proteção de lock.
>
> As duas tasks chegaram a `main` apenas pela reconciliação `epic` → `main`
> executada no bug **#196**. Antes dela, os critérios de aceite desta story não
> eram verificáveis em produção.

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
    com `lock_path`, `holder_pid` e `holder_started_at`) e encerra com
    `SystemExit(1)` sem executar `startup()` nem tocar no estado da instância
    detentora. O `host` do detentor é gravado nos metadados do arquivo de lock
    e aparece na mensagem de erro, mas não é emitido como campo estruturado
    próprio.
  - Liberação em `finally` externo ao loop principal — cobre encerramento
    normal, `SIGTERM` (via `_Shutdown`), `KeyboardInterrupt` e qualquer
    exceção não tratada do loop, garantindo que um arquivo remanescente sem
    lock ativo do kernel permita nova inicialização segura.
- **Suíte de testes concorrentes** (tasks #150/#152):
  - `tests/test_instance_lock.py` — 26 testes unitários da primitiva
    (aquisição, disputa, metadados do detentor, idempotência de `release`,
    reaproveitamento de lock órfão).
  - `tests/test_instance_lock_integration.py` (15 testes) +
    `tests/_lock_holder_helper.py` e `tests/_main_lock_holder_helper.py`
    — testes com subprocessos reais: disputa simultânea sobre o mesmo
    diretório de estado, rajada de N instâncias (no máximo uma ativa),
    reinicialização legítima após encerramento/crash sem intervenção manual,
    e o cenário de regressão composta do incidente #97 aplicado à frente de
    instância única.
  - `tests/test_instance_lock_concurrent.py` — 6 testes de concorrência do
    ciclo de vida completo de `main()` via processos separados.

## Verificação de bloqueios (critério desta etapa)

- Tasks filhas da story (`/blocked_by #150, #151, #152` registrado no body
  pelo planejamento): #150, #151 e #152 estão todas **encerradas** e
  integradas em `epic` (commits acima). **Retificação (#196):** apenas #150
  estava em `main`; #151 e #152 só chegaram a `main` pela reconciliação do bug
  #196.
- Nenhuma duplicata da C5 encontrada nos boards `story`/`task`.
- Sem `/blocked_by` pendente no body da issue #142 no momento desta etapa.

## Validação

Medições da etapa original, com a árvore em que foram feitas explicitada
(retificação #196 — o texto anterior não indicava a árvore, e
`test_instance_lock_integration.py` **não existia em `main`**):

- `tests/test_instance_lock.py` + `tests/test_instance_lock_integration.py`:
  41 testes aprovados, medidos na árvore da branch da story (equivalente a
  `epic`). Esse recorte **omitia** `tests/test_instance_lock_concurrent.py`
  (6 testes); o total real da frente de instância única é **47**.
- Suíte completa da etapa original: `1090 passed, 28 skipped, 1 xfailed`.

Medição após a reconciliação do bug #196 (branch
`hotfix196-196-integrar_instancelock_em_main_reconciliando_epic`):

- Suíte de lock completa (`test_instance_lock.py`,
  `test_instance_lock_integration.py`, `test_instance_lock_concurrent.py`):
  **47 passed**.
- `tests/test_epic_merge_ausente_146_147.py`: **21 passed, 0 failed**.
- Suíte completa: **1123 passed, 22 failed, 28 skipped, 1 xpassed**. As 22
  falhas são exatamente o mesmo conjunto medido em `origin/main` antes da
  correção (18 em `test_agent_log_descritivo.py`, 3 em `test_dockerfile.py`,
  1 em `test_agent_failure_detection.py`) — essas sim pré-existentes e não
  relacionadas a esta story.

**Retificação sobre as falhas de `tests/test_epic_merge_ausente_146_147.py`.**
O texto original classificava as 4 falhas desse arquivo como "pré-existentes e
não relacionadas a esta story". A classificação era incorreta: as 3 falhas de
`TestTC02SemDivergenciaDeCodigo` e a de `TestTC05CriteriosDeAceitePosMerge`
eram **causadas por código desta própria story ausente em `main`** — o teste
`test_nenhum_commit_de_epic_em_src_falta_em_head` nomeava explicitamente o
commit `570e699` ("Integrar InstanceLock ao ciclo de vida de main()"), que é a
task #151. O arquivo é o guard executável do elo `epic → main`, e estava
apontando precisamente a lacuna desta entrega. Após a reconciliação do #196 as
4 falhas desapareceram, sem qualquer alteração em `src/` ou `tests/`.

## Fora de escopo (conforme a story)

Lock distribuído entre hosts sem filesystem compartilhado e coordenação entre
diretórios de estado distintos.
