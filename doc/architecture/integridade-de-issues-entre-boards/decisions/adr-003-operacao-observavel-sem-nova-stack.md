# ADR-003 — Contingência e evidência operacional nos mecanismos existentes

Status: proposed
Owner: architecture
Last updated: 2026-08-27

## Inputs
- `doc/architecture/integridade-de-issues-entre-boards/overview.md`
- `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`
- `doc/requirements/integridade-de-issues-entre-boards/non-functional-requirements.md`
- `README.md` (logging, Docker e loop principal)
- `src/core/log.py`, `src/core/config.py`, `src/core/version.py`, `src/__main__.py`

## Contexto

O épico só pode ser validado com evidência de código efetivamente em execução,
30 dias e ao menos 17 relações novas. Merge em `main` não foi evidência
suficiente na entrega anterior. Também é necessário suspender temporariamente
novos vínculos entre boards sem restart/deploy e medir propagação,
reconciliação, intervenção e despacho.

O sistema já possui configuração YAML, logs JSON persistentes, versão no
startup e logs por execução de agente. Adicionar Prometheus, banco de auditoria
ou painel nesta etapa não melhora a barreira de integridade.

## Decisão

Reutilizar configuração e logging existentes.

1. Adicionar `safety.cross_board_parent_links: enabled|suspended` ao
   `pipe.yml`. O core relê essa chave por mtime antes de aplicar nova relação.
   `suspended` bloqueia apenas relação nova entre boards distintos, registra o
   fato e não altera vínculos existentes. O pedido deve ser submetido novamente
   após a reativação.
2. Emitir eventos JSON estáveis para classificação, reconciliação, falha,
   remoção externa, despacho bloqueado e contingência.
3. Emitir `rollout_evidence` no startup com versão, commit, ambiente e
   `started_at`. `PIPE_ENVIRONMENT` é obrigatório no runtime de produção; o
   commit vem do checkout ou de arquivo gravado no build.
4. Enriquecer o log de agente com intenção e board de origem. Isso permite
   relacionar eventual despacho indevido ao consumo já registrado.
5. Considerar remoção manual/externa quando uma participação previamente
   detectada desaparece sem sucesso de `participation_reconciled` registrado.

A janela de validação começa somente com um `rollout_evidence` completo. Perda
ou ausência dos logs reinicia a comprovação; não se infere sucesso por ausência
de reclamação.

## Justificativa

Logs estruturados são suficientes para o volume e para as métricas exigidas.
Reler uma chave de configuração por mtime é simples, reversível e compatível
com o processo único. A decisão reduz tempo de entrega e mantém a futura
exportação de métricas como preocupação externa.

Alternativas rejeitadas:

- **Variável de ambiente para contingência:** exigiria recriar/reiniciar o
  processo.
- **Feature flag SaaS:** nova dependência operacional sem necessidade.
- **Painel/banco de métricas no core:** duplica logs e amplia escopo.
- **Usar data do merge como rollout:** precedente demonstrou que não prova o
  artefato executado.
- **Suspender todos os vínculos:** degrada relações dentro do mesmo board sem
  relação com o incidente.

## Consequências

- Positivas: contingência reversível sem deploy; auditoria suficiente para RF-06
  e RF-07; nenhum serviço novo; eventos podem alimentar alertas futuramente.
- Negativas: apuração inicial depende da retenção do volume de logs; o operador
  precisa definir ambiente e ressubmeter vínculo recusado durante suspensão.
- Riscos: checkout sem `.git` não fornece commit. Mitigação: build grava o hash
  em arquivo somente leitura e startup falha a evidência quando não o encontra.
- Riscos: desaparecimento externo não identifica com certeza o autor humano.
  O evento deve ser chamado `removed_externally`, e contabilizado como manual
  apenas após confirmação operacional, sem inventar autoria.
