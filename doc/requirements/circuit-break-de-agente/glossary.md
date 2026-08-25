# Glossário — Circuit-break de agente

Status: approved · Owner: requirements · Updated: 2026-08-24
Inputs: `doc/product/circuit-break-de-agente/analise-negocio.md`, README.md
(seções "Seleção de Tarefas", "Cooldown de reexecução")

| Termo | Definição | Sinônimos / Evitar |
|-------|-----------|--------------------|
| Execução | Uma entrega da issue ao agente iniciada por `call_agent`, contada no instante em que é iniciada, independentemente do resultado (erro ou sucesso técnico). | "tentativa", "chamada ao agente". Evitar "run" isolado sem contexto. |
| Contexto de contagem | A combinação `(board, coluna, issue)` sobre a qual as execuções são contadas. Uma mudança de coluna cria um contexto novo, sem herdar a contagem do contexto anterior. | Evitar "issue" isolada — a coluna e o board fazem parte da identidade. |
| Janela | Intervalo de tempo configurado (`T`) dentro do qual execuções contam para o limite. Ocorrências mais antigas que a janela deixam de contar. | "período", "janela deslizante". |
| Limite | Quantidade máxima configurada (`N`) de execuções permitidas em um contexto de contagem dentro da janela `T`. | "máximo", "teto". Evitar "cota" (usado para orçamento de tokens no #177). |
| Bloqueio | Ato de impedir que uma nova execução seja entregue ao agente porque o contexto já atingiu o limite dentro da janela. | "circuit aberto", "interrupção". Evitar "cooldown" (mecanismo distinto, ver abaixo). |
| Franquia | Quantidade de execuções disponíveis a um contexto antes do próximo bloqueio. Uma franquia completa equivale a `N` execuções. É reiniciada (zerada e recomeçada) no instante do bloqueio, dando à issue uma nova franquia completa após a liberação humana. | "cota de tentativas". |
| Retomada | Ação humana de corrigir ou redirecionar a issue e remover `need_human`, liberando o contexto para receber uma nova franquia completa. | "liberação", "desbloqueio". |
| `need_human` | Marcação (label) que sinaliza necessidade de intervenção humana. Já existe na esteira para uso por agentes (comando `/need_human` no body); este épico introduz sua aplicação também pelo núcleo da esteira, sem intervenção do agente. | "gate humano". |
| Cooldown de reexecução (`boards.rerun_cooldown`) | Mecanismo já existente que apenas espaça novas execuções da mesma issue/board/coluna por um intervalo mínimo, sem impor teto de repetições. É complementar e distinto do circuit-break: o cooldown atrasa: o circuit-break contém. | Não confundir com "limite" ou "janela" deste épico. |
| Execução excedente | Uma execução que seria a `N+1`-ésima (ou posterior) dentro da janela `T` do mesmo contexto, e que portanto não deve ser iniciada. | "execução acima do limite". |
| Política de circuit-break | Configuração opcional, geral para a instância (não segmentada por board, coluna ou agente nesta versão), composta por limite `N` e janela `T`. Ausência de configuração equivale a política inativa. | "controle de circuit-break". |
