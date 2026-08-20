# Casos de Teste — Resolução do conflito do MR #130 (`panorama-branches.md`)

Issue: #136 — Resolver conflito do MR #130 consolidando `panorama-branches.md`
Etapa: Casos de Teste

## Contexto da verificação

Esta task é puramente documental/git: resolver um conflito de merge causado
por duas edições independentes de `doc/product/branchs-nao-mergeadas/panorama-branches.md`
(versão da story #74, já em `epic`, vs. versão da branch `epic75-...`, com a
análise da story #75). Não há código de produção envolvido, então os casos de
teste abaixo são de verificação estática do repositório (conteúdo do arquivo,
histórico git e estado do MR), não testes automatizados de software.

**Situação no momento desta verificação:** o MR #130 já foi mesclado
(`gh pr view 130` → `state: MERGED`, commit de merge `0633b6f`) e a branch
`epic75-75-limpeza_de_branches_orfas_de_tarefas_arquivadas` não existe mais no
remoto. Os casos de teste abaixo foram executados diretamente sobre o estado
atual de `epic` (que já contém o resultado do merge) e todos passaram — ver
seção "Resultado da execução". Ficam registrados como casos de teste formais
para reexecução caso o cenário se repita (novo conflito na mesma família de
documento) ou para auditoria do resultado já entregue.

## CT01 — Ausência de marcadores de conflito

**Objetivo:** garantir que o merge foi resolvido por completo, sem resíduo de
marcadores do Git.

**Procedimento:**
```bash
grep -n "^<<<<<<<\|^=======\|^>>>>>>>" doc/product/branchs-nao-mergeadas/panorama-branches.md
```

**Resultado esperado:** saída vazia (grep retorna código 1 / nenhuma linha).

**Status:** ✅ PASSOU — nenhum marcador encontrado.

---

## CT02 — Seções 1 a 4 e resumo executivo preservados intactos

**Objetivo:** garantir que a consolidação da story #74 (fonte de verdade) não
foi revertida pela resolução do conflito.

**Procedimento:** comparar o conteúdo das seções "1. Base do fluxo", "2.
Trabalho vivo", "3. Resíduo já integrado", "4. Duplicidade e nomenclatura
antiga" e a tabela "Resumo executivo" (exceto a linha "Órfãs de arquivadas",
tratada no CT04) entre a versão final em `epic` e a versão que estava em
`epic` imediatamente antes do merge do MR #130 (`git show origin/epic:...`
no commit anterior ao merge, ou `git log -p` no arquivo).

**Resultado esperado:** nenhuma diferença de conteúdo nessas seções — apenas
a seção 5 e a linha correspondente do resumo executivo devem ter mudado.

**Status:** ✅ PASSOU — seções 1–4 idênticas à versão pré-merge de `epic`;
nota da decisão #125 sobre `hotfix27` preservada integralmente dentro da
tabela da seção 5 (item 5.1).

---

## CT03 — Seção 5 consolidada com as decisões da story #75

**Objetivo:** confirmar que a seção 5 reflete o resultado da análise da story
#75: 8 branches removidas (absorvidas) e 2 branches encaminhadas para
análise.

**Procedimento:** inspecionar a seção "5. Branches órfãs de tarefas
arquivadas (story #75)" e confirmar:
- Subseção 5.1 lista exatamente `epic16, epic17, epic18, epic19, epic20,
  epic21, epic36, hotfix27` (8 branches) com issue e razão preenchidas.
- Subseção 5.2 lista exatamente `hotfix23` e `hotfix24` (2 branches), com a
  branch de preservação (`temp-hotfix23-merge` / `temp-hotfix24-merge`) e
  situação "aguardando decisão".
- Linha de total ("Total seção 5") indica 10 branches — 8 removidas / 2
  preservadas.

**Resultado esperado:** os três pontos acima verificados sem divergência.

**Status:** ✅ PASSOU.

---

## CT04 — Resumo executivo atualizado para a categoria "Órfãs de arquivadas"

**Objetivo:** garantir que a tabela "Resumo executivo" não ficou desatualizada
em relação à seção 5.

**Procedimento:** verificar a linha "Órfãs de arquivadas" na tabela do
"Resumo executivo".

**Resultado esperado:** coluna "Ação" com "8 removidas / 2 preservadas para
decisão" (ou equivalente), não mais o texto genérico "~10 branches para
análise e remoção conforme critério".

**Status:** ✅ PASSOU — linha atualizada para "8 removidas / 2 preservadas
para decisão".

---

## CT05 — Arquivo de story da #75 presente e sem alteração de conteúdo

**Objetivo:** confirmar que o arquivo trazido apenas pelo lado `epic75-...`
(sem conflito, `added in remote`) foi preservado no merge.

**Procedimento:**
```bash
test -f doc/product/branchs-nao-mergeadas/stories/limpeza-branches-orfas-arquivadas.md && echo OK
```

**Resultado esperado:** arquivo presente, `OK` impresso.

**Status:** ✅ PASSOU — arquivo presente em
`doc/product/branchs-nao-mergeadas/stories/limpeza-branches-orfas-arquivadas.md`.

---

## CT06 — Arquivos protegidos de #125/#74 não tocados

**Objetivo:** garantir que a resolução do conflito não alterou os
change-files de decisões já fechadas, fora do escopo desta task.

**Procedimento:** comparar
`doc/product/branchs-nao-mergeadas/change-files/125-destino-conteudo-hotfix27.md`
e
`doc/product/branchs-nao-mergeadas/change-files/74-remocao-residuo-integrado.md`
entre a versão em `epic` antes e depois do merge do MR #130.

**Resultado esperado:** nenhuma diferença nesses dois arquivos.

**Status:** ✅ PASSOU — ambos os arquivos inalterados pelo commit de merge
(`774af2c` não os modifica; conferido em `git show 774af2c --stat`, ausentes
da lista de arquivos alterados).

---

## CT07 — Merge realizado via merge commit (sem squash/rebase)

**Objetivo:** garantir que o histórico da story #75 foi preservado, conforme
restrição da issue.

**Procedimento:**
```bash
git log --merges --oneline | grep 130
git show <merge-commit> --stat | head -1   # deve listar dois parents
```

**Resultado esperado:** commit de merge com dois parents (merge commit
simples), não um commit único de squash.

**Status:** ✅ PASSOU — commit `0633b6f` é merge commit (`Merge pull request
#130 from .../epic75-75-...`), com parents `f5abe81` (epic) e `321d08c`
(epic75, incluindo `774af2c` como resolução do conflito).

---

## CT08 — MR #130 mergeável / mesclado

**Objetivo:** confirmar o critério de aceite final — o MR deixou de estar em
conflito.

**Procedimento:**
```bash
gh pr view 130 --json mergeable,state
```

**Resultado esperado:** `mergeable: MERGEABLE` (antes do merge) ou
`state: MERGED` (após o merge ser efetivado).

**Status:** ✅ PASSOU — `state: MERGED`. (`mergeable` retorna `UNKNOWN` pois o
GitHub não recalcula esse campo para PRs já mesclados; isso é esperado e não
indica falha.)

---

## Resultado da execução

Todos os 8 casos de teste (CT01–CT08) foram executados contra o estado atual
do repositório (branch `epic`, que já contém o resultado do merge do MR #130)
e **passaram**. Não foram encontradas divergências entre o resultado entregue
e os critérios de aceite da issue #136.

Nenhum caso de teste falhou; não há bloqueio, dúvida ou débito a registrar
para esta issue.
