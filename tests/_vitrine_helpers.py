import re
from datetime import date
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLOS = RAIZ / "exemplos"
DOC_EXEMPLOS = RAIZ / "doc" / "exemplos"
REGISTROS = DOC_EXEMPLOS / "registros"
PACOTES = ("minimalista", "referencia-hipotetica")

CAMPOS_MINIMOS = (
    "objetivo",
    "publico",
    "caso_de_uso",
    "pre_requisitos",
    "resultado_esperado",
    "limites",
    "versao_suportada",
    "responsavel_pela_revisao",
    "gatilho_de_revisao",
)

CAMPOS_VALIDACAO = (
    "exemplo",
    "data",
    "versao_suportada",
    "resultado",
    "ponto_da_falha",
    "ajuda_necessaria",
    "tempo_observado",
    "falhas",
    "duvidas",
    "qualidade_vs_objetivo",
    "modelo",
    "tokens",
    "custo",
    "cenario",
)

_LINHA_REGISTRO = re.compile(r"^([a-z_]+):\s*(.*)$")

PADROES_SENSIVEIS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[abp]-"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"),
    re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"),
    re.compile(r"\(?\d{2}\)?\s?9?\d{4}-\d{4}"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"\b(?!git@github\.com)[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)[A-Za-z0-9-]+\.[A-Za-z.]+"),
)


def parse_registro(texto):
    dados = {}
    for linha in texto.splitlines():
        m = _LINHA_REGISTRO.match(linha)
        if m:
            dados[m.group(1)] = m.group(2).strip()
    return dados


def carregar_registros(diretorio):
    return [
        (p, parse_registro(p.read_text(encoding="utf-8")))
        for p in sorted(Path(diretorio).glob("*.md"))
    ]


