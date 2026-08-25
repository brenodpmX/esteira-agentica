# ADR-003 — Política opt-in no bloco boards, sem defaults

Status: proposed
Owner: architecture
Last updated: 2026-08-25

## Inputs
- `doc/product/circuit-break-de-agente/analise-negocio.md`
- `doc/requirements/circuit-break-de-agente/functional-requirements.md` (RF-003, RF-004, RF-006)
- `doc/requirements/circuit-break-de-agente/business-rules.md` (RN-007, RN-008)
- `doc/requirements/circuit-break-de-agente/non-functional-requirements.md` (NFR-006)
- `doc/ux/circuit-break-de-agente/prototype-configuracao.html` (proposta ainda em draft)
- `src/core/config.py` e `src/__main__.py` (`boards.rerun_cooldown`)

## Contexto
O dono definiu política geral, opcional e sem valores padrão de limite ou janela. O produto já agrupa em `boards` o `rerun_cooldown`, que também governa seleção/reexecução em toda a instância. A UX propôs `boards.circuit_break.executions/window`, com janela em segundos, mas ainda aguarda validação.

Alternativas avaliadas:

1. configuração por board/coluna/agente — explicitamente fora do escopo;
2. bloco raiz `agent` ou `execution` — separa a política do cooldown correlato e sugere escopo por adapter;
3. duração textual (`2h`, `30m`) — amigável, mas exige parser/formato adicional sem precedente no projeto;
4. segundos inteiros — consistente com `sleep` e `rerun_cooldown`, validação simples e sem dependência.

## Decisão
Adotar como contrato proposto:

```yaml
boards:
  platform: github
  rerun_cooldown: 300
  circuit_break:
    executions: 5
    window: 3600
```

Os números são somente exemplo; não existem defaults.

Regras de validação:

- `boards.circuit_break` ausente: política inativa e startup silencioso;
- bloco presente: `executions` e `window` são obrigatórios juntos;
- ambos devem ser inteiros (não `bool`) maiores ou iguais a 1;
- `window` é expresso em segundos;
- campos desconhecidos são rejeitados para evitar falsa sensação de proteção por typo;
- erro cita o caminho completo e ocorre em `check_config`, antes de qualquer alteração de estado;
- política é única para a instância e não pode aparecer dentro de um board/coluna nesta versão.

A validação e um objeto imutável `CircuitBreakPolicy | None` pertencem ao core de configuração. O store continua registrando ocorrências quando o retorno é `None`; apenas a decisão de bloquear fica desativada.

Como o artefato de UX ainda está em draft, este ADR permanece `proposed`. Uma alteração de nomes antes da implementação muda somente o parser/configuração e a documentação, não a máquina de estados nem o formato conceitual do domínio.

## Justificativa
O bloco irmão de `rerun_cooldown` é o local de menor surpresa para uma política global de seleção. Segundos mantêm coerência com configurações existentes e evitam parser de duração. Exigir o par completo evita política parcialmente ativa, e a ausência válida preserva compatibilidade.

Separar ausência de política da persistência de ocorrências cumpre simultaneamente RN-007: instalações atuais não sofrem bloqueio, mas a instrumentação interna continua disponível quando a política for ativada.

## Consequências
- Positivas: configuração pequena, previsível, compatível e sem dependência; nenhum valor de negócio imposto pelo software.
- Positivas: erros são detectados no startup, antes de agente ou sync.
- Negativas: segundos são menos legíveis que duração textual; comentários/logs devem formatar a duração para leitura humana sem alterar o valor configurado.
- Negativas: o nome e a unidade dependem da validação da UX/dono antes de mudar o status para `accepted`.
- Riscos: usuários podem confundir `rerun_cooldown` e `circuit_break`. README e mensagem de configuração devem dizer explicitamente: cooldown espaça; circuit-break limita.
