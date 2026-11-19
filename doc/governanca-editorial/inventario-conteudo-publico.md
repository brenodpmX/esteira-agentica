# Inventário de conteúdo público

Este inventário classifica cada documento priorizado do repositório como
público ou interno, pela finalidade do conteúdo e não pela pasta onde ele está.
Cada item registra quem mantém o documento e o evento que obriga a revisá-lo.
As regras de preenchimento estão no
[manual de padrões de documentação](manual-padroes-documentacao.md) (MP-01 e
MP-15).

Campos de cada item:

- `documento`: caminho do arquivo ou da pasta.
- `audiencia`: `publico`, `interno` ou `misto`.
- `sensibilidade`: `baixa`, `media` ou `alta`.
- `fonte_canonica`: onde vive a versão de referência.
- `responsavel`: papel que mantém o documento.
- `gatilho_atualizacao`: evento que obriga a revisão do documento.
- `decisao`: justificativa da classificação, obrigatória quando a audiência é
  `misto` ou diverge do que a pasta sugere.

Um item sem `fonte_canonica`, `responsavel` ou `gatilho_atualizacao` é
incompleto e bloqueia o merge até ser completado.

## Decisões sobre o README

O `README.md` antigo misturava porta de entrada e mecânica interna. As seções de
laço de execução, seleção de tarefas, sincronização, proteção de estado interno,
limites de requisição do GitHub e relatos de incidentes foram movidas para
`doc/interno/funcionamento-interno.md`. As seções mistas (execução de agentes,
comandos no corpo da issue, integridade entre boards, eventos de coluna,
retirada de colunas, anexos e proteção contra falha de sincronização) foram
decididas assim: o que o operador configura ficou na
[referência de configuração](../configuracao/referencia.md), os comandos no
corpo da issue ficaram no `README.md`, e o detalhe de implementação foi para o
documento interno. A solução de problemas e o acesso ao estado pelo host, que
eram só do container, foram para `doc/runbook/docker.md`.

## Conteúdo público

### `README.md`

```text
documento: README.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: README.md
responsavel: Tech Lead
gatilho_atualizacao: mudança em pré-requisitos, instalação, execução local, capacidades ou limites do produto, ou no exemplo mínimo do pipe.yml
```

### `NOVIDADES.md`

```text
documento: NOVIDADES.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: NOVIDADES.md
responsavel: Engenharia (quem altera o motor)
gatilho_atualizacao: incremento de VERSION em src/core/version.py
```

### `doc/configuracao/referencia.md`

```text
documento: doc/configuracao/referencia.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: doc/configuracao/referencia.md
responsavel: Engenharia (quem altera o motor)
gatilho_atualizacao: chave do pipe.yml criada, alterada ou removida em src/core/config.py ou nos módulos de validação que ele chama
```

### `doc/runbook/docker.md`

```text
documento: doc/runbook/docker.md
audiencia: publico
sensibilidade: media
fonte_canonica: doc/runbook/docker.md
responsavel: Tech Lead
gatilho_atualizacao: mudança em Dockerfile, docker-compose.yml, compose.dev.yml, .env.example ou docker/versions.env
```

### `.env.example`

```text
documento: .env.example
audiencia: publico
sensibilidade: media
fonte_canonica: .env.example
responsavel: Tech Lead
gatilho_atualizacao: variável de ambiente do container criada, alterada ou removida
```

### `doc/runbook/limitador-consumo-ia-plataforma.md`

```text
documento: doc/runbook/limitador-consumo-ia-plataforma.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: doc/runbook/limitador-consumo-ia-plataforma.md
responsavel: Engenharia (quem altera o motor)
gatilho_atualizacao: mudança no comportamento ou nas chaves de agents.<platform_id>.limits
```

### `doc/runbook/limitador-reexecucoes-agente.md`

```text
documento: doc/runbook/limitador-reexecucoes-agente.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: doc/runbook/limitador-reexecucoes-agente.md
responsavel: Engenharia (quem altera o motor)
gatilho_atualizacao: mudança no comportamento ou nas chaves de agent_circuit_break
```

