import re
from pathlib import Path

from tests._vitrine_helpers import PADROES_SENSIVEIS

RAIZ = Path(__file__).resolve().parent.parent
README = RAIZ / "README.md"
NOVIDADES = RAIZ / "NOVIDADES.md"
CATALOGO = RAIZ / "doc" / "configuracao" / "referencia.md"
GOVERNANCA = RAIZ / "doc" / "governanca-editorial"
INVENTARIO = GOVERNANCA / "inventario-conteudo-publico.md"
MANUAL = GOVERNANCA / "manual-padroes-documentacao.md"
GATE = GOVERNANCA / "gate-revisao.md"
COMUNICACAO = GOVERNANCA / "comunicacao-versao.md"
BASELINE = GOVERNANCA / "baseline-avaliacao.md"

CAMPOS_CATALOGO = (
    "chave",
    "descricao",
    "tipo",
    "obrigatoriedade",
    "default",
    "valores_aceitos",
    "efeito_ausencia",
    "exemplo",
)
TIPOS_CATALOGO = ("string", "inteiro", "booleano", "lista", "mapa")
OBRIGATORIEDADES = ("obrigatória", "opcional")

CAMPOS_INVENTARIO = (
    "documento",
    "audiencia",
    "sensibilidade",
    "fonte_canonica",
    "responsavel",
    "gatilho_atualizacao",
)
AUDIENCIAS = ("publico", "interno", "misto")
SENSIBILIDADES = ("baixa", "media", "alta")
DECISAO_MINIMA = 20

CAMPOS_NOTA = ("versao", "data", "destaques", "acao")

PASTAS_PUBLICAS = ("doc/runbook/", "exemplos/", "doc/configuracao/")
PASTAS_INTERNAS = (
    "doc/architecture/",
    "doc/incidente/",
    "doc/product/",
    "doc/quality/",
    "doc/interno/",
    "doc/changes/",
    "doc/changelogs/",
    "doc/stories/",
    "doc/requirements/",
)

TERMOS_MECANICA_INTERNA = (
    "loop principal",
    "sleep_time",
    "keep_task",
    "otimização de sincronização",
    "rate limit",
    "proteção de estado interno",
)

LIMITE_NOTA_CARACTERES = 800
LIMITE_README_LINHAS = 600
LIMITE_CONFIGURACAO_LINHAS = 60

_LINHA_CAMPO = re.compile(r"^([a-z_]+):\s*(.*)$")
_IDENTIFICADOR_TRABALHO = re.compile(r"(?<![\w&/])#\d{1,5}\b")
_ARTEFATO_PROCESSO = re.compile(
    r"\b(épicos?|epics?|histórias?|story|stories)\b\s*#?\d*",
    re.IGNORECASE,
)
_PROMESSA_FINANCEIRA = re.compile(
    r"(economiz\w*\s+(até\s+)?\d+\s*%|retorno\s+garantido|"
    r"reduz\w*\s+(os\s+)?custos?\s+em\s+\d+|ROI\s+de\s+\d+|"
    r"\d+\s*%\s+(de\s+)?(economia|redução de custo))",
    re.IGNORECASE,
)
_ITEM_LISTA = re.compile(r"^\s*([-*+]|\d+[.)])\s+")


def parse_blocos(texto, campo_inicial):
    blocos = []
    atual = None
    for linha in texto.splitlines():
        m = _LINHA_CAMPO.match(linha)
        if not m:
            continue
        campo, valor = m.group(1), m.group(2).strip()
        if campo == campo_inicial:
            atual = {}
            blocos.append(atual)
        if atual is not None:
            atual[campo] = valor
    return blocos


def remover_blocos_codigo(texto):
    return re.sub(r"```.*?```", "", texto, flags=re.DOTALL)


def headings(texto):
    return [
        linha.lstrip("#").strip()
        for linha in remover_blocos_codigo(texto).splitlines()
        if re.match(r"^#{1,6}\s", linha)
    ]


