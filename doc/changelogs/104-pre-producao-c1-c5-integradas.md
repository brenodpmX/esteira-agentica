# Change File — Post-Mortem de Produto #104 e resolução C1–C5

**Data:** 2026-08-20
**Issue:** #104 — Post-Mortem de Produto — Incidente reportado em 01/08/2026
**Branch:** `epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026`
**Versão:** 1.10.0
**Status:** homologado; pronto para merge/release

## Resumo

As cinco user stories filhas (#138–#142) foram concluídas/encerradas e suas
correções estão integradas em `main`. O aceite humano “pode avançar”, registrado
em 20/08/2026, satisfaz o gate de homologação do épico #104. O incidente #97
passa de “mitigado, com risco residual” para **resolvido**.

## Escopo entregue

- **C1 — Associação segura (US-03/#140):** `_find_issue_files` valida o
  `body_path`, busca pelo nome completo e só aceita exatamente um candidato
  não reivindicado; artefatos órfãos são registrados sem mutação externa
  (#146/#147).
- **C2 — Relações válidas (US-01/#138):** auto-referências em `parent`,
  `children`, `blocked_by` e `blocks` são sanitizadas antes de qualquer I/O;
  referências válidas de listas mistas são preservadas (#143).
- **C3 — Falha isolada (US-02/#139):** o core classifica erros, limita
  tentativas, rotaciona a fila e persiste dead-letter por item, eliminando
  head-of-line blocking (#144/#145).
- **C4 — Estado protegido (US-04/#141):** `SnapshotGuard` captura, compara e
  restaura atomicamente o snapshot, inclusive seu modo, após execução do
  agente (#149).
- **C5 — Instância única (US-05/#142):** `InstanceLock` usa `fcntl.flock` e é
  adquirido antes de `startup()`; a integração foi reconciliada em `main` por
  #196 (#150/#151/#152).

## Documentação atualizada

- versão em `src/core/version.py`: `1.9.1` → `1.10.0`;
- `CHANGELOG.md` com release 1.10.0;
- `README.md` com incidente resolvido e limites conhecidos;
- ticket, homologação e change file do incidente #97;
- post-mortem, visão, requisitos, arquitetura e stories do épico #104;
- `CONTEXT.md` com o estado pós-homologação.

## Validação da integração

Na segunda rodada de pré-produção:

- `git diff --check` não apontou problemas de whitespace;
- a branch não divergia de `main` em `src/`; as correções já estavam na branch
  executada em produção;
- `pytest tests/ -q`: 1121 aprovados, 28 ignorados, 1 xpassed e 24 falhas;
- as 24 falhas foram reproduzidas de forma idêntica em `origin/main`, portanto
  eram pré-existentes e não introduzidas por #104;
- os arquivos Compose foram parseados com sucesso;
- suíte estrutural Docker: 213 aprovados e as mesmas falhas preexistentes de
  verificação de `KIRO_CLI_SHA256`.

### Limitação aceita

O sandbox da rodada final não tinha Docker; por isso, build, `up` e smoke test
reais não foram repetidos após a integração de C1–C5. A limitação foi
explicitada antes do gate e o humano autorizou o avanço em 20/08/2026. A
primeira rodada, ainda documental, havia executado build e smoke test com
sucesso, mas não é apresentada como validação das correções finais.

## Compatibilidade

- bump MINOR, sem breaking change;
- sem migração obrigatória de schema ou `pipe.yml`;
- `sync.max_attempts` é opcional;
- Linux permanece requisito para `fcntl.flock` e para a imagem atual;
- lock distribuído, sandbox completo de filesystem, replay automático de
  dead-letter e auditoria parcial em timeout permanecem fora do escopo.

## Critério de encerramento

O cenário composto do incidente fica protegido em cinco limites: associação
inequívoca, sanitização de relações, isolamento da fila, restauração do
snapshot e exclusividade de processo. Com todas as stories encerradas e o gate
humano aprovado, os critérios negociais do épico #104 foram atendidos.

## Referências

- `doc/incidente/parent-recursivo/ticket.md`
- `doc/incidente/parent-recursivo/homologacao.md`
- `doc/product/confiabilidade-parent-recursivo/post-mortem.md`
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md`
- `doc/stories/confiabilidade-parent-recursivo/user-stories.md`

— Helena Costa - Product Manager
