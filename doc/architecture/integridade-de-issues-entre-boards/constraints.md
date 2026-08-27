# Constraints — Integridade de issues entre boards

Status: draft
Owner: architecture
Last updated: 2026-08-27

## Inputs
- `doc/architecture/integridade-de-issues-entre-boards/overview.md`
- `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`
- `doc/requirements/integridade-de-issues-entre-boards/non-functional-requirements.md`
- `doc/incidente/sub-issues-propagadas/ticket.md`
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md`
- `CONTEXT.md`, `README.md`
- `src/core/sync.py`, `src/core/board.py`, `src/core/change_queue.py`, `src/core/snapshot.py`, `src/__main__.py`, `src/adapters/github_board.py`

## Restrições técnicas

- Preservar a arquitetura hexagonal: política no core; GraphQL/REST somente no
  adapter; nenhum import de adapter pelo domínio.
- Preservar o processo único e o loop sequencial. Não adicionar banco, broker,
  webhook obrigatório, worker ou serviço de coordenação.
- Operações de GitHub Projects V2 (`projectItems`, campos e
  `deleteProjectV2Item`) devem usar GraphQL. REST permanece reservado às APIs
  tradicionais de issues e sub-issues.
- `Status` preenchido ou vazio não prova intenção. A classificação deve ser a
  mesma para itens com e sem coluna.
- `parent` isolado não prova propagação. Remoção automática exige issue já
  confirmada em outro board configurado e ausência de autorização explícita
  para o board atual.
- Reconciliação remove somente o `ProjectV2Item`; nunca altera a relação
  pai/filho, dependências, body, labels comuns ou participação de origem.
- Participação adicional é autorizada pela label reservada
  `board-intent-<board_id>`. O board deve existir no `pipe.yml`; curingas não são
  permitidos.
- A label é autorização, não cache. O snapshot pode guardar o resultado da
  classificação, mas não pode inventar autorização multi-board.
- `keep_task` não pode chamar rede. O gate deve usar intenção previamente
  confirmada no snapshot.
- Toda entrada sem intenção confirmada deve falhar fechada, sem auto-advance,
  sem seleção e sem execução de agente.
- Falha transitória de classificação ou remoção não pode consumir o evento nem
  virar dead-letter apenas por atingir `sync.max_attempts`; deve ser retentada
  com atraso e sem bloquear outros itens.
- A solução deve funcionar para qualquer board configurado, sem listas de pares
  Epics→Stories ou Stories→Tasks.
- A contingência deve ser relida do `pipe.yml` sem restart e afetar somente
  novos vínculos entre boards distintos.
- Somente o core, por `Snapshot`/`ChangeQueue`, pode ler ou escrever estado
  interno. Agentes, adapters e ferramentas externas não acessam diretamente os
  arquivos protegidos.
- Erros do adapter devem ser tipados/estruturados. Não classificar falhas por
  substring de body de issue ou resposta GraphQL.
- Logs não podem conter token, chave SSH, body completo da issue ou conteúdo de
  arquivos protegidos.

## Premissas

- GitHub Projects V2 pode propagar uma sub-issue de forma assíncrona para o
  Project do pai e pode atribuir `Status` antes da observação pela esteira.
- Todos os boards relevantes compartilham o mesmo repositório GitHub e estão
  configurados no mesmo `pipe.yml`.
- O full sync de startup ocorre antes do primeiro `keep_task`, permitindo migrar
  snapshots legados com segurança.
- O processamento da fila ocorre antes da seleção de tarefa no ciclo principal.
- Uma issue legítima observada em apenas um board configurado pode ser assumida
  como participação de origem, conforme a exceção da RN-B01.
- Duplicidades legadas sem autorização são ambíguas. Bloqueá-las é seguro;
  escolher automaticamente qual board remover não é.
- Não existe caso multi-board real ativo na data desta decisão; a label fornece
  compatibilidade futura sem impor fluxo operacional agora.
- Os logs JSON persistidos são suficientes para a janela inicial de validação;
  dashboards externos podem ser adicionados depois sem alterar o core.
- `PIPE_ENVIRONMENT` identifica o ambiente e o checkout/imagem disponibiliza o
  commit efetivamente executado.

## Requisitos não-funcionais

| Atributo | Requisito |
|----------|----------|
| Integridade | Zero despacho quando `participation_intent` não for `origin` ou `authorized`. |
| Integridade | 100% das propagadas removidas antes de materialização executável, inclusive com `Status`. |
| Preservação | Zero alteração de relação pai/filho e zero remoção de participação explicitamente autorizada. |
| Disponibilidade | Um item pendente é rotacionado e não impede issues do mesmo ou de outros boards. |
| Retentativa | Pendências são reavaliadas em ciclos posteriores com `next_attempt_at`, sem loop apertado. |
| Performance | No máximo uma consulta de participações e uma remoção por candidata em cada tentativa; nenhuma varredura completa adicional. |
| Escalabilidade | Complexidade por candidata proporcional às participações da própria issue, não ao produto cartesiano de boards/issues. |
| Determinismo | Mesmo conjunto de boards, labels e intenções confirmadas produz a mesma classificação, independentemente da ordem. |
| Observabilidade | Cada classificação, reconciliação, falha, bloqueio e remoção externa registra issue, boards e timestamps correlacionáveis. |
| Rollout | Startup registra versão, commit, ambiente e instante; ausência de qualquer campo impede iniciar a janela de validação. |
| Segurança | Labels inválidas não concedem acesso; falha/ambiguidade bloqueia em vez de autorizar. |
| Compatibilidade | Snapshots e itens de fila anteriores continuam desserializáveis; migração ocorre antes do despacho. |
| Operabilidade | Contingência muda por configuração, sem deploy/restart, e deixa evidência auditável. |
| Testabilidade | Política é função pura e adapter é validado por contrato; ao menos um teste gated usa GraphQL real. |

## Limites e riscos aceitos

- A consulta imediata após criar o vínculo pode não observar propagação
  assíncrona; por isso não é garantia isolada. O fluxo down e o gate são
  obrigatórios.
- A label de autorização é global à issue, mas contém o board alvo e, portanto,
  representa de forma inequívoca cada participação permitida. Um campo custom
  por Project seria mais local, porém aumentaria configuração e dependência da
  API sem benefício atual.
- A migração não limpa resíduos históricos ambíguos. Ela os torna não
  executáveis e registra o conflito para o procedimento manual já fora de
  escopo.
- Logs locais fornecem evidência, não alta disponibilidade de telemetria. Perda
  do volume de logs impede comprovar a janela e deve reiniciar a medição.
- A classificação cobre apenas boards presentes no `pipe.yml`; projects externos
  não configurados são preservados e sinalizados, nunca removidos por inferência.
