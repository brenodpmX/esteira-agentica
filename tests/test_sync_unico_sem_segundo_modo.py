"""CT-05 — Ausência de segundo modo de sincronização (RF-06 / RN-04).

Guarda estática sobre `src/`: nenhum caminho, flag, parâmetro ou nome de função
pública seleciona um escopo de dados de sincronização diferente do modelo único.
Garante que não foi reintroduzido, sob outro nome ou como "otimização interna",
um segundo caminho de sincronização com escopo menor.

Escopo da varredura: apenas `src/` (ignora `tests/` e `doc/`).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"


def _src_files():
    return list(SRC.rglob("*.py"))


def _src_text():
    return {f: f.read_text(encoding="utf-8") for f in _src_files()}


# ── (1) A flag fullsync não seleciona dois comportamentos de down ─────────────

def test_fullsync_not_used_as_down_scope_selector():
    """`fullsync` sobrevive apenas como atributo do ChangeItem (reconcilia deps),
    nunca como seletor entre "só propriedades" vs "propriedades+deps" no caminho
    único de descoberta remota.

    A sincronização única (`sync_remote`) só enfileira change-down com
    `fullsync=True`; não existe mais um ramo que emita change-down parcial para
    "escolher" um escopo menor na descoberta do board.
    """
    sync_text = (SRC / "core" / "sync.py").read_text(encoding="utf-8")

    # Isola o corpo de sync_remote.
    start = sync_text.index("def sync_remote(")
    end = sync_text.index("\ndef ", start + 1)
    body = sync_text[start:end]

    # Todo CHANGE_DOWN emitido pela descoberta única é fullsync=True.
    assert "SyncEvent.CHANGE_DOWN" in body
    assert "fullsync=False" not in body
    # Não há leitura de um "since"/corte para decidir o que reconciliar.
    assert "since" not in body
    assert "last_board_update" not in body


# ── (2) last_board_update não decide o que reconciliar ────────────────────────

def test_no_last_board_update_cut_in_src():
    """Nenhum arquivo de `src/` usa `last_board_update` como critério de sync.

    O campo foi descontinuado do snapshot; as únicas menções aceitáveis são
    um comentário histórico de retrocompatibilidade OU o descarte explícito do
    campo legado na carga do snapshot (`pop`), que conclui a descontinuação.
    Qualquer uso que o leia como critério de decisão de fluxo falha.
    """
    for f, text in _src_text().items():
        for lineno, line in enumerate(text.splitlines(), 1):
            if "last_board_update" not in line:
                continue
            stripped = line.strip()
            is_comment = stripped.startswith("#")
            # Descarte do campo legado na carga (discontinuação), não leitura.
            is_discard = ".pop(\"last_board_update\"" in stripped
            assert is_comment or is_discard, (
                f"{f}:{lineno} usa last_board_update como critério: {line!r}")


# ── (3) Não existe função pública de "full sync" separada ─────────────────────

def test_no_separate_full_sync_function_or_daily_trigger():
    """Nenhum símbolo de "caminho completo" paralelo ao "reduzido": sem
    `detect_board_changes`, sem `list_issues_since`, sem acionamento diário
    (`last_full_sync`) em `src/`.
    """
    for f, text in _src_text().items():
        assert "def detect_board_changes" not in text, f"{f} define detect_board_changes"
        assert "detect_board_changes(" not in text, f"{f} chama detect_board_changes"
        assert "def list_issues_since" not in text, f"{f} define list_issues_since"
        assert "list_issues_since(" not in text, f"{f} chama list_issues_since"

    main_text = (SRC / "__main__.py").read_text(encoding="utf-8")
    # Sem o ramo de full sync diário.
    assert "last_full_sync" not in main_text
    # Sem o nome com qualificador "full".
    assert "board_full_sync" not in main_text
