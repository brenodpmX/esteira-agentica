# Casos de Teste — Primeira vitrine de exemplos executáveis da Esteira com validação interna e governança

- **Issue:** #312
- **Story relacionada:** n/a (issue única; bloqueia #317)
- **Autor(a):** André Tavares — Engenheiro de Qualidade PL (QA)
- **Data:** 2026-11-10
- **Branch:** `feature/312-primeira_vitrine_de_exemplos_executaveis_da_esteira_com_validacao_interna_e_governanca`

> Todo caso de teste é vinculado a um critério de aceitação (CA) da issue #312.
> Nenhum caso existe sem CA de origem. Cada caso tem resultado esperado
> explícito e verificável. Testes automatizados são da suíte Python do motor
> (pytest, em `tests/`); os marcados **manual** dependem de ambiente real
> (GitHub Project + kiro-cli) e são evidenciados por registro de validação
> interna (CA-8), não por pytest.

---

## 1. Baseline da suíte existente (avaliado antes de criar casos)

- Não existe `exemplos/`, nem `doc/exemplos/`, nem `pipe.yml`/`contexts/` de
  exemplo versionados. `.gitignore` ignora `pipe.yml` e `contexts/` **em
  qualquer profundidade** → sem exceção explícita, os pacotes de exemplo nunca
  seriam versionados (caso CT-03).
- Reutilizar, sem reescrever, o validador real do motor:
  `src.core.config.check_config()` (usa os globais `PIPE_FILE` e, via
  `_validate_agents`, `CONTEXTS_DIR`; exige `PIPE_SSH_KEY_FILE` apontando para
  arquivo existente, `project.name/summary`, `git.flow.<flow>.branch_pattern`,
  contexto **não vazio** em `contexts/<plataforma>/<agente>.md`). Padrão de
  teste a seguir: `tests/test_branch_pattern_config.py`,
  `tests/test_project_config.py`, `tests/test_agent_timeout_config.py`
  (monkeypatch de `config.PIPE_FILE` / `config.CONTEXTS_DIR` + `tmp_path`).
- Versão do motor: `src.core.version.VERSION` (hoje `1.29.0`).
- Plataforma de agente vigente: `kiro-cli` → contextos em
  `contexts/kiro-cli/<agente>.md`.

## 2. Decisões de especificação (ambiguidades pequenas resolvidas aqui)

O escopo deixa o *local/formato* dos artefatos em aberto (tecnologia e
empacotamento estão fora de escopo). Para os testes serem implementáveis sem
ambiguidade, fixa-se o **contrato mínimo de layout** abaixo; ele não define
tecnologia nem distribuição, apenas onde os testes procuram. Desenvolvimento
deve criar exatamente estes caminhos.

```
exemplos/
  minimalista/
    pipe.yml
    contexts/kiro-cli/<agente>.md        # um por agente de pipe.yml
    exemplo.yml                          # os 8 campos mínimos
    USO.md                               # documentação de uso
    CUSTOMIZACAO.md                      # documentação de customização
    issue-exemplo.md                     # issue de exemplo (hipotética)
  referencia-hipotetica/                 # mesma estrutura
doc/exemplos/
  validacao-interna.md                   # processo + formato do registro
  apresentacao.md                        # roteiro + formato do registro
  manutencao-por-impacto.md              # regra RF-07/RN-08
  reavaliacao-temas.md                   # regra RF-08/RN-10
  registros/
    validacao/<exemplo>-<AAAA-MM-DD>-<n>.md
    apresentacao/<exemplo>-<AAAA-MM-DD>-<n>.md
    impacto/                              # avaliações de impacto
    reavaliacao/                          # solicitação ao entrar em produção
.gitignore                               # exceções para exemplos/**/pipe.yml e exemplos/**/contexts/
```

Convenções:

- `<exemplo>` ∈ {`minimalista`, `referencia-hipotetica`}.
- `exemplo.yml` contém exatamente (no mínimo) as chaves: `objetivo`, `publico`,
  `caso_de_uso`, `pre_requisitos`, `resultado_esperado`, `limites`,
  `versao_suportada`, `responsavel_pela_revisao`. O de Referência contém ainda
  `diferenca_em_relacao_ao_minimalista`. Ambos contêm `gatilho_de_revisao`
  (RN-09).
- `responsavel_pela_revisao` é um **papel** (ex.: "Mantenedor(a) da Esteira"),
  nunca nome de pessoa real (RN-02).
- `versao_suportada` segue `MAJOR.MINOR.PATCH` e **não excede**
  `src.core.version.VERSION`.
- Registros usam linhas `chave: valor` (uma por linha, no início da linha),
  parseáveis por regex `^([a-z_]+):\s*(.*)$`. Registros trazem ainda `data`
  (`AAAA-MM-DD`) — campo extra permitido, necessário para ordenar CA-10.
- `CUSTOMIZACAO.md` tem as seções `## Valores substituíveis` e
  `## Configuração fixa`, e um bloco ` ```yaml ` marcado com a linha anterior
  `<!-- ajuste-testavel -->` contendo `caminho` (caminho pontilhado em
  `pipe.yml`, ex.: `boards.<id>.columns.<col>.target-prompt`) e `novo_valor`.
  O caminho deve estar listado em `## Valores substituíveis` e **não** em
  `## Configuração fixa`.
- `USO.md` tem as seções `## Pré-requisitos`, `## Como aplicar` e
  `## Resultado observável`.
- Rótulo de hipotético: as 15 primeiras linhas de `USO.md` e de `exemplo.yml`
  (comentário `#`) e de `issue-exemplo.md` contêm "hipotétic" (case-insensitive).
- Resultado observável (RF-01/02): `resultado_esperado` cita ao menos um de
  "coluna", "comentário" ou "pull request", e o encadeamento
  `change.advance` a partir da coluna de entrada chega a uma coluna com
  `archive: true` (estado final alcançável).
- Placeholders permitidos para identificadores: org `exemplo-org`, repositório
  terminado em `-hipotetico`, e-mails apenas em domínios `example.com|.org|.net`.

Decisão registrada: CA-3 e CA-4 (execução ponta a ponta contra GitHub real e
validador humano) **não são automatizáveis em pytest**; a evidência é o
registro de validação (CA-8/CA-10) + a verificação estática automatizada de que
o ciclo é *configurado* para chegar ao estado final (CT-05, CT-06, CT-07).

---

## 3. Rastreabilidade (CA → casos)

| Critério de aceitação | Caso(s) de teste |
|-----------------------|------------------|
| CA-1 (exatamente 2 pacotes) | CT-01, CT-02 |
| CA-2 (oito campos presentes e não vazios) | CT-08, CT-09 |
| CA-3 (issue na coluna de entrada → resultado observável sem intervenção) | CT-04, CT-05, CT-06, CT-07, CT-24 (manual) |
| CA-4 (validação somente com documentação de uso) | CT-10, CT-11, CT-24 (manual) |
| CA-5 (Referência > Minimalista, diferença justificada) | CT-12, CT-13 |
| CA-6 (customização mantém resultado; substituível ≠ fixo) | CT-14, CT-15 |
| CA-7 (sem dado real; rotulado hipotético) | CT-16, CT-17, CT-18 |
| CA-8 (registro de validação completo; custo amarrado) | CT-19, CT-20, CT-21 |
| CA-9 (registro de apresentação com decisão) | CT-22, CT-23 |
| CA-10 (validação com sucesso antes da apresentação) | CT-25 |
| CA-11 (regra de avaliação de impacto) | CT-26, CT-27 |
| CA-12 (reavaliação de temas ao entrar em produção) | CT-28, CT-29 |

Mapeamento dos cenários obrigatórios da issue (CT-01..CT-10 do corpo) →
casos deste documento: cenário 1→CT-04..07/24; 2→CT-04..07/12/24;
3→CT-10/11/24; 4→CT-14/15; 5→CT-16..18; 6→CT-08/09; 7→CT-19..21;
8→CT-22/23; 9→CT-21 (falha registrada); 10→CT-27.

---

## 4. Casos de teste

Arquivos de teste previstos (a criar pelo desenvolvimento):

- `tests/test_vitrine_estrutura.py` — CT-01..03, 08..13, 16..18
- `tests/test_vitrine_config.py` — CT-04..07, 14, 15
- `tests/test_vitrine_registros.py` — CT-19..23, 25
- `tests/test_vitrine_governanca.py` — CT-26..29
- Helper opcional: `tests/_vitrine_helpers.py` (parse de `chave: valor`, carga de
  `exemplo.yml`, cópia do pacote para `tmp_path`).

Fixture comum de `test_vitrine_config.py`: copiar `exemplos/<x>/` para
`tmp_path`; `monkeypatch.setattr(config, "PIPE_FILE", tmp/"pipe.yml")`;
`monkeypatch.setattr(config, "CONTEXTS_DIR", tmp/"contexts")`;
`monkeypatch.setenv("PIPE_SSH_KEY_FILE", <arquivo vazio em tmp_path>)`.
Parametrizar por `("minimalista", "referencia-hipotetica")`.

### CT-01 — Existem exatamente dois pacotes de exemplo

- **CA de origem:** CA-1 (RN-01)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_exatamente_dois_pacotes`
- **Pré-condição:** repositório com `exemplos/`.
- **Passos:**
  1. Listar subdiretórios imediatos de `exemplos/` que contêm `pipe.yml`.
- **Resultado esperado:** conjunto == `{"minimalista", "referencia-hipotetica"}`
  (tamanho 2, nomes exatos).
- **Observações:** diretórios sem `pipe.yml` (ex.: README do índice) não contam.

### CT-02 — Nenhum tema fora de escopo vira exemplo

- **CA de origem:** CA-1 (RN-01, fora de escopo)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_nenhum_tema_extra`
- **Pré-condição:** idem CT-01.
- **Passos:**
  1. Varrer nomes de diretórios/arquivos sob `exemplos/` (case-insensitive,
     sem acento).
- **Resultado esperado:** nenhum nome contém `kanban`, `scrum`, `academico`,
  `xgh`, `gestao`, `rh`(palavra inteira), `atendimento`.
- **Observações:** conteúdo textual pode *mencionar* temas como "fora de escopo"
  em `doc/exemplos/reavaliacao-temas.md`; a varredura é só de nomes sob `exemplos/`.

### CT-03 — Pacotes de exemplo são versionáveis (não ignorados pelo git)

- **CA de origem:** CA-1 (pacote "publicado"; `.gitignore` ignora `pipe.yml` e `contexts/`)
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_pacotes_nao_ignorados_pelo_git`
- **Pré-condição:** repositório git; pacotes criados.
- **Passos:**
  1. Para cada pacote, executar `git check-ignore -q` sobre `pipe.yml`, cada
     `contexts/kiro-cli/*.md`, `exemplo.yml`, `USO.md`, `CUSTOMIZACAO.md`.
  2. Verificar que `git ls-files exemplos/` (após `git add`, ou usando
     `git check-ignore` como proxy) lista esses arquivos.
- **Resultado esperado:** `git check-ignore` retorna código 1 (não ignorado)
  para todos. `pipe.yml` e `contexts/` na **raiz** continuam ignorados
  (`git check-ignore pipe.yml` → 0), ou seja, a exceção é restrita a `exemplos/`.
- **Observações:** requer exceções em `.gitignore` do tipo
  `!exemplos/**/pipe.yml` e `!exemplos/**/contexts/`. Pular (`skip`) se `git`
  indisponível no ambiente.

### CT-04 — `pipe.yml` de cada exemplo é aceito pelo validador real do motor

- **CA de origem:** CA-3 (RF-01, RF-02, RN-04)
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_vitrine_config.py::test_check_config_aceita_exemplo`
- **Pré-condição:** fixture comum (ver §4).
- **Passos:**
  1. Chamar `config.check_config()` com o pacote copiado.
- **Resultado esperado:** retorna `dict` sem levantar `ConfigError`; `config["boards"]`
  tem ao menos 1 board; `config["project"]["name"]` e `["summary"]` não vazios.
- **Observações:** não alterar `pipe.yml` publicado para passar (RNF-01).

### CT-05 — Contextos de agente: um por agente, no padrão, não vazios

- **CA de origem:** CA-3 (RN-04)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_config.py::test_contextos_preenchidos_padrao`
- **Pré-condição:** pacote lido de `exemplos/<x>/`.
- **Passos:**
  1. Ler `pipe.yml`; para cada `agents.<plataforma>.<agente>` (exceto `limits`),
     abrir `exemplos/<x>/contexts/<plataforma>/<agente>.md`.
  2. Listar arquivos em `exemplos/<x>/contexts/**` e comparar com os agentes declarados.
- **Resultado esperado:** cada arquivo existe e `.strip()` tem ≥ 50 caracteres;
  não há arquivo de contexto órfão (sem agente declarado) nem agente sem arquivo.
- **Observações:** negativo: remover/esvaziar um contexto na cópia e confirmar que
  `check_config()` levanta `ConfigError` mencionando "ausentes" / "vazios"
  (`test_contexto_vazio_reprova_exemplo`).

### CT-06 — Fluxo configurado chega a estado final observável

- **CA de origem:** CA-3 (RF-01, RF-02, glossário "resultado observável")
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_config.py::test_encadeamento_chega_ao_estado_final`
- **Pré-condição:** `pipe.yml` do pacote carregado (yaml).
- **Passos:**
  1. Identificar a coluna de entrada (primeira coluna do board; sem `agent`).
  2. Seguir `change.advance` coluna a coluna a partir da primeira coluna com agente,
     detectando ciclos (limite = nº de colunas).
- **Resultado esperado:** (a) a coluna de entrada existe e a primeira coluna com
  `agent` é alcançada; (b) todo `advance` aponta para coluna existente do mesmo
  board; (c) não há ciclo; (d) a cadeia termina em coluna com `archive: true`;
  (e) toda coluna com `agent` tem `target-prompt` não vazio.
- **Observações:** verificação estática do "ciclo completo"; a execução real é CT-24.

### CT-07 — `resultado_esperado` declara um resultado observável concreto

- **CA de origem:** CA-3 (RF-01/RF-02 "resultado observável descrito")
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_config.py::test_resultado_esperado_observavel`
- **Pré-condição:** `exemplo.yml` carregado.
- **Passos:**
  1. Ler `resultado_esperado` e `USO.md` (`## Resultado observável`).
- **Resultado esperado:** `resultado_esperado` contém (case-insensitive) ao menos
  um de "coluna", "comentário", "pull request"; a seção `## Resultado observável`
  de `USO.md` existe, não vazia, e cita o mesmo tipo de evidência; nome da coluna
  final citado existe em `pipe.yml`.
- **Observações:** riscos da issue exigem fixar o estado final por exemplo.

### CT-08 — Os oito campos mínimos estão presentes

- **CA de origem:** CA-2 (RF-05, RNF-03)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_oito_campos_presentes`
- **Pré-condição:** `exemplo.yml` de cada pacote.
- **Passos:**
  1. Carregar com `yaml.safe_load`.
  2. Conferir as chaves `objetivo`, `publico`, `caso_de_uso`, `pre_requisitos`,
     `resultado_esperado`, `limites`, `versao_suportada`, `responsavel_pela_revisao`.
- **Resultado esperado:** as 8 chaves presentes em ambos os pacotes. Também
  presente: `gatilho_de_revisao` (RN-09).

### CT-09 — Os oito campos não estão vazios e têm formato válido

- **CA de origem:** CA-2 (RF-05, RN-09, RNF-03)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_campos_nao_vazios_e_validos`
- **Pré-condição:** idem CT-08.
- **Passos:**
  1. Para cada campo, normalizar (`str`/lista → texto) e `.strip()`.
  2. Validar `versao_suportada` por regex `^\d+\.\d+\.\d+$` e `<= VERSION` (tupla de ints).
  3. Negativo: com a cópia do `exemplo.yml` removendo cada campo, uma função de
     verificação (`verificar_campos_minimos(dict)` — helper público do pacote de
     testes) deve reportar exatamente o campo faltante / vazio.
- **Resultado esperado:** nenhum campo vazio/`null`/só espaços; `versao_suportada`
  válida; `responsavel_pela_revisao` não vazio e `gatilho_de_revisao` não vazio;
  o negativo reporta o campo removido (exemplo "não publicado").
- **Observações:** `pre_requisitos` pode ser lista; deve ter ≥ 1 item.

### CT-10 — `USO.md` é autossuficiente quanto à estrutura e aos pré-requisitos

- **CA de origem:** CA-4 (RF-03, RN-03, RNF-04)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_uso_md_secoes_obrigatorias`
- **Pré-condição:** `USO.md` de cada pacote.
- **Passos:**
  1. Verificar seções `## Pré-requisitos`, `## Como aplicar`, `## Resultado observável`.
  2. Cada seção tem ≥ 3 linhas de conteúdo não vazias.
  3. `## Pré-requisitos` menciona `PIPE_SSH_KEY_FILE` e o item de GitHub Project/board
     (pré-requisitos de ambiente ficam declarados **antes** da execução —
     falha por pré-requisito não conta como falha do exemplo).
- **Resultado esperado:** seções presentes e preenchidas; pré-requisitos de
  ambiente declarados; cada pré-requisito de `exemplo.yml.pre_requisitos` aparece
  (por palavra-chave) em `USO.md`.

### CT-11 — Toda referência de `USO.md` a arquivo/caminho local existe no pacote

- **CA de origem:** CA-4 (RN-03; sem conhecimento não documentado)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_referencias_do_uso_resolvem`
- **Pré-condição:** `USO.md` e `CUSTOMIZACAO.md`.
- **Passos:**
  1. Extrair, de trechos em crase, caminhos terminados em `.yml`, `.md` ou iniciados
     por `contexts/` ou `exemplos/`.
  2. Resolver relativo ao pacote (ou à raiz do repo para `exemplos/`/`doc/`).
- **Resultado esperado:** todos os caminhos citados existem; `USO.md` cita
  `pipe.yml` e `contexts/kiro-cli/<agente>.md` de cada agente do pacote e o
  nome da coluna de entrada em que a issue de exemplo deve ser criada
  (a mesma de `pipe.yml`); `issue-exemplo.md` existe e é citado.
- **Observações:** não-automatizável por completo — o julgamento "nenhuma etapa
  exige conhecimento não documentado" é de CT-24; este caso cobre o que é mecânico.

### CT-12 — Referência demonstra mais de uma coluna e/ou agente que o Minimalista

- **CA de origem:** CA-5 (RF-02)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_config.py::test_referencia_mais_rica_que_minimalista`
- **Pré-condição:** `pipe.yml` de ambos carregados.
- **Passos:**
  1. Contar colunas, colunas com `agent` e agentes distintos de cada pacote.
- **Resultado esperado:** Minimalista: exatamente 1 board, exatamente 1 agente,
  exatamente 1 coluna com agente, ≤ 3 colunas. Referência: colunas
  (`>` Minimalista) **e** (colunas com agente ≥ 2 **ou** agentes distintos ≥ 2);
  ≥ 4 colunas; todos os agentes de colunas usados existem em `agents`.
- **Observações:** o Minimalista é "o menor": remover qualquer coluna/agente
  quebraria o fluxo de ponta a ponta (entrada → execução → final).

### CT-13 — Diferença de conteúdo da Referência é compreensível e justificada

- **CA de origem:** CA-5
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_diferenca_justificada`
- **Pré-condição:** `exemplo.yml` da Referência.
- **Passos:**
  1. Ler `diferenca_em_relacao_ao_minimalista`.
- **Resultado esperado:** não vazio, ≥ 80 caracteres, e cita pelo menos um dos
  nomes de coluna ou de agente que existem só na Referência (comparação com
  `pipe.yml`). `exemplo.yml` do Minimalista **não** precisa do campo.
- **Observações:** "compreensível" = cita elementos concretos, não texto genérico.

### CT-14 — Customização documentada: substituível ≠ fixo

- **CA de origem:** CA-6 (RF-03)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_customizacao_separa_substituivel_de_fixo`
- **Pré-condição:** `CUSTOMIZACAO.md` de cada pacote.
- **Passos:**
  1. Verificar seções `## Valores substituíveis` e `## Configuração fixa`.
  2. Extrair os caminhos pontilhados listados em cada seção (entre crases).
  3. Extrair o bloco `<!-- ajuste-testavel -->` (`caminho`, `novo_valor`).
- **Resultado esperado:** ambas as seções preenchidas; interseção entre os
  caminhos das duas seções é vazia; `caminho` do ajuste testável está em
  `Valores substituíveis`, não em `Configuração fixa`, e resolve a uma chave
  existente em `pipe.yml`; `git.repo.main` aparece como substituível.

### CT-15 — Após o ajuste documentado, o exemplo continua válido e com resultado observável

- **CA de origem:** CA-6 (RF-03, CT-04 do corpo)
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_vitrine_config.py::test_ajuste_documentado_preserva_resultado`
- **Pré-condição:** fixture comum.
- **Passos:**
  1. Aplicar `novo_valor` em `caminho` no `pipe.yml` copiado (dump com `yaml.safe_dump`).
  2. Rodar `config.check_config()`.
  3. Reexecutar a verificação de encadeamento de CT-06.
- **Resultado esperado:** sem `ConfigError`; encadeamento ainda chega a coluna
  `archive: true`; `novo_valor` ≠ valor original (o ajuste é efetivo).
- **Observações:** negativo (`test_ajuste_em_valor_fixo_nao_e_prometido`): alterar
  uma chave listada em `Configuração fixa` não precisa preservar o resultado — o
  teste apenas confirma que ela **não** está prometida como substituível (já coberto
  por CT-14; aqui só documentar).

### CT-16 — Nenhum segredo/credencial/PII em nenhum artefato publicado

- **CA de origem:** CA-7 (RN-02, RNF-02)
- **Tipo:** unitário (varredura)
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_varredura_sem_dados_sensiveis`
- **Pré-condição:** todos os arquivos sob `exemplos/` e `doc/exemplos/`.
- **Passos:**
  1. Varrer texto com regex: chave privada (`-----BEGIN .*PRIVATE KEY-----`), tokens
     (`ghp_[A-Za-z0-9]{20,}`, `github_pat_`, `AKIA[0-9A-Z]{16}`, `xox[abp]-`,
     `sk-[A-Za-z0-9]{20,}`), `password\s*[:=]\s*\S+`, CPF/CNPJ
     (`\d{3}\.\d{3}\.\d{3}-\d{2}`, `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}`), telefone
     (`\(?\d{2}\)?\s?9?\d{4}-\d{4}`), IPv4 públicos, e-mails fora de
     `example.(com|org|net)`.
- **Resultado esperado:** zero ocorrências. `git.repo.main` casa com
  `^git@github\.com:exemplo-org/[a-z0-9-]+-hipotetico\.git$`; nenhum `PIPE_SSH_KEY_FILE`
  com valor literal de caminho real é gravado (apenas referência ao nome da variável).
- **Observações:** negativo: injetar `ghp_` + 30 chars numa cópia e confirmar que
  a função de varredura reprova (`test_varredura_detecta_segredo_injetado`).

### CT-17 — Cenário rotulado como hipotético em todo artefato textual

- **CA de origem:** CA-7 (RN-02)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_cenario_rotulado_hipotetico`
- **Pré-condição:** pacotes publicados.
- **Passos:**
  1. Nas 15 primeiras linhas de `USO.md`, `exemplo.yml`, `issue-exemplo.md` e
     `CUSTOMIZACAO.md` de cada pacote, buscar "hipotétic" (case-insensitive).
- **Resultado esperado:** presente em todos; `pipe.yml` contém comentário
  `# ... hipotético ...` no cabeçalho e `project.name`/`summary` contêm "hipotétic".

### CT-18 — Cenário generalizado: sem identificadores reais de pessoa/empresa

- **CA de origem:** CA-7 (RN-02, "comportamento em falha: cenário se aproxima de instalação real")
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_estrutura.py::test_sem_identificadores_reais`
- **Pré-condição:** pacotes publicados.
- **Passos:**
  1. Verificar `project.humans` (se presente) em cada `pipe.yml` e `responsavel_pela_revisao`.
  2. Verificar que nenhum arquivo cita as org/repos reais deste projeto (ex.:
     `brenodpmX`, o nome real do repositório da Esteira em URLs).
- **Resultado esperado:** `humans[].name` (se existir) começa com "Pessoa " ou é um
  papel (ex.: "Pessoa Exemplo A"); nenhuma menção a `brenodpmX` ou a URL de remoto
  real do repositório; `responsavel_pela_revisao` é papel, não nome próprio.

### CT-19 — Processo de validação interna documentado com os 13 campos

- **CA de origem:** CA-8 (RF-04)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_registros.py::test_processo_validacao_documenta_campos`
- **Pré-condição:** `doc/exemplos/validacao-interna.md`.
- **Passos:**
  1. Ler o documento e procurar cada campo como `chave:` no bloco de formato.
- **Resultado esperado:** presentes `exemplo`, `versao_suportada`, `resultado`,
  `ponto_da_falha`, `ajuda_necessaria`, `tempo_observado`, `falhas`, `duvidas`,
  `qualidade_vs_objetivo`, `modelo`, `tokens`, `custo`, `cenario`; o documento
  afirma que o validador usa **somente** `USO.md` (RN-03) e descreve a regra de
  que lacuna de documentação = falha do exemplo; descreve que execução com falha
  também gera registro.

### CT-20 — Registro de validação válido: campos obrigatórios completos

- **CA de origem:** CA-8 (RF-04)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_registros.py::test_registros_validacao_completos`
- **Pré-condição:** arquivos em `doc/exemplos/registros/validacao/`.
- **Passos:**
  1. Parsear cada registro (`chave: valor`).
  2. Verificar os 13 campos + `data`.
- **Resultado esperado:** todos presentes e não vazios; exceção documentada: `ponto_da_falha`
  pode ser `n/a` quando `resultado: sucesso`, **e é obrigatório e ≠ `n/a`** quando
  `resultado: falha`; `resultado ∈ {sucesso, falha}`; `exemplo` ∈ os dois pacotes;
  `versao_suportada` casa com `exemplo.yml` do pacote; `data` é data válida.
  Existe ≥ 1 registro por pacote.

### CT-21 — Custo/tokens amarrados a modelo, cenário e versão; falha também gera registro

- **CA de origem:** CA-8 (RN-06, RNF-05; CT-09 do corpo)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_registros.py::test_custo_amarrado_e_falha_registrada`
- **Pré-condição:** idem CT-20; mais validador `validar_registro_validacao(dict)`.
- **Passos:**
  1. Para registros com `tokens` ou `custo` ≠ `n/a`: exigir `modelo`, `cenario`,
     `versao_suportada` não vazios; rejeitar expressões "típico", "universal",
     "médio geral" nos campos `tokens`/`custo`.
  2. Negativos sobre dict sintético: (a) custo informado sem `modelo` → inválido;
     (b) `resultado: falha` sem `ponto_da_falha` → inválido; (c)
     `resultado: falha` com `ponto_da_falha` preenchido e demais campos → válido;
     (d) `ajuda_necessaria` ≠ "nenhuma" em registro `sucesso` exige `duvidas` ou
     `falhas` descrever a lacuna — validar apenas que o campo existe e não é vazio.
- **Resultado esperado:** todos os registros reais passam; negativos reprovam com
  mensagem citando o campo.
- **Observações:** o validador é função utilitária em `tests/_vitrine_helpers.py`
  (ou módulo do motor, a critério do dev); o caso exige comportamento, não local.

### CT-22 — Roteiro e formato de registro de apresentação documentados

- **CA de origem:** CA-9 (RF-06)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_registros.py::test_apresentacao_documenta_roteiro_e_formato`
- **Pré-condição:** `doc/exemplos/apresentacao.md`.
- **Passos:**
  1. Ler o documento.
- **Resultado esperado:** contém seção `## Roteiro` (≥ 5 linhas) e bloco de formato
  com `compreensao_observada`, `decisao`, `objecoes`, `proximo_passo`; declara
  `decisao ∈ {interesse, recusa, pendente}`; declara que recusa exige ≥ 1 objeção
  e que `pendente` exige `proximo_passo` "acompanhamento agendado"; declara que
  opinião/visualização genérica não substitui decisão (RN-07) e que não há meta
  numérica (RN-05).

### CT-23 — Validador do registro de apresentação aplica as regras de decisão

- **CA de origem:** CA-9 (RF-06, RN-07)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_registros.py::test_registro_apresentacao_regras`
- **Pré-condição:** validador `validar_registro_apresentacao(dict)` + registros reais (se existirem).
- **Passos:**
  1. Casos sintéticos: (a) interesse com todos os campos → válido; (b) recusa com
     `objecoes` vazio → inválido; (c) recusa com 1 objeção → válido; (d) `pendente` sem
     `proximo_passo` → inválido; (e) `pendente` com `proximo_passo: acompanhamento agendado ...`
     → válido; (f) `decisao` ausente ou fora do conjunto (ex.: "gostou") → inválido;
     (g) `compreensao_observada` vazia → inválido.
  2. Para cada registro real em `doc/exemplos/registros/apresentacao/`, aplicar o validador.
- **Resultado esperado:** casos (a),(c),(e) válidos; (b),(d),(f),(g) inválidos;
  registros reais (se houver) válidos.
- **Observações:** diretório de registros de apresentação pode estar vazio na
  entrega (nenhuma apresentação ainda); o teste não falha por isso.

### CT-24 — Execução ponta a ponta de cada exemplo por validador interno (manual)

- **CA de origem:** CA-3 e CA-4 (CT-01, CT-02, CT-03 do corpo)
- **Tipo:** manual (E2E, evidenciado por registro de validação)
- **Arquivo/alvo:** `doc/exemplos/registros/validacao/<exemplo>-<data>-<n>.md`
- **Pré-condição:** ambiente com pré-requisitos de `USO.md` (chave SSH, GitHub
  Project de teste, kiro-cli); validador sem acesso a informação além de `USO.md`.
- **Passos:**
  1. Aplicar o pacote seguindo apenas `USO.md`.
  2. Criar a issue de `issue-exemplo.md` na coluna de entrada.
  3. Observar o resultado (coluna/comentário/PR) e cronometrar.
  4. Preencher o registro de validação.
- **Resultado esperado:** `resultado: sucesso`, `ajuda_necessaria: nenhuma`, resultado
  observável idêntico ao de `resultado_esperado`, `pipe.yml`/contextos inalterados.
  Se o validador precisar de conhecimento não documentado: `resultado: falha`
  (lacuna de documentação), corrigir `USO.md` e repetir.
- **Observações:** a existência e consistência do registro são verificadas por
  CT-20/21/25. Esta execução não bloqueia o pytest, mas bloqueia a apresentação
  (CA-10) e o veredito de QA da issue.

### CT-25 — Apresentação só existe após validação interna com sucesso do mesmo exemplo

- **CA de origem:** CA-10
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_registros.py::test_apresentacao_exige_validacao_previa`
- **Pré-condição:** `registros/validacao/` e `registros/apresentacao/`.
- **Passos:**
  1. Para cada registro de apresentação (campos `exemplo`, `data`), buscar registro de
     validação do mesmo `exemplo` com `resultado: sucesso` e `data` ≤ data da apresentação.
  2. Teste sintético com função `validacao_previa_existe(exemplo, data, registros)`:
     (a) sem nenhum registro → False; (b) só `falha` → False; (c) `sucesso` com
     data posterior → False; (d) `sucesso` anterior de outro exemplo → False;
     (e) `sucesso` anterior do mesmo exemplo → True.
- **Resultado esperado:** todo registro real de apresentação satisfaz a regra;
  sintéticos (a)–(d) False e (e) True. `doc/exemplos/apresentacao.md` declara a
  pré-condição explicitamente.

### CT-26 — Regra escrita de avaliação de impacto existe e obriga

- **CA de origem:** CA-11 (RF-07, RN-08)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_governanca.py::test_regra_impacto_escrita_e_obrigatoria`
- **Pré-condição:** `doc/exemplos/manutencao-por-impacto.md`.
- **Passos:**
  1. Ler o documento.
- **Resultado esperado:** contém "etapa de documentação"; usa termo de obrigação
  ("deve"/"obrigatóri"); descreve os dois desfechos (afeta → atualizar e revalidar;
  não afeta → registrar ausência de impacto); define formato do registro de impacto
  com `mudanca`, `afeta_exemplo` (`sim|nao`), `exemplos_afetados`, `acao`,
  `revalidacao`; declara que exemplo desatualizado sem avaliação é **falha de
  processo**; declara explicitamente que é processo, não automação.

### CT-27 — Validador de registro de impacto (com e sem necessidade de atualização)

- **CA de origem:** CA-11 (CT-10 do corpo, RNF-06)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_governanca.py::test_registro_impacto_regras`
- **Pré-condição:** validador `validar_registro_impacto(dict)`.
- **Passos:**
  1. Sintéticos: (a) `afeta_exemplo: nao` com justificativa em `acao` → válido;
     (b) `afeta_exemplo: sim` com `exemplos_afetados` e `revalidacao` referenciando um
     registro de validação → válido; (c) `afeta_exemplo: sim` sem `revalidacao` → inválido;
     (d) `afeta_exemplo` ausente/outro valor → inválido; (e) `mudanca` vazia → inválido.
  2. Registros reais em `registros/impacto/` (se houver) passam no validador.
- **Resultado esperado:** (a),(b) válidos; (c),(d),(e) inválidos.
- **Observações:** diretório pode estar vazio na entrega.

### CT-28 — Regra escrita de reavaliação de temas restantes

- **CA de origem:** CA-12 (RF-08, RN-10)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_vitrine_governanca.py::test_regra_reavaliacao_temas`
- **Pré-condição:** `doc/exemplos/reavaliacao-temas.md`.
- **Passos:**
  1. Ler o documento.
- **Resultado esperado:** cita o gatilho "Em produção"; lista os temas restantes
  (Kanban, Scrum, Acadêmico, XGH, Gestão, RH, Atendimento); declara que nenhum
  tema é tratado como aprovado/priorizado por herança e que cada tema mantém seus
  próprios gates; fornece formato da solicitação (`gatilho`, `data`, `temas`,
  `heranca_de_aprovacao: nenhuma`).

### CT-29 — Registro da solicitação de reavaliação ao entrar em produção

- **CA de origem:** CA-12
- **Tipo:** unitário + manual (parte condicionada à coluna "Em produção")
- **Arquivo/alvo:** `tests/test_vitrine_governanca.py::test_registro_reavaliacao_sem_heranca`
- **Pré-condição:** `doc/exemplos/registros/reavaliacao/`.
- **Passos:**
  1. Validador `validar_registro_reavaliacao(dict)`: (a) `heranca_de_aprovacao: nenhuma`
     e `temas` não vazio → válido; (b) `heranca_de_aprovacao` ≠ `nenhuma` → inválido;
     (c) tema marcado `aprovado`/`priorizado` → inválido; (d) `gatilho` ausente → inválido.
  2. Se existirem registros reais, validar cada um.
  3. **Manual:** quando a entrega alcançar "Em produção", confirmar que existe
     um registro em `registros/reavaliacao/` datado desse momento.
- **Resultado esperado:** sintéticos conforme acima; registro real (quando existir)
  válido e sem herança de aprovação.
- **Observações:** a existência do registro real só é exigível após "Em produção";
  antes disso o teste automatizado não falha por diretório vazio (documenta-se
  `skip` explícito com motivo, nunca `pass` silencioso).

---

## 5. Cobertura e lacunas declaradas

- Todos os 12 CAs possuem ≥ 1 caso. Nenhum caso sem CA.
- Não automatizável em pytest (declarado, não ignorado): execução real contra
  GitHub/kiro-cli (CT-24) e o registro de reavaliação pós-"Em produção" (CT-29,
  parte manual). A suíte cobre o que é verificável: estrutura, validação real do
  motor (`check_config`), encadeamento do fluxo, ausência de dados sensíveis,
  formatos e regras dos registros e dos documentos de governança.
- Fora de escopo e **não testado** por decisão: automação da avaliação de
  impacto, metas numéricas, galeria/telemetria, outros temas.
- Regressão: a suíte existente não deve ser alterada; a única mudança fora de
  `exemplos/`, `doc/exemplos/` e `tests/` esperada é em `.gitignore` (exceções)
  e eventual `CHANGELOG.md`/`README.md` (link para a vitrine).