def subsecao(texto, padrao, nivel=3):
    linhas = texto.splitlines()
    marcador = "#" * nivel + " "
    for i, linha in enumerate(linhas):
        if linha.startswith(marcador) and re.search(padrao, linha, re.IGNORECASE):
            corpo = []
            for seguinte in linhas[i + 1:]:
                m = re.match(r"^(#{1,6})\s", seguinte)
                if m and len(m.group(1)) <= nivel:
                    break
                corpo.append(seguinte)
            return "\n".join(corpo)
    return None


def links_markdown(texto):
    return re.findall(r"\]\(([^)\s]+)\)", texto)


def artefatos_internos(texto):
    achados = _IDENTIFICADOR_TRABALHO.findall(texto)
    achados += [m.group(0).strip() for m in _ARTEFATO_PROCESSO.finditer(texto)]
    return achados


def termos_mecanica_interna(texto):
    sem_links = re.sub(r"\[[^\]]*\]\([^)]*\)", "", remover_blocos_codigo(texto))
    minusculo = sem_links.lower()
    return [t for t in TERMOS_MECANICA_INTERNA if t in minusculo]


def validar_entrada_catalogo(bloco):
    erros = []
    for campo in CAMPOS_CATALOGO:
        if not bloco.get(campo):
            erros.append(f"{bloco.get('chave', '?')}: campo '{campo}' ausente ou vazio")
    tipo = bloco.get("tipo")
    if tipo and tipo not in TIPOS_CATALOGO:
        erros.append(f"{bloco.get('chave')}: tipo '{tipo}' fora de {TIPOS_CATALOGO}")
    obrig = bloco.get("obrigatoriedade")
    if obrig and obrig not in OBRIGATORIEDADES:
        erros.append(
            f"{bloco.get('chave')}: obrigatoriedade '{obrig}' fora de {OBRIGATORIEDADES}"
        )
    return erros


def validar_item_inventario(item):
    erros = []
    documento = item.get("documento", "?")
    for campo in CAMPOS_INVENTARIO:
        if not item.get(campo):
            erros.append(f"{documento}: campo '{campo}' ausente ou vazio")
    audiencia = item.get("audiencia")
    if audiencia and audiencia not in AUDIENCIAS:
        erros.append(f"{documento}: audiencia '{audiencia}' fora de {AUDIENCIAS}")
    sensibilidade = item.get("sensibilidade")
    if sensibilidade and sensibilidade not in SENSIBILIDADES:
        erros.append(
            f"{documento}: sensibilidade '{sensibilidade}' fora de {SENSIBILIDADES}"
        )
    decisao = item.get("decisao", "")
    if audiencia == "misto" and len(decisao) < DECISAO_MINIMA:
        erros.append(f"{documento}: audiencia 'misto' exige 'decisao' registrada")
    if _excecao_de_pasta(documento, audiencia) and len(decisao) < DECISAO_MINIMA:
        erros.append(
            f"{documento}: audiencia '{audiencia}' diverge da pasta; "
            f"exige 'decisao' registrada pela finalidade"
        )
    return erros


def _excecao_de_pasta(documento, audiencia):
    if audiencia == "publico":
        return documento.startswith(PASTAS_INTERNAS)
    if audiencia == "interno":
        return documento.startswith(PASTAS_PUBLICAS)
    return False


def avaliar_gate_revisao(texto, tipo="documento"):
    motivos = []
    for termo in termos_mecanica_interna(texto):
        motivos.append(
            f"fronteira público/interno: conteúdo de mecânica interna ('{termo}')"
        )
    for artefato in artefatos_internos(texto):
        motivos.append(f"artefato interno citado: '{artefato}'")
    for m in _PROMESSA_FINANCEIRA.finditer(texto):
        motivos.append(f"promessa de retorno financeiro: '{m.group(0)}'")
    for padrao in PADROES_SENSIVEIS:
        m = padrao.search(texto)
        if m:
            motivos.append(f"instrução insegura: dado sensível exposto ('{m.group(0)}')")
    if tipo == "nota_versao":
        motivos += _avaliar_estilo_nota(texto)
    return motivos


