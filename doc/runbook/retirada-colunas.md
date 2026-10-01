# Runbook — Retirada segura de colunas de board (`column-migrations`)

- **Issue:** #305
- **Componente:** reconciliação estrutural de boards (startup / full sync)

Este runbook descreve como retirar uma coluna de um board com segurança, como
declarar o destino de migração, como acompanhar a evidência nos logs e como agir
quando uma retirada fica bloqueada ou interrompida.

> **Escopo:** proteção para **mudança estrutural de board**. Não é uma regra
> geral de movimentação de trabalho entre colunas. Não há migração entre boards
> diferentes, nem roteamento de destino por issue, nem arquivamento/fechamento
> como destino.

---

## 1. Conceito

A cada ciclo de reconciliação estrutural (no startup / full sync), a esteira
compara as colunas declaradas em `boards.<board>.columns` com as opções do campo
`Status` publicadas no board remoto. Uma opção publicada que **não** está mais na
configuração é uma **coluna retirada** (candidata à retirada), e é tratada por:

```
validar → drenar → confirmar vazio → contrair
```

- **Coluna vazia:** retirada direta, após uma leitura remota imediatamente
  anterior confirmar zero issues. Não exige destino.
- **Coluna ocupada:** só é retirada depois que todas as issues forem migradas ao
  destino declarado (do mesmo board) e uma leitura remota confirmar a origem
  vazia.
- **Preparação não destrutiva:** antes de qualquer retirada, a esteira cria
  boards/campo `Status`/colunas ausentes preservando **todas** as opções remotas
  existentes (inclusive as em vias de retirada). A remoção de opção
  (**contração**) só acontece pelo núcleo de decisão, após confirmar a origem
  vazia.

A retomada após falha deriva o trabalho restante **do estado remoto** — não há
journal nem estado persistente paralelo.

---

## 2. Como retirar uma coluna

### 2.1 Coluna vazia

Basta remover a coluna da lista `columns` do board no `pipe.yml`. No próximo
ciclo, a esteira confirma que a coluna está vazia e contrai a opção. Nenhuma
declaração extra é necessária.

### 2.2 Coluna ocupada (com migração)

1. **Declare o destino** no mapa `column-migrations` do board e **remova a
   coluna de origem** da lista `columns`, no mesmo commit. A coluna de destino
   deve existir em `columns`:

   ```yaml
   boards:
     entrega:
       name: Entrega
       columns:
         backlog:
           name: Backlog
         done:
           name: Done
       column-migrations:
         revisao: done     # issues de 'revisao' (removida) migram para 'done'
   ```

2. **Deixe a esteira trabalhar.** Enquanto a origem (`revisao`) tiver issues, ela
   permanece publicada no board remoto. A cada ciclo, a esteira move as issues ao
   destino e, quando uma leitura confirma a origem vazia, contrai a opção.

3. **Depois de concluída,** a entrada em `column-migrations` pode ser removida.
   Com a origem já ausente do board remoto, nada mais é acionado. Deixá-la
   declarada é inofensivo.

---

## 3. Validação da configuração

**Forma** (validada no carregamento do `pipe.yml`): `column-migrations`, quando
presente, deve ser um **mapa de strings não-vazias** (origem → destino). Tipo
diferente (lista, string), chave/valor vazio após `strip`, nulo ou não-string é
rejeitado com `ConfigError` citando `boards.<board>.column-migrations` e a
entrada que falhou. A **ausência** do mapa é válida.

**Semântica** (validada em tempo de reconciliação): para uma coluna ocupada, o
destino deve existir na configuração resultante do **mesmo board**, ser
diferente da origem e não ser outra coluna também em retirada no mesmo ciclo.

---

## 4. Evidência nos logs

Cada tentativa (por origem) emite exatamente um evento
`column_migration_attempt` no log diário (`logs/<AAAA-MM-DD>.json`):

