# Constraints — Circuit-break de agente

Status: draft
Owner: architecture
Last updated: 2026-08-26

## Inputs
- `doc/architecture/circuit-break-de-agente/overview.md`
- `doc/product/circuit-break-de-agente/analise-negocio.md`
- `doc/requirements/circuit-break-de-agente/functional-requirements.md`
- `doc/requirements/circuit-break-de-agente/business-rules.md`
- `doc/requirements/circuit-break-de-agente/non-functional-requirements.md`
- `doc/ux/circuit-break-de-agente/navigation-flow.md` e protótipos em draft
- `README.md` e `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md`

## Restrições técnicas
- Preservar a arquitetura hexagonal: regra de limite, janela e reset pertence ao core; GitHub é acessado somente por `BoardPort`.
- Preservar o loop sequencial e a instância única já protegida por `InstanceLock`. Não adicionar banco, broker, daemon, thread ou lock distribuído.
- Fazer check-and-record em uma operação lógica única, persistindo a ocorrência antes de `keep_task` entregar a tarefa. Uma falha de persistência nunca pode iniciar o agente.
- Usar janela deslizante exata: conta somente timestamp com idade estritamente menor que `T`; idade `>= T` expira.
- Contar a decisão de entrega independentemente do resultado posterior de `call_agent`. Não inspecionar exit code, chat, commit, PR ou mudança de coluna para decidir se conta.
- Isolar o contexto por `(board, coluna, issue)`. Toda mudança de coluna detectada, local ou remota, descarta o contexto ativo anterior; revisitar a coluna começa vazio.
- Persistir contagem mesmo com política ausente. Ausência desativa apenas bloqueio e sinalização; não cria limite ou janela padrão.
- Usar arquivo JSON versionado em `.pipe/agentCircuitBreak.json`, com escrita por temporário no mesmo diretório, `fsync` e `os.replace`. O arquivo não pode ser editado por agentes ou operadores.
- Adicionar o arquivo a `PROTECTED_PATHS`, às instruções de contexto gerado e à cobertura de integridade aplicável. Prompt, comentário e logs nunca expõem seu conteúdo.
- Tratar estado ilegível/corrompido como erro de integridade explícito; não assumir contador vazio silenciosamente. Escrita que falha nega a admissão daquela issue.
- Persistir o evento de bloqueio e limpar a franquia antes de chamadas ao board. Em `keep_task`, reconciliar `trip` pendente antes de `_is_blocked`; a nova admissão ocorre somente depois dos filtros/cooldown. Enquanto label/comentário estiverem pendentes, a execução permanece negada e outras issues continuam sendo avaliadas.
- Reutilizar `Board.add_label`, `Board.list_comments` e `Board.add_comment`. Como `BoardPort.add_label` possui default no-op, política ativa exige adapter que sobrescreva explicitamente essa operação; ausência da capacidade deve falhar no startup, nunca simular sinalização bem-sucedida. Comentário deve carregar marcador técnico oculto por `event_id` para retry idempotente.
- Produzir exatamente um comentário por evento de bloqueio. Novo bloqueio após liberação cria novo `event_id` e nova evidência; ciclos enquanto `need_human` está ativo não criam comentários.
- O comentário contém no mínimo motivo, issue, board, coluna, limite e janela. Campos adicionais propostos pela UX não fazem parte do contrato até validação.
- Não mover a issue de coluna como efeito do bloqueio. `need_human` é o mecanismo de parada e sua remoção é o gesto de retomada.
- Não alterar semântica, chave ou cache de `boards.rerun_cooldown`; os mecanismos devem compor na ordem dos gates atuais.
- Configuração parcial ou inválida deve falhar no startup antes de lock/startup/sync; configuração ausente é válida e silenciosa. O bloco global deve ficar fora de `boards`: `_validate_boards`, `Board.board_ids` e `get_board_ids` tratam todo valor `dict` nesse mapa como um board.
- `bool` não é aceito como inteiro para limite ou janela.
- Usar relógio injetável nos testes e epoch UTC no estado. A sincronização correta do relógio do host é premissa; correção de clock skew distribuído está fora de escopo.
- O escopo não inclui política por board/coluna/agente, half-open automático, dashboard, diagnóstico de causa, SLA, tokens/custo ou loops de sincronização.

