# Problem Space — Rodar no Docker

Status: resolvido na versão 1.6.0
Owner: product
Last updated: 2026-08-03

## Resultado da entrega

O problema foi atendido com imagem Docker, orquestração por Compose, credenciais
externas, volumes persistentes e documentação operacional. O host ainda precisa
de Docker, credenciais e uma instalação completa do Kiro CLI no momento do
build, mas não precisa instalar dependências da esteira dentro do container nem
interagir com o runtime depois do startup. A homologação confirmou o ciclo real
de sincronização e agente.

## Inputs
- Issue #1 "Rodar no Docker"
- src/__main__.py (`_setup_ssh`, `startup`)
- src/core/config.py (`_validate_env`, `check_config`)
- src/adapters/kiro_cli_agent.py (`_run` chama `kiro-cli chat`)
- README.md (seção Requisitos)

## Contexto original
A execução anterior pressupunha uma máquina preparada à mão. O `startup` copia a
chave SSH indicada por `PIPE_SSH_KEY_FILE` para `~/.ssh/id_pipe`, configura o
`~/.ssh/config` e clona os repositórios. O adapter de agente invoca
`kiro-cli chat` assumindo que o binário existe no PATH e está autenticado. As
operações de board dependem do `gh` CLI autenticado. Nada disso é empacotado ou
parametrizado para um ambiente efêmero de container.

## Problemas
- **Dependência de máquina física:** o analista fica preso a um host preparado
  manualmente; não há forma reprodutível de subir a esteira em outro lugar.
- **Setup manual de credenciais:** SSH, `gh` e `kiro-cli` precisam ser
  autenticados a mão no host antes de rodar.
- **Configuração acoplada ao host:** `pipe.yml`, `contexts/` e variáveis de
  ambiente vivem no sistema de arquivos local, sem um mecanismo padronizado de
  injeção externa.
- **Ausência de execução autônoma verificável:** não há garantia de que o ciclo
  completo rode sem intervenção humana num ambiente limpo.
- **Falta de documentação de operação:** não existe guia enxuto de "o que
  preciso para rodar".

## Impacto
- Barreira de adoção alta e onboarding lento.
- Execução não reprodutível entre máquinas/ambientes.
- Risco operacional: passos manuais de credencial são propensos a erro e
  dificultam auditoria.

## Oportunidade
Containerizar agora destrava operar a esteira em qualquer host (servidor,
nuvem, CI) de forma reprodutível e autônoma, reduzindo drasticamente o esforço
de setup e removendo o vínculo com uma máquina específica.