| Campo | Significado |
|-------|-------------|
| `board` | id do board |
| `source` | coluna de origem (retirada) |
| `destination` | coluna de destino (vazio quando não aplicável) |
| `initial_count` | issues na origem no início da tentativa |
| `moved_count` | issues movidas nesta tentativa |
| `remaining_count` | issues ainda na origem ao final da tentativa |
| `result` | `completed` \| `blocked` \| `interrupted` |
| `reason` | motivo (quando `blocked`/`interrupted`) |

Níveis: `completed` em **INFO**; `blocked` e `interrupted` em **WARNING**. A
mensagem de `blocked`/`interrupted` é auto-contida (board, origem e motivo),
legível sem correlacionar linhas. A evidência é consultável **sem** abrir
arquivos internos protegidos (`.pipe/...`) e não vaza corpo de issue,
credenciais nem estado protegido.

### Motivos padronizados

Bloqueio (`blocked`):

| Motivo | Causa |
|--------|-------|
| `destino_ausente` | coluna ocupada sem entrada em `column-migrations` |
| `destino_inexistente` | destino não existe em nenhum board configurado |
| `destino_mesmo_board_invalido` | destino é coluna de **outro** board |
| `destino_e_origem` | destino declarado é igual à própria origem |
| `destino_tambem_retirado` | destino é outra coluna também em retirada no ciclo |

Interrupção (`interrupted`):

| Motivo | Causa |
|--------|-------|
| `sem_progresso` | uma passagem completa não reduziu a contagem da origem |
| *(vazio)* | falha de transporte / penalidade de rate limit (estado parcial preservado) |

---

## 5. Diagnóstico e correção

| Sintoma (no log) | Causa provável | Ação |
|------------------|----------------|------|
| `result=blocked reason=destino_ausente` | coluna ocupada sem destino | Declare `<origem>: <destino>` em `column-migrations`. |
| `result=blocked reason=destino_inexistente` | destino digitado errado / inexistente | Corrija o id de destino para uma coluna existente em `columns`. |
| `result=blocked reason=destino_mesmo_board_invalido` | destino aponta para outro board | Use um destino do mesmo board (migração cross-board não é suportada). |
| `result=blocked reason=destino_e_origem` | destino igual à origem | Aponte para uma coluna diferente da origem. |
| `result=blocked reason=destino_tambem_retirado` | destino também está sendo retirado no ciclo | Mantenha o destino na config, ou escolha um destino que permaneça. |
| `result=interrupted reason=sem_progresso` | provedor aceita a mutação mas a origem não esvazia (ex.: fluxo contínuo de novas issues) | A coluna fica retida; investigue por que as issues não saem da origem. Nova tentativa ocorre no ciclo seguinte. |
| `result=interrupted` sem motivo | indisponibilidade / penalidade de rate limit | Estado parcial preservado; a próxima execução retoma movendo só o que falta. |

> **Atenção:** remover a entrada de destino **antes** de uma origem ocupada
> concluir faz a próxima tentativa **bloquear** (`destino_ausente`) sem alterar
> nenhuma issue. Mantenha a entrada declarada até a origem esvaziar.

---

## 6. Garantias e limites

- **Integridade:** nenhuma issue fica sem coluna por retirada configurada;
  nenhuma retirada conclui com a origem ainda ocupada.
- **Idempotência:** repetir a reconciliação no mesmo estado produz a mesma
  estrutura final e move apenas issues ainda observadas na origem; issues já no
  destino não são recontadas nem reprocessadas.
- **Rate limit:** todas as chamadas respeitam o throttle/penalidade existentes;
  não há retentativa paralela própria.
- **Janela residual (RNF-11):** o provedor não oferece remoção condicional
  atômica de opção nem trava contra escritor externo. A garantia é construída por
  drenagem + leitura imediatamente anterior à contração, com verificação remota
  logo após contrair. Um item que apareça sem `Status` nessa janela é
  reconciliado para o destino explícito quando inequívoco. Essa janela é mínima,
  mas não é eliminável apenas pela aplicação.
- **Sem rollback:** itens já movidos após uma falha parcial **não** retornam; o
  estado parcial é válido e a próxima tentativa converge.
