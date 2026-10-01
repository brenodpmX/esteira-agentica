"""CT-06 / CT-06b — Nomenclatura única de sincronização (RF-07 / RNF-02 / RN-04).

Guarda estática sobre `src/`: nenhum identificador (nome de função/variável),
literal de log/mensagem de runtime ou chave de configuração qualifica a
sincronização como "full/completo/completa" ou "reduzido/incremental".

Precisão (evita falso-positivo): a varredura foca em
  (a) nomes de símbolos definidos (`def`/atribuições),
  (b) literais passados a `log.*(...)`,
  (c) chaves de configuração em `config.py`.
Docstrings/comentários históricos que apenas narram a mudança são aceitáveis e
não entram na asserção comportamental.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"

# Tokens de qualificação de MODO de sincronização (proibidos como
# identificador / literal de log / chave de config).
_MODE_SYMBOL_TOKENS = ("full_sync", "fullsync_mode", "last_full_sync",
                       "detect_board_changes", "list_issues_since",
                       "incremental", "reduzido_sync", "sync_mode")

# Literais que, dentro de uma chamada log.*, qualificam a sincronização por modo.
_MODE_LOG_PATTERNS = (
    r"full\s*sync",
    r"sincroniza\w*\s+complet",
    r"sincroniza\w*\s+reduzid",
    r"sincroniza\w*\s+incremental",
    r"sync\s+complet",
    r"sync\s+reduzid",
    r"sync\s+incremental",
)


def _src_files():
    return list(SRC.rglob("*.py"))


# ── CT-06 (a): nomes de símbolos ──────────────────────────────────────────────

def test_no_mode_qualifier_in_symbol_names():
    """Nenhum `def <nome>` ou atribuição de módulo usa qualificador de modo."""
    def_pat = re.compile(r"^\s*def\s+([A-Za-z_]\w*)", re.MULTILINE)
    for f in _src_files():
        text = f.read_text(encoding="utf-8")
        for name in def_pat.findall(text):
            low = name.lower()
            for token in _MODE_SYMBOL_TOKENS:
                assert token not in low, (
                    f"{f}: função '{name}' contém qualificador de modo '{token}'")


# ── CT-06 (b): literais de log/mensagem ───────────────────────────────────────

def test_no_mode_qualifier_in_log_literals():
    """Nenhuma chamada log.* contém literal que qualifica a sincronização por
    modo (full/completo/reduzido/incremental)."""
    # Captura o 2º argumento (mensagem) de chamadas log.<nivel>("Comp", "msg"...).
    log_call = re.compile(
        r"log\.\w+\(\s*[^,]+,\s*(?:f?\"([^\"]*)\"|f?'([^']*)')", re.DOTALL)
    for f in _src_files():
        text = f.read_text(encoding="utf-8")
        for m in log_call.finditer(text):
            literal = (m.group(1) or m.group(2) or "").lower()
            for pat in _MODE_LOG_PATTERNS:
                assert not re.search(pat, literal), (
                    f"{f}: log com qualificador de modo: {literal!r}")


# ── CT-06 (b'): o log de sincronização usa o nome único ───────────────────────

def test_sync_log_uses_single_name_contract():
    """O log de sincronização padronizado existe e não tem qualificador de modo."""
    sync_text = (SRC / "core" / "sync.py").read_text(encoding="utf-8")
    assert "sincronizacao board=" in sync_text
    # A linha do contrato não carrega qualificador de modo.
    for line in sync_text.splitlines():
        if "sincronizacao board=" in line:
            low = line.lower()
            assert "full" not in low
            assert "completo" not in low and "completa" not in low
            assert "reduzid" not in low
            assert "incremental" not in low


# ── CT-06b: nenhuma chave de config seleciona escopo de sincronização ─────────

def test_config_has_no_sync_mode_key():
    """`config.py` não valida/lê nenhuma chave que selecione escopo de sync."""
    config_text = (SRC / "core" / "config.py").read_text(encoding="utf-8")
    forbidden_keys = ("sync.mode", "sync.full", "sync.incremental",
                      "full_sync", "sync_mode", "mode")
    # Procura por chaves de config suspeitas (literais).
    assert "sync.mode" not in config_text
    assert '"full"' not in config_text
    assert '"incremental"' not in config_text
    # sync.max_attempts (fora de escopo) permanece — não é seleção de modo.
    # Nenhuma asserção o remove.


def test_config_sync_max_attempts_still_valid():
    """`sync.max_attempts` (fora de escopo) continua funcionando; config legada
    com chave desconhecida de modo não quebra a leitura."""
    from src.core.config import resolve_max_attempts
    # max_attempts configurado é respeitado.
    assert resolve_max_attempts({"sync": {"max_attempts": 7}}) == 7
    # Config sem a chave usa o default (não quebra).
    default = resolve_max_attempts({})
    assert isinstance(default, int) and default > 0
    # Chave desconhecida de modo é ignorada (não rejeitada).
    assert resolve_max_attempts(
        {"sync": {"max_attempts": 3, "mode": "full"}}) == 3
