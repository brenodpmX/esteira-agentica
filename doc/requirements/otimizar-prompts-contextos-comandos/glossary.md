# Glossário — Otimizar prompts, contextos e comandos

Status: approved · Owner: requirements · Updated: 2026-08-25

> Criado porque o histórico do épico já registrou uma ambiguidade real: em
> 23/08/2026 a análise de negócio foi lida como se o "manual `@---`" fosse a
> maior parte do bloco `## Prompt` do log, quando na verdade ele é um trecho
> *dentro* do prompt dinâmico — distinto do bloco `## Parâmetros` e do bloco
> `## Chat` do mesmo arquivo de log. Este glossário fixa os termos para que
> UX, arquitetura e quebra em stories leiam o mesmo significado.

| Termo | Definição | Sinônimos / Evitar |
|-------|-----------|--------------------|
| Prompt dinâmico | String única retornada por `build_prompt()` (`src/core/agent.py`), montada a cada execução a partir da task corrente (issue, coluna, board, flow). É o texto de entrada enviado ao adapter junto com o contexto do operador. | "prompt" (ambíguo sem qualificador); evitar confundir com "arquivo de log" |
| Contexto persistente / contexto do sistema | Conteúdo gerado por `generate_context()` (`src/core/context_generator.py`) a partir do `pipe.yml`, materializado em `.pipe/CONTEXT.md` e `.kiro/agents/pipe_context.json`. É injetado pelo adapter via mecanismo próprio (ex.: `--agent pipe_context` no kiro-cli), não concatenado ao prompt dinâmico. | "CONTEXT.md" isoladamente (há dois arquivos: Markdown e JSON do agente); "contexto" sem qualificador |
| Contexto do operador | Conteúdo de `contexts/<plataforma>/<agente>.md`, escrito e mantido pelo dono do produto/operador da esteira. Fora do escopo deste épico definir seu conteúdo. | "contexto" sem qualificador |
| Total sempre carregado | Soma do prompt dinâmico + contexto persistente (contexto do sistema) em uma execução — a métrica usada nos gates de sucesso 1 e 2 da análise de negócio. Não inclui o contexto do operador, cujo conteúdo não é escopo deste épico. | "contexto total" isolado sem explicitar os dois componentes somados |
| Manual de anotações (`@---`) | Texto fixo retornado por `annotations_doc()` (`src/core/commands.py`, constante `ANNOTATIONS_DOC`), hoje sempre concatenado ao final do prompt dinâmico por `build_prompt()`. Documenta a sintaxe e os comandos do bloco `@---` do body da issue. 281 palavras no benchmark de referência. | "manual de comandos" (usar completo: "manual de anotações `@---`"); não confundir com o bloco `## Chat` do log |
| Bloco `@---` | Seção final do body de uma issue (`-body.md`), separada do conteúdo real por uma linha exatamente `@---`, contendo os comandos (`/parent`, `/labels` etc.) que a esteira aplica no board. É dado da issue, gerado/consumido pelo agente — não confundir com o *manual* que o documenta. | "comandos" isolado; "anotações" isolado |
| Log de execução | Arquivo `logs/<issue_id>/<timestamp>.md`, com três blocos: `## Parâmetros` (metadados), `## Prompt` (o prompt dinâmico enviado, incluindo o contexto do operador quando concatenado pelo adapter) e `## Chat` (diálogo capturado da execução). | "prompt" sozinho para se referir ao arquivo inteiro |
| Adapter | Implementação de `AgentPort` (`src/core/agent.py`) para uma ferramenta de agente específica — hoje só `KiroCliAgent` (`src/adapters/kiro_cli_agent.py`). Cada adapter tem seu próprio mecanismo de injeção de contexto e prova de carregamento. | "agente" (ver "agente configurado" abaixo, termo diferente) |
| Agente configurado | Entrada em `agents.<plataforma>.<id>` do `pipe.yml` (ex.: `dev`), com `name` e `model`. Uma coluna referencia um agente configurado via `agent` ou `agent-hub`; o agente configurado é executado por um adapter. | "adapter" (ver acima, termo diferente) |
| Instrução obrigatória | Instrução que deve estar presente e carregada em toda execução, independentemente da tarefa: guardrails de `PROTECTED_PATHS`, regras de workdir/branch, e qualquer regra que a etapa de arquitetura decida manter na camada sempre carregada. Contrasta com "referência sob demanda". | "regra fixa" |
| Referência sob demanda | Conteúdo de referência (ex.: manual de anotações completo) disponibilizado para o agente sem ser concatenado em toda execução — acessível quando a tarefa realmente o exige. O mecanismo concreto (arquivo separado, seção condicional, etc.) é decisão de arquitetura. | "conteúdo lazy"; "documentação externa" |
| Prova de carregamento | Evidência verificável de que uma instrução obrigatória foi de fato composta e entregue ao adapter antes da execução (ver RF-004 e RN-004). Não é evidência de que o modelo obedeceu à instrução — apenas de que ela chegou ao adapter. | "confirmação de leitura pelo modelo" (fora do que é verificável) |
| Cenário de referência | Uma das combinações fixas de `gitevents` × presença de `change` × presença de `agent-hub` usadas no benchmark antes/depois (ver RF-006). Termo do benchmark, não da execução real de uma issue. | "caso de teste" isolado (cenário é o dado de entrada; caso de teste é o RF-006 completo) |
