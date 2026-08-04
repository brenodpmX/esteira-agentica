# Post Mortem — Duplicação e ausência de coluna em sub-issues propagadas entre boards (GitHub Projects V2)

## Registro

**Incidente ID:** 88 (registro), 98 (task de correção), 99 (este post mortem)
**Status:** Post mortem homologado em 04/08/2026. A correção foi implementada e
homologada no commit `01f9e83`, mas não foi integrada: o PR #103 foi fechado em
03/08/2026 sem merge, e o commit não pertence a `main` nem a esta branch
documental. Deploy em produção continua pendente.
**Owner:** engenharia
**Data de Abertura:** 2026-08-01
**Last Updated:** 2026-08-04

### Descrição

Ao vincular uma sub-issue a um parent que está em um board diferente (ex.: task filha de uma
story, story filha de um epic), o GitHub Projects V2 propaga automaticamente a sub-issue para
todos os projects onde o parent está presente — **sem coluna (`Status`) definida** no project
de destino. A esteira não possuía primitiva de remoção de item de project e o core
interpretava a ausência de coluna como "issue nova neste board", fabricando uma duplicata
local (arquivos + entrada de snapshot) via `_apply_create_down`.

O item duplicado nunca se autocorrigia: as comparações de coluna em `detect_board_changes`,
`_apply_change_down` e `_apply_change_up` ignoravam ou pulavam coluna vazia.

### Impacto observado

- Execução de agente duplicada: a duplicata era processada com o prompt/agente do board
  errado e, por prioridade de board, podia rodar antes da issue legítima.