def _avaliar_estilo_nota(texto):
    motivos = []
    if len(texto) > LIMITE_NOTA_CARACTERES:
        motivos.append(
            f"registro editorial inadequado: nota longa demais "
            f"({len(texto)} > {LIMITE_NOTA_CARACTERES} caracteres)"
        )
    itens = [linha for linha in texto.splitlines() if _ITEM_LISTA.match(linha)]
    if itens:
        motivos.append(
            f"registro editorial inadequado: lista tecnicista ({len(itens)} itens de lista)"
        )
    return motivos


def texto_nota(nota):
    return "\n".join(f"{campo}: {nota.get(campo, '')}" for campo in CAMPOS_NOTA)


def auditar_mudancas_elegiveis(mudancas, notas):
    relatos = []
    por_versao = {n["versao"]: n for n in notas}
    for mudanca in mudancas:
        if not mudanca.get("elegivel"):
            continue
        versao = mudanca["versao"]
        nota = por_versao.get(versao)
        if nota is None:
            relatos.append(f"{versao}: mudança elegível sem nota correspondente")
        elif nota.get("data") != mudanca.get("data"):
            relatos.append(
                f"{versao}: publicação fora do mesmo momento "
                f"(mudança {mudanca.get('data')}, nota {nota.get('data')})"
            )
    return relatos


def regras_do_manual(texto):
    corpo = []
    dentro = False
    for linha in texto.splitlines():
        if linha.startswith("## "):
            dentro = linha.strip() == "## Regras"
            continue
        if dentro:
            corpo.append(linha)
    regras = []
    for linha in corpo:
        m = re.match(r"^\d+\.\s+\*\*(MP-\d{2})\*\*\s*[—-]\s*(.+)$", linha)
        if m:
            regras.append([m.group(1), m.group(2)])
        elif regras and linha.startswith("   ") and linha.strip():
            regras[-1][1] += " " + linha.strip()
    return [(rid, txt) for rid, txt in regras]


def avaliar_conformidade_manual(texto, documento="README.md"):
    divergencias = []
    for artefato in artefatos_internos(texto):
        divergencias.append(f"MP-04: identificador de trabalho interno '{artefato}'")
    for padrao in PADROES_SENSIVEIS:
        m = padrao.search(texto)
        if m:
            divergencias.append(f"MP-05: dado sensível exposto ('{m.group(0)}')")
    if documento != "README.md":
        return divergencias
    for termo in termos_mecanica_interna(texto):
        divergencias.append(f"MP-06: mecânica interna na porta de entrada ('{termo}')")
    for titulo in headings(texto):
        if re.search(r"incidente|post[- ]mortem", titulo, re.IGNORECASE):
            divergencias.append(f"MP-06: relato de incidente na porta de entrada ('{titulo}')")
    total = len(texto.splitlines())
    if total > LIMITE_README_LINHAS:
        divergencias.append(f"MP-07: README com {total} linhas (> {LIMITE_README_LINHAS})")
    pos_local = _posicao_heading(texto, r"execução local|rodar localmente|python -m src")
    pos_container = _posicao_heading(texto, r"container|docker")
    if pos_local is None or pos_container is None or pos_local > pos_container:
        divergencias.append("MP-08: execução local deve aparecer antes do container")
    links = links_markdown(texto)
    for destino in ("doc/configuracao/referencia.md", "doc/runbook/docker.md", "exemplos/"):
        if not any(link.startswith(destino) for link in links):
            divergencias.append(f"MP-09: link obrigatório ausente para '{destino}'")
    return divergencias


def _posicao_heading(texto, padrao):
    for m in re.finditer(r"^#{2,6}\s+(.+)$", texto, re.MULTILINE):
        if re.search(padrao, m.group(1), re.IGNORECASE):
            return m.start()
    return None


def ler(caminho):
    return Path(caminho).read_text(encoding="utf-8")
