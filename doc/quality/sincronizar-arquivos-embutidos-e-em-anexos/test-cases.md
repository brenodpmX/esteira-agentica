# Casos de Teste — Sincronizar arquivos embutidos e em anexos

- **Issue:** #345
- **Story relacionada:** complemento à sincronização descendente de texto já
  existente (`src/core/sync.py`), com download de arquivo embutido ou anexado
  no corpo/comentário de uma issue, sob política de segurança por board
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-11-09
- **Branch:** `feature/345-sincronizar_arquivos_embutidos_e_em_anexos`

> Todo caso de teste abaixo é derivado de um dos 14 critérios de aceitação
> (CA-1..CA-14) do corpo da issue #345. Os testes são da suíte Python do motor
> (pytest, em `tests/`). Avaliei a suíte existente antes de propor casos novos
> (ver "Contexto de arquitetura" abaixo) — não há hoje nenhum teste, parsing de
> markdown/URL, ou política de tipo/tamanho de arquivo na suíte; esta é uma
> funcionalidade nova, sem risco de duplicação.

---

## Contexto de arquitetura (baseline do código atual)

Levantamento feito em `src/core/sync.py`, `src/core/board.py`,
`src/adapters/github_board.py`, `src/core/agent_circuit_break.py` e
`src/core/config.py` antes de derivar os casos:

