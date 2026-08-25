# Regras de Negócio — Exemplo de configurações de Esteira

Status: draft · Owner: requirements · Updated: 2026-08-24
Inputs: Issue #93 (body e histórico); `doc/product/exemplos-configuracoes-de-esteira/vision.md` (RN01–RN10); `doc/product/exemplos-configuracoes-de-esteira/epicos.md`; `README.md`

Este documento refina, para uso de UX/arquitetura/engenharia/QA, as regras de
negócio já aprovadas em `vision.md` (RN01–RN10). Não repete a redação de
negócio; adiciona contexto de aplicação, exceções e comportamento esperado nas
bordas de cada regra.

## RN-001 — Dois exemplos, nem mais nem menos, nesta entrega

**Descrição:** o escopo desta entrega contém exatamente dois exemplos:
Minimalista e Referência hipotética. Nenhum outro tema (Kanban, Scrum,
Acadêmico, XGH, Gestão, RH, Atendimento) é construído nesta entrega.
**Contexto:** aplica-se ao planejamento e à execução desta entrega, do
requisito à validação.
**Exceções:** nenhuma. Ampliar a lista exige nova evidência e aprovação
explícita do dono, e só pode ocorrer via o épico de expansão (RN09/RN10)
quando esta entrega estiver em produção.
**Comportamento na borda:** o Bloco 2 (`epicos.md`) explicitamente proíbe
incluir os temas restantes "como exemplos adicionais" mesmo que caibam no
mesmo esforço do Bloco 2 — a restrição é de escopo aprovado, não de
capacidade.
**Rastreamento:** referencia RN09/RN10 de `vision.md`. Blocos 1–3 de
`epicos.md`.

## RN-002 — Nenhum dado real, pessoal ou confidencial em qualquer exemplo

**Descrição:** nenhum exemplo pode conter dado pessoal, credencial, segredo,
identificador real de pessoa ou empresa, ou configuração copiada de um
ambiente real.
**Contexto:** aplica-se a todo artefato de ambos os exemplos — `pipe.yml` de
exemplo, contextos de agente, issues de exemplo, roteiro de apresentação e
qualquer registro de validação.
**Exceções:** nenhuma. É critério de aceite de negócio explícito (item 6 de
`vision.md`).
**Comportamento na borda:** cenários e dados devem ser explicitamente
identificados como hipotéticos (RN04) — não basta a ausência de dado real; a
rotulagem explícita de "hipotético" é parte da regra, para que ninguém
confunda o exemplo com uma instalação real na apresentação.
**Rastreamento:** referencia RN03/RN04 de `vision.md`. Blocos 1 e 2 de
`epicos.md`.

## RN-003 — Validação interna usa somente a documentação do usuário final

**Descrição:** a execução de validação de cada exemplo deve ser feita por uma
pessoa interna seguindo exclusivamente a documentação destinada ao usuário
(instruções de uso e customização do próprio exemplo) — sem depender de
conhecimento prévio da implementação da Esteira que não esteja documentado no
exemplo.
**Contexto:** aplica-se à etapa de validação/governança (Bloco 3) de cada
exemplo, antes de qualquer apresentação externa.
**Exceções:** nenhuma. Se a pessoa validadora precisar de conhecimento fora
da documentação do exemplo para completar o ciclo, isso é uma falha do
exemplo a ser corrigida, não uma validação aprovada.
**Comportamento na borda:** o critério de saída do Bloco 1 exige "execução
interna completa seguindo somente a documentação" — uma execução com ajuda
externa não documentada não satisfaz o critério de saída do bloco, mesmo que
o resultado final tenha sido produzido.
**Rastreamento:** referencia RN01/RN06 de `vision.md`. Blocos 1–3 de
`epicos.md`.

## RN-004 — Todo exemplo segue o padrão vigente de contextos

**Descrição:** os contextos de agente de cada exemplo devem seguir o padrão
`contexts/<plataforma>/<agente>.md` já documentado no README, com conteúdo
preenchido (não vazio) para cada agente referenciado pelo exemplo.
**Contexto:** aplica-se à configuração e aos contextos de ambos os exemplos.
**Exceções:** nenhuma. O histórico da issue descarta explicitamente
`pipe/contexts/kiro-cli/*.md` e `pipe/contexts/artifacts/*.md` como caminhos
válidos — eram apenas referência desatualizada, não uma mudança desejada.
**Comportamento na borda:** nenhuma — RN02 de `vision.md` é direta e sem
exceção registrada.
**Rastreamento:** referencia RN02 de `vision.md`; histórico, resposta do
dono, item 5 ("vamos usar o padrão mais atual").

## RN-005 — Resultado é avaliado contra o objetivo declarado do próprio exemplo, sem meta numérica

