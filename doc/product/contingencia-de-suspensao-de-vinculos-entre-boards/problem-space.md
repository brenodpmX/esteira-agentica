# Problem Space — Contingência de suspensão de vínculos entre boards

Status: draft — recomendação de aprovação negocial
Owner: product
Last updated: 2026-08-27

## Inputs
- Issue #241 e body recebido para análise.
- Issue #230, histórico da entrevista com o dono e decisão negocial aprovada.
- Evidências consolidadas do épico #230: issues #221–#223, #226–#229 e #231–#240; sete despachos indevidos; 20,35 créditos comprovados.
- [GitHub Docs — Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues).
- [LaunchDarkly Docs — Kill switch flags](https://launchdarkly.com/docs/eu-docs/home/flags/killswitch).
- [Atlassian Support — Link work items](https://support.atlassian.com/jira-software-cloud/docs/link-issues/).

## Contexto
O GitHub trata sub-issues como relações de hierarquia visíveis em toda a plataforma e em Projects. A documentação oficial permite inclusive associar issues de outros repositórios e não apresenta um controle nativo específico para suspender apenas vínculos que atravessam Projects. Portanto, a hierarquia entrega valor real, mas a fronteira de execução por board precisa ser protegida pela esteira.

O mercado oferece dois sinais úteis. Ferramentas de gestão, como Jira, preservam relações entre trabalhos de espaços distintos e permitem administrá-las explicitamente. Plataformas de feature management tratam kill switches como controles operacionais para interromper rapidamente uma capacidade durante eventos não planejados. Esses padrões favorecem uma suspensão seletiva, reversível e observável, em vez de eliminar permanentemente a hierarquia.

No épico pai, o dono autorizou explicitamente a suspensão temporária caso a recorrência fosse comprovada. A recorrência foi validada: em 17 novas relações entre boards, todas produziram participação indevida, e 35,3% das issues chegaram a executar ao menos uma vez no board errado. O dono também aprovou a documentação negocial do épico #230 em 26 e 27/08/2026.

## Problemas
- Não existe hoje uma barreira operacional específica para interromper novas relações entre boards durante uma exposição ativa.
- A limpeza manual ocorre depois da propagação e não impede que um agente seja despachado antes da intervenção.
- Parar toda a esteira conteria o risco, mas também interromperia trabalho não relacionado.
- Suspender toda relação pai/filho eliminaria hierarquias seguras dentro do mesmo board e ampliaria desnecessariamente o impacto.
- Rejeições silenciosas dificultariam auditoria, suporte ao operador e decisão de reativação.
- Reproduzir automaticamente pedidos recusados criaria uma fila oculta de exposição para o momento da retomada.

## Impacto
O custo de não fazer é mensurável pelo baseline do épico #230: em um lote de 17 vínculos, houve 17 remoções manuais, sete despachos errados e pelo menos 20,35 créditos desperdiçados. A exposição também permitiu que stories fossem tratadas como épicos e tasks como stories, criando risco de decomposição e alteração de trabalho sem fundamento.

O custo da própria contingência é a postergação dos novos vínculos entre boards recusados durante a suspensão. Esse custo é limitado porque vínculos preexistentes e relações dentro do mesmo board continuam ativos; após a reativação, apenas pedidos ainda necessários são submetidos novamente de forma consciente.

## Alternativas avaliadas

| Alternativa | Benefício | Custo/risco | Decisão de negócio |
|---|---|---|---|
| Aguardar somente a prevenção definitiva | Evita uma entrega intermediária | Mantém a exposição comprovada durante toda a espera | Rejeitada |
| Continuar removendo propagações manualmente | Não requer nova capacidade | Atua tarde, não escala e já permitiu sete despachos | Apenas reação emergencial, não solução |
| Parar toda a esteira | Contenção ampla | Bloqueia todos os boards e destrói o valor operacional | Rejeitada |
| Suspender toda criação de relação pai/filho | Regra simples | Interrompe também relações seguras no mesmo board | Rejeitada por excesso de impacto |
| Trocar hierarquia por labels ou campos | Evita o mecanismo atual | Perde semântica nativa e exige mudança ampla de processo | Fora de escopo |
| Adotar serviço externo de feature flags | Oferece gestão especializada | Introduz custo e dependência sem prova de necessidade | Não justificada; decisão técnica posterior |
| Suspender apenas novos vínculos entre boards | Contém a fonte e preserva operação segura | Adia hierarquias novas durante a contingência | Recomendada |

## Retorno e medição
O retorno direto é evitar despachos, créditos e remoções manuais durante a janela em que a prevenção definitiva ainda não está disponível. A apuração deve comparar, desde a ativação:
- tentativas entre boards recusadas;
- despachos indevidos atribuíveis a vínculos posteriores à ativação;
- créditos consumidos por esses despachos;
- remoções manuais necessárias;
- vínculos existentes afetados;
- relações do mesmo board processadas; e
- tempo entre decisão de ativar/desativar e vigência observada.

O baseline de 20,35 créditos é mínimo, não projeção financeira. Não há preço por crédito nem horas de limpeza medidos, portanto ROI em moeda não deve ser inventado.

## Ordem de esforço
A contingência ocupa a **primeira posição entre as seis entregas do épico #230** por reduzir exposição imediatamente e não depender das demais frentes. A prevenção e reconciliação definitivas continuam obrigatórias e vêm depois. O tamanho técnico não é estimado nesta análise; a ordem é definida por redução de risco e independência de negócio.

## Aderência a metas e políticas
Não foi apresentado OKR formal. Ainda assim, a entrega adere à meta aprovada do épico #230 de zero execução em board errado, zero remoção manual e zero resíduo novo. Também respeita as políticas negociais já aprovadas: integridade antes do despacho, preservação de hierarquia válida, contingência temporária e não retroativa, decisão auditável e retomada consciente.

## Oportunidade
Criar uma barreira operacional mínima agora reduz o raio de dano enquanto as demais entregas restauram a integridade de forma definitiva. A contingência permite manter a maior parte do produto operando e transforma uma reação manual tardia em uma decisão explícita, mensurável e reversível.

## Gate de decisão
A recomendação é **aprovar**. Dor, recorrência, custo mínimo, alternativa preferida, retorno mensurável, ordem e aderência às políticas estão fechados. A aprovação não encerra o épico #230 e não substitui prova de funcionamento no runtime.
