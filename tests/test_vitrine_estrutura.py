import re
import subprocess
import unicodedata

import pytest
import yaml

from src.core.version import VERSION
from tests import _vitrine_helpers as h

PACOTES = h.PACOTES


def _sem_acento(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    ).lower()


def _ler(pacote, nome):
    return (h.EXEMPLOS / pacote / nome).read_text(encoding="utf-8")


def test_exatamente_dois_pacotes():
    achados = {p.parent.name for p in h.EXEMPLOS.glob("*/pipe.yml")}
    assert achados == {"minimalista", "referencia-hipotetica"}


def test_nenhum_tema_extra():
    proibidos = ("kanban", "scrum", "academico", "xgh", "gestao", "atendimento")
    for caminho in h.EXEMPLOS.rglob("*"):
        nome = _sem_acento(caminho.name)
        for termo in proibidos:
            assert termo not in nome, caminho
        assert not re.search(r"\brh\b", nome), caminho


def _git_disponivel():
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _ignorado(caminho):
    r = subprocess.run(
        ["git", "check-ignore", "-q", str(caminho)], cwd=h.RAIZ, capture_output=True
    )
    return r.returncode == 0


@pytest.mark.skipif(not _git_disponivel(), reason="git indisponível")
@pytest.mark.parametrize("pacote", PACOTES)
def test_pacotes_nao_ignorados_pelo_git(pacote):
    base = h.EXEMPLOS / pacote
    arquivos = [base / "pipe.yml", base / "exemplo.yml", base / "USO.md", base / "CUSTOMIZACAO.md"]
    arquivos += sorted((base / "contexts" / "kiro-cli").glob("*.md"))
    assert len(arquivos) > 4
    for arquivo in arquivos:
        assert not _ignorado(arquivo), arquivo


@pytest.mark.skipif(not _git_disponivel(), reason="git indisponível")
def test_excecao_do_gitignore_restrita_a_exemplos():
    assert _ignorado(h.RAIZ / "pipe.yml")
    assert _ignorado(h.RAIZ / "contexts" / "kiro-cli" / "dev.md")


@pytest.mark.parametrize("pacote", PACOTES)
def test_oito_campos_presentes(pacote):
    exemplo = h.carregar_exemplo(pacote)
    for campo in h.CAMPOS_MINIMOS:
        assert campo in exemplo, campo


@pytest.mark.parametrize("pacote", PACOTES)
def test_campos_nao_vazios_e_validos(pacote):
    exemplo = h.carregar_exemplo(pacote)
    assert h.verificar_campos_minimos(exemplo) == []
    assert h.versao_tupla(exemplo["versao_suportada"]) <= h.versao_tupla(VERSION)
    assert len(exemplo["pre_requisitos"]) >= 1


@pytest.mark.parametrize("campo", h.CAMPOS_MINIMOS)
def test_campo_removido_ou_vazio_e_reportado(campo):
    exemplo = h.carregar_exemplo("minimalista")
    sem_campo = {k: v for k, v in exemplo.items() if k != campo}
    assert h.verificar_campos_minimos(sem_campo) == [f"{campo}: ausente"]
    vazio = dict(exemplo, **{campo: "   "})
    assert h.verificar_campos_minimos(vazio) == [f"{campo}: vazio"]


@pytest.mark.parametrize("pacote", PACOTES)
def test_uso_md_secoes_obrigatorias(pacote):
    uso = _ler(pacote, "USO.md")
    for titulo in ("Pré-requisitos", "Como aplicar", "Resultado observável"):
        corpo = h.secao(uso, titulo)
        assert corpo is not None, titulo
        assert len(h.linhas_nao_vazias(corpo)) >= 3, titulo
    pre = h.secao(uso, "Pré-requisitos")
    assert "PIPE_SSH_KEY_FILE" in pre
    assert "github project" in pre.lower()
    for item in h.carregar_exemplo(pacote)["pre_requisitos"]:
        assert item.lower() in uso.lower(), item


@pytest.mark.parametrize("pacote", PACOTES)
def test_referencias_do_uso_resolvem(pacote):
    base = h.EXEMPLOS / pacote
    uso = _ler(pacote, "USO.md")
    custom = _ler(pacote, "CUSTOMIZACAO.md")
    for texto in (uso, custom):
        for token in h.tokens_em_crase(texto):
            if token.endswith((".yml", ".md")) or token.startswith(("contexts/", "exemplos/")):
                assert (base / token).exists() or (h.RAIZ / token).exists(), token
    citados = h.tokens_em_crase(uso)
    assert "pipe.yml" in citados
    assert "issue-exemplo.md" in citados
    pipe = h.carregar_pipe(pacote)
    for plataforma, agentes in pipe["agents"].items():
        for agente in agentes:
            assert f"contexts/{plataforma}/{agente}.md" in citados
    board = next(iter(h.colunas_do_board(pipe).values()))
    entrada = next(iter(board["columns"].values()))["name"]
    assert entrada in uso


