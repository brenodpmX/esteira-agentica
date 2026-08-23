# Épicos — Reorganização das documentações públicas

Status: blocos de entrega propostos; aguardando aprovação de negócio
Owner: product / responsáveis de conteúdo a confirmar
Last updated: 2026-08-22

## Inputs

- `doc/product/reorganizacao-documentacoes-publicas/vision.md`
- `doc/product/reorganizacao-documentacoes-publicas/problem-space.md`
- Issue #202 e entrevista do dono em 22/08/2026

Os itens abaixo são blocos de resultado e ordem de esforço, não stories nem
decisões de arquitetura.

## Ordem recomendada

| Ordem | Bloco | Esforço relativo | Razão |
|---|---|---:|---|
| 1 | Validar público, tarefas e baseline | Pequeno | Evita reorganização guiada por opinião |
| 2 | Porta de entrada e primeiro sucesso | Médio | Entrega valor para a apresentação e testa a hipótese principal |
| 3 | Inventário e fontes canônicas | Médio | Reduz duplicação e delimita público/interno |
| 4 | Comunicação e operação de releases | Médio | Resolve consistência e responsabilidade futuras |
| 5 | Validação final e manutenção | Pequeno/médio | Demonstra retorno e impede regressão |
| 6 | Expansão do acervo | Grande, posterior | Só se dados mostrarem demanda além das jornadas prioritárias |

## Épico: Validar público, tarefas e baseline

**Objetivo:** transformar o relato inicial em evidência de comportamento e
fixar a unidade de decisão.

**Escopo:**

- confirmar público primário e três trabalhos prioritários;
- recrutar ao menos cinco representantes;
- medir sucesso sem ajuda, tempo, abandono e dúvidas;
- auditar dez mudanças candidatas a comunicação pública e esforço editorial;
- registrar indicadores disponíveis e limitações.

**Definição de pronto:** baseline reproduzível, tarefas e participantes
registrados, regra preliminar de elegibilidade de release e decisão entre
prosseguir, limitar ao README ou recusar.

**Fora de escopo:** analytics novo, pesquisa ampla de marca ou desenho técnico.

## Épico: Porta de entrada e primeiro sucesso

**Objetivo:** permitir que o público primário entenda e experimente o produto sem
consultar o código ou pedir ajuda.

**Escopo:**

- proposta de valor, público, capacidades, limites e pré-requisitos;
- README como índice das jornadas prioritárias;
- caminho local testado do zero como primeira opção e container como alternativa
  suportada;
- configuração e exemplo necessários para a avaliação inicial;
- correção de contradições críticas encontradas no teste.

**Definição de pronto:** os três trabalhos são executáveis apenas com conteúdo
público, comandos foram testados em ambiente limpo e o pós-teste registra
sucesso e tempo comparáveis ao baseline.

**Fora de escopo:** escolher portal, gerador, hospedagem ou traduzir conteúdo.

## Épico: Inventário e fontes canônicas

**Objetivo:** reduzir ambiguidade e manutenção acidental sem reescrever conteúdo
que não participa das jornadas prioritárias.

**Escopo:**

- inventariar cada documento por público, trabalho, sensibilidade, estado,
  responsável e fonte canônica;
- definir destino para duplicações e conteúdo obsoleto;
- separar conteúdo público de memória de produto/engenharia por política de
  audiência, não apenas pelo caminho `doc/`;
- garantir navegação e indicar conteúdo substituído.

**Definição de pronto:** todo conteúdo em escopo tem público, finalidade,
responsável e fonte canônica; não há link público apontando inadvertidamente
para conteúdo classificado como interno.

**Fora de escopo:** uniformização total de documentos internos ou migração
tecnológica.

## Épico: Comunicação e operação de releases

**Objetivo:** tornar mudanças relevantes compreensíveis e publicáveis de forma
consistente.

**Escopo:**

- definir se o gatilho é merge elegível ou release versionada;
- considerar elegíveis versões com épico ou incidente de impacto público,
  conforme confirmação do dono;
- formato público centrado em benefício, impacto, compatibilidade, ação
  necessária, data e versão;
- manual interno com entradas, responsável, aprovação, prazo e definição de
  pronto;
- relação inequívoca entre changelog consolidado, notas detalhadas e materiais
  internos.

**Definição de pronto:** regra aplicada à amostra de dez mudanças sem ambiguidade
e 100% das versões elegíveis do piloto têm nota e checklist completos no prazo
acordado.

**Fora de escopo:** publicar cada commit, automatizar arquitetura de release ou
expor detalhes internos de incidentes.

## Épico: Validação final e manutenção

**Objetivo:** demonstrar retorno e sustentar a qualidade após a entrega.

**Escopo:**

- repetir com representantes as mesmas tarefas do baseline;
- comparar sucesso, tempo, dúvidas e erros;
- medir completude e prazo das comunicações elegíveis;
- definir responsável, gatilho de revisão e tratamento de obsolescência;
- registrar decisão de expandir, manter, corrigir ou interromper.

**Definição de pronto:** resultado antes/depois publicado, nenhum erro crítico no
caminho recomendado, responsáveis aceitos e decisão de continuidade baseada em
evidência.

**Fora de escopo:** declarar ganho financeiro sem dados ou expandir tipos/canais
por preferência.

## Sequenciamento e corte de prazo

O corte para 31/08 deve abranger, no máximo, baseline enxuto, porta de entrada,
primeiro sucesso e regra mínima de release. Inventário completo e expansão só
entram no mesmo prazo se a capacidade confirmada comportar. Caso contrário,
são posteriores; o prazo não justifica omitir teste, segurança ou responsável.

A issue #93 é o custo de oportunidade declarado. Se a capacidade disponível não
cobrir ao menos os dois primeiros blocos e a manutenção, a recomendação é
limitar a entrega ao README e ao material da apresentação, em vez de iniciar uma
reorganização ampla incompleta.
