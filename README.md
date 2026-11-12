# Esteira Agêntica

A Esteira Agêntica orquestra agentes de IA sobre um board de issues do GitHub
Projects. Cada coluna do board vira uma etapa de trabalho: quando uma issue
chega numa coluna com agente, a esteira monta o objetivo da etapa, aciona o
agente no repositório do projeto e sincroniza o resultado de volta ao board
(comentários, labels, coluna, branch e pull request). Você descreve o fluxo
num único arquivo, o `pipe.yml`, e acompanha tudo pelo próprio board.

## O que a esteira faz

- Mantém o board e uma cópia local das issues sincronizados nos dois sentidos:
  o que muda no board chega ao agente, e o que o agente escreve sobe ao board.
- Aciona, por coluna, o agente configurado para a etapa, com o objetivo da
  etapa e as transições possíveis (ex.: avançar ou devolver a issue).
- Cria branch, faz merge ou abre pull request conforme a etapa pede.
- Escolhe o agente pela label `agent-hub-<valor>` da issue, para separar
  trabalho simples de trabalho complexo.
- Aplica relações e atributos escritos no corpo da issue (mãe/filha, bloqueios,
  labels, pedido de ajuda humana).
- Pede intervenção humana com a label `need_human` e pausa a issue até alguém
  retirá-la.
- Oferece controles opcionais de segurança: tempo máximo por execução, teto de
  reexecuções da mesma issue e limite de consumo de IA por período.
- Grava um registro de cada execução de agente, consultável depois.
- Roda em máquina local (Python) ou em container (Docker Compose).

## Limites

- O único board suportado é o GitHub Projects (V2), com issues do GitHub.
- A única plataforma de agente suportada é o `kiro-cli`.
- Uma instância da esteira por diretório de estado: uma segunda instância
  sobre o mesmo diretório é recusada na inicialização.
- O agente trabalha com as credenciais da esteira no repositório clonado. A
  esteira protege o próprio estado interno, mas não é um sandbox completo:
  revise o que os agentes entregam antes de ir para produção.
- O limite de consumo impede a próxima execução; uma execução já iniciada
  nunca é interrompida.
- Arquivos anexados às issues são baixados do board para a cópia local; o
  caminho inverso (agente anexar arquivo no board) não existe.
- A imagem de container é construída apenas para Linux `amd64`.

## Pré-requisitos

- Python 3.12 ou superior.
- Git.
- GitHub CLI (`gh`) autenticado (`gh auth login`) com os escopos `repo` e
  `project`.
- `kiro-cli` instalado, no `PATH` e autenticado.
- Chave SSH cadastrada no GitHub, com acesso ao repositório do projeto.
- Um repositório no GitHub com permissão de escrita para a sua conta. Para a
  primeira execução, use um repositório criado só para teste.

## Configuração

A esteira lê o `pipe.yml` da raiz da instalação (o arquivo não é versionado).
O exemplo abaixo é a menor configuração válida: um board com três colunas e um
agente que comenta a issue e a leva para o fim, sem mexer em branches.

```yaml
sleep: 60

project:
  name: Meu projeto
  summary: Primeira avaliação da Esteira Agêntica.

git:
  repo:
    main: git@github.com:minha-org/meu-repo.git
  flow:
    base: main
    feature:
      prefix: feature/
      branch_pattern: feature/{id}-{slug}

agents:
  kiro-cli:
    dev:
      name: Assistente
      model: claude-sonnet-5

boards:
  platform: github
  entrega:
    name: Entrega
    columns:
      entrada:
        name: Entrada
      execucao:
        name: Execução
        agent: dev
        gitevents: no-branch
        target-prompt: Resuma a issue num comentário e avance-a.
        change:
          advance: final
      final:
        name: Final
        archive: true
```

Cada agente precisa de um contexto em `contexts/<plataforma>/<agente>.md`
(aqui, `contexts/kiro-cli/dev.md`): um texto livre que diz ao agente quem ele
é e como trabalha. Todas as chaves, com tipo, default e efeito da ausência,
estão na [referência de configuração](doc/configuracao/referencia.md).

## Uso

### Primeira execução local (Python)

