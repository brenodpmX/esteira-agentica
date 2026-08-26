# ADR-003 — Política opt-in em bloco raiz, sem defaults

Status: proposed
Owner: architecture
Last updated: 2026-08-26

## Inputs
- `doc/product/circuit-break-de-agente/analise-negocio.md`
- `doc/requirements/circuit-break-de-agente/functional-requirements.md` (RF-003, RF-004, RF-006)
- `doc/requirements/circuit-break-de-agente/business-rules.md` (RN-007, RN-008)
- `doc/requirements/circuit-break-de-agente/non-functional-requirements.md` (NFR-006)
- `doc/ux/circuit-break-de-agente/prototype-configuracao.html` (proposta ainda em draft)
- `src/core/config.py` e `src/__main__.py` (`boards.rerun_cooldown`)

## Contexto
O dono definiu política geral, opcional e sem valores padrão de limite ou janela. A UX propôs `boards.circuit_break.executions/window`, com janela em segundos, mas ainda aguarda validação. A inspeção do código mostrou que esse endereço não é seguro: `_validate_boards`, `Board.board_ids` e `get_board_ids` tratam todo valor `dict` dentro de `boards` como configuração de um board. O bloco proposto seria validado, sincronizado e rotacionado como um board inexistente.

Alternativas avaliadas:

1. configuração por board/coluna/agente — explicitamente fora do escopo;
2. `boards.circuit_break` — próximo do cooldown, porém ambíguo com o mapa heterogêneo atual e exigiria alterar todos os enumeradores de boards;
3. bloco raiz genérico `circuit_break` — simples, mas não distingue este controle de futuros circuit-breaks de sincronização;
4. bloco raiz `agent_circuit_break` — explicita o alvo, preserva a enumeração de boards e não exige migração estrutural;
5. duração textual (`2h`, `30m`) — amigável, mas exige parser/formato adicional sem precedente no projeto;
6. segundos inteiros — consistente com `sleep` e `rerun_cooldown`, validação simples e sem dependência.

## Decisão
Adotar como contrato proposto:

```yaml
agent_circuit_break:
  executions: 5
  window: 3600

boards:
  platform: github
  rerun_cooldown: 300
```

Os números são somente exemplo; não existem defaults.

Regras de validação:

- `agent_circuit_break` ausente: política inativa e startup silencioso;
- bloco presente: `executions` e `window` são obrigatórios juntos;
- ambos devem ser inteiros (não `bool`) maiores ou iguais a 1;
- `window` é expresso em segundos;
- campos desconhecidos são rejeitados para evitar falsa sensação de proteção por typo;
- erro cita o caminho completo e ocorre em `check_config`, antes de qualquer alteração de estado;
- política é única para a instância e não pode aparecer em `boards`, dentro de um board ou de uma coluna nesta versão.

A validação e um objeto imutável `CircuitBreakPolicy | None` pertencem ao core de configuração. O store continua registrando ocorrências quando o retorno é `None`; apenas a decisão de bloquear fica desativada.

Como o artefato de UX ainda está em draft, este ADR permanece `proposed`. Uma alteração de nomes antes da implementação muda somente o parser/configuração e a documentação, não a máquina de estados nem o formato conceitual do domínio.

## Justificativa
O bloco raiz qualificado é a menor mudança segura: evita que metadados estruturados sejam confundidos com boards e deixa explícito que o limite é de execuções de agente. Segundos mantêm coerência com `sleep` e `rerun_cooldown` e evitam parser de duração. Exigir o par completo evita política parcialmente ativa, e a ausência válida preserva compatibilidade.

Separar ausência de política da persistência de ocorrências cumpre simultaneamente RN-007: instalações atuais não sofrem bloqueio, mas a instrumentação interna continua disponível quando a política for ativada.

## Consequências
- Positivas: configuração pequena, previsível, compatível e sem dependência; nenhum valor de negócio imposto pelo software.
- Positivas: erros são detectados no startup, antes de agente ou sync.
- Negativas: segundos são menos legíveis que duração textual; comentários/logs devem formatar a duração para leitura humana sem alterar o valor configurado.
- Negativas: o nome e a unidade dependem da validação da UX/dono antes de mudar o status para `accepted`; qualquer alternativa de nome deve continuar fora do mapa `boards`.
- Riscos: usuários podem confundir `rerun_cooldown` e `agent_circuit_break`. README e mensagem de configuração devem dizer explicitamente: cooldown espaça; circuit-break limita.
