# Épicos — Rodar no Docker

Status: entregues e homologados
Owner: product
Last updated: 2026-08-03

## Resultado final

Os três recortes foram entregues: imagem containerizada, configuração/segredos
por fora e operação autônoma do runtime. O Compose inclui persistência, restart
automático, logs em tempo real e shutdown limpo. O Kiro autentica por
`KIRO_API_KEY`; seus binários `kiro-cli` e `kiro-cli-chat` são copiados da
instalação do host durante a preparação do build.

## Inputs
- Issue #1 "Rodar no Docker"
- doc/product/rodar-no-docker/vision.md
- doc/product/rodar-no-docker/problem-space.md

## Épico: Imagem containerizada da esteira

**Objetivo:** ter uma imagem que contenha a esteira e todas as suas
dependências de runtime (Python 3.12+, Git, GitHub CLI, kiro-cli), pronta para
executar `python -m src` sem preparação manual do host.
**Escopo:**
- Empacotamento da aplicação e dependências numa imagem.
- Execução do loop principal dentro do container.
**Fora de escopo:**
- Alteração da lógica de negócio da esteira.
- Publicação da imagem em registries (definido em etapas posteriores, se
  necessário).

## Épico: Configuração e segredos por fora (docker-compose)

**Objetivo:** permitir que toda configuração e todo segredo sejam informados
via `docker-compose`, sem nada sensível fixo na imagem.
**Escopo:**
- `pipe.yml`, `contexts/`, chave SSH, credencial do GitHub e autenticação do
  agente injetáveis via ambiente/volumes declarados no compose.
- Persistência do estado de runtime (`.pipe/`, `logs/`, `repo/`) conforme
  necessidade do usuário.
**Fora de escopo:**
- Escolha da tecnologia de gestão de segredos (decisão de arquitetura).
- Autenticação headless do `kiro-cli` definida por `KIRO_API_KEY`; detalhes e
  pré-requisitos estão na arquitetura e no guia operacional.

## Épico: Operação autônoma sem humano

**Objetivo:** garantir que, uma vez configurado, o ciclo completo rode sem
intervenção humana durante a execução.
**Escopo:**
- Execução do loop sem prompts interativos.
- Comportamento previsível em falhas de credencial/setup (falha clara no
  arranque, não travamento silencioso).
**Fora de escopo:**
- Colunas do fluxo que, por design, exigem intervenção humana
  (`need_human`: aprovação de negócio, validações, homologação). Essas
  continuam sendo pontos de espera humana — "sem humano" refere-se à operação
  do runtime, não à eliminação dos gates de aprovação do fluxo.

**Mecanismo de espera humana (confirmado):** a intervenção humana nesses gates
não exige acesso à máquina/container. O humano atua diretamente no board do
GitHub (move o card no site); no ciclo seguinte a esteira sincroniza a issue
localmente e retoma o trabalho automaticamente. O container permanece rodando o
loop ininterruptamente enquanto aguarda.

## Épico: Documentação de operação

**Objetivo:** documentação simples e completa do que é necessário para colocar
a esteira para rodar em Docker.
**Escopo:**
- Pré-requisitos, variáveis/segredos necessários, passo a passo de subida,
  verificação de que está rodando.
**Fora de escopo:**
- Documentação interna de arquitetura da solução Docker (pertence às etapas
  técnicas).
