# Uso do exemplo de Referência (cenário hipotético)

> Cenário hipotético: nenhum dado real. Este documento é a única fonte necessária para aplicar e observar o exemplo.

## Pré-requisitos

- PIPE_SSH_KEY_FILE definida e apontando para um arquivo de chave existente.
- GitHub Project de teste: um repositório com a branch main e um board vazios, criados só para este exemplo.
- kiro-cli instalado e acessível no PATH.

Sem esses itens a execução falha por pré-requisito de ambiente, o que não conta como falha do exemplo.

## Como aplicar

1. Copie `pipe.yml` para a raiz da instalação da Esteira.
2. Copie `contexts/kiro-cli/planejador.md`, `contexts/kiro-cli/desenvolvedor.md` e `contexts/kiro-cli/revisor.md` para `contexts/kiro-cli/` na raiz da instalação.
3. Substitua `git.repo.main` pelo repositório do seu GitHub Project de teste (veja `CUSTOMIZACAO.md`).
4. Inicie a Esteira: `python -m src`.
5. Crie no board a issue descrita em `issue-exemplo.md` e deixe-a na coluna Entrada.
6. Mova a issue da coluna Entrada para a coluna Planejamento e aguarde os ciclos seguintes; as demais passagens são feitas pela própria Esteira.

## Resultado observável

- A issue recebe um comentário do Planejador Exemplo, depois um do Desenvolvedor Exemplo e depois um do Revisor Exemplo.
- Um pull request da branch de trabalho da issue é aberto na coluna Revisão.
- A issue termina na coluna Final.
- Se algo diferente disso acontecer, registre a execução como falha (veja o processo de validação interna).
