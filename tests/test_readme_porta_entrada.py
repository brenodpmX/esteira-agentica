import re

from tests import _editorial_helpers as e
from tests import _vitrine_helpers as h


def _readme():
    return e.ler(e.README)


def _abertura(texto):
    m = re.search(r"^# Esteira Agêntica\n(.*?)^## ", texto, re.MULTILINE | re.DOTALL)
    assert m, "CA-1: README sem bloco de abertura entre o título e o primeiro '## '"
    return m.group(1)


def _itens_lista(texto):
    return [l for l in texto.splitlines() if re.match(r"^\s*([-*]|\d+\.)\s+", l)]


def test_intro_comunica_valor_e_capacidades():
    texto = _readme()
    abertura = _abertura(texto)
    assert len(abertura.split()) >= 40, "CA-1: abertura com menos de 40 palavras"
    assert re.search(r"orquestr|automatiz|executa agentes|board", abertura, re.IGNORECASE), (
        "CA-1: abertura não cita nenhuma capacidade do produto"
    )
    assert not e.termos_mecanica_interna(abertura), "CA-1: abertura cita mecânica interna"
    requisitos = h.secao(texto, "Pré-requisitos") or h.secao(texto, "Requisitos")
    assert requisitos, "CA-1: seção '## Pré-requisitos' ausente"
    assert len(_itens_lista(requisitos)) >= 3, "CA-1: pré-requisitos com menos de 3 itens"


def test_secao_limites_presente():
    texto = _readme()
    titulos = [t for t in e.headings(texto)
               if re.search(r"limit|limitaç|fora do escopo|não faz", t, re.IGNORECASE)]
    assert titulos, "CA-1: README sem seção de limites"
    corpo = e.subsecao(texto, re.escape(titulos[0]), nivel=2) or e.subsecao(
        texto, re.escape(titulos[0]), nivel=3)
    assert corpo and len(_itens_lista(corpo)) >= 2, "CA-1: seção de limites com menos de 2 itens"


def test_execucao_local_antes_do_container():
    uso = h.secao(_readme(), "Uso")
    assert uso, "CA-2: seção '## Uso' ausente"
    local = re.search(r"^###\s+.*(execução local|rodar localmente|python -m src)", uso,
                      re.IGNORECASE | re.MULTILINE)
    container = re.search(r"^###\s+.*(container|docker)", uso, re.IGNORECASE | re.MULTILINE)
    assert local and container, "CA-2/CA-3: subseções local e container devem existir em '## Uso'"
    assert local.start() < container.start(), "RN-08: execução local deve vir antes do container"


def test_execucao_local_autossuficiente():
    local = e.subsecao(_readme(), r"execução local|rodar localmente|python -m src")
    assert local, "CA-2: subseção de execução local ausente"
    marcos = ["pip install", "pipe.yml", "PIPE_SSH_KEY_FILE", "python -m src"]
    posicoes = [local.find(m) for m in marcos]
    assert all(p >= 0 for p in posicoes), (
        f"CA-2: elementos ausentes na execução local: "
        f"{[m for m, p in zip(marcos, posicoes) if p < 0]}"
    )
    assert posicoes == sorted(posicoes), f"CA-2: ordem esperada {marcos}"
    assert not re.search(r"código[- ]fonte|src/", local, re.IGNORECASE), (
        "CA-2: a jornada local não pode remeter ao código-fonte"
    )
    permitidos = ("#", "doc/configuracao/referencia.md", "exemplos/")
    externos = [l for l in e.links_markdown(local) if not l.startswith(permitidos)]
    assert not externos, f"CA-2: jornada local remete a fontes fora do escopo: {externos}"


def test_container_alternativa_com_link_runbook():
    container = e.subsecao(_readme(), r"container|docker")
    assert container, "CA-3: subseção de container ausente"
    assert re.search(r"alternativa suportada", container, re.IGNORECASE), (
        "CA-3: container não é apresentado como alternativa"
    )
    assert "doc/runbook/docker.md" in e.links_markdown(container), (
        "CA-3: subseção de container sem link para doc/runbook/docker.md"
    )
    assert (e.RAIZ / "doc" / "runbook" / "docker.md").exists()


def test_links_configuracao_e_exemplos():
    links = e.links_markdown(_readme())
    assert "doc/configuracao/referencia.md" in links, "CA-4: link ao catálogo ausente"
    exemplos = [l for l in links if l.startswith("exemplos/")]
    assert exemplos, "CA-4: link para exemplos/ ausente"
    for link in ["doc/configuracao/referencia.md", *exemplos]:
        assert (e.RAIZ / link.split("#")[0]).exists(), f"CA-4: link quebrado: {link}"


def test_secao_configuracao_enxuta():
    secao = h.secao(_readme(), "Configuração")
    assert secao is not None, "CA-4: seção '## Configuração' ausente"
    linhas = secao.splitlines()
    assert len(linhas) <= e.LIMITE_CONFIGURACAO_LINHAS, (
        f"RNF-05: seção Configuração com {len(linhas)} linhas (> {e.LIMITE_CONFIGURACAO_LINHAS})"
    )
    assert "doc/configuracao/referencia.md" in e.links_markdown(secao)
    assert secao.count("```yaml") == 1, "CA-4: Configuração deve ter um único exemplo mínimo"


def test_sem_mecanica_interna():
    texto = _readme()
    for titulo in e.headings(texto):
        for termo in e.TERMOS_MECANICA_INTERNA:
            assert termo not in titulo.lower(), f"CA-5: heading de mecânica interna: {titulo}"
    assert not e.termos_mecanica_interna(texto), (
        f"CA-5: mecânica interna no README: {e.termos_mecanica_interna(texto)}"
    )


def test_sem_incidentes_e_identificadores():
    texto = _readme()
    incidentes = [t for t in e.headings(texto) if "incidente" in t.lower()]
    assert not incidentes, f"CA-5: heading de incidente: {incidentes}"
    assert not re.search(r"post[- ]mortem", texto, re.IGNORECASE), "CA-5: menção a post-mortem"
    ids = re.findall(r"#\d{2,4}", e.remover_blocos_codigo(texto))
    assert not ids, f"CA-5: identificadores de trabalho no README: {ids}"


def test_readme_enxuto():
    total = len(_readme().splitlines())
    assert total <= e.LIMITE_README_LINHAS, f"RNF-05: README com {total} linhas"


def test_links_relativos_do_readme_resolvem():
    quebrados = [
        l for l in e.links_markdown(_readme())
        if not l.startswith(("http", "#", "mailto:"))
        and not (e.RAIZ / l.split("#")[0]).exists()
    ]
    assert not quebrados, f"RNF-03: links quebrados no README: {quebrados}"
