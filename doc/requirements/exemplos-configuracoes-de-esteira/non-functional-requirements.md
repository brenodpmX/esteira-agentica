# Requisitos Não-Funcionais — Exemplo de configurações de Esteira

Status: draft · Owner: requirements · Updated: 2026-08-24
Inputs: Issue #93 (body e histórico); `doc/product/exemplos-configuracoes-de-esteira/vision.md`; `business-rules.md` deste mesmo diretório

> Esta entrega é uma vitrine de configuração e documentação, não uma mudança
> de comportamento em runtime da Esteira. Por isso os NFRs abaixo medem
> atributos de qualidade dos **artefatos de exemplo** (reprodutibilidade,
> segurança de dados, manutenibilidade) — não desempenho, escalabilidade ou
> disponibilidade do software em produção, que não são afetados por este
> épico. Conforme decisão do dono e `vision.md` ("Retorno e como medir"),
> não há meta numérica de conversão/adoção; os NFRs abaixo são mensuráveis
> sobre o próprio processo de entrega, não sobre resultado de mercado.

| ID | Atributo | Requisito (mensurável) | Como medir |
|----|----------|------------------------|-----------|
| NFR-001 | Reprodutibilidade | 100% das execuções de validação interna de um mesmo exemplo (RF-004), por validadores diferentes, seguindo apenas a documentação de uso, devem chegar ao resultado demonstrável declarado no exemplo, sem alteração no `pipe.yml`/contextos publicados. | Comparar os registros de validação (RF-004) de execuções distintas do mesmo exemplo; qualquer divergência de resultado sem alteração do exemplo é falha de reprodutibilidade a corrigir antes da publicação. |
| NFR-002 | Segurança de dados | Zero ocorrências de dado pessoal, credencial, segredo ou identificador real de pessoa/empresa em qualquer artefato publicado dos dois exemplos (`pipe.yml`, contextos, issues de exemplo, roteiro de apresentação, registros). | Revisão de conteúdo por checklist (RN-002) antes da publicação de cada exemplo; qualquer ocorrência encontrada bloqueia a publicação até ser removida. |
| NFR-003 | Completude documental | 100% dos exemplos publicados possuem os oito campos mínimos de RF-005 (objetivo, público, caso de uso, pré-requisitos, resultado esperado, limites, versão suportada, responsável) preenchidos e não vazios. | Checklist de revisão por exemplo, aplicado pelo responsável pela revisão antes da publicação. |
| NFR-004 | Autossuficiência da documentação | 0 dependências de conhecimento não documentado: na validação interna (RF-004), o validador não deve precisar de nenhuma informação fora da documentação do próprio exemplo para concluir o ciclo. | Contagem de "ajuda necessária" registrada em RF-004; qualquer ajuda que revele lacuna na documentação do exemplo (não do ambiente/pré-requisito já declarado) deve ser corrigida e a validação repetida. |
| NFR-005 | Rastreabilidade de custo observado | 100% dos registros de validação (RF-004) que mencionem tokens/custo identificam o modelo, o cenário e a versão observados — nenhum registro generaliza o valor para "custo típico" sem escopo declarado (critério de aceite 5 de `vision.md`). | Revisão dos registros de validação antes de usá-los em material de apresentação (RN-006). |
| NFR-006 | Manutenibilidade / atualização | Toda mudança de produto que altere comportamento referenciado por um exemplo publicado gera uma avaliação de impacto registrada (RF-007) até o próximo release em que a mudança entrar em produção — sem backlog de exemplos desatualizados sem registro. | Auditoria periódica: para cada épico concluído desde a última verificação, confirmar existência do registro de avaliação de impacto (RN-008). |

Atributos fora de escopo nesta entrega (justificativa): performance,
escalabilidade e disponibilidade do software da Esteira não são alterados
por este épico — ele produz artefatos de configuração/documentação, não
código de execução. Caso um exemplo futuro exija medir tempo de resposta do
próprio software, isso pertence a um épico de arquitetura/engenharia, não a
este épico de requisitos de exemplo.
