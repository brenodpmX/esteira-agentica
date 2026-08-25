# Fluxo de Navegação — Circuit-break de agente

Status: draft
Owner: ux
Last updated: 2026-08-25

> **Draft aguardando entrevista.** As decisões marcadas com `?` em "Dúvidas em
> aberto" foram preenchidas com uma **proposta** para o dono reagir, não com
> uma decisão fechada. Nada aqui deve ser implementado antes da resposta.

## Inputs

- `doc/product/circuit-break-de-agente/analise-negocio.md` (RN01–RN09,
  critérios de aceite 1–8)
- `doc/requirements/circuit-break-de-agente/functional-requirements.md`
  (RF-001 a RF-008)
- `doc/requirements/circuit-break-de-agente/business-rules.md` (RN-001 a RN-009)
- `doc/requirements/circuit-break-de-agente/non-functional-requirements.md`
  (NFR-003 é o requisito que esta etapa materializa: sinalização completa e
  diagnosticável sem acesso a estado interno)
- `doc/requirements/circuit-break-de-agente/glossary.md` (vocabulário aplicado
  literalmente na copy)
- Código das superfícies existentes: `src/__main__.py` (`keep_task`,
  `_in_rerun_cooldown`), `src/core/config.py` (`_validate_boards`),
  `src/core/log.py` (formato de terminal e arquivo), `src/core/board.py`
  (`add_comment`), `src/core/commands.py` (`need_human`)

## Nota sobre "telas"

A esteira não tem interface gráfica. O produto é um processo de linha de
comando e o board do GitHub. Portanto "tela" aqui significa **superfície de
interação com o operador** — o ponto concreto onde ele lê ou escreve algo.
Foram mapeadas seis, e é nelas que os protótipos foram feitos.

## Telas mapeadas

1. **Configuração da política** — bloco novo no `pipe.yml`
   (protótipo: `prototype-configuracao.html`)
2. **Erro de configuração no arranque** — mensagem de `check_config`
   (protótipo: `prototype-configuracao.html`)
3. **Log de bloqueio** — linha no terminal e no arquivo diário
   (protótipo: `prototype-log-de-bloqueio.html`)
4. **Marcação na issue** — label `need_human` no board
   (protótipo: `prototype-comentario-de-bloqueio.html`)
5. **Comentário de bloqueio** — a peça principal de copy, o que o operador lê
   para diagnosticar (protótipo: `prototype-comentario-de-bloqueio.html`)
6. **Retomada** — remoção da marcação pelo operador e confirmação de que a
   franquia foi renovada (protótipo: `prototype-comentario-de-bloqueio.html`)

## Fluxo — jornada A: ativar a política (opt-in)

```
pipe.yml sem política  (estado atual de qualquer instalação)
  → (operador não faz nada)          → nenhum bloqueio; comportamento vigente preservado (RF-006)
  → (operador declara N e T)         → arranque valida → política ativa
  → (operador declara só N ou só T)  → Erro de configuração no arranque → processo não sobe
```

## Fluxo — jornada B: bloqueio, diagnóstico e retomada

```
Execuções repetidas no mesmo contexto (board + coluna + issue)
  → (execução nº N entregue)              → Log informativo de franquia consumida
  → (seleção nº N+1 seria entregue)       → BLOQUEIO
                                              ├→ Log de bloqueio (WARNING)
                                              ├→ Marcação need_human na issue
                                              ├→ Comentário de bloqueio na issue
                                              └→ contagem do contexto zerada (RF-007)

Issue bloqueada
  → (operador vê a label/comentário)      → lê motivo, board, coluna, limite, janela
  → (operador abre logs/<id>/)            → lê prompt e diálogo das execuções repetidas
  → (operador corrige ou redireciona)     → issue pronta para retomar
  → (operador remove need_human)          → sync reconcilia → issue volta a ser elegível
                                              └→ nova franquia completa de N execuções (RF-007)
  → (operador move a issue de coluna)     → contexto novo, franquia nova (RF-002)
  → (operador não faz nada)               → issue permanece parada; demais issues seguem (RF-008)
```

Ponto de atenção do fluxo: **enquanto `need_human` está presente, `keep_task`
já pula a issue** pelo gate que existe hoje (`_is_blocked`). Ou seja, não há
reavaliação, não há segundo bloqueio e não há comentário repetido a cada ciclo.
Isso é uma propriedade desejável de UX (silêncio depois do aviso) e está
registrado como pressuposto a confirmar.

## Estados

Adaptação do template: em produto de linha de comando não existe "loading" de
tela. A coluna equivalente é "Em espera" — o que o operador vê enquanto nada
aconteceu ainda.

