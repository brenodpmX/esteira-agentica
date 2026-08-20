# Homologação — Sub-issues propagadas entre boards

## Escopo

Este documento substitui o roteiro histórico da branch documental #99 e
registra o estado efetivamente homologado da correção do incidente #88.

- **Veículo:** issue #88 / PR #102
- **Retrabalho final:** issue #106 / commit `a00ba7c`
- **Tentativa cancelada:** issue #98 / PR #103
- **Homologação:** aprovada em 19/08/2026
- **Disponibilidade:** merge e deploy pendentes

A branch original do post mortem #99 não continha mudança de runtime. A
correção final foi integrada posteriormente à branch do PR #102; por isso,
referências antigas ao commit `01f9e83` como entrega final ou à correção como
“fora desta branch” não representam mais o estado atual.

## O que validar

1. Vincular uma sub-issue a um parent presente em outro board configurado.
2. Confirmar que o item propagado sem `Status` é removido do project indevido.
3. Confirmar que nenhum `-body.md`, `-history.md` ou `-addcomment.md` duplicado
   é criado no board indevido.
4. Confirmar que o item no project de origem é preservado, mesmo se estiver
   temporariamente sem `Status`.
5. Confirmar que um item multi-board com `Status` definido é preservado.
6. Confirmar que uma issue nova com `parent`, sem prova de presença em outro
   board configurado, usa o fallback da primeira coluna em vez de ser removida.
7. Simular falha de remoção e verificar que o evento é reenfileirado, sem criar
   arquivos locais.

## Validação automatizada

Executar:

```bash
python3 -m pytest tests/test_sub_issue_propagation_fix.py -q
python3 -m pytest tests/test_hotfix24_incident_doc_cleanup.py -q
git diff --check
```

A suíte canônica deve exercitar a implementação real do adapter e do core, sem
`monkeypatch` de `_remove_propagated_items_without_status`.

## Ambiente Docker

O procedimento atualizado está em [`doc/runbook/docker.md`](../../runbook/docker.md).
Em resumo:

```bash
cp .env.example .env
# Preencher GH_TOKEN, KIRO_API_KEY e SSH_KEY_FILE_HOST absoluto

docker compose build
docker compose up -d
docker compose logs -f pipe
```

`docker compose ps` deve mostrar o serviço `pipe` em execução, e os logs devem
passar por configuração, startup e sync inicial sem falhas de autenticação.

## Resultado

Homologação aprovada em 19/08/2026. A correção previne novas duplicações; não
remove automaticamente os resíduos #84/#85/#86. A disponibilização em produção
requer merge do PR #102 e deploy, seguidos da limpeza manual do resíduo com a
esteira parada.
