# Resultados de Execução de Testes — Registro de execução de agentes com consolidação por linhagem histórica

- **Issue:** #307
- **Etapa:** Execução de Testes
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-02
- **Branch:** `feature/307-registro-execucao-agentes-linhagem-historica`
- **Commit sob teste:** `63b27a0` — feat(307): registro de execução de agentes + consolidação por linhagem histórica
- **Ambiente:** Python 3.12.14, pytest 9.1.1, pluggy 1.6.0 (Linux)

---

## Veredito

**APROVADO (sucesso) — avançar para `documentação`.**

Todos os casos de teste especificados (CT-01..CT-21, derivados dos critérios de
aceitação CA-1..CA-18 e das regras RN/RNF) passam. As suítes de não regressão
indicadas permanecem verdes. As 26 falhas da suíte completa foram comprovadas
como **pré-existentes à base `origin/main`** (idênticas sem nenhuma alteração do
#307) e são alheias a esta entrega — não constituem falha de código desta
mudança. Não há reprovação total nem parcial atribuível ao #307.

---

## Comando e resultado — suíte pertinente à mudança

```
python -m pytest tests/test_execution_record.py tests/test_execution_lineage.py \
  tests/test_execution_record_retention.py tests/test_execution_record_config.py \
  tests/test_execution_record_surface.py tests/test_execution_record_integration.py -v
```

**Resultado: `63 passed in 2.02s` — 0 falhas, 0 erros.**

| Arquivo | Casos | Resultado |
|---------|-------|-----------|
| `tests/test_execution_record.py` | 25 (inclui CT-20 parametrizado) | ✅ todos passaram |
| `tests/test_execution_lineage.py` | 9 | ✅ todos passaram |
| `tests/test_execution_record_retention.py` | 6 | ✅ todos passaram |
| `tests/test_execution_record_config.py` | 12 | ✅ todos passaram |
| `tests/test_execution_record_surface.py` | 4 | ✅ todos passaram |
| `tests/test_execution_record_integration.py` | 7 | ✅ todos passaram |
| **Total** | **63** | **✅ 63 passed** |

### Rastreabilidade caso de teste → critério de aceitação (todos ✅)

| CT (test-cases.md) | CA / RN / RNF | Teste(s) correspondente(s) | Status |
|---|---|---|---|
| CT-01 — concluída sem avanço | CA-2, CA-1, RN-01 | `test_ct01_concluida_sem_avanco` | ✅ |
| CT-02 — interrompida com avanço prévio | CA-3, RN-01 | `test_ct02_interrompida_com_avanco_previo` | ✅ |
| CT-03 — consumo indisponível | CA-5, RN-04, RNF-02 | `test_ct03_consumo_indisponivel` | ✅ |
| CT-04 — consumo zero reportado | CA-6, RN-04 | `test_ct04_consumo_zero_reportado` | ✅ |
| CT-04b — consumo disponível | CA-4, RN-04/05, RNF-08 | `test_ct04b_consumo_disponivel_positivo` | ✅ |
| CT-05 — repetição sem avanço (mesma etapa) | CA-8, RN-03 | `test_ct05_repeticao_sem_avanco_mesma_etapa` | ✅ |
| CT-06 — não repetição após mudar etapa | CA-8, RN-03 | `test_ct06_nao_repeticao_apos_mudanca_de_etapa` | ✅ |
| CT-07 — linhagem resiliente à limpeza local | CA-9, RN-06, RNF-03 | `test_ct07_linhagem_resiliente_a_limpeza_local` | ✅ |
| CT-08 — descendente sem registro | CA-10, RN-08, RNF-04 | `test_ct08_descendente_sem_registro`, `test_ct08_descendente_intermediario_sem_registro` | ✅ |
| CT-09 — ciclo na linhagem | CA-11, RN-07 | `test_ct09_ciclo_conta_cada_uma_vez` | ✅ |
| CT-09b — caminho duplo (grafo) | CA-11, RN-07 | `test_ct09b_caminho_duplo_sem_dupla_contagem` | ✅ |
| CT-10 — unidades diferentes segmentadas | CA-7, RN-05, RNF-08 | `test_ct10_agregado_unidades_distintas_segmentado` | ✅ |
| CT-11 — retenção configurada expira | CA-12, RN-09, RNF-06 | `test_ct11_borda_menor_que_n_permanece`, `test_ct11_borda_igual_a_n_elegivel`, `test_ct11_borda_maior_que_n_elegivel`, `test_ct11_retencao_independe_do_log_ttl` | ✅ |
| CT-12 — retenção não configurada | CA-12, RN-09, RNF-06 | `test_ct12_sem_retencao_nenhum_expurgo`, `test_registro_sem_inicio_nao_expurgado` | ✅ |
| CT-11b — validação de forma da retenção | contrato de config | `test_ausente_aceito`, `test_inteiro_positivo_aceito`, `test_valores_invalidos_rejeitados[0/-1/True/False/7.5/"7"]`, `test_bool_rejeitado_antes_de_int`, `test_bloco_nao_mapa_rejeitado`, `test_campo_desconhecido_rejeitado`, `test_resolve_retencao_dias` | ✅ |
| CT-13 — exclusão preserva registros (direta) | CA-13, RN-10, RNF-09 | `test_ct13_exclusao_de_issue_preserva_registros` | ✅ |
| CT-13b — exclusão preserva na linhagem | CA-13, RN-10, RNF-09 | `test_ct13b_exclusao_preserva_na_linhagem` | ✅ |
| CT-14 — ausência de exclusão manual | CA-14, RN-11, RNF-10 | `test_ct14_sem_funcao_de_exclusao_manual`, `test_ct14_purge_expired_so_remove_por_retencao` | ✅ |
| CT-15 — resposta sem abrir logs | CA-15, RN-13, RNF-05 | `test_ct15_resposta_sem_abrir_logs` | ✅ |
| CT-16 — isolamento de conteúdo | CA-17, RN-13, RNF-07 | `test_ct16_isolamento_sem_prompt_nem_conversa`, `test_ct16_store_em_protected_paths`, `test_ct16_build_prompt_rejeita_o_caminho` | ✅ |
| CT-17 — fonte única de contagem | CA-18, RN-01 | `test_ct17_sem_contador_paralelo_de_contexto` | ✅ |
| CT-18 — interrupção preserva início/parciais | RN-02, falha | `test_ct18_interrupcao_preserva_inicio_e_parciais` | ✅ |
| CT-19 — inclassificável → desconhecida | RN-02, falha | `test_ct19_inclassificavel_grava_desconhecida` | ✅ |
| CT-20 — taxonomia total e determinística | RN-02, CA-1 | `test_ct20_mapeamento_total_e_deterministico[13 variações]`, `test_ct20_todas_as_classes_tem_destino`, `test_resultado_fora_da_taxonomia_vira_desconhecida_na_gravacao` | ✅ |
| CT-21 — baseline de 30 dias | CA-16, RN-01/04, RNF-01 | `test_ct21_baseline_30_dias_compoe_metricas` | ✅ |
| Integração em `call_agent` (CA-1) | CA-1, RN-01 | `test_call_agent_grava_concluida_sem_avanco`, `test_call_agent_grava_interrompida_com_avanco`, `test_call_agent_grava_em_falha_terminal`, `test_call_agent_grava_mesmo_com_result_none`, `test_call_agent_captura_issue_parent`, `test_call_agent_registro_sem_prompt_nem_conversa`, `test_call_agent_um_registro_por_execucao` | ✅ |

Cobertura: os 17 cenários obrigatórios da issue (CT-01..CT-17) estão
integralmente verdes; CA-1/RN-02 travados adicionalmente por CT-18/19/20; CA-16
por CT-21; a integração real no ponto de execução (`call_agent`, qualquer
desfecho) confirmada pela suíte de integração.

---

## Não regressão

```
python -m pytest tests/test_agent_circuit_break.py tests/test_rerun_cooldown.py \
  tests/test_execucao_autonoma_confiavel.py tests/test_error_classification.py \
  tests/test_snapshot_guard_call_agent.py tests/test_build_prompt_protected_paths.py \
  tests/test_startup.py
```

**Resultado: `225 passed, 3 skipped in 2.08s`.** As suítes indicadas pela
especificação como sensíveis à mudança no ponto de execução (`call_agent`,
fonte única de contagem, guarda de snapshot, `PROTECTED_PATHS`, startup)
permanecem verdes.

---

## Suíte completa e análise de causa-raiz das falhas pré-existentes

```
python -m pytest
```

**Resultado: `26 failed, 1579 passed, 17 skipped, 1 xpassed`.**

As 26 falhas concentram-se exclusivamente em:

- `tests/test_agent_log_descritivo.py` (formato de log de terminal)
- `tests/test_agent_failure_detection.py` (1 caso de formato de linha inicial)
- `tests/test_docker_compose.py` (config de compose no ambiente)
- `tests/test_dockerfile.py` (pinning `KIRO_CLI_SHA256`/`gh` no Dockerfile do ambiente)

### Prova de que são pré-existentes e alheias ao #307

Executei os mesmos 4 arquivos sobre a **base limpa `origin/main`** (sem nenhuma
alteração do #307), via `git worktree`:

```
git worktree add /tmp/base-main origin/main
cd /tmp/base-main && python -m pytest tests/test_agent_log_descritivo.py \
  tests/test_agent_failure_detection.py tests/test_docker_compose.py tests/test_dockerfile.py
```

**Resultado na base: `26 failed, 221 passed, 6 skipped`** — o **mesmo conjunto
de 26 falhas**, sem nenhum arquivo do #307 presente. (Worktree removido ao final.)

**Conclusão de causa-raiz:** as falhas são do **ambiente/base** (formato de log
de terminal e pinning docker/kiro-cli), anteriores a esta issue e independentes
dela. A entrega #307 é **aditiva** no ponto de execução (`call_agent`) e não
toca nesses caminhos. Portanto **não** há reprovação (nem total nem parcial)
atribuível ao código do #307 — não se aplica classificação `falha` nem
`revisar-caso-de-teste`.

---

## Aderência à arquitetura

- Capacidade implementada no **core** (`src/core/execution_record.py`), com o
  ponto de gravação no orquestrador (`src/__main__.py::call_agent`), sem violar a
  separação hexagonal core/adapters.
- Armazenamento durável adicionado a `PROTECTED_PATHS` (`src/core/agent.py`) e
  rejeitado por `build_prompt` — isolamento de estado interno preservado
  (verificado por `test_ct16_store_em_protected_paths` e
  `test_ct16_build_prompt_rejeita_o_caminho`).
- Adesão à fonte única `agent_circuit_break` sem contador paralelo de contexto
  (verificado por `test_ct17_sem_contador_paralelo_de_contexto`).
- Validação de config no padrão da casa (`ConfigError` citando o caminho, `bool`
  antes de `int`) — verificada por `tests/test_execution_record_config.py`.

Nenhuma violação de arquitetura detectada.

---

## Observações

- Nenhum código de produção nem caso de teste foi alterado nesta etapa — apenas
  execução, análise e registro de resultados, conforme o papel de QA na etapa de
  Execução de Testes.
- O consumo com `disponibilidade = indisponível` para o adapter `kiro-cli` (sem
  contagem de tokens) é comportamento **correto** validado por CT-03, não falha.
