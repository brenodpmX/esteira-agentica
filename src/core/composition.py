"""Composição em camadas do prompt e do contexto entregues ao agente (#308).

Este módulo formaliza, sob um contrato observável, a separação do conteúdo
entregue ao agente em CAMADAS por responsabilidade e a MEDIÇÃO por execução.

Camadas (cada uma com ORIGEM ÚNICA — RN-04):

1. ``POLITICA_INVARIAVEL``  — guardrails/regras que não mudam entre execuções
   (proteção de estado interno, manual `@---`, estrutura do `-body.md`,
   convenções de criação de issue, git flow/branches). ORIGEM: o steering
   ``.kiro/steering/esteira.md`` gerado por ``context_generator`` (contexto
   SEMPRE carregado). NÃO é repetida no prompt dinâmico.
2. ``CONTEXTO_PROJETO``     — metadados do projeto e papéis humanos. ORIGEM: o
   steering (contexto SEMPRE carregado).
3. ``WORKFLOW_ETAPA``       — objetivo/passos/git da etapa corrente e transição.
   ORIGEM: o prompt dinâmico (``build_prompt``).
4. ``DADOS_TAREFA``         — título, caminhos dos arquivos da issue, nome da
   branch resolvido. ORIGEM: o prompt dinâmico (``build_prompt``).

As camadas 1 e 2 são SEMPRE carregadas (steering). As camadas 3 e 4 compõem o
prompt dinâmico, enxuto, específico da tarefa — sem repetir material invariável.

Função pura ``compose_measurement`` emite o registro de medição por execução
(contrato do escopo). O adapter e o orquestrador a consomem SEM acionar o
``kiro-cli``, de modo que a medição seja determinística e testável.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.core.config import ConfigError


# ══════════════════════════════════════════════════════════════════════════════
# Identificação das camadas
# ══════════════════════════════════════════════════════════════════════════════

# Classes de responsabilidade (escopo: política invariável, contexto do projeto,
# workflow da etapa, dados da tarefa).
POLITICA_INVARIAVEL = "politica_invariavel"
CONTEXTO_PROJETO = "contexto_projeto"
WORKFLOW_ETAPA = "workflow_etapa"
DADOS_TAREFA = "dados_tarefa"

RESPONSABILIDADES = (
    POLITICA_INVARIAVEL,
    CONTEXTO_PROJETO,
    WORKFLOW_ETAPA,
    DADOS_TAREFA,
)

# Camadas SEMPRE carregadas (steering). O prompt dinâmico (workflow + dados da
# tarefa) é composto por execução; o steering é o contexto automático.
CAMADA_STEERING = "contexto_sempre_carregado"
CAMADA_PROMPT = "prompt_dinamico"


# ══════════════════════════════════════════════════════════════════════════════
# Inventário auditável de regras por camada (CA-3 / RN-04)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RuleEntry:
    """Uma regra/instrução classificada por responsabilidade e por camada."""
    rule_id: str
    responsabilidade: str
    camada: str  # CAMADA_STEERING | CAMADA_PROMPT
    descricao: str = ""


# Inventário autoritativo das regras SEMPRE carregadas (steering) e das do prompt
# dinâmico. Cada regra tem ORIGEM ÚNICA: nenhuma aparece em mais de uma camada
# SEMPRE carregada (RN-04). As regras de workflow/dados vivem no prompt dinâmico
# (não são "sempre carregadas", pois mudam por etapa/execução).
#
# A regra do manual `@---` e a estrutura do `-body.md` vivem EXCLUSIVAMENTE no
# steering (antes eram duplicadas no prompt via annotations_doc()).
_INVENTORY: tuple[RuleEntry, ...] = (
    # ── Camada 1: política invariável (steering) ──
    RuleEntry("protecao_estado_interno", POLITICA_INVARIAVEL, CAMADA_STEERING,
              "Arquivos protegidos (NÃO acessar)."),
    RuleEntry("criacao_issues_sem_prefixo", POLITICA_INVARIAVEL, CAMADA_STEERING,
              "Convenção de nomeação de issues (sem prefixo numérico)."),
    RuleEntry("estrutura_body_md", POLITICA_INVARIAVEL, CAMADA_STEERING,
              "Estrutura do -body.md (corpo/anotações/comandos)."),
    RuleEntry("manual_comandos_arroba", POLITICA_INVARIAVEL, CAMADA_STEERING,
              "Manual dos comandos @--- (referência extensa)."),
    RuleEntry("git_flow_branches", POLITICA_INVARIAVEL, CAMADA_STEERING,
              "Git flow e prefixos de branch."),
    # ── Camada 2: contexto do projeto (steering) ──
    RuleEntry("metadados_projeto", CONTEXTO_PROJETO, CAMADA_STEERING,
              "Nome, descrição e papéis humanos do projeto."),
    # ── Camada 3: workflow da etapa (prompt dinâmico) ──
    RuleEntry("diretorio_trabalho", WORKFLOW_ETAPA, CAMADA_PROMPT,
              "Sandbox: operar apenas no clone repo/<repo_id>."),
    RuleEntry("preparacao_branch", WORKFLOW_ETAPA, CAMADA_PROMPT,
              "Preparação da branch de trabalho conforme gitevents."),
    RuleEntry("versionar", WORKFLOW_ETAPA, CAMADA_PROMPT,
              "Commit/push incondicional quando o fluxo exige."),
    RuleEntry("abrir_pr", WORKFLOW_ETAPA, CAMADA_PROMPT,
              "Abrir merge/PR quando o fluxo exige."),
    RuleEntry("transicao_coluna", WORKFLOW_ETAPA, CAMADA_PROMPT,
              "Mover os arquivos para a coluna de destino."),
    # ── Camada 4: dados da tarefa (prompt dinâmico) ──
    RuleEntry("dados_tarefa", DADOS_TAREFA, CAMADA_PROMPT,
              "Título, caminhos dos arquivos e branch resolvido."),
)


def layer_inventory() -> tuple[RuleEntry, ...]:
    """Retorna o inventário auditável completo das regras por camada."""
    return _INVENTORY


def always_loaded_inventory() -> tuple[RuleEntry, ...]:
    """Regras das camadas SEMPRE carregadas (steering)."""
    return tuple(r for r in _INVENTORY if r.camada == CAMADA_STEERING)


def find_duplicated_rules() -> dict[str, list[str]]:
    """Detecta regras presentes em mais de uma camada SEMPRE carregada (RN-04).

    Como todas as regras sempre carregadas vivem numa única camada (steering),
    a duplicidade real a prevenir é a mesma ``rule_id`` aparecer com camadas
    distintas entre as sempre carregadas. Retorna ``{rule_id: [camadas...]}``
    apenas para as regras duplicadas (vazio quando não há duplicidade).
    """
    seen: dict[str, list[str]] = {}
    for entry in always_loaded_inventory():
        seen.setdefault(entry.rule_id, [])
        if entry.camada not in seen[entry.rule_id]:
            seen[entry.rule_id].append(entry.camada)
    return {rid: camadas for rid, camadas in seen.items() if len(camadas) > 1}


# ══════════════════════════════════════════════════════════════════════════════
# Resolução única do nome da branch (CA-10 / CA-11 / RN-05)
# ══════════════════════════════════════════════════════════════════════════════

_MARKER = re.compile(r"\{([^{}]*)\}")


def _slugify(title: str) -> str:
    """Converte um título em slug kebab-case ASCII simples."""
    import unicodedata

    norm = unicodedata.normalize("NFKD", title)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", "-", norm).strip("-")
    return norm or "issue"


def resolve_branch_name(branch_pattern: str, data: dict) -> str:
    """Resolve o nome da branch a partir do ``branch_pattern`` e dos dados.

    ``data`` fornece os valores dos marcadores (ex.: ``{id}``, ``{slug}``).
    Resolve UMA ÚNICA VEZ por execução (RN-05): o chamador reutiliza o retorno
    idêntico em todos os blocos.

    Marcador não resolvível (ausente/vazio em ``data``) levanta ``ConfigError``
    nomeando o marcador e NÃO emite nome parcialmente resolvido (CA-11/CT-21/22).
    """
    if not isinstance(branch_pattern, str) or not branch_pattern.strip():
        raise ConfigError(
            "branch_pattern: deve ser uma string não-vazia para resolver o nome "
            "da branch"
        )

    markers = _MARKER.findall(branch_pattern)
    faltantes = [
        m for m in markers
        if m not in data or data.get(m) in (None, "")
    ]
    if faltantes:
        raise ConfigError(
            f"branch_pattern '{branch_pattern}': marcador(es) não resolvível(is) "
            f"com os dados da tarefa: {', '.join('{' + m + '}' for m in faltantes)}"
        )

    def _sub(match: re.Match) -> str:
        return str(data[match.group(1)])

    resolved = _MARKER.sub(_sub, branch_pattern)
    # Defesa dupla: nenhum marcador literal pode remanescer.
    if _MARKER.search(resolved):
        raise ConfigError(
            f"branch_pattern '{branch_pattern}': resolução deixou marcador "
            f"não substituído em '{resolved}'"
        )
    return resolved


def branch_data_from_task(task: dict) -> dict:
    """Deriva os dados usados na resolução do nome da branch a partir do task."""
    issue = task.get("issue", {})
    body_path = Path(issue.get("body_path", ""))
    slug = body_path.stem.removesuffix("-body") if body_path.name else ""
    # O slug do arquivo pode já conter o id como prefixo (ex.: 308-foo); para o
    # marcador {slug} preferimos o slug "limpo", mas aceitamos o derivado do
    # título quando disponível.
    title = ""
    if body_path.exists():
        first = body_path.read_text(encoding="utf-8").split("\n", 1)[0]
        title = first.lstrip("# ").strip()
    issue_id = str(issue.get("id", "") or "")
    # Remove um eventual prefixo "<id>-" do slug do arquivo.
    clean_slug = slug
    if issue_id and clean_slug.startswith(f"{issue_id}-"):
        clean_slug = clean_slug[len(issue_id) + 1:]
    clean_slug = clean_slug or (_slugify(title) if title else "")
    return {"id": issue_id, "slug": clean_slug}


# ══════════════════════════════════════════════════════════════════════════════
# Contrato de instruções obrigatórias (CA-4 / CA-5)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class InstructionsCheck:
    """Resultado da verificação das instruções obrigatórias carregadas."""
    carregadas: bool
    motivo: str = ""


def check_required_instructions(steering_path: Path | None) -> InstructionsCheck:
    """Verifica se as instruções obrigatórias (steering) estão carregadas.

    Contrato (CA-4/CA-5): o steering (contexto SEMPRE carregado) deve existir e
    não estar vazio. Ausente/vazio ⇒ ``carregadas=False`` com motivo não-vazio
    (fail-closed: o orquestrador NÃO aciona o agente).
    """
    if steering_path is None:
        return InstructionsCheck(False, "caminho do contexto obrigatório não resolvido")
    try:
        content = steering_path.read_text(encoding="utf-8")
    except OSError:
        return InstructionsCheck(
            False, f"contexto obrigatório ausente em '{steering_path}'"
        )
    if not content.strip():
        return InstructionsCheck(
            False, f"contexto obrigatório vazio em '{steering_path}'"
        )
    return InstructionsCheck(True, "")


# ══════════════════════════════════════════════════════════════════════════════
# Medição por execução (contrato observável do escopo)
# ══════════════════════════════════════════════════════════════════════════════

def _measure(text: str) -> dict:
    """Mede caracteres, palavras e linhas de um texto."""
    text = text or ""
    return {
        "caracteres": len(text),
        "palavras": len(text.split()),
        "linhas": len(text.splitlines()) if text else 0,
    }


def compose_measurement(
    *,
    execucao: str,
    adapter: str,
    prompt_dinamico: str,
    contexto_sempre_carregado: str,
    instrucoes_obrigatorias_carregadas: bool,
    referencias_sob_demanda_incluidas: list[str] | None = None,
    tokens_entrada: int | None = None,
    motivo: str = "",
) -> dict:
    """Monta o registro de medição por execução (contrato observável).

    Função PURA: não aciona o ``kiro-cli``. Emitida por execução ANTES de
    acionar o agente. Quando o adapter não expõe tokens, ``tokens_entrada`` é
    ``None`` (CA-17), sem falhar.
    """
    prompt_m = _measure(prompt_dinamico)
    ctx_m = _measure(contexto_sempre_carregado)
    total_chars = prompt_m["caracteres"] + ctx_m["caracteres"]
    total_words = prompt_m["palavras"] + ctx_m["palavras"]
    registro = {
        "execucao": str(execucao),
        "adapter": str(adapter),
        "prompt_dinamico": prompt_m,
        "contexto_sempre_carregado": ctx_m,
        "total_sempre_carregado": {
            "caracteres": total_chars,
            "palavras": total_words,
        },
        "tokens_entrada": tokens_entrada,
        "referencias_sob_demanda_incluidas": list(referencias_sob_demanda_incluidas or []),
        "instrucoes_obrigatorias_carregadas": bool(instrucoes_obrigatorias_carregadas),
    }
    if motivo:
        registro["motivo"] = motivo
    return registro


# ══════════════════════════════════════════════════════════════════════════════
# Baseline congelado (medição determinística — CA-1 / CA-2 / RN-08)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BaselineSnapshot:
    """Baseline congelado da versão-base para a medição determinística.

    A versão-base é a composição ANTERIOR (todo material invariável embutido no
    prompt dinâmico, e o manual `@---` sempre incluído). Congelamos as métricas
    estáticas aqui para o teste de redução não depender de execução real.
    """
    prompt_dinamico_estatico_chars: int
    prompt_dinamico_chars: int
    contexto_sempre_carregado_chars: int

    @property
    def total_sempre_carregado_chars(self) -> int:
        return self.prompt_dinamico_chars + self.contexto_sempre_carregado_chars
