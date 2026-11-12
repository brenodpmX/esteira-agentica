# Gate de revisão do conteúdo público

Este documento define o comportamento do gate que aprova ou reprova conteúdo
público antes da publicação. Ele define o que o gate revisa, os critérios de
reprovação e o efeito da reprovação. Não define como o gate é implementado.

## Quem opera o gate

O gate é aplicado pelo agente de revisão de código da esteira, configurado no
`pipe.yml` do repositório de configuração da esteira, na etapa de revisão do
pull request. Pessoas que revisam um pull request aplicam os mesmos critérios.

## O que o gate revisa

Todo conteúdo com `audiencia: publico` no
[inventário de conteúdo público](inventario-conteudo-publico.md) que é criado ou
alterado num pull request, incluindo cada nota nova em `NOVIDADES.md`.
Conteúdo interno não passa pelo gate.

## Contrato

```text
entrada:         conteúdo público candidato à publicação (documento inteiro ou nota de versão)
criterios:       C1 fronteira público/interno respeitada;
                 C2 ausência de artefatos internos;
                 C3 ausência de promessa de retorno financeiro;
                 C4 instruções corretas e seguras;
                 C5 registro editorial adequado (nota de versão curta, informal e informativa)
saida_aprovado:  conteúdo liberado para publicação
saida_reprovado: conteúdo bloqueado, com um motivo registrado por critério violado
```

## Critérios de reprovação

| Critério | Reprova quando | Motivo registrado |
|----------|----------------|-------------------|
| C1 fronteira público/interno respeitada | o conteúdo traz mecânica interna de desenvolvimento: laço de execução, seleção de tarefas, otimização de sincronização, limites de requisição do GitHub, proteção de estado interno ou relato de incidente | `fronteira público/interno: conteúdo de mecânica interna ('<termo>')` |
| C2 ausência de artefatos internos | o conteúdo cita identificador de trabalho (`#` seguido de número), épico ou história | `artefato interno citado: '<artefato>'` |
| C3 ausência de promessa de retorno financeiro | o conteúdo promete economia, redução de custo ou retorno com número ou garantia | `promessa de retorno financeiro: '<trecho>'` |
| C4 instruções corretas e seguras | o conteúdo expõe credencial, token, chave privada ou dado pessoal; ou um comando, chave ou pré-requisito citado não existe ou não corresponde ao produto | `instrução insegura: dado sensível exposto ('<trecho>')` ou `instrução incorreta: <ponto>` |
| C5 registro editorial adequado | a nota de versão passa de 800 caracteres ou tem itens de lista | `registro editorial inadequado: nota longa demais (...)` ou `registro editorial inadequado: lista tecnicista (...)` |

C5 vale só para notas de versão. C1 a C4 valem para todo conteúdo público.

O comportamento verificável de C1, C2, C3, C5 e da parte de dados sensíveis de
C4 está automatizado em `tests/_editorial_helpers.py`
(`avaliar_gate_revisao`) e roda na suíte de testes sobre o `README.md`, a
[referência de configuração](../configuracao/referencia.md) e cada nota de
`NOVIDADES.md`. A correção das instruções (C4) exige que quem revisa execute ou
confira cada comando e chave citados contra a versão em revisão.

## Efeito da reprovação

- O conteúdo reprovado não é publicado: o pull request não é aprovado enquanto
  houver motivo registrado.
- Cada critério violado gera um motivo próprio, registrado no comentário de
  revisão do pull request, apontando o trecho que causou a reprovação.
- Corrigido o conteúdo, o gate roda de novo sobre a versão nova. Só a ausência
  de motivos aprova.