- Escrita concorrente no mesmo número de issue (oscilação de body entre boards).
- Itens invisíveis em qualquer coluna do board até materializarem localmente.
- Resíduo de dados: 3 itens duplicados no project `story` (issues #84/#85/#86), 9 arquivos
  locais e 3 entradas de snapshot — limpeza manual necessária, fora do escopo da correção de
  código (esteira precisa estar parada).

### Reincidência

Este é o **terceiro** registro do mesmo fenômeno raiz:

| # | Data | Issues afetadas | Observação |
|---|------|------------------|------------|
| #24 | 07-06 | #16–21 | Primeiro diagnóstico do "Fenômeno 1" (post mortem #24, issue #30, board `epic`) |
| #45 | 07-22 | — | Segunda ocorrência |
| #88 | 08-01 | #84–86 | Terceira ocorrência; origem direta desta correção e deste post mortem |

Duas tentativas de correção também precederam a que foi finalmente homologada — ver
"Tentativas de correção" abaixo.

## Triagem

**Problema confirmado:** sim — reincidência de causa raiz já diagnosticada em post mortem
anterior (#24), sem correção efetiva até a task #98.

**Classificação:** bug de robustez do core/adapter GitHub (ausência de primitiva de remoção
de item de project + tratamento incorreto de coluna vazia como "issue nova").

**Severidade:** Alta (dados duplicados em produção, execução de agente em contexto errado,
e histórico de reincidência sem correção efetiva por três ciclos).

## Análise Técnica

### Causa raiz

O GitHub Projects V2 propaga automaticamente uma sub-issue para todos os projects em que o
parent está presente, ao vincular via `_add_sub_issue`. Essa propagação chega sem `Status`
definido no project de destino. A esteira não distinguia "item propagado automaticamente,
sem coluna, pertencente a outro board" de "issue nova nesse board, ainda sem coluna
sincronizada" — ambos chegavam como coluna vazia em `_apply_create_down`, e o código tratava
os dois casos da mesma forma (fallback para a primeira coluna configurada), materializando a
duplicata.

Quatro defeitos específicos, encadeados:

1. **Sem primitiva de remoção.** `BoardPort`/`Board`/`github_board.py` não tinham nenhuma
   operação para remover um item de um project (`deleteProjectV2Item` nunca era chamado).
   Sem essa primitiva, nenhuma das outras correções tem como agir — é a base de tudo.
2. **Sem pós-hook de limpeza em `_add_sub_issue`.** Depois de vincular a sub-issue, nada
   verificava se a propagação automática do GitHub havia deixado o item sem `Status` em
   outro project.
3. **Sem guard em `_apply_create_down`.** Coluna vazia + issue já pertencente a outro board
   (tem `parent` ou já existe em outro snapshot) deveria descartar o evento, não criar
   arquivos locais.
4. **Comparações de coluna ignoravam vazio.** `detect_board_changes`, `_apply_change_down`
   e `create_issue` tratavam `Status` vazio como "nada a fazer" em vez de aplicar fallback ou
   sinalizar divergência — permitindo que o estado inconsistente persistisse indefinidamente
   sem nunca se autocorrigir.

### Tentativas de correção (histórico até a correção final)

A causa raiz é conhecida desde o post mortem do incidente #24, mas levou três ciclos de
implementação até uma correção efetiva chegar a homologação:

**Tentativa 1 — PR #102 (task #88 original).** Rejeitada em code review pelo mesmo padrão de
defeito da tentativa 2 (endpoint REST inexistente mascarado por testes que não exercitavam o
caminho real). Motivou a criação da task #98 como retrabalho.

**Tentativa 2 — PR #103 (task #98, commit `e34db5f`).** Reprovada por Bruno Ferreira
(Engenheiro de Software SR) em code review, com três problemas:

1. `_remove_propagated_without_column` chamava
   `GET /repos/{owner}/{repo}/issues/{issue_number}/projectitems` via REST — **endpoint que
   não existe na API do GitHub**. O padrão real já estabelecido no mesmo arquivo
   (`_belongs_to_board`, `get_issue`) usa GraphQL (`self._gql`) com
   `projectItems{nodes{project{id}}}`. A chamada falhava, a exceção era capturada
   genericamente e apenas logada como warning — ou seja, o pós-hook **nunca removia de fato**
   o item duplicado em produção. A causa raiz permanecia sem correção efetiva apesar da
   suíte de testes passar (201 passed).
2. Cobertura de teste insuficiente: dos 4 cenários exigidos no escopo, só 2 foram
   implementados; os outros 2 foram comentados com "verificar via testes de integração",
   sem substituto real.
3. Risco de reversão circular entre o guard do `create-down` (item 3) e o fallback de coluna
   do `change-down` (item 4): como o pós-hook não funcionava de fato, o fallback tendia a
   reaplicar coluna a um item que deveria ter sido removido do project — reintroduzindo o
   próprio sintoma que a correção deveria eliminar.

Esse é o **mesmo padrão de defeito** (endpoint inexistente mascarado por testes que não
exercitam o código real) já visto na tentativa de correção do incidente raiz anterior (task
#88, PR #102) — ou seja, a reincidência aconteceu tanto no bug de produto quanto no padrão de
falha da correção.

**Tentativa 3 — correção final (commit `01f9e83`, branch `hotfix98-...`).** Isabela Gomes
(Tech Lead), durante a etapa de pré-produção, executou **cinco verificações consecutivas**
confirmando de forma independente e reprodutível o mesmo defeito (endpoint inexistente ainda
presente, sem nenhum commit novo entre as checagens). Em vez de insistir numa sexta repetição
idêntica do mesmo diagnóstico, corrigiu o defeito diretamente:

- `_remove_propagated_without_column` reescrito usando GraphQL (`self._gql`), no mesmo
  padrão real de `_belongs_to_board`/`get_issue`: consulta `projectItems{nodes{id
  project{id} fieldValues{...}}}`, filtra por `Status` vazio, chama `deleteProjectV2Item`.
- Os 2 cenários de teste faltantes foram adicionados, exercitando o adapter real via mock de
  `_gql`/`_gh` (sem monkeypatch do próprio método sob teste).
- Teste de regressão adicionado para a interação apontada no ponto 3 do code review (guard do
  `create-down` × fallback do `change-down`).
- Suíte final: **208 passed, 3 skipped** (7 testes novos em relação à tentativa reprovada).

### Linha do tempo consolidada

| Data/Hora | Evento |
|-----------|--------|
| 2026-07-06 | Fenômeno 1 diagnosticado pela primeira vez (post mortem do incidente #24) |
| 2026-07-22 | Segunda ocorrência (#45) |
| 2026-08-01 | Terceira ocorrência: duplicação em #84–86, registrada como incidente #88 |
| 2026-08-01 16:55 | Task de correção #98 criada, com escopo técnico de 5 itens em ordem obrigatória |
| 2026-08-01 17:22 | Tentativa 2 implementada (commit `e34db5f`); 201 testes passam |
| 2026-08-01 22:18 | PR #103 aberto |
| 2026-08-01 22:22 | PR #103 **reprovado** em code review (Bruno Ferreira): endpoint REST inexistente |
| 2026-08-01 22:29–22:36 | Cinco verificações consecutivas confirmam o mesmo defeito sem alteração de código |
| 2026-08-01 22:43 | Correção final aplicada (commit `01f9e83`); 208 testes passam; ambiente pré-produtivo preparado e branch homologada por Isabela Gomes - Tech Lead |
| 2026-08-01 | Post mortem (esta issue, #99) executado |

## Correção implementada (estado final, commit `01f9e83`)

1. **Primitiva `remove_from_board`** via mutation GraphQL `deleteProjectV2Item`, exposta em
   `BoardPort` e `Board` (`src/core/board.py`, `src/adapters/github_board.py`).
2. **Pós-hook em `_add_sub_issue`** (`_remove_propagated_without_column`): após vincular a
   sub-issue, consulta via GraphQL os `projectItems` do filho; remove (via
   `remove_from_board`) qualquer propagação com `Status` vazio, preservando itens legítimos
   com coluna própria no mesmo board.
3. **Guard em `_apply_create_down`**: coluna vazia + issue já pertencente a outro board não
   cria arquivos locais — chama `remove_from_board` e descarta o evento.
4. **Fallback de coluna** em `create_issue` e `_apply_change_down` quando a coluna remota vem
   vazia, em vez de deixar o item sem `Status`.
5. **`detect_board_changes`** não ignora mais coluna vazia — trata como divergência a
   corrigir.

Cobertura de teste: `tests/test_sub_issue_propagation_fix.py`, 8 cenários (incluindo os 4
exigidos no escopo original e os 2 de regressão adicionados na correção final).

**Fora de escopo** (não corrigido por esta task): limpeza do resíduo já existente (#84/#85/#86
duplicados no project `story`) — operação manual, com a esteira parada.

## Fatores que permitiram a reincidência por 3 ciclos

1. **Ausência de teste de integração real contra a API do GitHub.** A suíte usa
   `FakeBoardPort`/mocks de `_gql`/`_gh`; um endpoint REST inexistente só é detectado por
   inspeção manual de código (code review) ou em produção — nunca pela suíte automatizada,
   mesmo com 100% dos testes "passando".
2. **Padrão de "cenário de teste comentado sem substituto".** Nas duas tentativas reprovadas,
   cenários exigidos no escopo foram comentados com anotações como "verificar via testes de
   integração com board real", sem nenhum teste real ser adicionado em substituição — a
   lacuna de cobertura ficava invisível ao olhar superficial do CI (suíte "passa").
3. **Delírio de API (hallucination) recorrente no mesmo padrão.** Duas tentativas
   consecutivas (#88/PR#102 e #98/PR#103) implementaram uma chamada REST para um endpoint que
   nunca existiu na API do GitHub, replicando exatamente o mesmo tipo de erro apesar de haver
   um padrão correto (GraphQL) já estabelecido no mesmo arquivo, poucas linhas abaixo
   (`_belongs_to_board`, `get_issue`).
4. **Code review humano foi a única rede de proteção efetiva.** As duas tentativas com o
   defeito só foram capturadas por revisão humana (Bruno Ferreira), não por qualquer
   verificação automatizada — e a segunda rejeição só não gerou um quarto ciclo porque a Tech
   Lead decidiu corrigir diretamente em vez de reabrir mais uma rodada de retrabalho.

## O que funcionou bem

- O processo de code review humano capturou corretamente, nas duas vezes, um defeito que a
  suíte de testes automatizada não detectou — validando a decisão de manter revisão humana
  obrigatória antes de merge em `main`.
- A Tech Lead, ao identificar que a quinta verificação consecutiva não traria informação
  nova, interrompeu o ciclo de reverificação redundante e corrigiu o defeito diretamente,
  evitando um sexto relatório idêntico e um quarto ciclo de retrabalho.
- A ordem obrigatória de implementação definida no escopo da task #98 (item 1 antes de 2 e 3,
  que por sua vez precedem o item 4) preveniu que o fallback de coluna materializasse a
  duplicata antes do guard/pós-hook estarem prontos para bloqueá-la.

## Recomendações

1. **Adicionar um smoke test de integração real (opcional, gated) contra a API do GitHub**
   para os métodos que chamam endpoints REST/GraphQL específicos (`_gql`/`_gh`), executável
   manualmente ou em pipeline separado com token de teste — para capturar delírios de
   endpoint inexistente antes do code review humano, não só depois.
2. **Proibir merge de cenário de teste "comentado sem substituto".** Quando um cenário do
   critério de aceite não puder ser automatizado, o code review deve exigir uma nota explícita
   no PR (não apenas um comentário no código) apontando a lacuna e um responsável/prazo para
   supri-la — em vez de permitir que a suíte "passe" silenciosamente com cobertura reduzida.
3. **Documentar o padrão de acesso à API do GitHub usado no projeto** (GraphQL via `self._gql`
   para tudo que envolve `projectItems`/campos de projeto; REST via `self._gh` apenas para
   operações de issue/PR tradicionais) em `CONTEXT.md` ou como comentário no topo de
   `github_board.py`, para reduzir a chance de um agente (ou humano) inventar um endpoint REST
   inexistente para operações de Projects V2.
4. **Agendar a limpeza do resíduo (#84/#85/#86)** como tarefa própria, com a esteira parada,
   antes ou logo após o deploy desta correção em produção — resíduo não se autocorrige mesmo
   com o bug corrigido nos novos vínculos.
5. **Fechar o bug de acompanhamento** (`correcao-98-sub-issues-propagadas-reincide-endpoint-inexistente`,
   board `bug`) após a homologação confirmar o comportamento em staging, removendo o
   `/blocks #98` do seu body.

— Isabela Gomes - Tech Lead
