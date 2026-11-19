import pytest
import yaml

from tests import _editorial_helpers as e

CHAVES_CONFIGURACAO_CONHECIDAS = (
    "sleep",
    "log.dir",
    "log.ttl",
    "log.level",
    "registro.retencao_dias",
    "agent_timeout_seg",
    "retry.max_tentativas",
    "retry.backoff_inicial_seg",
    "retry.backoff_fator",
    "safety.cross_board_parent_links",
    "sync.max_attempts",
    "sync.circuit_breaker.persistence",
    "sync.circuit_breaker.escalation_agent",
    "sync.circuit_breaker.issue.max_failures",
    "sync.circuit_breaker.issue.block_duration",
    "sync.circuit_breaker.issue.max_blocks",
    "sync.circuit_breaker.platform.max_blocked_issues",
    "sync.circuit_breaker.platform.block_window",
    "sync.circuit_breaker.platform.block_duration",
    "sync.circuit_breaker.half_open.success_threshold",
    "agent_circuit_break.executions",
    "agent_circuit_break.window",
    "project.name",
    "project.summary",
    "project.humans.name",
    "project.humans.role",
    "git.repo.main",
    "git.repo.<repo_id>",
    "git.flow.base",
    "git.flow.<flow_id>.prefix",
    "git.flow.<flow_id>.name",
    "git.flow.<flow_id>.branch_pattern",
    "git.flow.<flow_id>.create",
    "git.flow.<flow_id>.merge",
    "agents.<platform_id>.<agent_id>.name",
    "agents.<platform_id>.<agent_id>.model",
    "agents.<platform_id>.limits.timezone",
    "agents.<platform_id>.limits.daily.limit",
    "agents.<platform_id>.limits.weekly.limit",
    "agents.<platform_id>.limits.weekly.reset_weekday",
    "agents.<platform_id>.limits.monthly.limit",
    "agents.<platform_id>.limits.monthly.reset_day",
    "boards.platform",
    "boards.rerun_cooldown",
    "boards.<board_id>.name",
    "boards.<board_id>.priority",
    "boards.<board_id>.flow",
    "boards.<board_id>.repo",
    "boards.<board_id>.todo",
    "boards.<board_id>.parallel",
    "boards.<board_id>.column-migrations.<origem>",
    "boards.<board_id>.file-sync.allowed-types",
    "boards.<board_id>.file-sync.max-size",
    "boards.<board_id>.file-sync.on-reject",
    "boards.<board_id>.columns.<column_id>.name",
    "boards.<board_id>.columns.<column_id>.agent",
    "boards.<board_id>.columns.<column_id>.agent-hub.<valor>",
    "boards.<board_id>.columns.<column_id>.on_in",
    "boards.<board_id>.columns.<column_id>.on_out",
    "boards.<board_id>.columns.<column_id>.gitevents",
    "boards.<board_id>.columns.<column_id>.target-prompt",
    "boards.<board_id>.columns.<column_id>.step-prompt",
    "boards.<board_id>.columns.<column_id>.change.advance",
    "boards.<board_id>.columns.<column_id>.change.<condicao>",
    "boards.<board_id>.columns.<column_id>.archive",
)

TIPOS_PYTHON = {
    "string": (str,),
    "inteiro": (int,),
    "booleano": (bool,),
    "lista": (list,),
    "mapa": (dict,),
}


@pytest.fixture(scope="module")
def entradas():
    assert e.CATALOGO.exists(), f"CA-9: {e.CATALOGO} ausente"
    return e.parse_blocos(e.ler(e.CATALOGO), "chave")


def test_entradas_tem_oito_campos(entradas):
    assert entradas, "CA-9: catálogo sem nenhuma entrada"
    erros = [erro for bloco in entradas for erro in e.validar_entrada_catalogo(bloco)]
    assert not erros, "CA-9: entradas incompletas:\n" + "\n".join(erros)


def test_cobertura_completa(entradas):
    descritas = {b["chave"].strip("`") for b in entradas}
    ausentes = [c for c in CHAVES_CONFIGURACAO_CONHECIDAS if c not in descritas]
    assert not ausentes, f"RNF-06: chaves sem entrada no catálogo: {ausentes}"


def test_sem_duplicatas_e_sem_chave_estranha(entradas):
    chaves = [b["chave"] for b in entradas]
    duplicadas = sorted({c for c in chaves if chaves.count(c) > 1})
    assert not duplicadas, f"CA-9: chaves duplicadas: {duplicadas}"
    estranhas = [
        b["chave"] for b in entradas
        if b["chave"] not in CHAVES_CONFIGURACAO_CONHECIDAS
        and b.get("status") not in ("obsoleta", "experimental")
    ]
    assert not estranhas, f"CA-9: chaves fora da lista canônica sem status: {estranhas}"


def test_exemplo_valido_por_tipo(entradas):
    erros = []
    for bloco in entradas:
        try:
            valor = yaml.safe_load(bloco["exemplo"])
        except yaml.YAMLError as exc:
            erros.append(f"{bloco['chave']}: exemplo não é YAML válido ({exc})")
            continue
        esperado = TIPOS_PYTHON[bloco["tipo"]]
        ok = isinstance(valor, esperado)
        if bloco["tipo"] == "inteiro" and isinstance(valor, bool):
            ok = False
        if not ok:
            erros.append(f"{bloco['chave']}: exemplo {valor!r} incompatível com '{bloco['tipo']}'")
    assert not erros, "RNF-03: exemplos inválidos:\n" + "\n".join(erros)


def test_chaves_obrigatorias_batem_com_o_motor(entradas):
    obrigatorias = {b["chave"] for b in entradas if b["obrigatoriedade"] == "obrigatória"}
    esperadas = {
        "sleep",
        "project.name",
        "project.summary",
        "git.repo.main",
        "git.flow.base",
        "git.flow.<flow_id>.branch_pattern",
        "agents.<platform_id>.<agent_id>.name",
        "boards.platform",
        "boards.<board_id>.name",
        "boards.<board_id>.columns.<column_id>.name",
    }
    assert esperadas <= obrigatorias, (
        f"RNF-03: chaves exigidas pelo motor marcadas como opcionais: {esperadas - obrigatorias}"
    )