def test_diferenca_justificada():
    exemplo = h.carregar_exemplo("referencia-hipotetica")
    diferenca = exemplo["diferenca_em_relacao_ao_minimalista"]
    assert len(diferenca) >= 80
    minimalista = h.carregar_pipe("minimalista")
    referencia = h.carregar_pipe("referencia-hipotetica")

    def nomes(pipe):
        itens = set()
        for board in h.colunas_do_board(pipe).values():
            for col in board["columns"].values():
                itens.add(col["name"].lower())
        for agentes in pipe["agents"].values():
            itens.update(a.lower() for a in agentes)
        return itens

    exclusivos = nomes(referencia) - nomes(minimalista)
    assert any(n in diferenca.lower() for n in exclusivos)


@pytest.mark.parametrize("pacote", PACOTES)
def test_customizacao_separa_substituivel_de_fixo(pacote):
    custom = _ler(pacote, "CUSTOMIZACAO.md")
    sub = h.secao(custom, "Valores substituíveis")
    fixo = h.secao(custom, "Configuração fixa")
    assert sub and h.linhas_nao_vazias(sub)
    assert fixo and h.linhas_nao_vazias(fixo)
    caminhos_sub = set(h.tokens_em_crase(sub))
    caminhos_fixo = set(h.tokens_em_crase(fixo))
    assert caminhos_sub and caminhos_fixo
    assert not (caminhos_sub & caminhos_fixo)
    assert "git.repo.main" in caminhos_sub
    ajuste = _ajuste_testavel(pacote)
    assert ajuste["caminho"] in caminhos_sub
    assert ajuste["caminho"] not in caminhos_fixo
    h.caminho_pontilhado(h.carregar_pipe(pacote), ajuste["caminho"])


def _ajuste_testavel(pacote):
    custom = _ler(pacote, "CUSTOMIZACAO.md")
    m = re.search(r"<!-- ajuste-testavel -->\s*```yaml\n(.*?)```", custom, re.DOTALL)
    assert m, "bloco ajuste-testavel ausente"
    return yaml.safe_load(m.group(1))


def _arquivos_publicados():
    return h.arquivos_texto(h.EXEMPLOS) + h.arquivos_texto(h.DOC_EXEMPLOS)


def test_varredura_sem_dados_sensiveis():
    arquivos = _arquivos_publicados()
    assert arquivos
    for arquivo in arquivos:
        achados = h.varrer_sensiveis(arquivo.read_text(encoding="utf-8"))
        assert achados == [], (arquivo, achados)


@pytest.mark.parametrize("pacote", PACOTES)
def test_repositorio_hipotetico(pacote):
    pipe = h.carregar_pipe(pacote)
    assert re.fullmatch(
        r"git@github\.com:exemplo-org/[a-z0-9-]+-hipotetico\.git", pipe["git"]["repo"]["main"]
    )


def test_varredura_detecta_segredo_injetado():
    assert h.varrer_sensiveis("token ghp_" + "a" * 30)
    assert h.varrer_sensiveis("contato fulano@empresa.com.br")
    assert h.varrer_sensiveis("-----BEGIN RSA PRIVATE KEY-----")
    assert h.varrer_sensiveis("contato fulano@example.com") == []


@pytest.mark.parametrize("pacote", PACOTES)
def test_cenario_rotulado_hipotetico(pacote):
    for nome in ("USO.md", "exemplo.yml", "issue-exemplo.md", "CUSTOMIZACAO.md"):
        cabecalho = "\n".join(_ler(pacote, nome).splitlines()[:15]).lower()
        assert "hipotétic" in cabecalho, nome
    pipe_texto = _ler(pacote, "pipe.yml")
    primeira = pipe_texto.splitlines()[0]
    assert primeira.startswith("#") and "hipotétic" in primeira.lower()
    projeto = h.carregar_pipe(pacote)["project"]
    assert "hipotétic" in projeto["name"].lower()
    assert "hipotétic" in projeto["summary"].lower()


@pytest.mark.parametrize("pacote", PACOTES)
def test_sem_identificadores_reais(pacote):
    pipe = h.carregar_pipe(pacote)
    for humano in pipe["project"].get("humans", []):
        assert humano["name"].startswith("Pessoa ")
    responsavel = h.carregar_exemplo(pacote)["responsavel_pela_revisao"]
    assert not re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", responsavel.replace("Mantenedor(a) da Esteira", ""))
    for arquivo in h.arquivos_texto(h.EXEMPLOS / pacote):
        texto = arquivo.read_text(encoding="utf-8")
        assert "brenodpmX" not in texto
        for url in re.findall(r"git@github\.com:[^\s]+", texto):
            assert "exemplo-org/" in url
