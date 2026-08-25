# Requisitos Não-Funcionais — Otimizar prompts, contextos e comandos

Status: approved · Owner: requirements · Updated: 2026-08-25
Inputs: `doc/product/otimizar-prompts-contextos-comandos/analise-negocio.md`;
`functional-requirements.md` e `business-rules.md` deste mesmo diretório.

Este documento detalha, com número/unidade/condição, os atributos de
qualidade já definidos como gate de sucesso pela análise de negócio. Não
redefine escopo funcional.

| ID | Atributo | Requisito (mensurável) | Como medir |
|----|----------|------------------------|-----------|
| NFR-001 | Eficiência de contexto | O prompt dinâmico deve ter, em média sobre a matriz fixa de cenários (RF-006), pelo menos 40% menos palavras estáticas do que a versão-base, sem redução de nenhum guardrail (RN-001). | Benchmark antes/depois (RF-006): contagem de palavras por cenário via a mesma função de composição usada em produção; comparação percentual agregada. |
| NFR-002 | Eficiência de contexto | O total sempre carregado (prompt dinâmico + contexto persistente) deve ter, em média sobre a matriz fixa, pelo menos 20% menos palavras do que a versão-base, no adapter Kiro atual. | Benchmark antes/depois (RF-006): soma de palavras de `build_prompt` + `generate_context` por cenário; comparação percentual agregada. |
| NFR-003 | Consistência | Zero duplicidades de regra remanescentes entre camadas sempre carregadas, conforme o inventário auditável (RF-001). | Inspeção do inventário (RF-001): toda entrada marcada como duplicidade na versão-base deve estar ausente (ou reduzida a uma única ocorrência) na versão proposta. |
| NFR-004 | Observabilidade / Verificabilidade | 100% das execuções do adapter Kiro devem ter prova de carregamento (RF-004) das instruções obrigatórias vigentes no momento da execução, consultável sem acesso a `PROTECTED_PATHS`. | Amostragem de execuções reais ou de teste: verificar presença do registro de prova de carregamento associado a cada execução; confirmar que a verificação não depende de ler arquivos protegidos. |
| NFR-005 | Compatibilidade / Não regressão | 100% dos cenários de referência de workdir, branch, proteção de estado, leitura/escrita dos arquivos da issue (`-body.md`, `-history.md`, `-addcomment.md`), finalização e transição de coluna devem continuar se comportando de forma idêntica à versão-base após a simplificação. | Suíte de regressão existente (`tests/test_build_prompt_git_setup.py`, `tests/test_build_prompt_protected_paths.py` e equivalentes) executada contra a versão proposta, sem nenhum teste de comportamento preexistente quebrado ou removido sem substituição equivalente. |
| NFR-006 | Segurança / Isolamento | Zero ocorrências, na suíte de regressão e nos cenários da matriz fixa, de acesso indevido a `PROTECTED_PATHS` ou de execução fora do workdir resolvido (`resolve_work_dir`) para o board/repositório correto. | `_assert_no_protected` (ou verificação equivalente na versão proposta) executado sobre o prompt e o contexto persistente de cada cenário da matriz; nenhuma ocorrência de path protegido tolerada. |
| NFR-007 | Manutenibilidade | O inventário de instruções (RF-001) deve ser mantido atualizado: qualquer instrução nova adicionada ao prompt dinâmico ou ao contexto persistente após esta entrega deve ser classificável em uma das quatro camadas (política invariável, contexto do operador, workflow da etapa, dado da tarefa) sem exigir uma quinta categoria ad hoc. | Revisão de PR/change file: toda alteração em `build_prompt`/`generate_context` que adicione texto sempre carregado deve referenciar sua classificação de camada no inventário. |

## Observações de medição

- As métricas de acompanhamento citadas na análise de negócio (percentual de
  execuções sem correção por instrução ausente/conflitante, reexecuções
  atribuídas a prompt/contexto, falhas de workdir/branch/commit/PR,
  intervenções humanas por instrução) **não são gate de aprovação** desta
  entrega — são observação contínua, coerente com RN-009 (nenhuma suposição
  de taxa de erro como fato já comprovado).
- Tokens de entrada por execução devem ser registrados quando o adapter
  expuser essa informação, mas a ausência de contagem de tokens não bloqueia
  a aprovação (a análise de negócio trata tokens como observação, não como
  gate único).