**Descrição:** cada exemplo declara seu próprio objetivo, e o resultado da
validação é avaliado contra esse objetivo específico — não contra uma meta
numérica de conversão, adoção ou retorno financeiro, que esta entrega
explicitamente não define.
**Contexto:** aplica-se à avaliação de qualidade de cada exemplo (RN06) e à
leitura do resultado da apresentação ao prospect.
**Exceções:** nenhuma. É decisão explícita do dono, registrada no histórico e
consolidada em `vision.md` ("Retorno e como medir") — não deve ser
reinterpretada como ausência de critério: o critério existe, é qualitativo e
por exemplo.
**Comportamento na borda:** visualização, download ou opinião genérica não
são tratados isoladamente como prova de valor (última linha de "Retorno e
como medir" em `vision.md`).
**Rastreamento:** referencia RN06 de `vision.md`; histórico, resposta do
dono, item 6.

## RN-006 — Toda execução de validação registra modelo, tokens e custo observados, sem promessa de custo universal

**Descrição:** cada execução de validação de um exemplo deve registrar o
modelo usado, os tokens consumidos e o custo observado naquele cenário
específico. Esse registro é informativo do cenário testado — não pode ser
apresentado como custo garantido ou universal para outros cenários/modelos.
**Contexto:** aplica-se ao registro de cada execução de validação (Bloco 3),
e a qualquer material usado na apresentação ao prospect que mencione custo.
**Exceções:** nenhuma.
**Comportamento na borda:** o critério de aceite 5 de `vision.md` exige que
"tokens e custo estão ligados ao cenário, modelo e versão usados" — um
registro que informe apenas um número de custo sem essas três amarrações
não satisfaz a regra.
**Rastreamento:** referencia RN05 de `vision.md`.

## RN-007 — Toda apresentação a um prospect registra uma decisão explícita

**Descrição:** ao final de cada apresentação da vitrine a um prospect, deve
existir um registro explícito de uma das duas decisões — interesse em uma
próxima avaliação/uso, ou não interesse — acompanhado de razões/objeções no
caso de não interesse.
**Contexto:** aplica-se à apresentação dirigida ao público externo inicial
(empresa de tecnologia que desenvolve software próprio e inicia adoção de
IA no desenvolvimento).
**Exceções:** visualizações ou opiniões genéricas, sem manifestação explícita
de interesse/recusa, não satisfazem esta regra e não podem ser tratadas como
prova de valor.
**Comportamento na borda:** o critério de saída do Bloco 3 aceita
explicitamente "a apresentação produz uma decisão registrada, mesmo que seja
não avançar" — a ausência de decisão (nem interesse, nem recusa) é o único
resultado que não satisfaz a regra.
**Rastreamento:** referencia resultado esperado 3 e "Retorno e como medir"
(item 4) de `vision.md`.

## RN-008 — Toda mudança de produto que afete um exemplo publicado exige avaliação de impacto

**Descrição:** todo épico que alcançar a etapa de documentação deve avaliar se
a mudança entregue afeta algum exemplo já publicado (Minimalista ou
Referência hipotética) e atualizar o exemplo quando necessário.
**Contexto:** aplica-se ao processo de qualquer épico futuro da Esteira, a
partir do momento em que os dois exemplos desta entrega existirem, e é
transversal — não se limita ao board `epic`.
**Exceções:** nenhuma. É critério de aceite de negócio explícito (item 8 de
`vision.md`, "sem antecipar sua implementação técnica").
**Comportamento na borda:** o Bloco 3 marca explicitamente como fora de
escopo "implementar automação de board ou `target-prompt` nesta etapa de
negócio" — a regra exige a avaliação de impacto como processo; a automação
dessa avaliação (ex.: ajuste de `target-prompt` na coluna de documentação)
é decisão de configuração do dono, fora do escopo deste épico.
**Rastreamento:** referencia RN08 de `vision.md`; histórico, resposta do
dono, item 7.

## RN-009 — Responsável, versão suportada e regra de revisão são explícitos e obrigatórios

**Descrição:** cada exemplo deve declarar um responsável pela revisão, a
versão da Esteira suportada, e a condição que obriga uma revisão (RN-008 é o
gatilho principal; a declaração aqui é o registro no próprio exemplo).
**Contexto:** aplica-se à documentação de cada exemplo (Bloco 3), como parte
do conteúdo mínimo exigido.
**Exceções:** nenhuma. É critério de aceite de negócio explícito.
**Comportamento na borda:** nenhuma — RN07 de `vision.md` é direta.
**Rastreamento:** referencia RN01/RN07 de `vision.md`.

## RN-010 — Entrada em produção solicita novo épico para os temas restantes, sem compromisso de construí-los

**Descrição:** quando esta entrega entrar em produção, um novo épico deve ser
solicitado para reavaliar os temas hoje fora de escopo. Esse novo épico está
sujeito à mesma diligência e aprovação desta entrega — não há compromisso
prévio de construir todos os temas restantes.
**Contexto:** aplica-se à transição desta entrega para produção; é o gatilho
que fecha o RN-001 sem impedir expansão futura por evidência.
**Exceções:** nenhuma.
**Comportamento na borda:** o Bloco 3 reforça que "o novo épico não nasce
pré-aprovado e não assume compromisso com todos os temas" — mesmo a
solicitação do épico não implica aprovação de conteúdo.
**Rastreamento:** referencia RN09/RN10 de `vision.md`; histórico, resposta do
dono, item 8.