def carregar_exemplo(pacote):
    with open(EXEMPLOS / pacote / "exemplo.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def carregar_pipe(pacote):
    with open(EXEMPLOS / pacote / "pipe.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def secao(texto, titulo):
    linhas = texto.splitlines()
    cabecalho = f"## {titulo}"
    for i, linha in enumerate(linhas):
        if linha.strip() == cabecalho:
            corpo = []
            for seguinte in linhas[i + 1:]:
                if seguinte.startswith("## "):
                    break
                corpo.append(seguinte)
            return "\n".join(corpo)
    return None


def linhas_nao_vazias(texto):
    return [linha for linha in texto.splitlines() if linha.strip()]


def _vazio(valor):
    if valor is None:
        return True
    if isinstance(valor, (list, tuple)):
        return not any(not _vazio(v) for v in valor)
    return not str(valor).strip()


def verificar_campos_minimos(exemplo):
    problemas = []
    for campo in CAMPOS_MINIMOS:
        if campo not in exemplo:
            problemas.append(f"{campo}: ausente")
        elif _vazio(exemplo[campo]):
            problemas.append(f"{campo}: vazio")
    versao = exemplo.get("versao_suportada")
    if not _vazio(versao) and not re.fullmatch(r"\d+\.\d+\.\d+", str(versao)):
        problemas.append("versao_suportada: formato inválido")
    return problemas


def versao_tupla(versao):
    return tuple(int(p) for p in str(versao).split("."))


def varrer_sensiveis(texto):
    achados = []
    for padrao in PADROES_SENSIVEIS:
        for m in padrao.finditer(texto):
            achados.append(m.group(0))
    return achados


def arquivos_texto(base):
    return [
        p
        for p in sorted(Path(base).rglob("*"))
        if p.is_file() and p.name != ".gitkeep"
    ]


def caminho_pontilhado(dados, caminho):
    atual = dados
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            raise KeyError(caminho)
        atual = atual[parte]
    return atual


def definir_caminho_pontilhado(dados, caminho, valor):
    partes = caminho.split(".")
    atual = dados
    for parte in partes[:-1]:
        atual = atual[parte]
    atual[partes[-1]] = valor


def tokens_em_crase(texto):
    return re.findall(r"`([^`\n]+)`", texto)


def colunas_do_board(pipe):
    boards = {
        k: v
        for k, v in pipe["boards"].items()
        if isinstance(v, dict) and "columns" in v
    }
    return boards


def cadeia_de_execucao(colunas):
    ids = list(colunas)
    entrada = ids[0]
    atual = next((c for c in ids if colunas[c].get("agent")), None)
    percurso = [entrada]
    vistos = set()
    problemas = []
    if atual is None:
        return percurso, ["nenhuma coluna com agente"]
    while True:
        if atual in vistos:
            problemas.append("ciclo no encadeamento")
            break
        vistos.add(atual)
        percurso.append(atual)
        col = colunas[atual]
        if col.get("archive") is True:
            break
        if col.get("agent") and not str(col.get("target-prompt", "")).strip():
            problemas.append(f"{atual}: target-prompt vazio")
        destino = (col.get("change") or {}).get("advance")
        if destino is None:
            problemas.append(f"{atual}: sem change.advance e sem archive")
            break
        if destino not in colunas:
            problemas.append(f"{atual}: advance para coluna inexistente {destino}")
            break
        atual = destino
    return percurso, problemas


def _data_valida(valor):
    try:
        date.fromisoformat(valor)
    except (TypeError, ValueError):
        return False
    return True


def validar_registro_validacao(reg):
    erros = []
    for campo in CAMPOS_VALIDACAO:
        if not str(reg.get(campo, "")).strip():
            erros.append(f"{campo}: ausente ou vazio")
    if erros:
        return erros
    if reg["resultado"] not in ("sucesso", "falha"):
        erros.append("resultado: deve ser sucesso ou falha")
    if reg["exemplo"] not in PACOTES:
        erros.append("exemplo: deve ser um dos pacotes publicados")
    if not _data_valida(reg["data"]):
        erros.append("data: inválida")
    if reg["resultado"] == "falha" and reg["ponto_da_falha"].lower() == "n/a":
        erros.append("ponto_da_falha: obrigatório quando resultado é falha")
    informa_consumo = any(reg[c].lower() != "n/a" for c in ("tokens", "custo"))
    if informa_consumo:
        for campo in ("modelo", "cenario", "versao_suportada"):
            if reg[campo].lower() == "n/a":
                erros.append(f"{campo}: obrigatório quando tokens ou custo são informados")
        for campo in ("tokens", "custo"):
            if re.search(r"t[ií]pic|universal|m[eé]dio geral", reg[campo], re.IGNORECASE):
                erros.append(f"{campo}: não pode ser apresentado como valor típico ou universal")
    return erros


DECISOES = ("interesse", "recusa", "pendente")


def validar_registro_apresentacao(reg):
    erros = []
    if not str(reg.get("compreensao_observada", "")).strip():
        erros.append("compreensao_observada: ausente ou vazio")
    decisao = str(reg.get("decisao", "")).strip()
    if decisao not in DECISOES:
        erros.append("decisao: deve ser interesse, recusa ou pendente")
    if decisao == "recusa" and not str(reg.get("objecoes", "")).strip():
        erros.append("objecoes: obrigatório quando decisao é recusa")
    if decisao == "pendente":
        passo = str(reg.get("proximo_passo", "")).strip().lower()
        if "acompanhamento agendado" not in passo:
            erros.append("proximo_passo: deve indicar acompanhamento agendado quando decisao é pendente")
    elif decisao and not str(reg.get("proximo_passo", "")).strip():
        erros.append("proximo_passo: ausente ou vazio")
    return erros


def validacao_previa_existe(exemplo, data, registros):
    for reg in registros:
        if (
            reg.get("exemplo") == exemplo
            and reg.get("resultado") == "sucesso"
            and _data_valida(reg.get("data"))
            and _data_valida(data)
            and date.fromisoformat(reg["data"]) <= date.fromisoformat(data)
        ):
            return True
    return False


def validar_registro_impacto(reg):
    erros = []
    if not str(reg.get("mudanca", "")).strip():
        erros.append("mudanca: ausente ou vazio")
    afeta = str(reg.get("afeta_exemplo", "")).strip()
    if afeta not in ("sim", "nao"):
        erros.append("afeta_exemplo: deve ser sim ou nao")
    if not str(reg.get("acao", "")).strip():
        erros.append("acao: ausente ou vazio")
    if afeta == "sim":
        for campo in ("exemplos_afetados", "revalidacao"):
            if not str(reg.get(campo, "")).strip():
                erros.append(f"{campo}: obrigatório quando afeta_exemplo é sim")
    return erros


def validar_registro_reavaliacao(reg):
    erros = []
    if not str(reg.get("gatilho", "")).strip():
        erros.append("gatilho: ausente ou vazio")
    if not str(reg.get("temas", "")).strip():
        erros.append("temas: ausente ou vazio")
    if str(reg.get("heranca_de_aprovacao", "")).strip() != "nenhuma":
        erros.append("heranca_de_aprovacao: deve ser nenhuma")
    if re.search(r"aprovad|priorizad", str(reg.get("temas", "")), re.IGNORECASE):
        erros.append("temas: nenhum tema pode constar como aprovado ou priorizado")
    return erros
