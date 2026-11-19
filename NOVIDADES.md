# Novidades

O que muda em cada versão da Esteira Agêntica, em poucas linhas. O campo
`acao` diz o que você precisa fazer ao atualizar; `nenhuma` quer dizer que
basta atualizar. A versão mais recente fica no topo.

## 1.30.0

versao: 1.30.0
data: 2026-11-20
destaques: Agora dá para acompanhar a esteira em painéis de qualquer ferramenta compatível com OpenTelemetry. Execuções de agentes, fila de sincronismo, limites de consumo e o estado do board chegam ao seu coletor, e um coletor fora do ar nunca atrasa o trabalho das issues.
acao: nenhuma. Para ligar, defina OTEL_EXPORTER_OTLP_ENDPOINT e siga o guia de telemetria.

## 1.29.0

versao: 1.29.0
data: 2026-11-09
destaques: Imagens e arquivos colados ou anexados nas issues agora chegam junto com o texto. A esteira baixa o que está no corpo e nos comentários e guarda ao lado dos arquivos da issue, pronto para o agente usar. Você escolhe, por board, quais tipos e tamanhos aceitar e se um arquivo recusado vira só um aviso ou pede ajuda humana.
acao: nenhuma. Para restringir tipos ou tamanho, use boards.<board_id>.file-sync, descrita na referência de configuração.
