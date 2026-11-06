# Resultados de Teste — Limitador opcional de consumo de IA por plataforma

- **Issue:** #311
- **Etapa:** Execução de Testes
- **Autor(a):** André Tavares — Engenheiro de Qualidade PL
- **Data:** 2026-11-06
- **Branch:** `feature/311-limitador_opcional_de_consumo_de_ia_por_plataforma`
- **Commit sob teste:** `5116770` — feat(consumo): limitador opcional de consumo de IA por plataforma (#311)
- **Base de comparação:** `6a78e7e` (casos de teste, anterior ao código)

> Registra a execução dos casos de `test-cases.md` (CT-A1..CT-F1). Nenhum código
> nem caso de teste foi alterado nesta etapa.

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

## 2. Execução

| Escopo | Comando | Resultado |
|---|---|---|
| Testes da mudança | `python -m pytest tests/test_consumption_limit*.py` | 129 passaram, 0 falhas |
| Suíte completa | `python -m pytest` | 1933 passaram, 26 falharam, 17 skipped, 1 xpassed |

As 26 falhas (`test_agent_log_descritivo`, `test_agent_failure_detection`,
`test_docker_compose`, `test_dockerfile`) são **baseline pré-existente**: as mesmas
26 falham em `6a78e7e`, antes do código de #311 (zero regressão). Não têm relação
com o escopo da issue (formato de log descritivo e infra Docker).

## 3. Cobertura dos casos

| Grupo | Casos | Arquivo | Resultado |
|---|---|---|---|
| A — Configuração | CT-A1..CT-A10 | `tests/test_consumption_limit_config.py` | Aprovado |
| B — Decisão/acúmulo/isolamento/retomada/falha | CT-B1..CT-B15 | `tests/test_consumption_limit.py` | Aprovado |
| C — Reset e fuso | CT-C1..CT-C7 | `tests/test_consumption_limit_reset.py` | Aprovado |
| D — Observabilidade | CT-D1..CT-D4 | `tests/test_consumption_limit.py` | Aprovado |
| E — Integração pré-agente | CT-E1..CT-E3 | `tests/test_consumption_limit_integration.py` | Aprovado |
| F — Baseline | CT-F1 | `tests/test_consumption_limit_integration.py` | Aprovado |

## 4. Critérios de aceitação

| CA | Casos | Resultado |
|---|---|---|
| CA-1 | CT-B1..B3 | Aprovado |
| CA-2 | CT-A1, CT-B4 | Aprovado |
| CA-3 | CT-B5 | Aprovado |
| CA-4 | CT-B6 | Aprovado |
| CA-5 | CT-B7 | Aprovado |
| CA-6 | CT-C1..C4 | Aprovado |
| CA-7 | CT-B9, CT-B10 | Aprovado |
| CA-8 | CT-B11, CT-D4 | Aprovado |
| CA-9 | CT-D1..D3 | Aprovado |
| CA-10 | CT-C5, CT-C6 | Aprovado |
| CA-11 | CT-B8 | Aprovado |
| CA-12 | CT-F1 | Aprovado |

## 5. Observações

- Não há violação de arquitetura: o gate fica antes do despacho do agente, sem rede síncrona (CT-E1/E2).
- Limitação conhecida e declarada (RN-11): bloqueio da próxima execução, não teto rígido.
- A documentação de operação (runbook) segue para a etapa de Documentação.
