# Comunicação pública de mudanças por versão

Este documento define quando uma mudança do produto ganha nota pública, como a
nota é escrita e em que momento ela é publicada. Ele segue o
[manual de padrões de documentação](manual-padroes-documentacao.md) e toda nota
passa pelo [gate de revisão](gate-revisao.md).

## Canal

`NOVIDADES.md`, na raiz do repositório, é o canal único da comunicação pública
de mudanças. Nenhum outro arquivo publica notas de versão para o público
externo.

O `CHANGELOG.md` continua existindo como registro técnico detalhado de cada
versão, para quem desenvolve a esteira. Ele não substitui a nota pública e não
segue as regras de redação deste documento.

## Elegibilidade

Uma mudança é elegível quando chega à branch `main` e altera comportamento,
instalação, configuração ou compatibilidade do produto. O critério objetivo é o
incremento de `VERSION` em `src/core/version.py`: pela regra de versionamento
do projeto, toda alteração de código incrementa a versão, e toda versão nova
exige uma nota em `NOVIDADES.md`.

Mudanças que só alteram documentação ou testes não incrementam a versão e não
geram nota.

A fonte da versão é sempre `VERSION`. A tag git `v1.5.0`, que ficou defasada,
não é usada como referência.

## Formato

Cada nota é um bloco em `NOVIDADES.md`, sob um título `## <versão>`, com os
quatro campos abaixo, um por linha:

```text
versao:      identificador da versão, igual a VERSION
data:        data do merge na main, no formato AAAA-MM-DD
destaques:   texto curto, informal e de benefício (melhorias, correções, novidades)
acao:        o que o usuário precisa fazer ao atualizar, ou "nenhuma"
```

A nota mais recente fica no topo do arquivo.

Exemplo:

```text
versao: 1.29.0
data: 2026-11-09
destaques: Imagens e arquivos colados ou anexados nas issues agora chegam junto com o texto. ...
acao: nenhuma. Para restringir tipos ou tamanho, use boards.<board_id>.file-sync, ...
```

## Regras de redação

A nota é escrita em linguagem de benefício: diz o que o usuário ganha ou o
que deixou de dar errado, não como foi implementado.

- A nota inteira (os quatro campos) tem no máximo 800 caracteres.
- `destaques` é prosa corrida, informal e informativa. A nota nunca é uma
  lista tecnicista: não tem itens de lista nem nomes de função, de classe ou de
  arquivo interno.
- `destaques` consolida tudo o que a versão trouxe: melhorias, correções e
  novidades.
- A nota não cita artefatos do processo interno: identificadores de trabalho
  (como `#` seguido de número), épicos ou histórias.
- A nota não promete retorno financeiro, economia ou adoção.
- `acao` descreve passo de compatibilidade ou migração quando houver; sem
  passo necessário, começa com `nenhuma`.

## Momento da publicação

A nota é escrita no mesmo pull request que carrega a mudança, junto com o
incremento de `VERSION` e a entrada do `CHANGELOG.md`. Assim ela chega à `main`
no mesmo momento da mudança, no mesmo merge. A nota nunca é publicada depois do
merge nem acumulada para publicação periódica.

O campo `data` é a data desse merge.

## Revisão e ausência de nota

- O pull request que incrementa `VERSION` sem nota correspondente em
  `NOVIDADES.md` é reprovado na revisão de código.
- O teste `tests/test_comunicacao_versao.py::test_versao_corrente_tem_nota`
  falha quando a versão corrente não tem nota.
- O texto da nota passa pelo [gate de revisão](gate-revisao.md); nota reprovada
  bloqueia o merge até ser corrigida.

## Auditoria

A cada merge na `main`, quem revisa confere se cada versão elegível tem nota
com a mesma `versao` e a mesma `data`. O resultado é um destes relatos:

- `<versão>: mudança elegível sem nota correspondente`;
- `<versão>: publicação fora do mesmo momento`.

A regra vale a partir da versão 1.29.0, a primeira publicada em `NOVIDADES.md`.
As versões anteriores ficam registradas apenas no `CHANGELOG.md`.