### `doc/runbook/retirada-colunas.md`

```text
documento: doc/runbook/retirada-colunas.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: doc/runbook/retirada-colunas.md
responsavel: Engenharia (quem altera o motor)
gatilho_atualizacao: mudança no comportamento ou nas chaves de boards.<board_id>.column-migrations
```

### `exemplos/minimalista/USO.md`

```text
documento: exemplos/minimalista/USO.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: exemplos/minimalista/USO.md
responsavel: Tech Lead
gatilho_atualizacao: mudança no pipe.yml do pacote ou em chave usada por ele; nova versão suportada
```

### `exemplos/minimalista/CUSTOMIZACAO.md`

```text
documento: exemplos/minimalista/CUSTOMIZACAO.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: exemplos/minimalista/CUSTOMIZACAO.md
responsavel: Tech Lead
gatilho_atualizacao: mudança no pipe.yml do pacote ou em chave usada por ele; nova versão suportada
```

### `exemplos/referencia-hipotetica/USO.md`

```text
documento: exemplos/referencia-hipotetica/USO.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: exemplos/referencia-hipotetica/USO.md
responsavel: Tech Lead
gatilho_atualizacao: mudança no pipe.yml do pacote ou em chave usada por ele; nova versão suportada
```

### `exemplos/referencia-hipotetica/CUSTOMIZACAO.md`

```text
documento: exemplos/referencia-hipotetica/CUSTOMIZACAO.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: exemplos/referencia-hipotetica/CUSTOMIZACAO.md
responsavel: Tech Lead
gatilho_atualizacao: mudança no pipe.yml do pacote ou em chave usada por ele; nova versão suportada
```

### `doc/governanca-editorial/manual-padroes-documentacao.md`

```text
documento: doc/governanca-editorial/manual-padroes-documentacao.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: doc/governanca-editorial/manual-padroes-documentacao.md
responsavel: Tech Lead
gatilho_atualizacao: mudança em regra editorial ou em critério do gate de revisão
```

### `doc/governanca-editorial/gate-revisao.md`

```text
documento: doc/governanca-editorial/gate-revisao.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: doc/governanca-editorial/gate-revisao.md
responsavel: Tech Lead
gatilho_atualizacao: mudança em critério de reprovação ou no agente de revisão configurado
```

### `doc/governanca-editorial/comunicacao-versao.md`

```text
documento: doc/governanca-editorial/comunicacao-versao.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: doc/governanca-editorial/comunicacao-versao.md
responsavel: Tech Lead
gatilho_atualizacao: mudança na regra de elegibilidade, no formato ou no momento da nota de versão
```

### `doc/governanca-editorial/inventario-conteudo-publico.md`

```text
documento: doc/governanca-editorial/inventario-conteudo-publico.md
audiencia: publico
sensibilidade: baixa
fonte_canonica: doc/governanca-editorial/inventario-conteudo-publico.md
responsavel: Tech Lead
gatilho_atualizacao: documento criado, removido ou reclassificado; mudança de fonte, responsável ou gatilho
```

## Conteúdo interno

### `doc/runbook/homologacao-branches-nao-mergeadas.md`

```text
documento: doc/runbook/homologacao-branches-nao-mergeadas.md
audiencia: interno
sensibilidade: baixa
fonte_canonica: doc/runbook/homologacao-branches-nao-mergeadas.md
responsavel: Tech Lead
gatilho_atualizacao: nova homologação da limpeza de branches
decisao: roteiro de homologação de uma correção do motor; a finalidade é validar o desenvolvimento, não orientar quem opera o produto, apesar de estar na pasta de runbooks
```

### `doc/governanca-editorial/baseline-avaliacao.md`

```text
documento: doc/governanca-editorial/baseline-avaliacao.md
audiencia: interno
sensibilidade: media
fonte_canonica: doc/governanca-editorial/baseline-avaliacao.md
responsavel: Dono do produto
gatilho_atualizacao: confirmação de participantes para o teste de avaliação ou conclusão de uma rodada de teste
decisao: registro de medição com participantes e decisão de continuidade; serve à gestão do produto, não a quem avalia ou opera
```

