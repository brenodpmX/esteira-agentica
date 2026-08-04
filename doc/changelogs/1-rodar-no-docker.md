# Change File — Rodar no Docker

**Data:** 2026-08-03
**Issue:** #1 — Rodar no Docker
**Branch:** `epic1-1-rodar_no_docker`
**Versão:** 1.6.0
**Status:** homologado

## Resumo

A Esteira Agêntica passa a ter uma distribuição Docker Compose operacional para
execução contínua e headless. Configuração, credenciais e estado ficam fora da
imagem, e a homologação confirmou sincronização com GitHub Projects e execução
real de um agente dentro do container.

## Alterações entregues

### Empacotamento

- `Dockerfile` baseado em `python:3.12-slim`, com git, SSH, GitHub CLI 2.94.0,
  PyYAML e código da esteira.
- `prepare-docker.sh` localiza a instalação real do Kiro CLI e copia os dois
  executáveis necessários: `kiro-cli` e `kiro-cli-chat`.
- `.dockerignore` exclui estado, clones, logs, segredos e metadados Git do
  contexto de build.
- Binários locais e `.env` permanecem ignorados pelo Git.

### Configuração e autenticação

- `docker-compose.yml` monta `pipe.yml`, contextos, chave SSH e configuração
  opcional do `gh`.
- `GH_TOKEN` autentica o GitHub CLI sem interação.
- `KIRO_API_KEY` autentica o Kiro CLI em modo headless.
- `.env.example` documenta tokens e caminhos configuráveis.

### Persistência e operação

- Volumes nomeados preservam `.pipe/`, clones em `repo/` e logs.
- `restart: unless-stopped` mantém o serviço após crash ou reboot.
- `PYTHONUNBUFFERED=1` publica logs em tempo real.
- `init: true` e o handler de `SIGTERM` encerram o loop de forma limpa em
  `docker compose stop/down` (issue #70).

### Correção pós-homologação

A issue #120 revelou que `kiro-cli` é apenas o launcher do subcomando de chat.
O build anterior copiava somente esse arquivo e falhava com
`No such file or directory (os error 2)`. A correção passou a validar, copiar e
instalar também `kiro-cli-chat`. O smoke test `kiro-cli chat --help` foi
executado com sucesso dentro da imagem.

### Documentação

- README ampliado com pré-requisitos, configuração, build, execução, smoke
  test, rotação de API key, volumes e troubleshooting.
- Documentos de produto, requisitos, arquitetura e stories atualizados para o
  estado entregue e homologado.
- Arquitetura pública alinhada aos artefatos reais, incluindo limitações e
  débitos residuais.

## Compatibilidade e limitações

- Build atual para Linux `amd64`.
- Exige Docker Compose V2 e instalação completa do Kiro CLI no host do build.
- Imagem aproximada de 1,7 GB devido aos binários nativos do Kiro.
- Execução atual como `root`.
- Pinagem integral de base, APT, PyYAML e Kiro permanece como débito de
  reprodutibilidade; o GitHub CLI está pinado em 2.94.0.

## Validação

- Build Docker concluído sem erros.
- Python 3.12.13, git 2.47.3, gh 2.94.0, Kiro CLI 2.16.0 e PyYAML verificados na
  imagem de pré-produção.
- `kiro-cli chat --help` executado dentro do container.
- 207 testes aprovados e 3 ignorados na pré-produção.
- Homologação funcional em 03/08/2026: startup da versão 1.6.0, acesso ao
  GitHub, sincronização dos boards, seleção de tarefa e execução concluída do
  agente.
