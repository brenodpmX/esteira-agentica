# Requisitos Não-Funcionais — Circuit-break de agente

Status: approved · Owner: requirements · Updated: 2026-08-24
Inputs: `doc/product/circuit-break-de-agente/analise-negocio.md` (indicadores
de retorno, riscos), `doc/requirements/circuit-break-de-agente/functional-requirements.md`,
`doc/requirements/circuit-break-de-agente/business-rules.md`

Nenhum valor numérico de limite (`N`) ou janela (`T`) é definido aqui: o dono
decidiu explicitamente não fixar um padrão (histórico, 22/08/2026) — esses
valores são de configuração do operador, não requisito de qualidade. Os NFRs
abaixo tratam de propriedades do próprio mecanismo de contenção, mensuráveis
independentemente do valor configurado.

| ID | Atributo | Requisito (mensurável) | Como medir |
|----|----------|------------------------|-----------|
| NFR-001 | Confiabilidade / Precisão da contagem | Zero execuções entregues ao agente além do limite `N` configurado, em qualquer contexto `(board, coluna, issue)`, para qualquer valor de `N` e `T` configurados. | Reproduzir o cenário de referência (issue #1: pelo menos 32 ciclos repetidos sem avanço) com política ativa e contar execuções entregues após o limite — meta zero. Indicador primário 1 da análise de negócio. |
| NFR-002 | Confiabilidade / Isolamento de bloqueio | 100% dos cenários de aceite (critério 8) mantêm outras issues elegíveis avançando no mesmo ciclo em que uma issue está bloqueada, em qualquer board configurado. | Cenário com ao menos uma issue bloqueada e uma issue elegível em outro contexto/board; verificar que a segunda é processada sem espera pela primeira. Indicador primário 4. |
| NFR-003 | Observabilidade / Completude da sinalização | 100% dos bloqueios produzem `need_human` e um comentário contendo, no mínimo, motivo, issue, board, coluna, limite e janela — sem exigir acesso a `snapshot.json`, `changeQueue.json` ou outro estado interno protegido para diagnosticar. | Auditar cada bloqueio ocorrido em ambiente de teste e checklist dos 5 dados mínimos presentes no comentário. Indicador primário 3. |
| NFR-004 | Corretude temporal / Precisão da janela | A decisão de bloqueio deve refletir exatamente as ocorrências com idade menor que `T` no instante da avaliação — nenhuma ocorrência com idade `>= T` deve ser contada, e nenhuma ocorrência com idade `< T` deve ser descartada. | Testes com ocorrências cronometradas nas bordas da janela (idade `T - 1`, `T`, `T + 1`, em unidade compatível com a resolução de `T`) e verificação do total considerado na decisão. |
| NFR-005 | Recuperabilidade / Retomada sem bloqueio residual | 100% das issues liberadas pelo operador (remoção de `need_human` após bloqueio) recebem a franquia completa de `N` execuções, sem sofrer um novo bloqueio imediato causado por ocorrências da janela anterior ao reinício da contagem. | Cenário: bloquear, remover `need_human`, executar até `N - 1` novas ocorrências e confirmar que nenhuma delas é rejeitada por resíduo da contagem anterior. Indicador primário 5. |
| NFR-006 | Compatibilidade / Não regressão sem configuração | Zero bloqueios por este mecanismo em qualquer instância sem a política de circuit-break configurada, incluindo instâncias que já usam `boards.rerun_cooldown`. | Rodar a suíte de regressão existente (cooldown, keep_task, auto-advance) sem a política configurada e confirmar ausência de bloqueios novos e ausência de alteração no comportamento hoje coberto por testes. Indicador primário 6. |
| NFR-007 | Desempenho | A verificação de limite (RF-003) e o registro de ocorrência (RF-001) não devem introduzir latência perceptível na seleção de tarefas (`keep_task`) — o custo adicional deve ser da mesma ordem de grandeza da checagem de cooldown já existente (operação em memória/arquivo local, sem chamada de rede ao board). | Comparar tempo de execução de `keep_task` com e sem a política configurada, sob a mesma carga de issues; a diferença não deve depender de chamada de API externa. |
| NFR-008 | Escalabilidade | A contagem por contexto deve permanecer correta e não degradar com o crescimento do número de boards, colunas ou issues configurados na instância — consistente com o isolamento por item já exigido em `doc/requirements/confiabilidade-parent-recursivo/non-functional-requirements.md` (seção Escalabilidade). | Cenário com múltiplos boards/colunas ativos simultaneamente, cada um com seu próprio contexto de contagem, e verificação de que a decisão de bloqueio de um contexto não é influenciada pelo volume de outros contextos. |

## Fora de escopo destes NFRs

Métricas de tokens, custo monetário e duração de execução não são
mensuráveis nesta etapa por falta de telemetria consolidada (dependem do
épico #176) — a análise de negócio já registra essa lacuna como indicador de
acompanhamento, não como indicador primário exigível no baseline atual.
Limites diferenciados por board/coluna/agente, dashboard e SLA de resposta
humana permanecem fora de escopo, conforme a análise de negócio.
