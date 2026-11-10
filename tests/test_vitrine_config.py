import re
import shutil

import pytest
import yaml

from src.core import config
from tests import _vitrine_helpers as h

PACOTES = h.PACOTES


@pytest.fixture
def instalar(tmp_path, monkeypatch):
    def _instalar(pacote):
        destino = tmp_path / pacote
        shutil.copytree(h.EXEMPLOS / pacote, destino)
        chave = tmp_path / "chave-exemplo"
        chave.write_text("", encoding="utf-8")
        monkeypatch.setattr(config, "PIPE_FILE", destino / "pipe.yml")
        monkeypatch.setattr(config, "CONTEXTS_DIR", destino / "contexts")
        monkeypatch.setenv("PIPE_SSH_KEY_FILE", str(chave))
        return destino

    return _instalar


def _colunas(pipe):
    boards = h.colunas_do_board(pipe)
    assert len(boards) >= 1
    return next(iter(boards.values()))["columns"]


@pytest.mark.parametrize("pacote", PACOTES)
def test_check_config_aceita_exemplo(instalar, pacote):
    instalar(pacote)
    cfg = config.check_config()
    assert len(h.colunas_do_board(cfg)) >= 1
    assert cfg["project"]["name"].strip()
    assert cfg["project"]["summary"].strip()


@pytest.mark.parametrize("pacote", PACOTES)
def test_contextos_preenchidos_padrao(pacote):
    pipe = h.carregar_pipe(pacote)
    esperados = set()
    for plataforma, agentes in pipe["agents"].items():
        for agente in agentes:
            arquivo = h.EXEMPLOS / pacote / "contexts" / plataforma / f"{agente}.md"
            assert arquivo.exists(), arquivo
            assert len(arquivo.read_text(encoding="utf-8").strip()) >= 50
            esperados.add(arquivo)
    existentes = set((h.EXEMPLOS / pacote / "contexts").rglob("*.md"))
    assert existentes == esperados


@pytest.mark.parametrize("pacote", PACOTES)
def test_contexto_vazio_reprova_exemplo(instalar, pacote):
    destino = instalar(pacote)
    arquivo = next((destino / "contexts" / "kiro-cli").glob("*.md"))
    arquivo.write_text("  \n", encoding="utf-8")
    with pytest.raises(config.ConfigError, match="vazios"):
        config.check_config()
    arquivo.unlink()
    with pytest.raises(config.ConfigError, match="ausentes"):
        config.check_config()


@pytest.mark.parametrize("pacote", PACOTES)
def test_encadeamento_chega_ao_estado_final(pacote):
    colunas = _colunas(h.carregar_pipe(pacote))
    ids = list(colunas)
    assert not colunas[ids[0]].get("agent")
    percurso, problemas = h.cadeia_de_execucao(colunas)
    assert problemas == []
    assert colunas[percurso[-1]].get("archive") is True
    assert len(percurso) <= len(colunas) + 1


@pytest.mark.parametrize("pacote", PACOTES)
def test_resultado_esperado_observavel(pacote):
    exemplo = h.carregar_exemplo(pacote)
    esperado = exemplo["resultado_esperado"].lower()
    tipos = [t for t in ("coluna", "comentário", "pull request") if t in esperado]
    assert tipos
    uso = (h.EXEMPLOS / pacote / "USO.md").read_text(encoding="utf-8")
    observavel = h.secao(uso, "Resultado observável")
    assert observavel and observavel.strip()
    assert any(t in observavel.lower() for t in tipos)
    colunas = _colunas(h.carregar_pipe(pacote))
    nome_final = next(c["name"] for c in colunas.values() if c.get("archive") is True)
    assert nome_final in observavel
    assert nome_final in exemplo["resultado_esperado"]


def test_referencia_mais_rica_que_minimalista():
    mini = h.carregar_pipe("minimalista")
    ref = h.carregar_pipe("referencia-hipotetica")
    col_mini = _colunas(mini)
    col_ref = _colunas(ref)
    com_agente_mini = [c for c in col_mini.values() if c.get("agent")]
    com_agente_ref = [c for c in col_ref.values() if c.get("agent")]
    agentes_mini = {a for ags in mini["agents"].values() for a in ags}
    agentes_ref = {a for ags in ref["agents"].values() for a in ags}
    assert len(h.colunas_do_board(mini)) == 1
    assert len(agentes_mini) == 1
    assert len(com_agente_mini) == 1
    assert len(col_mini) <= 3
    assert len(col_ref) > len(col_mini)
    assert len(col_ref) >= 4
    assert len(com_agente_ref) >= 2 or len(agentes_ref) >= 2
    assert {c["agent"] for c in com_agente_ref} <= agentes_ref


@pytest.mark.parametrize("pacote", PACOTES)
def test_ajuste_documentado_preserva_resultado(instalar, pacote):
    destino = instalar(pacote)
    custom = (h.EXEMPLOS / pacote / "CUSTOMIZACAO.md").read_text(encoding="utf-8")
    m = re.search(r"<!-- ajuste-testavel -->\s*```yaml\n(.*?)```", custom, re.DOTALL)
    ajuste = yaml.safe_load(m.group(1))
    pipe = yaml.safe_load((destino / "pipe.yml").read_text(encoding="utf-8"))
    original = h.caminho_pontilhado(pipe, ajuste["caminho"])
    assert ajuste["novo_valor"] != original
    h.definir_caminho_pontilhado(pipe, ajuste["caminho"], ajuste["novo_valor"])
    (destino / "pipe.yml").write_text(yaml.safe_dump(pipe, allow_unicode=True), encoding="utf-8")
    cfg = config.check_config()
    percurso, problemas = h.cadeia_de_execucao(_colunas(cfg))
    assert problemas == []
    assert _colunas(cfg)[percurso[-1]].get("archive") is True
