# Change File — Incidente #97: Parent Recursivo

**Data:** 2026-08-01
**Issue:** #97 — Erro reportado dia 01/08/26
**Branch:** `hotfix97-97-erro_reportado_dia_010826`
**Status:** Mitigado operacionalmente; correções C1–C5 pendentes

---

## Resumo

Esta entrega consolida a documentação do incidente que interrompeu a esteira
por 2h37 e corrompeu o conteúdo da issue `#76`. O estado afetado foi reparado
operacionalmente, e cinco frentes de correção definitiva foram planejadas.

**Não há correção de código nesta branch.** As mudanças em C1–C5 continuam
pendentes e serão entregues pelas tasks próprias do board `task`.

## Alterações entregues

### 1. Registro público do incidente

`doc/incidente/parent-recursivo/ticket.md` documenta:

- linha do tempo e impacto (225 ciclos com erro e bloqueio global);
- causa raiz encadeada C1–C4 e hardening C5;
- risco de disponibilidade e integridade;
- workaround, mitigação operacional e estado atual; e
- plano de correção, ordem e estimativas das cinco tasks.

### 2. Orientação de homologação

`doc/incidente/parent-recursivo/homologacao.md` delimita o que pode ser
homologado nesta branch: documentação, build e ausência de regressão. O bug não
deve ser marcado como corrigido antes da entrega e homologação de C1–C5.

### 3. README operacional

O `README.md` passou a registrar o incidente conhecido, o estado mitigado e os
cuidados temporários: não usar prefixo numérico em issues novas, não executar
duas instâncias sobre o mesmo estado, não alterar a memória interna e escalar
repetições contínuas do mesmo erro.

### 4. Mitigação do caso concreto

O histórico registra a restauração do título, body e labels da issue `#76`, a
remoção dos arquivos órfãos das colunas ativas e a retomada do processamento.
Essas ações recuperam o caso ocorrido, mas não substituem as correções de
produto.

## Correções pendentes

| Frente | Resultado esperado | Situação |
|--------|--------------------|----------|
| C2 | Rejeitar auto-referência em relações | Task criada, pendente |
| C3 | Retirar mensagem-veneno da fila e aplicar dead-letter/tentativas | Task criada, pendente |
| C1 | Resolver body com segurança e reportar arquivos órfãos | Task criada, pendente |
| C4 | Verificar integridade do estado após execução de agente | Task criada, pendente |
| C5 | Impedir duas instâncias sobre o mesmo estado | Task criada, pendente |

Ordem planejada: **C2 → C3 → C1 → C4 → C5**.

## Impacto da entrega

- **Código-fonte:** sem alteração.
- **Comportamento do produto:** inalterado; risco residual documentado.
- **Dados do incidente:** recuperados por ação operacional.
- **Operação:** alerta e resposta temporária documentados.
- **Rastreabilidade:** incidente, homologação e plano C1–C5 consolidados.

## Validação

A etapa de pré-produção registrou build Docker concluído e importação dos
módulos sem erros. Após os ajustes documentais finais, a suíte foi reexecutada
com **199 testes aprovados e 3 ignorados**; `git diff --check` não encontrou
erros e os links locais dos quatro documentos foram validados.