## Premissas
- O processo que lê e escreve o estado detém `InstanceLock`; não há escritor concorrente legítimo no mesmo diretório `.pipe`.
- O filesystem local/volume suporta rename atômico no mesmo diretório.
- O sync remoto ocorre antes de nova seleção de tarefa e reconcilia a label `need_human` para o body local.
- `BoardPort.add_label` é idempotente; comentários não são e por isso exigem marcador + `list_comments`.
- O operador remove `need_human` somente depois de diagnosticar/corrigir ou redirecionar a issue. A franquia já foi zerada no instante do bloqueio.
- Movimentos só podem reiniciar contexto quando observados pelo sistema; transições remotas que ocorram integralmente entre duas leituras e deixem a issue na coluna original não são observáveis pela API atual.
- Enquanto não existe política, ocorrências do contexto ativo não podem ser podadas por tempo sem inventar uma janela. Esse crescimento linear é aceito nesta versão e termina em mudança de coluna, remoção da issue ou ativação de uma janela.

## Requisitos não-funcionais
| Atributo | Requisito |
|----------|----------|
| Confiabilidade | Zero chamada de agente acima de N no contexto/janela; persistência e sinalização falham fechadas para a issue afetada. |
| Isolamento | Um bloqueio ou falha de sinalização não impede `keep_task` de avaliar outras issues; exceções são capturadas por contexto. |
| Corretude temporal | Timestamps com idade `< T` contam; `>= T` não contam, com relógio controlável em teste. |
| Recuperabilidade | Crash/restart não apaga ocorrências nem abre o gate; retry completa label/comentário sem duplicação. |
| Observabilidade | 100% dos bloqueios têm warning estruturado, `need_human` e comentário mínimo; pendências de sinalização têm erro acionável. |
| Compatibilidade | Sem `agent_circuit_break`, nenhum bloqueio novo ocorre e cooldown/auto-advance mantêm comportamento vigente. |
| Performance | Admissão normal faz somente leitura/poda/escrita local; nenhuma API externa. Custo por avaliação é O(k), sendo k as ocorrências do contexto. |
| Escalabilidade | Estado mantém um contexto ativo por `(board, issue)` e remove contextos órfãos após full sync; não varre histórico de outros contextos para admitir uma issue. |
| Segurança | Estado interno e marcadores não contêm body, prompt, chat, token ou credencial; permissões seguem o diretório `.pipe`. |
| Operabilidade | Configuração usa segundos, alinhada a `sleep` e `rerun_cooldown`, e não possui valores default de negócio. |

## Riscos e guardrails de implementação
| Risco | Guardrail |
|------|-----------|
| Crash entre persistir bloqueio e aplicar label | `trip` persistido mantém DENY e é reconciliado no ciclo seguinte. |
| Label aplicada e comentário falha | Flags por etapa + marcador oculto permitem retomar somente o passo faltante. |
| Comentário publicado e processo cai antes do ack local | `list_comments` encontra o `event_id` e não duplica. |
| Estado antigo retomado ao voltar à mesma coluna | Hook nos pontos de transição e comparação defensiva de `column` em `admit`. |
| Reinício usado para contornar limite | Contagem e `trip` são persistentes e carregados no startup. |
| Arquivo cresce sem política | Um contexto ativo por issue; limpeza em mudança/remoção e poda quando T existir; documentar métrica de tamanho. |
| Falha externa bloqueia o loop global | Captura por issue, manutenção de `trip` e continuação da varredura. |
| Configuração com typo parece ativa | Validação estrita do bloco raiz `agent_circuit_break` e rejeição de campo desconhecido. |
