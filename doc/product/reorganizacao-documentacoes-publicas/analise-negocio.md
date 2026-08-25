# Análise de negócio — Reorganização das documentações públicas

**Épico:** #202
**Data da diligência:** 25/08/2026
**Status:** diligência concluída; apto à aprovação de negócio

Esta página preserva o ponto de entrada citado nas rodadas da entrevista. A
documentação vigente está organizada conforme os modelos de negócio:

- [Visão](vision.md): decisão recomendada, resultado, público, retorno, métricas,
  políticas e limites;
- [Cenário do problema](problem-space.md): fatos, hipóteses, mercado,
  alternativas, custo de não fazer e validação;
- [Blocos de entrega](epicos.md): ordem relativa de esforço, dependências,
  critérios de conclusão e corte para o prazo de agosto.

## Decisão recomendada

**Aprovar a reorganização incremental**, controlada por baseline, pós-teste e
capacidade de manutenção. O dono confirmou público e tarefas, disponibilizou
potenciais participantes, definiu a fronteira público/interno, estabeleceu
comunicação no mesmo dia da versão, nomeou o agente reviewer como aprovador,
aceitou o fallback e postergou o épico #93.

A evidência do repositório confirma fragmentação e inconsistência de governança,
mas não permite prometer ROI financeiro: são 51 arquivos Markdown públicos,
README com 733 linhas/41 títulos, canais paralelos de mudanças e apenas uma tag
Git visível apesar de versões posteriores no changelog. O relato de dificuldade
continua sendo amostra única até os testes.

## Condições de investimento

- baseline e pós-teste com pelo menos cinco representantes;
- auditoria de dez mudanças candidatas;
- pelo menos 4/5 concluindo as três tarefas sem ajuda ou consulta ao código;
- melhora de sucesso e tempo, nenhum erro crítico e 100% das versões elegíveis
  comunicadas no mesmo dia;
- fonte canônica e responsável para conteúdo público priorizado.

A capacidade até 31/08 não foi quantificada. Por isso, a aprovação não equivale
a compromisso de reorganização completa: se não houver fricção material ou
capacidade de manutenção, limitar a entrega ao README/material da apresentação,
correções críticas e processo mínimo de comunicação de versões.
