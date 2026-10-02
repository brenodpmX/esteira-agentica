# Composição em camadas do prompt e do contexto (#308)

Documenta o contrato de composição em camadas do conteúdo entregue ao agente e
as novas chaves de configuração. Implementação: `src/core/composition.py`,
`src/core/agent.py` (`build_prompt`), `src/core/context_generator.py`,
`src/core/config.py` e `src/__main__.py` (`call_agent` /
`compose_execution_record`).

## Camadas

O conteúdo entregue ao agente é separado em quatro camadas por
responsabilidade, cada uma com **origem única** (RN-04):

| Camada | Responsabilidade | Origem | Sempre carregada? |
|--------|------------------|--------|-------------------|
| `politica_invariavel` | Guardrails/regras invariáveis (proteção de estado, manual `@---`, estrutura do `-body.md`, criação de issues, git flow) | steering `.kiro/steering/esteira.md` | sim |
| `contexto_projeto` | Metadados do projeto e papéis humanos | steering | sim |
| `workflow_etapa` | Objetivo/passos/git da etapa + transição | prompt dinâmico (`build_prompt`) | não |
| `dados_tarefa` | Título, caminhos dos arquivos, branch resolvido | prompt dinâmico | não |

As camadas 1 e 2 são SEMPRE carregadas (steering). As camadas 3 e 4 compõem o
prompt dinâmico, enxuto e específico da tarefa, sem repetir material invariável.

O inventário auditável vive em `composition.layer_inventory()`;
`composition.find_duplicated_rules()` prova que nenhuma regra aparece em mais de
uma camada sempre carregada (RN-04).

### Redução real (RN-08)

- O manual completo dos comandos `@---` deixou de ser embutido no prompt
  dinâmico (antes via `annotations_doc()`), passando a existir
  **exclusivamente** no steering. O prompt dinâmico não contém mais nenhum
  ponteiro ou menção ao manual `@---` — nem completo, nem sob demanda (#325).
- As regras de operação invariáveis do bloco de diretório foram condensadas no
  prompt (a política completa está no steering).
- O exemplo redundante de nome de branch foi removido do steering (o nome agora
  é resolvido pelo motor a partir do `branch_pattern`).

Resultado medido (fixture canônica, `create-merge`, caminhos normalizados):

- conteúdo **estático** do prompt dinâmico: **≥ 40% menor** (ratio ≈ 0,40);
- **total sempre carregado** (prompt + steering): **≥ 20% menor** (ratio ≈ 0,79).

A redução é líquida (o aumento de uma camada, se houver, é estritamente menor
que a redução da outra — RN-08).

## Referência sob demanda do manual `@---` (removida — #325)

A entrega #308 introduzira um ponteiro curto sob demanda ao manual `@---` no
prompt dinâmico (CA-8), com gate derivado do conjunto de comandos permitidos da
coluna (`composition.on_demand_references(col)`, chave `allowed-commands`). A
entrega #325 removeu esse ponteiro por completo: o prompt dinâmico não contém
mais nenhuma menção ao manual `@---`, em nenhuma condição. A constante
`REF_MANUAL_ARROBA` e as funções `allowed_commands`/`on_demand_references`
foram removidas de `src/core/composition.py`. O manual completo permanece,
inalterado, exclusivamente no steering (origem única).

## Resolução única do nome da branch (CA-10/CA-11/RN-05)

`composition.resolve_branch_name(branch_pattern, data)` resolve o nome **uma
única vez** por execução e é reutilizado idêntico em todos os blocos que o
citam (criação e merge/PR). Marcador não resolvível com os dados da tarefa
levanta `ConfigError` nomeando o marcador faltante — **nenhum** nome
parcialmente resolvido é emitido.

Precedência em `build_prompt`: a anotação `branch:` já gravada vence; caso
contrário, resolve-se do `branch_pattern` do flow quando a etapa pode criar
branch.

## Contrato de instruções obrigatórias (CA-4/CA-5)

Antes de acionar o agente, `call_agent` verifica o contexto obrigatório
(steering) via `composition.check_required_instructions(STEERING_FILE)` e emite
o registro de medição. Se o contexto estiver ausente/vazio, a composição é
**recusada (fail-closed)**: o agente **não** é acionado e a falha é sinalizada
com `instrucoes_obrigatorias_carregadas: false` + motivo.

## Registro de medição por execução (contrato observável)

`composition.compose_measurement(...)` (função pura, não aciona o `kiro-cli`)
emite, por execução, antes do acionamento:

```json
{
  "execucao": "<id da issue>",
  "adapter": "<nome do adapter>",
  "prompt_dinamico": { "caracteres": 0, "palavras": 0, "linhas": 0 },
  "contexto_sempre_carregado": { "caracteres": 0, "palavras": 0, "linhas": 0 },
  "total_sempre_carregado": { "caracteres": 0, "palavras": 0 },
  "tokens_entrada": null,
  "referencias_sob_demanda_incluidas": [],
  "instrucoes_obrigatorias_carregadas": true,
  "motivo": "<presente apenas em falha>"
}
```

O adapter `kiro-cli` não expõe contagem de tokens de entrada: `tokens_entrada`
é `null` (CA-17), sem falhar. O campo `referencias_sob_demanda_incluidas`
permanece no contrato por compatibilidade de tipo, mas desde #325 é **sempre**
uma lista vazia — o manual `@---` nunca é reportado como incluído no prompt,
pois deixou de existir qualquer referência a ele fora do steering. O evento é
logado como `composicao_medicao` (INFO) e, em falha, `composicao_fail_closed`
(ERROR).

## Novas chaves de configuração

| Chave | Local | Tipo | Obrigatoriedade | Validação |
|-------|-------|------|-----------------|-----------|
| `target-prompt` (objetivo da etapa) | `boards.<b>.columns.<c>` | texto | obrigatória quando a etapa aciona o agente | não vazia ao acionar |
| `step-prompt` (passo a passo) | `boards.<b>.columns.<c>` | texto | opcional | ausência válida; quando presente, não vazio |
| `branch_pattern` (formato por fluxo) | `git.flow.<flow>` | texto com marcadores | obrigatória por flow | marcadores resolvíveis com os dados da tarefa |
| `project.name` / `project.summary` | `project` | texto | obrigatórias | string não vazia |
| `project.humans` | `project` | lista `{name, role}` | opcional | cada item com `name`/`role` não vazios |

> A chave `allowed-commands` (`boards.<b>.columns.<c>`) existiu entre #308 e
> #325 para derivar o gate de referência sob demanda do manual `@---`. Foi
> **removida** em #325 junto com o próprio ponteiro: não é mais reconhecida
> pelo schema validado e não produz efeito algum sobre o prompt dinâmico. O
> manual `@---` permanece exclusivamente no steering, sempre carregado,
> independente de qualquer configuração de coluna.

## Comportamento em falha (resumo)

| Cenário | Comportamento | Evidência |
|---------|---------------|-----------|
| Instruções obrigatórias ausentes | não aciona o agente | `instrucoes_obrigatorias_carregadas: false` + motivo |
| `branch_pattern` com marcador não resolvível | não gera nome; `ConfigError` | marcador faltante nomeado |
| Escrita no steering (contexto da raiz) | bloqueada (protegido) | path em `PROTECTED_PATHS`/steering |
| Adapter sem tokens | prossegue | `tokens_entrada: null` |
