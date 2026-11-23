# Dashboard de telemetria das esteiras

Recebe via OTLP a telemetria de qualquer número de pipes da Esteira Agêntica
(Contrato de telemetria v1), guarda no ClickHouse e mostra no Grafana uma aba por
pipe, com o mesmo layout em todas. Tudo gratuito e em Docker.

```
pipes ──OTLP──▶ otel-collector ──▶ clickhouse ◀── grafana (127.0.0.1:3000)
  (rede esteira-telemetria,          ▲
   host esteira-otlp:4317/4318)      └── config-sync (views SQL + dashboard.yml)
```

| Serviço | Imagem | Papel |
|---|---|---|
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.165.0` | recebe OTLP gRPC 4317 / HTTP 4318 e grava no ClickHouse |
| `clickhouse` | `clickhouse/clickhouse-server:26.9.37.5-alpine` | armazenamento (sem porta no host) |
| `config-sync` | `./tools` (Python 3.12) | aplica as views de `sql/` e copia o `dashboard.yml` para a tabela `dashboard_config` |
| `grafana` | `grafana/grafana-oss:13.0.2` + plugins `grafana-clickhouse-datasource@4.23.5`, `volkovlabs-echarts-panel@7.3.0` (Apache-2.0) | visualização |
| `gerador` (profile `exemplo`) | `./tools` | dados fictícios de duas pipes |

## Subir

```bash
cd dashboard
cp .env.example .env          # preencha GRAFANA_ADMIN_PASSWORD e CLICKHOUSE_PASSWORD
docker compose up -d
# opcional: dados de exemplo
docker compose --profile exemplo up -d
```

Abra http://127.0.0.1:3000 (usuário/senha do `.env`). O dashboard "Esteira —
acompanhamento" é a página inicial.

**Ordem:** suba o dashboard **antes** das pipes. Ele cria a rede Docker
`esteira-telemetria`, que o override da pipe usa como rede externa. Se precisar subir
a pipe antes, crie a rede à mão (idempotente):
`docker network inspect esteira-telemetria >/dev/null 2>&1 || docker network create esteira-telemetria`.

## Ligar uma pipe

A pipe usa `network_mode: service:dind`, então quem entra na rede é o serviço `dind`
(override `compose.telemetria.yml`, demanda 01). Variáveis na pipe:

| Variável | Valor |
|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://esteira-otlp:4318` |
| `OTEL_RESOURCE_ATTRIBUTES` | opcional: `service.instance.id=<id único>,esteira.pipe.nome=<nome>`; obrigatório se duas pipes usam o mesmo repositório |

A pipe aparece numa aba nova no primeiro ciclo, sem editar nada aqui.

## `dashboard.yml`

Relido a cada `CONFIG_SYNC_INTERVALO` segundos (padrão 30), sem rebuild nem restart.
Chave de cada pipe = `service.instance.id` (aparece no seletor Pipe).

| Chave | Efeito | Padrão |
|---|---|---|
| `boards_raiz` | issues desses boards viram barras do "Custo por árvore" | vazio = issues sem pai |
| `colunas_finais` | colunas que contam como concluída (além de closed/arquivada) | vazio |
| `ordem_colunas` | ordem do fluxo; voltar para coluna anterior = retrabalho | vazio = sem retrabalho |

Pipe sem bloco usa `padrao`. YAML inválido mantém a configuração anterior (aviso em
`docker compose logs config-sync`).

## Página da pipe

| Seção | Painéis |
|---|---|
| Pipe | abas das pipes; consumo × limite; acumulado; execuções; sucesso; avanço; custo/avanço; pipe viva; fila e dead-letter |
| Custo das issues | **Custo por árvore** (lista viva, pilha por nível, cor = status); **Custo por issue**; **Custo por execução** |
| Consumo | acumulado × limite; projeção; consumo por coluna; consumo diário por modelo |
| Resultados | resultados por dia; admissões negadas |
| Agentes | indicadores; placar com Δ contra o período anterior; ranking; sucesso e falhas; eficiência; dispersão de custo; duração; consumo no tempo |
| Agentes — detalhe (recolhida) | agente × coluna; agente × modelo; tamanho do contexto; robustez |
| Fluxo das issues | throughput; WIP; tempo por coluna; retrabalho; caminho das issues |
| Board e sincronismo (recolhida) | latência da API; throttle e penalty; circuit breaker; fila; lag; desfechos; dead-letter |
| Saúde e detalhe (recolhida) | vida da pipe; incidentes; árvore da raiz; execuções; spans do trace |

Regras que valem em todo painel:

- **Lista viva:** a issue raiz entra no gráfico quando é criada (barra vazada "Sem
  execução"); cada execução dela ou de uma descendente soma na barra e a leva para a
  esquerda. O período só escolhe quais barras entram; o tamanho é sempre o total.
- **Cores de status:** Concluída `#2E9E44`, Em andamento `#2F6FDB`, Falha `#D93025`,
  Timeout `#F28C28`, Interrompida `#E8C21B`, Bloqueada `#8E44AD`, Desconhecida `#8A8A8A`.
  No custo por árvore, cada nível abaixo da raiz fica 20% mais claro.
- **Unidade:** o filtro Unidade é obrigatório; unidades diferentes nunca são somadas.
  Consumo não informado conta no tempo e nas execuções, nunca como zero.
- **Cliques:** barra do custo por árvore → filtro Raiz; barra do custo por issue →
  filtro Issue; agente no placar → filtro Agente; Trace na tabela de execuções →
  spans do trace. Limpe o campo para tirar o filtro.

## Retenção

`RETENCAO_HORAS` (padrão 720 = 30 dias) vale **na criação** das tabelas. Para mudar
depois:

```bash
docker compose exec clickhouse clickhouse-client -u "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" -d esteira -q "
  ALTER TABLE otel_logs MODIFY TTL toDateTime(Timestamp) + toIntervalDay(60);
  ALTER TABLE otel_traces MODIFY TTL toDateTime(Timestamp) + toIntervalDay(60);
  ALTER TABLE otel_metrics_gauge MODIFY TTL toDateTime(TimeUnix) + toIntervalDay(60);"
```

O snapshot diário de `esteira.issue.upsert` enviado pela pipe mantém a hierarquia de
árvores mais antigas que a retenção.

## Backup

```bash
docker compose stop
docker run --rm -v esteira-dashboard_clickhouse-data:/d -v "$PWD":/b alpine tar czf /b/clickhouse-$(date +%F).tgz -C /d .
docker compose start
```

`docker compose down` preserva os dados; `docker compose down -v` apaga tudo.

## Mudar ou adicionar painel

O dashboard é código. Não edite pela UI (o provisionamento bloqueia).

1. Painéis padrão: edite `grafana/build_dashboard.py`. Painéis ECharts: o `.js` em
   `grafana/echarts/` (`comum.js` tem cores e utilitários).
2. `python3 grafana/build_dashboard.py` (só biblioteca padrão) regrava
   `grafana/dashboards/esteira.json`; o Grafana recarrega em até 30 s.
3. `GRAFANA_PASSWORD=... python3 grafana/verificar_consultas.py` executa todas as
   consultas do dashboard e falha se alguma quebrar.

Views SQL ficam em `sql/` (aplicadas em ordem pelo `config-sync` sempre que mudam).
Nomes OTel não são traduzidos: atributos ficam como texto em
`LogAttributes['esteira.x']` e as views convertem os tipos.

## Eventos manuais de teste

`./enviar-eventos.sh` manda eventos avulsos para a pipe `teste-manual` (aba própria;
já configurada no `dashboard.yml`). O estado das issues criadas fica no volume do
gerador, então os comandos podem ser encadeados.

```bash
./enviar-eventos.sh cenario                       # épico → 2 histórias → 4 tarefas, uma execução a cada 8 s
./enviar-eventos.sh listar
./enviar-eventos.sh issue --board epicos          # nova raiz: aparece vazada, sem execução
./enviar-eventos.sh execucao --issue 5 --agente revisor --resultado "falha terminal" --consumo 12
./enviar-eventos.sh execucao --issue 6 --sem-consumo --nao-avancou
./enviar-eventos.sh mover --issue 5 --para revisao
./enviar-eventos.sh fechar --issue 1
./enviar-eventos.sh bloqueio --issue 6            # status Bloqueada
./enviar-eventos.sh throttle --valor 8
./enviar-eventos.sh breaker --estado open
./enviar-eventos.sh --help
```

`TESTE_PIPE_ID=outra ./enviar-eventos.sh ...` usa outra pipe (aba nova).

## Gerador de exemplo

`docker compose --profile exemplo up -d gerador` simula 7 dias de histórico e depois
segue ao vivo (um passo a cada 6 s). Pipes `loja-ficticia` e `escrevas-ficticio`
(a segunda também com execuções em Tokens). `GERADOR_PIPES=3` liga uma terceira.
Para recomeçar do zero: `docker compose --profile exemplo rm -sf gerador`,
`docker volume rm esteira-dashboard_gerador-estado` e `TRUNCATE` das tabelas `otel_*`.
Dados 100% fictícios.