### `CHANGELOG.md`

```text
documento: CHANGELOG.md
audiencia: interno
sensibilidade: baixa
fonte_canonica: CHANGELOG.md
responsavel: Engenharia (quem altera o motor)
gatilho_atualizacao: incremento de VERSION em src/core/version.py
decisao: registro técnico detalhado de cada versão, com identificadores de trabalho e detalhes de implementação; a comunicação pública de versão vive em NOVIDADES.md
```

### `CONTEXT.md`

```text
documento: CONTEXT.md
audiencia: interno
sensibilidade: baixa
fonte_canonica: CONTEXT.md
responsavel: Tech Lead
gatilho_atualizacao: decisão técnica nova ou alteração de arquitetura
```

### `doc/interno/funcionamento-interno.md`

```text
documento: doc/interno/funcionamento-interno.md
audiencia: interno
sensibilidade: media
fonte_canonica: doc/interno/funcionamento-interno.md
responsavel: Tech Lead
gatilho_atualizacao: mudança no laço de execução, na seleção de tarefas, na sincronização ou nas proteções internas do motor
decisao: mecânica de desenvolvimento remanejada do README.md; os fatos de operação foram extraídos para a referência de configuração e os runbooks
```

### `doc/exemplos/`

```text
documento: doc/exemplos/
audiencia: interno
sensibilidade: baixa
fonte_canonica: doc/exemplos/
responsavel: Tech Lead
gatilho_atualizacao: novo pacote de exemplo, nova validação interna ou mudança no roteiro de apresentação
decisao: processo de validação interna, roteiro de apresentação e manutenção dos exemplos; quem usa um exemplo precisa só do USO.md do pacote
```

### `doc/architecture/`

```text
documento: doc/architecture/
audiencia: interno
sensibilidade: baixa
fonte_canonica: doc/architecture/
responsavel: Tech Lead
gatilho_atualizacao: novo item de trabalho que produza decisões e contratos técnicos do motor
```

### `doc/incidente/`

```text
documento: doc/incidente/
audiencia: interno
sensibilidade: media
fonte_canonica: doc/incidente/
responsavel: Tech Lead
gatilho_atualizacao: novo item de trabalho que produza tickets e homologações de incidentes
```

### `doc/product/`

```text
documento: doc/product/
audiencia: interno
sensibilidade: media
fonte_canonica: doc/product/
responsavel: Tech Lead
gatilho_atualizacao: novo item de trabalho que produza análises e post-mortems de produto
```

### `doc/quality/`

```text
documento: doc/quality/
audiencia: interno
sensibilidade: baixa
fonte_canonica: doc/quality/
responsavel: Tech Lead
gatilho_atualizacao: novo item de trabalho que produza casos de teste e resultados de execução de testes
```

### `doc/changes/`

```text
documento: doc/changes/
audiencia: interno
sensibilidade: baixa
fonte_canonica: doc/changes/
responsavel: Tech Lead
gatilho_atualizacao: novo item de trabalho que produza registros de mudança por item de trabalho
```

### `doc/changelogs/`

```text
documento: doc/changelogs/
audiencia: interno
sensibilidade: baixa
fonte_canonica: doc/changelogs/
responsavel: Tech Lead
gatilho_atualizacao: novo item de trabalho que produza registros de mudança por item de trabalho
```

### `doc/stories/`

```text
documento: doc/stories/
audiencia: interno
sensibilidade: baixa
fonte_canonica: doc/stories/
responsavel: Tech Lead
gatilho_atualizacao: novo item de trabalho que produza detalhamento de itens de trabalho
```

### `doc/requirements/`

```text
documento: doc/requirements/
audiencia: interno
sensibilidade: baixa
fonte_canonica: doc/requirements/
responsavel: Tech Lead
gatilho_atualizacao: novo item de trabalho que produza requisitos de itens de trabalho
```
