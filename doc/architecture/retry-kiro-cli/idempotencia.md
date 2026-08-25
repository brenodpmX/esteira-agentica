# ADR — Idempotência no retry do kiro-cli

**Status:** aceita

**Data:** 2026-08-25

**Owner:** architecture

**Issues relacionadas:** #217 (decisão) e #208 (implementação bloqueada)

## 1. Contexto

O `kiro-cli` pode encerrar um turno com `dispatch failure` ou
`InternalServerError`. O erro pode aparecer depois que o agente já executou
ferramentas, inclusive `git commit`, `git push` e movimentação dos arquivos da
issue. O processo não oferece rollback e o adapter atual executa o CLI como um
subprocesso com `--trust-all-tools`.

O adapter preserva um `session_id` e pode retomar com `--resume-id`, mas não
intercepta nem registra, em uma fronteira confiável, cada efeito produzido
pelas ferramentas. O texto capturado do subprocesso também não é prova de que
uma ferramenta não executou: o stream pode falhar antes de o evento ou o
resultado ser recebido e persistido.

Portanto, após esses aborts, o estado da tentativa é **ambíguo**: a esteira não
consegue afirmar se houve zero, parte ou todos os efeitos pretendidos.

## 2. Decisão

Adotar a alternativa 3 para a entrega de #208: **não realizar retry automático
inline** em `KiroCliAgent.execute()`/`_run()` quando ocorrer `dispatch failure`
ou `InternalServerError`.

Esses erros são classificados como `UNKNOWN_OUTCOME` (resultado ambíguo), não
como falhas seguramente anteriores à execução. Para esse estado, a política é
fail-closed:

1. executar o subprocesso no máximo uma vez naquela entrega ao agente;
2. preservar o output, o request ID disponível e o `session_id` para auditoria
   e continuidade;
3. registrar a falha de forma acionável;
4. não iniciar backoff seguido de nova chamada ao `kiro-cli` na mesma execução;
5. permitir que o loop normal reconcilie filesystem, git e board antes de uma
   eventual nova seleção da tarefa.

O `rerun_cooldown` permanece como mecanismo de reentrega diferida já existente.
Ele não é uma garantia de exactly-once; sua vantagem sobre retry inline é
permitir que os ciclos de descoberta e sincronização observem efeitos já
aplicados — por exemplo, uma mudança de coluna que torne a tarefa inelegível —
antes de qualquer nova entrega.

`--resume-id` continua sendo usado numa entrega posterior quando a sessão
existir. Ele garante continuidade de contexto, **não idempotência** e nem
permissão para retry imediato.

### Consequência para #208

O critério atual de “reprocessar automaticamente dentro da mesma execução” é
incompatível com o requisito simultâneo de “não duplicar efeitos colaterais”
na arquitetura vigente. #208 não deve implementar loop de retry/backoff para
esses marcadores. Seu escopo seguro deve ser ajustado para:

- classificar explicitamente os aborts como resultado ambíguo;
- manter uma única invocação por entrega;
- melhorar logs/telemetria e cobrir a política fail-closed com testes;
- validar preservação da sessão para eventual retomada pelo loop normal; e
- documentar que backoff inline depende da fronteira idempotente descrita na
  seção 4.

Essa revisão é uma restrição técnica de segurança, não depende de definição de
Produto ou UX.

### Contrato normativo de entrega de #208

Em 2026-08-25, o objetivo, o escopo e os critérios de aceite de #208 foram
alinhados a esta decisão. Para evitar interpretações conflitantes nas etapas de
QA e implementação, o contrato é:

- `dispatch failure`, `InternalServerError` após output parcial e timeout
  resultam em `UNKNOWN_OUTCOME`;
- cada um desses resultados permite exatamente uma invocação do subprocesso
  por entrega, sem sleep/backoff seguido de nova chamada;
- output, request ID quando disponível, erro e `session_id` são preservados;
- uma entrega posterior pode usar `--resume-id` somente pelo fluxo normal,
  depois da reconciliação de filesystem, git e board; e
- os testes devem demonstrar a ausência de retry inline, a preservação e
  retomada posterior da sessão e a ausência de regressão no caminho de
  sucesso.

O título histórico de #208 menciona retry com backoff, mas não prevalece sobre
este contrato. Alterar a classificação desses aborts ou habilitar retry inline
exige nova decisão arquitetural e o atendimento prévio das condições da seção
4.

## 3. Alternativas rejeitadas

### 3.1 Retry apenas com `--resume-id`

Rejeitada. A sessão ajuda o modelo a reconstruir contexto, mas não impede uma
ferramenta de repetir uma ação. Um commit pode já existir, um push pode ter
concluído no remoto e uma movimentação pode já ter ocorrido antes da queda.
Delegar a deduplicação ao raciocínio probabilístico do agente não é uma
garantia arquitetural.

### 3.2 Retry quando o output não mostrar ferramenta de efeito externo

Rejeitada na forma proposta. Ausência no output não prova ausência de
execução: o stream pode quebrar justamente entre a realização do efeito e a
recepção/persistência do evento. Instrumentação apenas observacional no
adapter deixa uma janela de crash e não cobre comandos arbitrários executados
sob `--trust-all-tools`.

