# Resultados de Teste — Documentação pública de avaliação e governança editorial do produto

Status: approved
Owner: quality
Last updated: 2026-11-11

## Inputs
- `doc/quality/documentacao-publica-governanca-editorial/test-cases.md` (CT-01 a CT-39)
- Issue #313
- Branch `feature/313-documentacao_publica_de_avaliacao_e_governanca_editorial_do_produto`, commit sob teste `851518e`

## Execução

- Testes da issue (7 arquivos `tests/test_readme_porta_entrada.py`, `test_catalogo_configuracao.py`, `test_inventario_editorial.py`, `test_comunicacao_versao.py`, `test_gate_revisao.py`, `test_manual_padroes.py`, `test_baseline_avaliacao.py`): 44 passaram, 1 pulado.
- Suíte completa (`python -m pytest`): 2130 passaram, 19 pulados, 1 xpassed, 26 falharam.
- Comparação com `origin/main` nos 4 arquivos das falhas (`test_agent_failure_detection.py`, `test_agent_log_descritivo.py`, `test_docker_compose.py`, `test_dockerfile.py`): as mesmas 26 falhas ocorrem na main. Não são regressão desta entrega e não têm relação com ela (formato de log do agente, ambiente Docker e SHA256 do kiro-cli no Dockerfile).
- Ambiente: `pytest` e `pyyaml` não estavam instalados e foram instalados no ambiente local. O repositório não foi alterado.

## CT-01 a CT-10 — README como porta de entrada (CA-1 a CA-5)

**Resultado:** passed

**Observações:**
- `tests/test_readme_porta_entrada.py` (11 testes) verde. Cobre valor, limites e pré-requisitos, execução local antes do container, container com link ao runbook, links para configuração e exemplos, ausência das seções internas e de incidentes, e concisão.

## CT-11 — Avaliador externo real lê o README (manual)

**Resultado:** blocked

**Observações:**
- Caso manual com participantes reais. Sem participantes confirmados, aplica-se a entrega mínima (RN-11). Não é falha.

## CT-12 a CT-15 — Catálogo de configuração (CA-9)

**Resultado:** passed

**Observações:**
- `tests/test_catalogo_configuracao.py` (5 testes) verde. Os 8 campos por entrada, 100% das chaves da lista canônica (ampliada de 60 para 65 pelo desenvolvimento, registrado no histórico), ausência de duplicatas e exemplos YAML válidos.
- A ampliação da lista estende a cobertura e não muda critério.

## CT-16 a CT-19, CT-37 — Inventário e classificação (CA-8)

**Resultado:** passed

**Observações:**
- `tests/test_inventario_editorial.py` (6 testes) verde. Seis campos por item, documentos públicos presentes, item incompleto detectado, decisão registrada nos casos mistos, classificação por finalidade.

## CT-20 a CT-25, CT-39 — Comunicação de versão (CA-6, CA-7)

**Resultado:** passed (CT-25 parcial: manual)

**Observações:**
- `tests/test_comunicacao_versao.py` (7 testes) verde. Processo com os 4 campos, publicação na mesma mudança, validador de estilo e de artefato interno, nota da versão corrente em `NOVIDADES.md`, auditoria sintética.
- CT-25 (auditoria manual das dez mudanças recentes) é de processo. A parte automatizável (CT-39) passou.

## CT-26 a CT-30 — Gate de revisão (CA-11)

**Resultado:** passed

**Observações:**
- `tests/test_gate_revisao.py` (9 testes) verde. Contrato com 4 campos, reprovação com motivo por artefato interno, registro tecnicista e promessa financeira, e aprovação do conteúdo válido.

## CT-31 a CT-33, CT-38 — Manual de padrões (CA-10)

**Resultado:** passed

**Observações:**
- `tests/test_manual_padroes.py` (5 testes) verde. Regras verificáveis, sem contradição com as decisões da issue, README sem divergência, alteração fora do padrão recusada.

## CT-34, CT-35 — Baseline (CA-12, RN-11)

**Resultado:** passed (CT-35 skipped por RN-11)

**Observações:**
- `tests/test_baseline_avaliacao.py`: CT-34 passa, com `decisao_continuidade: sem baseline disponível` registrada.
- CT-35 é pulado de propósito: "RN-11: sem participantes confirmados, o baseline não se aplica".

## CT-36 — Teste com participantes reais (manual)

**Resultado:** blocked

**Observações:**
- Não se aplica sem participantes confirmados (RN-11, CA-12 segunda parte). A entrega segue como mínima.

## Resumo

- Total de casos: 39 (CT-01 a CT-39)
- Passou: 35 (automatizados verdes)
- Falhou: 0
- Bloqueado/não aplicável: 4 (CT-11, CT-25 manual, CT-35 e CT-36 por RN-11)
- Falhas da suíte completa: 26, preexistentes e idênticas na main, fora do escopo da issue

## Veredito
aprovado
