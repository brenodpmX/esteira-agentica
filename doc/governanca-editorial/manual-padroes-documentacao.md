# Manual de padrões de documentação

Este manual rege toda alteração de documentação do repositório, pública ou
interna. Não há exceções: uma alteração que viola uma regra é recusada até ser
corrigida. Quando outro documento contradiz este manual, vale o manual.

## Definições

- **Documento público**: documento com `audiencia: publico` no
  [inventário de conteúdo público](inventario-conteudo-publico.md). Serve a
  quem quer conhecer, avaliar ou operar o produto.
- **Documento interno**: documento com `audiencia: interno`. Serve a quem
  desenvolve o produto.
- **Porta de entrada**: o `README.md` da raiz.
- **Fonte canônica**: o único documento em que um fato é descrito por inteiro.

## Regras

1. **MP-01** — Todo documento novo deve entrar no inventário de conteúdo
   público no mesmo pull request, com os campos `documento`, `audiencia`,
   `sensibilidade`, `fonte_canonica`, `responsavel` e `gatilho_atualizacao`
   preenchidos. A audiência deve ser decidida pela finalidade do conteúdo e
   nunca pela pasta onde o arquivo está; audiência `misto`, ou audiência
   diferente da sugerida pela pasta, deve ter o campo `decisao` com a
   justificativa.
2. **MP-02** — Cada fato deve ter fonte canônica única. Os demais documentos
   devem apontar para ela com link e nunca copiar o conteúdo. A descrição de
   chaves do `pipe.yml` vive só em `doc/configuracao/referencia.md`; o
   procedimento do container vive só em `doc/runbook/docker.md`; as notas de
   versão vivem só em `NOVIDADES.md`.
3. **MP-03** — Documento público nunca deve conter conteúdo cuja finalidade
   seja exclusivamente o desenvolvimento do produto. Esse conteúdo deve ficar
   em documento interno, como `doc/interno/funcionamento-interno.md`.
4. **MP-04** — Documento público nunca deve citar artefatos do processo
   interno: identificadores de trabalho (`#` seguido de número), épicos ou
   histórias, nem dentro de blocos de código.
5. **MP-05** — Documento público nunca deve conter credencial, token, chave
   privada, endereço IP ou dado pessoal real. Exemplos devem usar valores
   fictícios, como `minha-org` e `example.com`.
6. **MP-06** — A porta de entrada deve conter só conteúdo público para quem
   quer conhecer e usar o produto e nunca deve ter conteúdo de desenvolvimento:
   laço de execução, seleção de tarefas, otimização de sincronização, limites
   de requisição da plataforma, proteção de estado interno, relato de
   incidente ou post-mortem.
7. **MP-07** — A porta de entrada deve ser concisa: no máximo 600 linhas no
   total e no máximo 60 linhas na seção `## Configuração`, que deve ter um
   único exemplo mínimo de `pipe.yml`.
8. **MP-08** — Na porta de entrada, a execução local deve sempre aparecer antes
   do container. O container deve ser apresentado como alternativa suportada,
   com link para `doc/runbook/docker.md`.
9. **MP-09** — A porta de entrada deve ter links para
   `doc/configuracao/referencia.md`, `doc/runbook/docker.md` e `exemplos/`.
10. **MP-10** — Toda nota de versão deve seguir
    [comunicação de versão](comunicacao-versao.md): campos `versao`, `data`,
    `destaques` e `acao`, no máximo 800 caracteres, linguagem de benefício e
    publicação no mesmo pull request da mudança. A nota nunca deve ser uma
    lista tecnicista.
11. **MP-11** — Toda chave do `pipe.yml` criada, alterada ou removida no motor
    deve ser refletida em `doc/configuracao/referencia.md` no mesmo pull
    request, com os oito campos do catálogo, e na lista
    `CHAVES_CONFIGURACAO_CONHECIDAS` de `tests/test_catalogo_configuracao.py`.
12. **MP-12** — Todo link relativo deve apontar para um arquivo que existe no
    repositório.
13. **MP-13** — Nomes de chave, comando, arquivo e caminho devem sempre ser
    escritos entre crases no texto corrido.
14. **MP-14** — Todo documento público criado ou alterado deve ser aprovado no
    [gate de revisão](gate-revisao.md) antes do merge. Conteúdo reprovado nunca
    deve ser publicado.
15. **MP-15** — Quando a fonte canônica, o responsável ou o gatilho de
    atualização de um documento mudar, o item do inventário deve ser
    atualizado no mesmo pull request.

## Como verificar

| Regra | Verificação |
|-------|-------------|
| MP-01, MP-15 | `tests/test_inventario_editorial.py` |
| MP-02 | revisão do pull request: o fato alterado existe em um só documento |
| MP-03 | revisão do pull request contra a finalidade registrada no inventário |
| MP-04, MP-05, MP-06, MP-07, MP-08, MP-09 | `tests/test_manual_padroes.py` e `tests/test_readme_porta_entrada.py` |
| MP-10 | `tests/test_comunicacao_versao.py` |
| MP-11 | `tests/test_catalogo_configuracao.py` |
| MP-12 | `tests/test_readme_porta_entrada.py` para a porta de entrada; revisão do pull request para os demais |
| MP-13 | revisão do pull request |
| MP-14 | `tests/test_gate_revisao.py` e revisão do pull request |

Uma divergência é registrada citando o id da regra e o ponto do documento, por
exemplo `MP-06: mecânica interna na porta de entrada ('loop principal')`.
