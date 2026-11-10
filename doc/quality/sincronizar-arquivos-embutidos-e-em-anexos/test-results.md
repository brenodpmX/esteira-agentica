# Resultados de Teste — Sincronizar arquivos embutidos e em anexos

- **Issue:** #345
- **Etapa:** Execução de Testes
- **Autor:** André Tavares — Engenheiro de Qualidade PL
- **Data:** 2026-11-09
- **Branch:** `feature/345-sincronizar_arquivos_embutidos_e_em_anexos`
- **Commit sob teste:** `c0c3462` — feat(345): sincroniza arquivos embutidos e anexados de corpo e comentarios com politica por board
- **Base de comparação:** `1c27dc4` (commit dos casos de teste, anterior ao código)

> Execução dos casos de `test-cases.md` (CT-01..CT-23, 14 critérios de aceitação). Nenhum código nem caso de teste foi alterado nesta etapa.

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

## 2. Execução

| Escopo | Comando | Resultado |
|---|---|---|
| Pertinente à mudança | `python -m pytest tests/test_file_sync.py tests/test_file_sync_config.py -q` | 79 passed |
| Suíte completa | `python -m pytest -q` | 2012 passed, 26 failed, 17 skipped, 1 xpassed |
| Suíte completa na base `1c27dc4` | `python -m pytest -q` (worktree temporário) | 1933 passed, 26 failed |

As 26 falhas são idênticas na base (pré-existentes, sem relação com #345): `tests/test_agent_log_descritivo.py`, `tests/test_agent_failure_detection.py::...preserva_formato_do_epic`, `tests/test_docker_compose.py` (sem docker) e `tests/test_dockerfile.py` (ARG `KIRO_CLI_SHA256`). A diferença de +79 passados corresponde exatamente aos testes novos: sem regressão.

## 3. Cobertura dos casos

| Caso | CA | Teste | Resultado |
|---|---|---|---|
| CT-01 | 1 | `test_ct01_ct08_imagem_embutida_no_corpo_...` | Passou |
| CT-02 | 2 | `test_ct02_arquivo_anexado_no_corpo_baixado` | Passou |
| CT-03 | 1,2 | `test_ct03_corpo_com_embutido_e_anexado_baixa_ambos` | Passou |
| CT-04 | 4 | `test_ct04_corpo_sem_arquivo_...` | Passou |
| CT-05 | 3 | `test_ct05_comentario_novo_com_imagem_embutida_...` | Passou |
| CT-06 | 3 | `test_ct06_comentario_novo_com_upload_...` | Passou |
| CT-07 | 3 | `test_ct07_novo_comentario_nao_refaz_download_...` | Passou |
| CT-08 | 1,2 | `test_ct01_ct08_...` | Passou |
| CT-09 | 14 | `test_ct09_...change_down` e `..._change_up` | Passou |
| CT-10 | 5 | `test_ct10_*` (file_sync e config) | Passou |
| CT-11 | 6 | `test_ct11_*` (file_sync e config) | Passou |
| CT-12 | 7 | `test_ct12_*` | Passou |
| CT-13 | 8 | `test_ct13_*` | Passou |
| CT-14 | 9 | `test_ct14_primeira_recusa_aviso_...` | Passou |
| CT-15 | 9 | `test_ct15_ausencia_equivale_a_aviso_explicito` | Passou |
| CT-16 | 10 | `test_ct16_...sem_comentario_duplicado` | Passou |
| CT-17 | 10 | `test_ct17_conjunto_recusado_muda_novo_aviso` | Passou |
| CT-18 | 11 | `test_ct18_silencioso_...` | Passou |
| CT-19 | 12 | `test_ct19_bloqueante_aviso_e_need_human` | Passou |
| CT-20 | 13 | `test_ct20_bloqueante_reaplica_label_...` | Passou |
| CT-21 | 13 | `test_ct21_bloqueante_cessa_...` | Passou |
| CT-22 | 9 | `test_ct22_permitido_e_recusado_juntos` | Passou |
| CT-23 | 1,2 | `test_ct23_nomes_colidentes_...` | Passou |

Os 14 CAs têm ao menos um teste verde. Testes adicionais (validação de forma de config, falha de download não bloqueia texto, delete-down, extração de links, `is_attachment` do adapter GitHub) também passaram.

## 4. Arquitetura

Métodos opcionais acrescentados ao `BoardPort` com default "nenhum anexo"; lógica no core (`src/core/file_sync.py`), detalhes GitHub no adapter. Sem violação da arquitetura hexagonal.

## 5. Limitações

Testes offline com fake de board/download; download real contra o GitHub não foi exercitado. Retroatividade (fora de escopo) é registrada pelo desenvolvimento: issues antigas terão anexos baixados na primeira mudança remota.
