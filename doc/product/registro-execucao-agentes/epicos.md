# Épicos — Registro de execução de agentes

Status: draft
Owner: product
Last updated: 2026-08-25

## Inputs
- `doc/product/registro-execucao-agentes/vision.md`
- `doc/product/registro-execucao-agentes/problem-space.md`
- Issue #176 e histórico de entrevista com o dono.

## Épico: Registro confiável de cada execução

**Objetivo:** preservar uma evidência consultável de cada entrega de issue a agente, suficiente para medir volume, duração, resultado, avanço e consumo sem depender da vida útil do log detalhado.

**Escopo:** identidade da execução e da issue; início, fim e duração; board e etapa no momento da execução; plataforma, agente e modelo; resultado; indicação separada de avanço; consumo com valor, unidade, fonte e disponibilidade; referência ao log detalhado. Resultados mínimos: concluída, falha terminal, timeout, interrompida e desconhecida.

**Fora de escopo:** duplicar prompt/chat; estimar uso ausente; converter créditos ou tokens em moeda sem fonte auditável; escolher armazenamento, protocolo ou arquitetura.

## Épico: Consolidação pela linhagem histórica

**Objetivo:** revelar o esforço ponta a ponta de uma issue raiz, incluindo todo descendente histórico conhecido e as repetições sem avanço.

**Escopo:** raiz e descendentes já vinculados, inclusive posteriormente removidos; agregação de quantidade, duração e consumo por unidade; segmentação por board, etapa, plataforma, agente, modelo, resultado e avanço; prevenção de ciclo e dupla contagem; sinalização de descendentes sem registro; regra aceita de repetição sem avanço.

**Fora de escopo:** inferir relações nunca observadas; ocultar lacunas; definir sucesso de produto apenas pelo término técnico da execução; escolher estrutura de dados ou algoritmo.

## Épico: Consulta, exportação e baseline operacional

**Objetivo:** permitir que operação, SRE e monitoramento respondam em até 5 minutos às perguntas sobre uma execução ou entrega completa e publiquem o primeiro baseline de gestão.

**Escopo:** consulta e exportação utilizáveis sem leitura de logs individuais; totais e cortes operacionais; distinção entre zero e consumo indisponível; aferição da cobertura; publicação em 30 dias do baseline de falhas terminais, repetições sem avanço, cobertura de consumo e consumo/duração por etapa.

**Fora de escopo:** dashboard, alertas, avaliação automática de qualidade, recomendação automática de agente/modelo e ROI monetário antes de baseline e regra de conversão.

## Ordem de entrega
1. Registro confiável de cada execução.
2. Consolidação pela linhagem histórica.
3. Consulta, exportação e baseline operacional.

A ordem decorre das dependências de negócio: não há agregado confiável sem registros confiáveis, e não há consulta completa da raiz sem linhagem. Dashboard será tratado em novo épico disparado após o merge desta entrega na `main`, conforme decisão do dono.

## Condições pendentes para aprovação
- TTL exato e ciclo de vida do registro.
- Papéis autorizados a consultar, exportar e excluir.
- Regra de exclusão quando a issue é removida.
- Meta/OKR ou objetivo organizacional, prazo e responsável pela aferição.

Enquanto essas condições não forem aceitas, os blocos permanecem em `draft` e não devem ser derivados em stories.