| Tela | Em espera | Erro | Vazio |
|------|-----------|------|-------|
| 1. Configuração da política | Bloco ausente do `pipe.yml`: política inativa, sem aviso | Valor inválido ou par incompleto: arranque falha com mensagem citando a chave, o tipo e a unidade esperados | Ausência **é** o estado vazio e é legítima (opt-in); não há aviso nem sugestão de valor |
| 2. Erro de configuração | — | Mensagem única, na saída padrão do arranque, antes de qualquer execução | — |
| 3. Log de bloqueio | Linha informativa de franquia consumida (`4/5`) nas execuções que antecedem o limite | Falha ao aplicar marcação ou comentário: linha de erro; o bloqueio da execução permanece válido | Sem política configurada, nenhuma linha de circuit-break é emitida |
| 4. Marcação na issue | Issue sem `need_human`: fluxo normal | Marcação não aplicada por falha de API: log de erro e nova tentativa no ciclo seguinte | — |
| 5. Comentário de bloqueio | Nenhum comentário antes do primeiro bloqueio | Comentário não publicado: log de erro; a marcação `need_human` continua sendo o sinal mínimo | — |
| 6. Retomada | `need_human` presente: issue parada, sem novos comentários | Correção incompleta: a issue bloqueia novamente após consumir a nova franquia (comportamento correto, não erro) | Franquia zerada é o estado inicial esperado da retomada |

## Decisões de UX

Decisões que tomo como responsabilidade de UX, sem depender de resposta do
dono:

- **Vocabulário do glossário, literalmente.** A copy usa "execução", "janela",
  "limite", "franquia", "bloqueio" e "contexto" exatamente como definidos em
  `glossary.md`. Justificativa: o glossário já distingue `bloqueio` de
  `cooldown` e `limite` de `cota` (esta reservada ao épico #177); reescrever
  esses termos na copy reintroduziria a confusão que o glossário eliminou.
- **A copy nomeia board e coluna, nunca arquivo de estado.** O comentário cita
  `logs/<issue>/` (log de execução, artefato público) e nunca `snapshot.json`,
  `changeQueue.json` ou qualquer caminho protegido. Justificativa: NFR-003
  exige diagnóstico sem acesso a estado interno, e a proteção de estado da
  esteira proíbe expor esses caminhos.
- **O comentário termina em ação, não em explicação.** Estrutura fixa: o que
  aconteceu → dados do bloqueio → próximo passo numerado. Justificativa: o
  operador chega ao comentário já sabendo que algo travou; o que falta a ele é
  o que fazer.
- **A copy declara explicitamente que o resto continuou.** Uma linha final
  informa que nenhuma outra issue foi afetada. Justificativa: sem isso, o
  operador interpreta o bloqueio como parada da esteira e reage com urgência
  desnecessária — risco de falso incidente.
- **Sinal duplo, ação única.** O bloqueio produz dois sinais (label + comentário),
  mas o comentário indica **um único** gesto de liberação, para o operador não
  ficar em dúvida sobre o que remover.
- **Nada de valor sugerido para `N` e `T` na copy.** Nem na mensagem de erro,
  nem em comentário. Justificativa: o dono decidiu não ter padrão (histórico,
  22/08/2026); sugerir número na mensagem cria padrão de fato.
- **Acessibilidade dos protótipos.** `lang="pt-BR"`, estrutura semântica,
  tabelas com `caption` e `th scope`, contraste mínimo AA e nenhum significado
  transmitido só por cor — o ícone/rótulo textual sempre acompanha a cor.
  Justificativa: o próprio produto emite log colorido no terminal, e a copy
  precisa continuar legível sem cor (arquivo diário, terminal sem ANSI, leitor
  de tela).

## Dúvidas em aberto

Perguntas enviadas ao dono no `addcomment` desta etapa. Cada uma tem uma
proposta registrada nos protótipos; a resposta confirma ou corrige.

1. `?` Forma e nome da chave de configuração, e unidade da janela (segundos,
   como `sleep`/`rerun_cooldown`, ou string legível como `2h`).
2. `?` Configuração parcial (só limite ou só janela): falhar no arranque
   (proposta) ou avisar e manter inativa.
3. `?` Conteúdo do comentário além do mínimo exigido: horário da primeira e da
   última execução, caminho da pasta de log, agente/model usados.
4. `?` Ciclo de vida do comentário: um comentário novo por bloqueio (proposta,
   preserva trilha) ou um único comentário atualizado.
5. `?` Aviso antes do bloqueio: emitir linha de log na franquia quase esgotada
   (proposta: só log, sem comentário na issue).
6. `?` Onde o operador remove a marcação — label no board ou `/need_human` no
   body — e qual dos dois a copy deve instruir como gesto canônico.
7. `?` Confirmação do pressuposto de silêncio: nenhum comentário novo enquanto
   a issue estiver com `need_human`.
8. `?` O bloqueio deve mover a issue de coluna (proposta: não).
