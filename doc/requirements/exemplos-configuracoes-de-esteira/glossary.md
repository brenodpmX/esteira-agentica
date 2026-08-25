# Glossário — Exemplo de configurações de Esteira

Status: draft · Owner: requirements · Updated: 2026-08-24

## Inputs
- Issue #93 (body e histórico)
- `doc/product/exemplos-configuracoes-de-esteira/vision.md`
- `doc/product/exemplos-configuracoes-de-esteira/epicos.md`
- `README.md` (estrutura vigente de `contexts/<plataforma>/<agente>.md` e `pipe.yml`)

| Termo | Definição | Sinônimos / Evitar |
|-------|-----------|--------------------|
| Exemplo | Pacote de configuração e documentação, hipotético e completo, que demonstra um ciclo de uso da Esteira do início (configuração) ao fim (resultado observável). Não é código de produção nem template genérico sem cenário. | "Template" isolado (evitar: um exemplo inclui cenário e narrativa, não apenas arquivos vazios) |
| Exemplo Minimalista | O exemplo com o menor `pipe.yml` e menor conjunto de contextos capazes de produzir um resultado demonstrável de ponta a ponta (da issue criada ao resultado no board). Bloco 1 de `epicos.md`. | "Hello world" (evitar como termo formal; usar "Minimalista") |
| Exemplo Referência hipotética | Exemplo baseado em um cenário plausível de empresa que desenvolve software com apoio de IA — sem copiar configuração, dados, nomes ou identificadores de uma empresa real. Mais completo que o Minimalista (mais boards/colunas/agentes), mas ainda dentro do escopo de vitrine. Bloco 2 de `epicos.md`. | "Exemplo Intermediário" (termo usado no histórico da entrevista antes da decisão do dono; **evitar** — o escopo aprovado usa "Referência hipotética") |
| Vitrine | Conjunto dos exemplos publicados com o objetivo de demonstrar o produto a um prospect, sem compromisso de conversão ou meta numérica nesta entrega. | "Showcase", "produtos na vitrine" (linguagem do dono, mantida como sinônimo) |
| Prospect | Pessoa ou empresa externa que recebe a apresentação da vitrine e manifesta interesse ou recusa. Nesta entrega, o prospect é uma empresa de tecnologia que desenvolve software próprio e inicia adoção de IA no desenvolvimento apoiado por IA. | "Cliente" (evitar — não há relação comercial formal nesta etapa) |
| Validação interna | Execução de cada exemplo por uma pessoa interna, usando somente a documentação destinada ao usuário final (sem atalhos de quem já conhece a implementação), com registro de resultado, fricções, tempo, versão, modelo, tokens e custo. Bloco 3 de `epicos.md`. | "Teste de aceitação", "homologação" (evitar — a issue e a visão usam especificamente "validação interna"; ver RN-003) |
| Cenário hipotético | Situação de uso plausível, mas fictícia: nenhum dado pessoal, credencial, segredo ou identificador real de pessoa ou empresa (RN03/RN04 de `vision.md`). | "Dados de exemplo" (evitar isoladamente — nem todo dado de exemplo é necessariamente hipotético/anonimizado; usar o termo completo) |
| Board (no domínio da Esteira) | Quadro de trabalho configurado em `pipe.yml` (`boards.<id>`), com colunas, agentes e regras de fluxo, mapeado para um GitHub Project. Cada exemplo desta entrega deve declarar ao menos um board plausível para seu cenário. | — |
| Contexto de agente | Arquivo em `contexts/<plataforma>/<agente>.md` com as instruções que o agente recebe ao ser executado numa coluna. Cada exemplo requer os contextos completos e preenchidos (não vazios) dos agentes que ele referencia (RN02 de `vision.md`). | — |
| Resultado demonstrável | Evidência observável e reproduzível de que o exemplo funciona: no mínimo, uma issue criada, processada pela esteira segundo a configuração do exemplo, e chegando a um estado final (ex.: coluna de destino, PR aberto, comentário do agente) sem intervenção manual fora do previsto no próprio exemplo. | "Funciona" (termo vago — sempre substituir pela descrição do resultado observável específico do exemplo) |
| Épico de expansão | Épico futuro, a ser solicitado somente quando esta entrega (Minimalista + Referência hipotética) entrar em produção, para reavaliar os demais temas hoje fora de escopo (Kanban, Scrum, Acadêmico, XGH, Gestão, RH, Atendimento). Sujeito a diligência e aprovação próprias (RN09/RN10 de `vision.md`) — não é compromisso desta entrega. | — |