- **Sync descendente hoje é "tudo ou nada" por issue.** `_apply_create_down` e
  `_apply_change_down` (`src/core/sync.py`) sempre reescrevem o `-body.md`
  inteiro (`_compose_down_body`) e o `-history.md` inteiro
  (`_format_history(board_obj.list_comments(...))`) a partir do estado remoto
  completo. Não existe hoje um "sync incremental só do comentário novo": um
  comentário novo é detectado porque o `updated_at` da issue mudou
  (`sync_remote` comparando contra o snapshot), o que dispara um
  `CHANGE_DOWN` que **relê e reescreve todo o `-history.md`**. A cláusula do
  CA-3 ("sem exigir ressincronização do restante da issue") deve ser
  interpretada no nível observável do **trabalho de download de arquivo**: um
  arquivo já baixado em um ciclo anterior não é baixado de novo (idempotência
  por URL/arquivo), ainda que o texto do `-history.md` seja, como hoje,
  reescrito por completo a cada ciclo — isto não é uma regressão desta
  entrega, é o comportamento vigente do texto, fora do escopo de mudança
  (ver "Fora de escopo" do corpo da issue: "qualquer alteração no formato ou
  comportamento atual da sincronização de texto").
- **Não existe hoje nenhum campo de anexos vindo da API nem parsing de
  markdown/links em lugar algum do código.** `Issue.body` e
  `comment["body"]` (`list_comments`, `github_board.py`) são a string
  markdown crua do GitHub. A extração de URL de arquivo embutido/anexado
  (`![alt](url)` para imagem colada, `[nome-do-arquivo](url)` para upload —
  é assim que o GitHub renderiza cada caso na prática, embora a API não
  distinga os dois) precisa ser implementada do zero sobre `issue.body` e
  sobre `comment["body"]`, ANTES de qualquer tentativa de download. Um link
  comum (ex.: para outra issue, um site) não é um arquivo e não deve disparar
  tentativa de download — só URLs cujo caminho termina em uma extensão de
  arquivo são candidatas.
- **`_issue_files` (`sync.py`) já define o prefixo previsível
  `<id>-<slug>`** para os 3 arquivos da issue
  (`.pipe/boards/<board>/<col>/<id>-<slug>-{body,history,addcomment}.md`).
  O diretório de arquivos sincronizados desta entrega deve usar o MESMO
  prefixo, dentro do MESMO diretório de coluna, para que a movimentação entre
  colunas (hoje feita por `Path.rename` em `_apply_change_down`/
  `_apply_create_up`, movendo os 3 arquivos) continue sendo "mover os
  irmãos de mesmo prefixo" — é essa convenção observável que os casos de
  CA-14 verificam, não uma função nomeada em específico.
- **Padrão de comentário idempotente a reusar:** `agent_circuit_break.py`
  publica um comentário de aviso exatamente uma vez por evento, verificando
  antes de publicar se um marcador HTML oculto (`<!-- agent-circuit-break:
  <event_id> -->`) já existe em algum comentário (`_comment_exists`, via
  `board_obj.list_comments`). O aviso de arquivos recusados desta entrega deve
  seguir o mesmo princípio observável: o teste verifica que **não há
  comentário duplicado enquanto o conjunto de arquivos recusados não mudar**,
  e que **muda o conjunto → publica de novo** — sem fixar se a
  implementação usa marcador por hash do conjunto, por nome de arquivo, ou
  outro mecanismo equivalente.
- **Padrão de aplicação de `need_human` a reusar:** `NEED_HUMAN_LABEL`
  (`src/core/commands.py`) é aplicada por código via `board_obj.add_label`
  (ver `agent_circuit_break.py::_reconcile_trip`). É idempotente no board
  (adicionar uma label já presente não duplica) — os casos de modo
  "bloqueante" verificam a PRESENÇA da label após a recusa, não quantas vezes
  `add_label` foi chamado.
- **Padrão de config por board a reusar:** `validate_column_migrations`
  (`src/core/config.py`) é o molde de uma chave opcional em
  `boards.<board_id>.<chave>` — valida só FORMA, citando o caminho da chave
  no `ConfigError`; a chamada vive dentro de `_validate_boards`, no loop por
  board. `tests/test_column_migrations_config.py` é o molde de teste de
  configuração (CT-a: válido aceito; CT-b: ausência válida; CT-c: tipos
  inválidos rejeitados, parametrizado).

> **Decisão de design NÃO fixada pela QA (é do desenvolvimento):** nome exato
> da(s) chave(s) em `pipe.yml` (ex.: `file-sync`, `allowed-types`,
> `max-size-bytes`, `on-reject` são sugestões ilustrativas usadas nos exemplos
> abaixo para tornar os casos executáveis sem ambiguidade — qualquer nome de
> chave equivalente é aceitável), nome do módulo/função que extrai URLs do
> markdown, formato do nome de arquivo local, e exata função que decide
> idempotência do aviso/bloqueio. Os casos abaixo testam **comportamento e
> invariantes observáveis** dos 14 CAs; onde citam um símbolo concreto
> (`_issue_files`, `list_comments`, `add_label`, `_validate_boards`), o alvo é
> o ponto de integração **provável** pela arquitetura atual — se o
> desenvolvimento usar outro símbolo, o caso vale sobre o comportamento
> equivalente.

### Convenções para o desenvolvimento (todos os casos automatizados)

- **Offline, sem rede:** usar um `BoardPort` fake no padrão de
  `tests/test_sync_optimization.py`/`tests/test_full_sync_order.py`,
  estendendo `get_issue`/`list_comments` para devolver `body`/comentários com
  markdown contendo links de arquivo. O "download" em si também não deve
  bater em rede real nos testes: o fake deve servir o conteúdo do arquivo a
  partir de um dado de teste em memória/`tmp_path` (ex.: um stub de cliente
  HTTP injetável, ou o próprio fake de board expondo os bytes do "arquivo
  remoto" por URL), nunca uma chamada HTTP real.
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` autouse por teste,
  mesmo padrão dos demais testes de sync — `.pipe/` isolado por teste.
- **Config mínima:** cada caso de política (Grupos D, E, F, G, H) assume um
  `config: dict` válido com o bloco opcional de política de arquivos dentro de
  `boards.<board_id>` quando pertinente ao cenário (ausente quando o CA testa
  o default).
- **Nunca** fazer `monkeypatch` do próprio núcleo de decisão sob teste (lição
  do incidente #106) — só o provedor de rede/download e o board port são
  substituídos por fakes/espiões.
- **Evidência de log/trace** (CT-18): ler o log estruturado do dia
  (`logs/<data>.json`, mesmo padrão de `tests/test_rate_limit_detection.py`/
  `agent_circuit_break.py`) e localizar o evento pelo campo que identifica a
  recusa — sem exigir um nome de evento específico, apenas que exista e
  contenha identificação do arquivo e motivo.

---

## Rastreabilidade (CA → casos)

| CA | Resumo | Caso(s) de teste |
|----|--------|-------------------|
| CA-1 | Arquivo embutido no corpo → baixado e associado à issue | CT-01, CT-03, CT-08, CT-23 |
| CA-2 | Arquivo anexado (upload) no corpo → baixado e associado à issue | CT-02, CT-03, CT-08, CT-23 |
| CA-3 | Comentário novo com arquivo em issue já sincronizada → sincronizado, sem ressincronizar o resto | CT-05, CT-06, CT-07 |
| CA-4 | Corpo/comentário sem arquivo → comportamento idêntico ao atual | CT-04 |
| CA-5 | Sem lista de tipos declarada → default do motor aplicada | CT-10 |
| CA-6 | Lista de tipos declarada no board → substitui a default | CT-11 |
| CA-7 | Sem limite de tamanho declarado → nenhuma recusa por tamanho | CT-12 |
| CA-8 | Limite de tamanho declarado → excedente recusado independente do tipo | CT-13 |
| CA-9 | Recusa + "aviso" (default) na primeira vez → não baixa, texto sincroniza, comentário único com lista e motivo | CT-14, CT-15, CT-22 |
| CA-10 | Mesmo conjunto recusado já avisado → sem comentário duplicado | CT-16, CT-17 |
| CA-11 | Recusa + "silencioso" → sem mensagem, log/trace com arquivo e motivo | CT-18 |
| CA-12 | Recusa + "bloqueante" → aviso + label `need_human` automática | CT-19 |
| CA-13 | "bloqueante" com arquivo ainda referenciado → recusa e label reaplicadas até deixar de ser referenciado | CT-20, CT-21 |
| CA-14 | Arquivo sincronizado + mudança de coluna → diretório move junto com os 3 arquivos, associação íntegra | CT-09 |

> Cobertura: todos os 14 CAs do corpo da issue têm ao menos um caso; nenhum
> caso existe sem CA de origem. O escopo está completo e internamente
> consistente para derivar estes casos — não há contradição ou lacuna que
> exija devolver ao planejamento.

---

## Grupo A — Download de arquivo embutido/anexado no corpo (CA-1, CA-2, CA-4)

### CT-01 — Arquivo embutido (imagem colada) no corpo é baixado e associado à issue

- **CA de origem:** CA-1.
- **Tipo:** unitário/integração (sync down + extração/download de arquivo)
- **Arquivo/alvo:** `tests/test_file_sync.py` (novo)
- **Pré-condição:** issue remota nova (sem arquivos locais ainda), cujo `body`
  contém markdown de imagem colada, ex.:
  `"Veja o print: ![print](https://user-images.githubusercontent.com/0/img.png)"`.
  Fake de board/download serve bytes conhecidos para essa URL.
- **Passos:**
  1. Disparar a sincronização descendente da issue (ex.: `sync_remote` +
     `apply_changes`, ou chamada direta ao equivalente de
     `_apply_create_down`).
  2. Inspecionar o diretório local da issue.
- **Resultado esperado:** o arquivo `img.png` é baixado e fica disponível em
  um caminho local associado à issue (mesmo diretório/prefixo dos arquivos
  `-body.md`/`-history.md`/`-addcomment.md`, ver CT-08); o conteúdo baixado
  corresponde exatamente aos bytes servidos pelo fake. `-body.md` continua
  contendo o texto original (markdown não é removido/alterado pela
  sincronização de arquivo).
- **Observações:** a URL de teste imita o domínio real de imagem colada do
  GitHub (`user-images.githubusercontent.com`) para que a extração não
  dependa de um domínio fictício aceito só pelo teste.

### CT-02 — Arquivo anexado (upload, link de arquivo não-imagem) no corpo é baixado

- **CA de origem:** CA-2.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue remota nova cujo `body` contém markdown de upload de
  arquivo (sintaxe de link simples, não de imagem), ex.:
  `"Logs em anexo: [erro.log](https://github.com/org/repo/files/1/erro.log)"`.
- **Passos:** mesmos de CT-01.
- **Resultado esperado:** `erro.log` é baixado e fica disponível localmente,
  associado à issue — confirmando que a extração reconhece tanto a sintaxe de
  imagem embutida (`![]()`, CT-01) quanto a de link de upload (`[]()`,
  CT-02), já que a API do board não distingue as duas (conforme a Descrição
  da issue).

### CT-03 — Corpo com múltiplos arquivos (embutido + anexado) baixa todos

- **CA de origem:** CA-1 e CA-2 (cenário combinado).
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** `body` com uma imagem embutida E um arquivo anexado no
  mesmo texto (combinação de CT-01 e CT-02).
- **Passos:** sincronizar a issue; inspecionar o diretório local.
- **Resultado esperado:** ambos os arquivos aparecem localmente, cada um
  distinto e correspondendo ao seu conteúdo de origem; nenhum sobrescreve o
  outro.

### CT-04 — Corpo sem nenhum arquivo: comportamento idêntico ao atual

- **CA de origem:** CA-4.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue remota cujo `body` é só texto, sem nenhum link de
  imagem/arquivo (inclusive um sub-caso com um link comum, ex.:
  `[veja a doc](https://example.com/guia)`, sem extensão de arquivo
  reconhecível na URL).
- **Passos:** sincronizar a issue.
- **Resultado esperado:** `-body.md` é escrito exatamente como hoje (sem
  mudança de formato/conteúdo); nenhuma tentativa de download ocorre (o fake
  de download/HTTP não registra nenhuma chamada); nenhum diretório/arquivo de
  anexos é criado para esta issue.
- **Observações:** cobre explicitamente a cláusula "sem tentativa de
  download" do CA-4 — o teste falha se qualquer chamada de rede for
  registrada, não só se o arquivo não aparecer.

---

## Grupo B — Sincronização incremental em comentários (CA-3)

### CT-05 — Comentário novo com arquivo embutido em issue já sincronizada é sincronizado

- **CA de origem:** CA-3.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue já sincronizada anteriormente (arquivos locais
  `-body.md`/`-history.md`/`-addcomment.md` existentes, sem arquivos
  embutidos/anexados ainda). Um novo comentário remoto é adicionado contendo
  uma imagem embutida; o `updated_at` da issue reflete a novidade.
- **Passos:**
  1. Rodar um novo ciclo de sincronização descendente.
  2. Inspecionar o diretório local.
- **Resultado esperado:** o arquivo do novo comentário é baixado e fica
  disponível localmente, associado à issue; `-history.md` passa a conter o
  novo comentário (comportamento de texto já vigente).

### CT-06 — Comentário novo com arquivo anexado (upload) também é sincronizado

- **CA de origem:** CA-3 (variação de sintaxe, simétrica a CT-02).
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** igual a CT-05, mas o novo comentário usa sintaxe de link
  de upload (`[nome](url)`) em vez de imagem embutida.
- **Passos/Resultado esperado:** iguais a CT-05, confirmando a mesma cobertura
  de sintaxe de CT-02 agora em comentário.

### CT-07 — Novo comentário não refaz o download de arquivos já sincronizados

- **CA de origem:** CA-3 (cláusula "sem exigir ressincronização do restante
  da issue").
- **Tipo:** unitário/integração, idempotência
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue já sincronizada com um arquivo do corpo já baixado
  (estado pós CT-01). Um novo comentário (sem nenhum arquivo, ou com um
  arquivo diferente) é adicionado e um novo ciclo de sync roda.
- **Passos:**
  1. Sincronizar a issue (arquivo do corpo baixado — igual a CT-01).
  2. Adicionar novo comentário remoto e rodar um segundo ciclo de
     sincronização.
  3. Verificar quantas vezes o fake de download foi chamado para a URL do
     arquivo do CORPO (já baixado no passo 1).
- **Resultado esperado:** o arquivo do corpo, já baixado no primeiro ciclo,
  **não é baixado de novo** no segundo ciclo (nenhuma nova chamada de
  download para a mesma URL/arquivo já presente localmente); o arquivo
  continua disponível e íntegro. Se o novo comentário também tiver um
  arquivo, esse (e só esse) é baixado no segundo ciclo.
- **Observações:** o reexame do texto (`-history.md` reescrito por completo a
  cada ciclo, comportamento vigente — ver "Contexto de arquitetura") não é o
  que este caso avalia; o invariante testado é especificamente sobre o
  **trabalho de download de arquivo** não ser refeito.

---

## Grupo C — Diretório previsível e associação com a issue (CA-1, CA-2, CA-14)

### CT-08 — Arquivos sincronizados vivem em diretório com o mesmo prefixo `<id>-<slug>`

- **CA de origem:** CA-1 e CA-2 (cláusula "disponibilização... em um diretório
  previsível... identificado pelo mesmo prefixo" do Escopo).
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue `#77` com slug `exemplo`, na coluna `desenvolvimento`
  do board `entrega`, cujo body tem um arquivo embutido.
- **Passos:**
  1. Sincronizar a issue.
  2. Localizar onde o arquivo baixado foi gravado.
- **Resultado esperado:** o caminho do arquivo baixado está sob o mesmo
  diretório de coluna dos arquivos `-body.md`/`-history.md`/`-addcomment.md`
  desta issue (`.pipe/boards/entrega/desenvolvimento/...`), identificado pelo
  prefixo `77-exemplo` (igual ao prefixo dos 3 arquivos) — não em um caminho
  solto, global, ou sem relação ao `id`/`slug` da issue.

### CT-09 — Diretório de arquivos sincronizados move junto com os 3 arquivos ao trocar de coluna

- **CA de origem:** CA-14.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue `#77` já sincronizada com sucesso com um arquivo
  dentro da política (estado pós CT-08), na coluna `desenvolvimento`. A issue
  muda de coluna no board remoto para `execucao-testes` (simulando o
  `CHANGE_DOWN` que hoje já faz `Path.rename` dos 3 arquivos em
  `_apply_change_down`).
- **Passos:**
  1. Alterar a coluna remota da issue no fake de board.
  2. Rodar o ciclo de sincronização.
  3. Verificar o diretório final dos arquivos (os 3 + os sincronizados).
- **Resultado esperado:** o diretório/arquivos de anexos sincronizados estão
  agora sob `.pipe/boards/entrega/execucao-testes/...` (junto com os 3
  arquivos `-body.md`/`-history.md`/`-addcomment.md` renomeados/movidos para
  lá); nada permanece no diretório antigo (`desenvolvimento`); o conteúdo do
  arquivo sincronizado é preservado (mesmos bytes), e a associação
  arquivo↔issue permanece íntegra (o arquivo segue localizável a partir do
  prefixo `<id>-<slug>` da issue no novo diretório).
- **Observações:** o corpo da issue atribui esse ciclo de vida (criação e
  movimentação do diretório) exclusivamente à pipe, não ao agente — este caso
  testa o resultado observável da movimentação, não qual componente a
  executa.

---

## Grupo D — Política de segurança: tipos de arquivo permitidos (CA-5, CA-6)

### CT-10 — Sem lista declarada no board: default do motor aplicada

- **CA de origem:** CA-5.
- **Tipo:** unitário (decisão de política) + integração (efeito no download)
- **Arquivo/alvo:** `tests/test_file_sync_config.py` (validação/resolução) e
  `tests/test_file_sync.py` (efeito)
- **Pré-condição:** `config` sem qualquer chave de política de arquivos
  declarada para o board `entrega`. Corpo da issue referencia dois arquivos:
  um de tipo presente na lista default (`relatorio.pdf`) e um de tipo fora da
  lista default (`script.sh`).
- **Passos:**
  1. Resolver a política de tipos para o board `entrega` sem declaração.
  2. Sincronizar a issue com os dois arquivos.
- **Resultado esperado:** a lista efetiva aplicada é exatamente a default do
  motor (`png`, `jpg`, `jpeg`, `gif`, `webp`, `pdf`, `txt`, `md`, `csv`,
  `json`, `log`, `zip`); `relatorio.pdf` é baixado normalmente;
  `script.sh` é recusado (não baixado) por não estar na lista.
- **Observações:** parametrizar com pelo menos um representante de cada
  extensão da lista default aceito, e um tipo fora da lista (ex.: `.sh`,
  `.exe`) recusado, para não depender de um único par.

### CT-11 — Lista declarada no board substitui a default (não soma)

- **CA de origem:** CA-6.
- **Tipo:** unitário + integração
- **Arquivo/alvo:** `tests/test_file_sync_config.py` e `tests/test_file_sync.py`
- **Pré-condição:** `config` com o board `entrega` declarando uma lista
  customizada de tipos permitidos que (a) OMITE um tipo presente na lista
  default (ex.: omite `zip`) e (b) INCLUI um tipo ausente da lista default
  (ex.: inclui `mp4`). Corpo com um arquivo `.zip`, um `.mp4` e um `.png`
  (presente em ambas as listas).
- **Passos:**
  1. Resolver a política de tipos para o board com a declaração customizada.
  2. Sincronizar a issue com os três arquivos.
- **Resultado esperado:** `.zip` é RECUSADO (a lista customizada substitui a
  default — não é união); `.mp4` é ACEITO (presente só na lista customizada);
  `.png` é ACEITO (presente em ambas). Confirma que a declaração do board
  **substitui integralmente** a default, não a complementa.

---

## Grupo E — Política de segurança: limite de tamanho (CA-7, CA-8)

### CT-12 — Sem limite declarado no board: nenhuma recusa por tamanho

- **CA de origem:** CA-7.
- **Tipo:** unitário + integração
- **Arquivo/alvo:** `tests/test_file_sync_config.py` e `tests/test_file_sync.py`
- **Pré-condição:** `config` sem limite de tamanho declarado para o board.
  Corpo referencia um arquivo de tipo permitido e tamanho grande (ex.: 50 MB,
  simulado via `Content-Length`/tamanho conhecido do fake, sem precisar
  transferir 50 MB reais em teste).
- **Passos:** sincronizar a issue.
- **Resultado esperado:** o arquivo é baixado normalmente — nenhuma recusa
  por tamanho ocorre independentemente de quão grande seja o arquivo.

### CT-13 — Limite declarado no board recusa arquivo que o excede, mesmo de tipo permitido

- **CA de origem:** CA-8.
- **Tipo:** unitário + integração
- **Arquivo/alvo:** `tests/test_file_sync_config.py` e `tests/test_file_sync.py`
- **Pré-condição:** `config` com limite de tamanho declarado para o board
  (ex.: `1_000_000` bytes). Corpo com dois arquivos de tipo permitido (ex.:
  `.png`): um dentro do limite, outro excedendo-o.
- **Passos:** sincronizar a issue.
- **Resultado esperado:** o arquivo dentro do limite é baixado normalmente; o
  arquivo que excede o limite é recusado — por TAMANHO, independentemente de
  seu tipo estar na lista permitida (a recusa por tamanho é uma verificação
  independente da verificação de tipo, não condicionada a ela).

---

## Grupo F — Comportamento de recusa "aviso" (default) (CA-9, CA-10)

### CT-14 — Primeira recusa em modo "aviso": não baixa, texto sincroniza, comentário único com lista e motivo

- **CA de origem:** CA-9.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** board sem comportamento de recusa declarado (ou declarado
  explicitamente como `aviso` — ver CT-15 para a equivalência). Corpo com um
  arquivo de tipo não permitido (ex.: `script.exe`) e texto normal ao redor.
  Nenhum comentário de aviso publicado ainda para este conjunto de arquivos
  recusados.
- **Passos:**
  1. Sincronizar a issue.
  2. Verificar: (a) se `script.exe` foi baixado; (b) o conteúdo de
     `-body.md`; (c) os comentários publicados no fake de board.
- **Resultado esperado:** `script.exe` NÃO é baixado; `-body.md` é
  sincronizado normalmente (texto completo, sem alteração por causa da
  recusa); exatamente UM comentário é publicado na issue, listando o(s)
  arquivo(s) recusado(s) (`script.exe`) e o motivo da recusa (tipo não
  permitido).

### CT-15 — Ausência de declaração e declaração explícita de "aviso" produzem o mesmo resultado

- **CA de origem:** CA-9 (cláusula "sem comportamento de recusa declarado
  (ou declarado como 'aviso')").
- **Tipo:** unitário (resolução de política)
- **Arquivo/alvo:** `tests/test_file_sync_config.py`
- **Pré-condição:** dois `config` equivalentes para o mesmo cenário de CT-14 —
  um sem a chave de comportamento de recusa, outro com a chave declarada
  explicitamente como `aviso`.
- **Passos:** resolver o comportamento de recusa efetivo para os dois
  `config`.
- **Resultado esperado:** ambos resolvem para o mesmo comportamento efetivo
  (`aviso`) — a ausência da chave é tratada como default idêntico à
  declaração explícita, não como um terceiro estado.

### CT-16 — Mesmo conjunto de arquivos recusados já avisado: sem comentário duplicado

- **CA de origem:** CA-10.
- **Tipo:** unitário/integração, idempotência
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue já recebeu o comentário de aviso para o conjunto
  `{script.exe}` (estado pós CT-14). Um novo ciclo de sincronização roda sem
  nenhuma mudança nos arquivos referenciados (mesmo `script.exe` ainda no
  corpo, nenhum arquivo novo).
- **Passos:**
  1. Rodar um segundo ciclo de sincronização.
  2. Contar quantos comentários de aviso existem na issue.
- **Resultado esperado:** nenhum comentário duplicado é publicado — o total
  de comentários de aviso permanece 1 após o segundo ciclo.

### CT-17 — Conjunto de arquivos recusados muda: novo comentário é publicado (não é duplicata)

- **CA de origem:** CA-10 (contraprova: a dedução é pelo CONJUNTO, não por
  "já existe algum aviso").
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue já avisada para `{script.exe}` (pós CT-14 /CT-16).
  O corpo/comentário passa a referenciar um conjunto DIFERENTE de arquivos
  recusados (ex.: `script.exe` removido do texto e `binario.bin` adicionado,
  também recusado).
- **Passos:** rodar um novo ciclo de sincronização; contar comentários de
  aviso.
- **Resultado esperado:** um NOVO comentário de aviso é publicado, referente
  ao novo conjunto (`{binario.bin}`) — o total de comentários de aviso passa
  a 2 (o anterior, para o conjunto antigo, mais o novo). Confirma que a
  deduplicação do CA-10 é por conjunto de arquivos recusados, não uma
  trava "um aviso por issue para sempre".

---

## Grupo G — Comportamento de recusa "silencioso" (CA-11)

### CT-18 — Recusa em modo "silencioso": sem mensagem na issue, com log/trace

- **CA de origem:** CA-11.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** board com comportamento de recusa declarado como
  `silencioso`. Corpo com um arquivo de tipo não permitido.
- **Passos:**
  1. Sincronizar a issue.
  2. Verificar os comentários publicados no fake de board.
  3. Ler o log estruturado do dia (`logs/<data>.json`) procurando um registro
     da recusa.
- **Resultado esperado:** nenhum comentário é publicado na issue por causa da
  recusa (zero comentários novos); o arquivo não é baixado; existe um
  registro de log (nível trace, conforme o corpo da issue) com identificação
  do arquivo recusado e o motivo da recusa.

---

## Grupo H — Comportamento de recusa "bloqueante" (CA-12, CA-13)

### CT-19 — Primeira recusa em modo "bloqueante": aviso + label `need_human` automática

- **CA de origem:** CA-12.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** board com comportamento de recusa declarado como
  `bloqueante`. Corpo com um arquivo de tipo não permitido. Issue sem a label
  `need_human` antes do ciclo.
- **Passos:**
  1. Sincronizar a issue.
  2. Verificar comentários publicados e as labels da issue no fake de board.
- **Resultado esperado:** o comentário de aviso é publicado (mesmo conteúdo
  mínimo de CT-14 — lista de arquivos recusados e motivo); ALÉM disso, a
  label `need_human` passa a estar presente na issue (aplicada
  automaticamente pela sincronização, sem exigir ação do agente).

### CT-20 — "Bloqueante": arquivo ainda referenciado, recusa e label reaplicadas mesmo após remoção manual da label

- **CA de origem:** CA-13.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue já passou pelo ciclo de CT-19 (label `need_human`
  presente, arquivo recusado ainda referenciado no corpo). Um humano remove a
  label `need_human` no board SEM remover a referência ao arquivo recusado
  do corpo/comentário.
- **Passos:**
  1. Remover a label `need_human` no fake de board (simulando a ação humana).
  2. Rodar um novo ciclo de sincronização.
  3. Verificar as labels da issue após o ciclo.
- **Resultado esperado:** a label `need_human` é REAPLICADA pela
  sincronização, porque o arquivo recusado continua referenciado na fonte —
  a remoção manual da label, isolada, não é suficiente para suprimir a
  recusa enquanto o arquivo continuar no texto (diferente do padrão de
  retomada humana do `agent_circuit_break`, que é um mecanismo distinto — ver
  Fora de escopo/Descrição da issue).

### CT-21 — "Bloqueante": arquivo deixa de ser referenciado, recusa e label cessam

- **CA de origem:** CA-13 (cláusula final: "até que o arquivo deixe de ser
  referenciado na fonte").
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** issue em estado de CT-20 (label reaplicada, arquivo ainda
  referenciado). O corpo/comentário é editado remotamente para remover a
  referência ao arquivo recusado (ex.: o link é apagado do texto).
- **Passos:**
  1. Atualizar o `body` remoto removendo a referência ao arquivo recusado.
  2. Rodar um novo ciclo de sincronização.
  3. Verificar se a recusa é reaplicada e o estado da label.
- **Resultado esperado:** a partir deste ciclo, não há mais nenhum arquivo
  recusado referenciado — nenhuma nova recusa ocorre e a sincronização não
  reaplica a label `need_human` por este motivo (a label pode ou não
  permanecer presente, mas não é a sincronização de arquivos que a reaplica
  neste ciclo, já que não há mais arquivo recusado referenciado).

---

## Grupo I — Interação entre regras (derivado de CA-9 e do Escopo)

### CT-22 — Corpo com arquivo permitido e arquivo recusado juntos: um baixa, outro é recusado, texto sincroniza

- **CA de origem:** CA-9 e a regra do Escopo "Recusa nunca bloqueia a
  sincronização do texto do corpo/comentário — apenas o arquivo recusado não
  é baixado".
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** corpo com um arquivo de tipo permitido (`foto.png`) e um
  arquivo de tipo não permitido (`virus.exe`) no mesmo texto. Comportamento de
  recusa padrão (`aviso`).
- **Passos:** sincronizar a issue; inspecionar arquivos locais, `-body.md` e
  comentários.
- **Resultado esperado:** `foto.png` é baixado normalmente; `virus.exe` é
  recusado (não baixado); `-body.md` contém o texto completo, incluindo a
  referência a ambos os arquivos (a recusa de um não trunca nem bloqueia a
  sincronização do texto); um único comentário de aviso lista apenas
  `virus.exe` (o arquivo aceito não aparece na lista de recusados).

### CT-23 — Dois arquivos de nomes colidentes (um no corpo, outro em comentário) permanecem distintos e associados corretamente

- **CA de origem:** CA-1 e CA-2 (cláusula "fica disponível localmente,
  associado à issue" — a associação deve ser íntegra mesmo sob colisão de
  nome).
- **Tipo:** unitário/integração, caso de borda
- **Arquivo/alvo:** `tests/test_file_sync.py`
- **Pré-condição:** o corpo da issue referencia um arquivo chamado
  `imagem.png` (conteúdo A) e um comentário da mesma issue referencia outro
  arquivo, também chamado `imagem.png` mas em URL diferente (conteúdo B).
- **Passos:** sincronizar a issue; inspecionar os arquivos locais
  resultantes e seu conteúdo.
- **Resultado esperado:** os dois arquivos ficam disponíveis localmente sem
  um sobrescrever o outro — cada um recuperável com o conteúdo correto
  (A e B, respectivamente); nenhum dado é perdido por colisão de nome.
- **Observações:** não fixa a estratégia de desambiguação (ex.: subpasta por
  origem, sufixo, hash) — só o invariante de não perda/sobrescrita de
  conteúdo.

---

## Observações finais

- Nenhum caso cobre sincronização local → board, varredura retroativa de
  issues antigas, ou análise de conteúdo binário (antivírus/sandboxing) — são
  explicitamente Fora de escopo no corpo da issue.
- Os casos de política (Grupos D e E) e de comportamento de recusa (Grupos F,
  G, H) devem compartilhar um helper de fake de board/download único dentro
  de `tests/test_file_sync.py` para reduzir duplicação — decisão de
  organização interna do arquivo de teste, não fixada aqui.
- O arquivo `tests/test_file_sync_config.py` segue o molde de
  `tests/test_column_migrations_config.py`: funções `validate_*`/`resolve_*`
  isoladas, sem rede, parametrizadas para os casos de forma inválida (tipo
  errado, valor vazio/nulo, etc.) análogos aos já cobertos para
  `column-migrations` — a validação de FORMA da(s) nova(s) chave(s) de
  política de arquivos deve seguir o mesmo padrão de `ConfigError` citando o
  caminho da chave, ainda que os CTs acima não enumerem cada combinação de
  forma inválida (responsabilidade do desenvolvimento espelhar o padrão
  existente, como fez para `column-migrations`/`retry`/`agent_circuit_break`).