1. Instale a dependência: `pip install pyyaml`.
2. Crie o `pipe.yml` na raiz a partir do exemplo da seção
   [Configuração](#configuração), trocando `git.repo.main` pelo seu
   repositório de teste.
3. Escreva o contexto do agente em `contexts/kiro-cli/dev.md`.
4. Aponte a chave SSH: `export PIPE_SSH_KEY_FILE=~/.ssh/id_ed25519`.
5. Inicie a esteira na raiz da instalação: `python -m src`.

Na inicialização a esteira valida o `pipe.yml`, confere o acesso de escrita
ao repositório, clona o repositório em `repo/`, procura o GitHub Project com o
nome do board (`Entrega`, no exemplo), cria o projeto e as colunas que faltam e
começa a ler o board.
Se algo estiver faltando, ela para com uma mensagem que diz o campo ou arquivo
a corrigir (veja [Solução de problemas](#solução-de-problemas)).

Para ver o fluxo funcionar, crie uma issue no board, coloque-a em **Entrada** e
depois mova-a para **Execução**. No ciclo seguinte o agente comenta a issue e a
move para **Final**. Os logs ficam em `logs/` e aparecem no terminal. Para
parar, use `Ctrl+C`.

### Alternativa: container (Docker Compose)

O container é uma alternativa suportada à execução local e é o caminho
indicado para deixar a esteira rodando continuamente. Ele dispensa Python,
`gh` e `kiro-cli` no host; você precisa de Docker com Compose V2, um token do
GitHub (escopos `repo` e `project`), uma API key do Kiro e a chave SSH.

```bash
cp .env.example .env      # preencha GH_TOKEN, KIRO_API_KEY e SSH_KEY_FILE_HOST
docker compose build
docker compose up -d
docker compose logs -f
```

O mesmo `pipe.yml` e os mesmos contextos da execução local valem no container.
Credenciais, volumes, verificação de saúde, parada, rotação de chave e solução
de problemas estão no runbook [`doc/runbook/docker.md`](doc/runbook/docker.md).

## Exemplos

Dois pacotes de exemplo completos e hipotéticos (nenhum dado real) demonstram a
Esteira de ponta a ponta, cada um com `pipe.yml`, contextos de agente já
preenchidos, issue de exemplo e documentação própria de uso e customização:

- [`exemplos/minimalista/`](exemplos/minimalista/USO.md): a menor configuração
  possível, com uma coluna de execução, um agente e um comentário de resumo na
  issue.
- [`exemplos/referencia-hipotetica/`](exemplos/referencia-hipotetica/USO.md):
  cenário fictício de uma empresa de software, com três colunas e três agentes
  (planejador, desenvolvedor, revisor) encadeados e abertura de pull request.

Siga apenas o `USO.md` do pacote escolhido para aplicar e observar o
resultado. O `CUSTOMIZACAO.md` de cada pacote mostra o que trocar para adaptar
o exemplo ao seu caso.

## Comandos no corpo da issue

O corpo de uma issue pode terminar com um bloco de comandos, separado do texto
por uma linha contendo apenas `@---`. O que está escrito é o estado final:
comando presente garante a relação ou o atributo; comando ausente remove.

| Comando | Efeito |
|---------|--------|
| `/parent #N` | esta issue é filha de N |
| `/children #N, #M` | N e M são filhas desta issue |
| `/blocked_by #N, #M` | esta issue espera N e M fecharem |
| `/blocks #N, #M` | esta issue trava N e M até fechar |
| `/labels a, b, c` | define as labels da issue |
| `/agent-hub-<valor>` | escolhe o agente da coluna pelo mapa `agent-hub` |
| `/need_human` | pede intervenção humana e pausa a issue |
| `/close [completed\|not_planned]` | fecha a issue |
| `/reopen` | reabre a issue |
| `/archive` | arquiva a issue no board |

```markdown
# Implementar login

Validar credenciais e retornar um token.

@---
/blocked_by #N
/labels backend, segurança
/agent-hub-high
```

## Solução de problemas

| Mensagem na inicialização | Correção |
|---------------------------|----------|
| `variável PIPE_SSH_KEY_FILE não definida ou vazia` | Exporte `PIPE_SSH_KEY_FILE` com o caminho da chave privada. |
| `Arquivo pipe.yml não encontrado` | Rode `python -m src` na pasta que contém o `pipe.yml`. |
| `Arquivos de contexto ausentes` ou `vazios` | Preencha os arquivos listados em `contexts/<plataforma>/<agente>.md`. |
| `<caminho>: campo '<chave>' é obrigatório` | Complete a chave indicada; veja a [referência de configuração](doc/configuracao/referencia.md). |
| `Plataforma '<valor>' não suportada` | Use `boards.platform: github`. |

## Novidades

O que muda a cada versão, em poucas linhas e com a ação necessária quando
houver, está em [`NOVIDADES.md`](NOVIDADES.md).

## Documentação pública

- [Referência de configuração do `pipe.yml`](doc/configuracao/referencia.md)
- [Runbook do container](doc/runbook/docker.md)
- [Runbook do limite de consumo de IA](doc/runbook/limitador-consumo-ia-plataforma.md)
- [Runbook do limitador de reexecuções](doc/runbook/limitador-reexecucoes-agente.md)
- [Runbook de retirada de colunas](doc/runbook/retirada-colunas.md)
- [Exemplos](exemplos/minimalista/USO.md)
- [Novidades por versão](NOVIDADES.md)
- [Manual de padrões de documentação](doc/governanca-editorial/manual-padroes-documentacao.md)
