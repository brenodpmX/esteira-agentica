# Changelog #181 — Restauração das mudanças perdidas no merge `c27f813`

- **Versão:** 1.9.0 (bump MINOR de `1.8.3`)
- **Tipo:** correção de regressão por perda de código em merge
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`
- **Branch:** `fix/restaurar-mudancas-perdidas-merge-c27f813`

## Como o problema foi descoberto

O banner do terminal voltou ao modelo anterior. Esse sintoma cosmético levou à
investigação que revelou quatro perdas funcionais no mesmo merge — três delas
silenciosas, sem nenhum sinal em log ou na saída do programa.

## Causa raiz

O merge `c27f813` ("Merge: integrar epic em main", 12/08/2026) integrou dois
lados legítimos:

- **Parent 1 — `45c8b14`** (`main`): commits manuais com `rerun_cooldown`,
  banner da locomotiva, descoberta local global, correção do `create-up` de slug
  em underscore e refactor dos logs de agente.
- **Parent 2 — `87037f9`** (`epic`): refatoração ampla — `SnapshotGuard`,
  `AgentGuard`, `preflight`, `migrate_agent_level_labels`, `agent_level` por
  label, criação atômica de branch.

A `merge-base` era `26d863e`, muito anterior aos commits manuais de `main`. Na
resolução dos conflitos, o lado `epic` foi adotado por inteiro nos arquivos em
disputa, sem reconciliar o que era exclusivo de `main`.

O que tornou a perda difícil de perceber: os commits de `main` continuaram
**ancestrais** de `main`. `git log` os listava e `git merge-base --is-ancestor`
confirmava a ancestralidade — mas a árvore do merge havia revertido o conteúdo.

## Mudanças

### `boards.rerun_cooldown` voltou a funcionar

Origem: `28fea7e`. Arquivo: `src/__main__.py`.

A validação em `src/core/config.py` sobreviveu ao merge; o comportamento não.
`pipe.yml` aceitava `boards.rerun_cooldown` sem erro e a chave não surtia efeito
— uma issue que falha era reentregue ao agente a cada ciclo, queimando quota do
modelo sem progresso.

Restaurados `_rerun_cache`, `_cooldown_seconds`, `_in_rerun_cooldown`,
`_mark_rerun`, `_purge_expired_rerun` e os pontos de chamada em `keep_task`
(purga no início, skip e marcação na seleção).

A chave do cache é `(board_id, col_id, issue_id)` — inclui a coluna de
propósito: se a issue avança no board, é trabalho novo e fica elegível
imediatamente, sem esperar o cooldown.

### `create-up` de body com slug em underscore

Origem: `6176819`. Arquivo: `src/core/sync.py`.

O merge reintroduziu a heurística `elif body_file.name.count("-") >= 2` em
`detect_local_changes`. Como `_slugify` converte hífens e espaços em underscore
(`re.sub(r"[-\s]+", "_", text)`), **todo** arquivo nomeado pelo próprio sistema
tem exatamente um hífen — o do sufixo `-body`. A condição descartava esses nomes
em silêncio: o `create-up` nunca era gerado e a issue criada localmente nunca
subia ao board.

Voltou a ser `else`: todo `*-body.md` sem prefixo numérico é issue local nova.
Verificado que convive com a detecção de órfãos adicionada pelo `epic`, que trata
o caso oposto (arquivos **com** prefixo numérico sem match confiável).

### Descoberta local global por ciclo

Origem: `d8d85d9`. Arquivo: `src/__main__.py`.

O merge voltou ao `sync_board` acoplado, que faz a detecção local apenas no board
da rotação priorizada. Efeitos colaterais de agente são cross-board: atuando em
um board, o agente pode criar artefatos em outro (ex.: uma issue bloqueante).
Preso à rotação, boards de baixa prioridade eram inanidos enquanto os de cima
tinham atividade.

Restaurados `detect_local_all` (todos os boards; barato, só varredura de
filesystem) e `sync_remote_board` (um board, por consumir API do provider e estar
sujeito a rate limit). `sync_board` permanece como wrapper de compatibilidade.

### Detecção da falha real do kiro-cli

Origem: `3a1196a`. Arquivo: `src/adapters/kiro_cli_agent.py`.

O adapter passou a logar sempre "execução concluída", inclusive quando o kiro-cli
falhava — porque erros de modelo/servidor voltam como texto no output com
exit-code 0.

Reconciliação dos dois lados:

- linha de **início**: mantém o formato do `epic`, mais informativo (`title`,
  `col_name`, path do log). É contrato de `tests/test_agent_log_descritivo.py`.
- linhas de **conclusão/erro**: recuperam `_detect_failure` e
  `_last_meaningful_line`, classificando sucesso × falha pelo conteúdo do output
  e extraindo a causa real em vez de exibir a última linha (tipicamente
  `Request ID: ...`, que escondia o motivo).

### Banner da locomotiva

Origem: `7ed7bf0` e `45c8b14`. Arquivo: `src/__main__.py`. Restaurado byte a
byte.

### `AgentParams` saneado

Arquivo: `src/core/agent.py`. Efeito colateral do próprio conflito: o merge
manteve campos dos dois lados, deixando `col_name` declarado duas vezes e
`issue_title` sem nenhum consumidor. Funcionava por acidente da semântica de
`__annotations__` em dataclass.

## Testes

**Restaurados** (deletados pelo merge):

- `tests/test_detect_local_all.py`
- `tests/test_create_up_underscore_slug.py`

**Novos:**

- `tests/test_rerun_cooldown.py` — 32 testes: skip por cooldown, elegibilidade
  imediata ao trocar de coluna/board/issue, purga de expirados, `cooldown <= 0`
  desabilitando, coerência com a validação de `config.py`.
- `tests/test_agent_failure_detection.py` — classificação sucesso × falha,
  extração da causa real, não-regressão do formato da linha de início.
- `tests/test_banner.py` — elementos do desenho, altura, impressão no arranque,
  não-regressão para o wordmark genérico.

**Corrigido:** `tests/test_sigterm_shutdown.py`.

O teste amarrava o stop do loop em `sync_board`. Quando o loop deixou de chamar
essa função, o monkeypatch parou de interceptar e `main()` passou a rodar
indefinidamente — o `except Exception` do loop dorme e continua, então a suíte
**travava** em vez de falhar. O stop passou a cobrir as três funções de
descoberta (`detect_local_all`, `sync_remote_board`, `sync_board`), preservando a
intenção original (#70) e tornando o teste robusto a refactor do loop.

## Verificação

Baseline antes das mudanças: `4 failed, 1015 passed, 10 skipped, 1 xfailed,
13 errors`. As falhas e erros são ambientais, não de código:

- `tests/test_docker_compose.py` (4): `docker compose config` exige o arquivo
  `.env`, que não é versionado.
- `tests/test_dockerfile.py` (13): testes de integração que exigem a imagem
  Docker construída.

## Nota operacional

`boards.rerun_cooldown` volta a ter efeito nesta versão. Se o `pipe.yml` em uso
já declara a chave, o comportamento muda: issues passam a respeitar o intervalo
mínimo de reexecução. Para manter o comportamento das versões 1.8.x, remova a
chave ou defina `0`.

## Lição para merges de branch longa

Commit ancestral não garante conteúdo presente. Após integrar uma branch com
`merge-base` antiga, verificar cada arquivo em conflito:

```bash
git diff <parent-main> <merge-commit> -- <arquivo>
```

e confirmar que nenhum hunk reverte trabalho exclusivo do lado `main`.
