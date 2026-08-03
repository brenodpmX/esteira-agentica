# Arquitetura — Rodar no Docker

**Status:** implementada e homologada
**Owner:** architecture
**Última atualização:** 2026-08-03
**Versão homologada:** 1.6.0

## 1. Resultado entregue

A esteira é distribuída com `Dockerfile`, `docker-compose.yml`, `.env.example`,
`.dockerignore` e `prepare-docker.sh`. A homologação executou o fluxo completo:
preparação dos binários, build da imagem, startup, sincronização com GitHub
Projects e execução de um agente pelo Kiro CLI dentro do container.

A solução preserva a arquitetura da aplicação (`python -m src`) e externaliza
configuração, credenciais e estado. A única adaptação no runtime Python foi o
tratamento de `SIGTERM` para encerramento limpo no Docker (issue #70), sem
alterar regras de negócio.

## 2. Imagem implementada

A imagem usa `python:3.12-slim` e contém:

- Python 3.12 e o código em `src/`;
- `git`, cliente SSH, `curl`, `jq` e certificados;
- GitHub CLI 2.94.0, instalado em `/usr/local/bin/gh`;
- `kiro-cli` e `kiro-cli-chat`, copiados da instalação do host para
  `/usr/local/bin`;
- PyYAML; e
- `PYTHONUNBUFFERED=1`, para logs em tempo real.

O Kiro CLI não possui distribuição pública usada por este build. Por isso,
`prepare-docker.sh` resolve o caminho real do launcher no host, valida os dois
binários necessários e os copia para o contexto. O launcher executa
`kiro-cli-chat` como processo irmão; omiti-lo causa o erro corrigido na issue
#120. `kiro-cli-term` não é necessário.

Os binários ocupam cerca de 775 MB no contexto e levam a imagem final a
aproximadamente 1,7 GB. `.dockerignore` evita acrescentar repositórios clonados,
logs, estado, segredos e metadados Git ao contexto.

A implementação atual roda como `root` e é voltada a Linux `amd64`. Os
executáveis são instalados em `/usr/local/bin`, independentes de `$HOME`, para
permitir uma futura migração para usuário não-root.

## 3. Configuração e credenciais

| Item | Entrada | Destino/consumo |
|------|---------|-----------------|
| Configuração | bind `./pipe.yml:ro` | `/app/pipe.yml` |
| Contextos | bind `./contexts` | `/app/contexts` |
| SSH privada e pública | binds `SSH_KEY_FILE:ro` | `/root/.ssh/id_ed25519[.pub]` |
| GitHub | `GH_TOKEN` e bind opcional de `GH_CONFIG_DIR:ro` | `gh api` |
| Kiro | `KIRO_API_KEY` | modo headless do `kiro-cli chat` |

`KIRO_API_KEY` é o mecanismo oficial de autenticação headless e elimina login
interativo no container. A chave exige plano Kiro compatível e deve permanecer
em `.env` ou em um gerenciador de segredos, nunca na imagem ou no Git.

A esteira copia a chave SSH montada para sua área interna com permissões
adequadas. `GH_TOKEN` é a credencial principal do GitHub CLI; a configuração do
`gh` montada do host funciona como apoio operacional.

## 4. Estado e ciclo de vida

O Compose cria três volumes nomeados:

| Volume | Montagem | Finalidade |
|--------|----------|------------|
| `pipe_state` | `/app/.pipe` | snapshots, fila e sessões |
| `pipe_repos` | `/app/repo` | clones Git |
| `pipe_logs` | `/app/logs` | logs da esteira e agentes |

`docker compose down` preserva os volumes; `docker compose down -v` remove todo
o estado. O serviço usa `restart: unless-stopped` para retomar após crash ou
reboot do host.

Para shutdown, `init: true` executa o `tini` como PID 1 e repassa sinais. O
runtime registra handler de `SIGTERM`, interrompe inclusive o `sleep` ocioso e
encerra de forma limpa. Em conjunto com `PYTHONUNBUFFERED=1`, isso resolveu logs
retidos e encerramentos por `SIGKILL`/137 (issue #70).

## 5. Decisões consolidadas

- **ADR-01 — Kiro por API key:** `KIRO_API_KEY`, sem login ou cache SSO.
- **ADR-02 — GitHub por token:** `GH_TOKEN`, com configuração local do `gh`
  disponível como montagem auxiliar.
- **ADR-03 — SSH read-only:** chave fornecida pelo host e copiada internamente.
- **ADR-04 — Persistência padrão:** volumes nomeados para estado, clones e logs.
- **ADR-05 — Binários do Kiro fornecidos pelo host:** launcher e chat são
  obrigatórios no build; não há download público automatizado.
- **ADR-06 — Operação resiliente:** logs sem buffer, `tini`, handler de
  `SIGTERM` e `restart: unless-stopped`.

## 6. Validação e homologação

Em 2026-08-03 foram validados:

- build limpo da imagem;
- Python 3.12.13, git 2.47.3, gh 2.94.0, Kiro CLI 2.16.0 e import do PyYAML;
- `kiro-cli chat --help` e execução headless dentro do container;
- startup da esteira 1.6.0, sincronização dos boards e conclusão de uma execução
  real de agente; e
- suíte com 207 testes aprovados e 3 ignorados na etapa de pré-produção.

## 7. Limitações e débitos conhecidos

- O build depende de uma instalação Linux completa do Kiro CLI no host.
- A imagem é `amd64` e não há publicação em registry neste escopo.
- A imagem roda como `root`; usuário não-root permanece hardening futuro.
- A base Python, pacotes APT, PyYAML e binários do Kiro não estão integralmente
  fixados por digest/versão. O GitHub CLI está pinado em 2.94.0. Assim, a
  reprodutibilidade estrita de RNF-05 é parcial.
- Variáveis de ambiente são adequadas ao Compose local, mas instalações com
  maior exigência de segurança devem usar um mecanismo externo de secrets.

O procedimento operacional e a solução de problemas estão no
[`README.md`](../../../README.md#execução-via-docker-compose-recomendado-para-produção).
