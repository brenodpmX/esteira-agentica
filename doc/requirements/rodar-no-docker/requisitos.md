# Requisitos — Rodar no Docker

**Status:** implementados e homologados, com débitos residuais aceitos
**Owner:** requirements
**Última atualização:** 2026-08-03
**Versão:** 1.6.0

## Contexto

Antes desta feature, a execução dependia de um host preparado manualmente com
Python, dependências, GitHub CLI e Kiro CLI. A entrega passou a empacotar o
runtime da esteira e a declarar configuração, credenciais e persistência em
Docker Compose.

O build ainda precisa de uma instalação completa do Kiro CLI no host, porque
não há distribuição pública utilizada pela imagem. `prepare-docker.sh` copia
`kiro-cli` e `kiro-cli-chat`; depois do build, o runtime depende apenas da
imagem, das configurações e das credenciais montadas.

## Requisitos funcionais e aceite

| ID | Requisito | Resultado homologado | Status |
|----|-----------|-----------------------|--------|
| RF-01 | Imagem com dependências de runtime | `python:3.12-slim`, código, PyYAML, git, SSH, gh, `kiro-cli` e `kiro-cli-chat` na imagem | Atendido |
| RF-02 | Chave SSH externa | chave privada e `.pub` montadas read-only; `PIPE_SSH_KEY_FILE` aponta para o caminho interno | Atendido |
| RF-03 | GitHub CLI headless | `GH_TOKEN` injetado pelo Compose; configuração local do `gh` pode ser montada como apoio | Atendido |
| RF-04 | Kiro CLI headless | `KIRO_API_KEY` por ambiente e execução não interativa dentro do container | Atendido |
| RF-05 | Configuração via Compose | `pipe.yml`, `contexts/`, credenciais e caminhos declarados sem rebuild | Atendido |
| RF-06 | Persistência | volumes nomeados para `.pipe/`, `repo/` e `logs/`, preservados em `down/up` | Atendido |
| RF-07 | Operação autônoma | loop sem stdin, restart automático, logs em tempo real e shutdown limpo por SIGTERM | Atendido com ressalva |
| RF-08 | Guia operacional | instalação, configuração, build, execução, verificação, rotação, parada e troubleshooting no README | Atendido |

### RF-01 — Imagem executável

O runtime inicia com `python -m src` e não instala dependências durante o
startup. Para construir localmente, o host deve fornecer os dois binários do
Kiro CLI por meio de `prepare-docker.sh`. Essa restrição é pública e validada
antes de qualquer cópia.

### RF-02 a RF-04 — Autenticação sem interação

- **SSH:** `SSH_KEY_FILE` define a chave do host; os arquivos são montados em
  `/root/.ssh/` como read-only e copiados internamente pela aplicação.
- **GitHub:** `GH_TOKEN` é consumido nativamente pelo `gh` e deve ter escopos
  `repo` e `project`.
- **Kiro:** `KIRO_API_KEY` usa o modo headless oficial. Não há login por browser
  nem montagem de cache SSO.

A homologação executou um agente real no container, cobrindo a autenticação e o
binário `kiro-cli-chat` que havia causado o bug #120.

### RF-05 — Configuração sem rebuild

O Compose monta `pipe.yml` read-only e `contexts/` em runtime. `.env` fornece os
segredos e caminhos do host. Alterações nesses itens não exigem reconstrução da
imagem; mudanças nos binários do Kiro exigem nova preparação e build.

### RF-06 — Estado persistente

Os volumes `pipe_state`, `pipe_repos` e `pipe_logs` são criados por padrão.
`docker compose down` os preserva e `docker compose down -v` os remove. A
operação efêmera não é o padrão do arquivo entregue, mas pode ser obtida por um
override de Compose que substitua/remova os volumes.

### RF-07 — Autonomia e falhas

O processo não lê `stdin`; o agente usa modo não interativo. O serviço combina
`restart: unless-stopped`, `init: true`, `PYTHONUNBUFFERED=1` e handler de
`SIGTERM`. Assim, logs chegam imediatamente e `stop/down` encerram o loop sem
esperar `SIGKILL`.

Configuração local inválida (`pipe.yml`, SSH ou contextos) falha no startup com
mensagem explícita. Credenciais externas inválidas podem ser detectadas apenas
na primeira operação do GitHub/Kiro, e não em um preflight único; o erro fica
visível nos logs. Essa é a ressalva aceita para RF-07.

### RF-08 — Documentação

O `README.md` cobre:

1. Docker Compose V2 e demais pré-requisitos;
2. preparação dos dois binários do Kiro;
3. `.env`, `pipe.yml` e contextos;
4. build e execução foreground/background;
5. sinais esperados de startup e smoke test do agente;
6. persistência, parada, limpeza e rotação de API key; e
7. solução de problemas, inclusive o erro da issue #120.

## Requisitos não funcionais

| ID | Requisito | Situação final |
|----|-----------|----------------|
| RNF-01 | Segredos fora da imagem | Atendido: `.env` ignorado, tokens por ambiente e SSH por bind read-only |
| RNF-02 | Base oficial e dependências mínimas | Parcial: base slim e pacotes necessários; Kiro eleva a imagem para ~1,7 GB |
| RNF-03 | Docker Compose V2 | Atendido e validado com `docker compose` |
| RNF-04 | Não alterar regras de negócio | Atendido; a mudança Python limita-se ao ciclo de vida por SIGTERM |
| RNF-05 | Build integralmente reprodutível | Parcial: gh 2.94.0 pinado; base, APT, PyYAML e Kiro não estão todos fixados por versão/digest |

Os itens parciais não impediram a homologação funcional, mas permanecem como
débitos explícitos de hardening e reprodutibilidade.

## Dependências e riscos — encerramento

| ID | Item | Resultado |
|----|------|-----------|
| D-01 | Autenticação headless do Kiro | Resolvida por `KIRO_API_KEY` |
| D-02 | Distribuição do Kiro CLI | Resolvida operacionalmente copiando launcher + chat do host; há risco de drift de versão |
| D-03 | GitHub CLI por token | Confirmada com `GH_TOKEN` |
| D-04 | Persistência | Definida com três volumes nomeados por padrão |

Riscos residuais: build restrito a Linux `amd64`, execução como `root`, tamanho
da imagem, dependência da instalação do Kiro no host e pinagem incompleta.

## Fora de escopo

- publicação da imagem em registry;
- Kubernetes ou outros orquestradores;
- remoção dos gates `need_human`;
- CI/CD de build e push da imagem;
- suporte multi-arquitetura; e
- gestão corporativa de secrets.

## Evidência de conclusão

Em 03/08/2026, a homologação iniciou a Esteira Agêntica 1.6.0 no container,
validou o `pipe.yml`, acessou o GitHub, sincronizou os boards, selecionou uma
issue e concluiu a execução de um agente. Na pré-produção, o build e o smoke
test do Kiro foram aprovados e a suíte registrou 207 testes aprovados e 3
ignorados.