Também não basta persistir “efeito concluído” depois da chamada. Uma queda
entre o efeito externo e essa persistência produziria o mesmo resultado
ambíguo.

### 3.3 Reexecutar o prompt em sessão nova

Rejeitada. Perde o contexto da tentativa anterior e aumenta a chance de repetir
operações já concluídas.

## 4. Condição arquitetural para retry automático futuro

Retry automático de uma tentativa com possível execução parcial só poderá ser
habilitado quando efeitos mutáveis passarem por uma fronteira controlada e
idempotente. A solução futura deve conter, no mínimo:

1. **ID estável da tentativa e da operação:** cada efeito recebe uma chave como
   `(board, issue, agent, execution_id, operation_id)`; retries reutilizam a
   mesma chave.
2. **Journal/outbox durável:** registrar intenção e estados da operação antes e
   depois do efeito (`pending`, `applied`, `verified`), com escrita atômica sob
   responsabilidade do core, não do agente.
3. **Interposição real:** commit/push, mudança de coluna e mutações de board não
   podem contornar a fronteira por shell ou CLI arbitrários. Observar texto de
   saída não satisfaz essa condição.
4. **Verificação de pós-condição:** ao recuperar `pending`, consultar o destino
   para resolver a janela de queda entre efeito e confirmação. Exemplos: ref
   remota já aponta ou contém o commit esperado; issue já está na coluna alvo;
   mutação de board já reflete o valor desejado.
5. **Operações declarativas:** expressar estado desejado (`ensure branch
   contains commit`, `ensure issue in column`) em vez de comandos imperativos
   cegos (`push`, `mv`). Reaplicar o mesmo estado deve ser no-op.
6. **Retomada de sessão:** somente depois da reconciliação do journal, retomar
   com `--resume-id` e informar ao agente quais operações já estão verificadas.
7. **Limite e backoff:** tentativas limitadas, atraso exponencial com jitter e
   logs correlacionados pelo `execution_id`.

Uma alternativa de isolamento transacional por worktree/sandbox pode reduzir
os efeitos locais, mas não resolve sozinha efeitos externos já confirmados,
como push ou mutação remota; estes ainda exigem chave e pós-condição.

## 5. Máquina de estados recomendada

```text
RUNNING
  -> SUCCEEDED                 execução concluída
  -> DEFINITE_NOT_STARTED      falha comprovadamente anterior ao subprocesso
  -> UNKNOWN_OUTCOME           dispatch failure/InternalServerError/timeout

DEFINITE_NOT_STARTED
  -> retry limitado com backoff (quando houver erro transitório aplicável)

UNKNOWN_OUTCOME
  -> persistir evidência
  -> encerrar a entrega sem retry inline
  -> reconciliar estado no loop normal
  -> eventual nova entrega com resume-id
```

Somente evidência positiva e estruturada de que a execução não começou permite
`DEFINITE_NOT_STARTED`. Ausência de tool call em output parcial não é essa
evidência.

## 6. Testes exigidos para #208

A implementação decorrente desta ADR deve provar:

- `dispatch failure` real capturado no incidente gera exatamente uma chamada ao
  subprocesso, sem sleep/backoff seguido de nova chamada;
- `InternalServerError` após output parcial também gera uma única chamada;
- request ID, erro e log integral permanecem disponíveis;
- o `session_id` descoberto após a chamada é preservado quando disponível;
- uma entrega posterior utiliza `--resume-id` pelo fluxo já existente;
- sucesso continua inalterado;
- timeout é tratado como `UNKNOWN_OUTCOME`, pois o processo pode ter produzido
  efeitos antes de exceder o limite; e
- nenhuma alteração é necessária nos mecanismos de proteção de estado interno.

Quando a fronteira da seção 4 existir, novos testes deverão simular queda em
cada janela: antes do efeito, durante o efeito, depois do efeito e antes da
confirmação do journal. Em todos os casos, reaplicar a mesma operação deve
produzir o mesmo estado final e nenhuma duplicação observável.

## 7. Impactos e riscos residuais

- A decisão prioriza integridade sobre recuperação imediata e não reduz, por si
  só, o crédito perdido no turno abortado.
- Uma reentrega posterior ainda depende de o agente respeitar o estado já
  reconciliado; por isso ela não deve ser descrita como exactly-once.
- O `rerun_cooldown` é memória de processo e reinício libera a issue
  imediatamente, conforme comportamento vigente.
- Retry inline limitado pode continuar existindo para falhas cuja
  **não-inicialização** seja comprovada mecanicamente, mas os dois erros de #208
  não pertencem a essa categoria.

## 8. Rastreabilidade

| Questão de #217 | Resolução |
|---|---|
| `--resume-id` garante idempotência? | Não; preserva contexto apenas. |
| É seguro inferir ausência de efeitos pelo output? | Não; stream parcial deixa janela ambígua. |
| Haverá retry inline em #208? | Não para `dispatch failure`, `InternalServerError` ou timeout. |
| Como ocorre nova tentativa hoje? | Pelo loop normal após reconciliação e cooldown, com retomada de sessão quando disponível. |
| O que habilita retry seguro no futuro? | Interposição de efeitos, journal/outbox, chaves idempotentes e verificação de pós-condição. |
