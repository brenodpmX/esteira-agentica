# Change #142 — Garantir uma única instância por diretório de estado

- **Tipo:** feature / hardening de confiabilidade
- **Plataforma afetada:** todas (lock é local ao filesystem, independe de board provider)
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`; novo arquivo de
  estado interno `.pipe/pipe.lock`
- **Story:** #142, épico #104 (post-mortem do incidente #97 — parte da C5)

## Resumo

Implementado lock de instância única (`InstanceLock`) por diretório de
estado, integrado ao ciclo de vida completo de `main()`, com cobertura de
testes unitários, de integração e concorrentes. A correção fecha a lacuna que
permitia duas instâncias operarem sobre o mesmo `.pipe`, causa raiz de parte
do incidente #97 (parent recursivo).

## Contexto da entrega (segunda passagem)

Na primeira passagem desta etapa, o merge para `epic` (PR #195) incluiu
apenas o change file — sem código, sem testes. O code review seguinte
reprovou a entrega e abriu o bug #196 (`/blocks #142`) por ausência da
integração de `InstanceLock` em `src/__main__.py` no destino real do merge.

O bug #196 foi corrigido via hotfix
(`hotfix196-196-integrar_instancelock_em_main_reconciliando_epic`, PR #197,
merge commit `fec6fe1`), reconciliando `main` com `origin/epic` e trazendo os
commits de integração e testes que já existiam em `epic`. Nesta passagem, a
branch da story foi remesclada com `main` (já contendo a correção) antes de
redigir este change file, e a implementação foi conferida diretamente no
repositório — não apenas no histórico da issue.

## Verificação de código realizada

- `src/core/lock.py` — `InstanceLock`/`LockHeldError`: `fcntl.flock`
  exclusivo não bloqueante, metadados do detentor (pid, host, horário de
  início) e reaproveitamento seguro de lock órfão após crash (via
  propriedade do kernel de liberar o `flock` no encerramento do processo
  detentor).
- `src/__main__.py`:
  - Lock adquirido em `main()` **antes** de `startup()`, portanto antes de
    qualquer alteração persistida do estado (ex.: remoção da fila).
  - `LockHeldError` tratado com log estruturado
    (`event="instance_lock_refused"`, `lock_path`, `holder_pid`,
    `holder_started_at`) e `SystemExit(1)` — recusa fail-fast sem tocar no
    estado da instância detentora.
  - `lock.release()` em `finally` externo ao loop principal, cobrindo
    encerramento normal, `SIGTERM`, `KeyboardInterrupt` e qualquer exceção
    não tratada que escape do loop.
- `.pipe/pipe.lock` presente em `PROTECTED_PATHS` (`src/core/agent.py`) e no
  bloco de restrições do `.pipe/CONTEXT.md` gerado.
- Confirmado via `git merge-base --is-ancestor`: o commit `570e699`
  (integração ao ciclo de vida de `main()`) é ancestral de `origin/main`
  após o hotfix #197 — ausente na primeira passagem, presente agora.

## Testes executados

- `tests/test_instance_lock.py` + `tests/test_instance_lock_concurrent.py` +
  `tests/test_instance_lock_integration.py`: **47 testes, todos aprovados**.
- `tests/test_epic_merge_ausente_146_147.py` (guard de regressão do padrão
  "merge `epic → main` incompleto", débito #165): **21 testes, todos
  aprovados** — na passagem anterior, 4 falhavam nomeando exatamente o
  commit `570e699` como ausente; a falha não existe mais.
- Suíte completa: `1123 passed, 28 skipped, 1 xpassed, 22 failed`. As 22
  falhas são em `tests/test_agent_log_descritivo.py` e
  `tests/test_dockerfile.py` — features não relacionadas (formato de log
  descritivo do agente e verificação de SHA-256 do Dockerfile), introduzidas
  pelo commit `a7bb76c`, sem relação com `InstanceLock` ou com esta story.

## Critérios de aceite — cobertura

- Exclusividade adquirida antes de qualquer alteração persistida, mantida
  durante startup, loop e encerramento: **atendido**.
- Segunda instância recusada sem executar startup nem alterar o estado da
  primeira: **atendido**.
- Recusa informa caminho e dados do detentor, sem exigir edição de arquivos
  internos: **atendido**.
- Encerramento/sinal/crash liberam a posse; lock remanescente sem posse ativa
  permite nova inicialização: **atendido**.
- Verificação O(1), sem varredura do diretório de estado: **atendido**
  (`flock` é uma chamada de sistema O(1)).
- Testes concorrentes comprovam no máximo uma instância ativa e
  reinicialização legítima sem intervenção manual: **atendido**.

## Bloqueios da story #142

As 3 tasks filhas estão encerradas e integradas em `main`: #150 (LockGuard),
#151 (integração ao ciclo de vida), #152 (suíte concorrente). O bug #196
também está encerrado após o hotfix #197. Sem `/blocked_by` pendente no body
de #142.

## Épico #104 — bloqueios verificados, NÃO avançado

O body do épico #104 declara `/blocked_by #141, #149, #139`. Status apurado
nesta etapa:

- **#149** — concluída (board `task`, coluna `concluido`).
- **#139** — "Isolar falhas sem bloquear os demais trabalhos" — ainda em
  `story/planejamento-tecnico`.
- **#141** — "Restaurar alterações indevidas no snapshot após execução do
  agente" — ainda em `story/change-file`.

Como #139 e #141 continuam em andamento, o épico #104 não teve todos os seus
bloqueios resolvidos. Nenhuma ação foi tomada sobre a issue #104 nesta etapa.

— Isabela Gomes - Tech Lead
