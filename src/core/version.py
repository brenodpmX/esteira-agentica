import os
import subprocess
from pathlib import Path

VERSION = "1.9.1"

# Arquivo texto simples com o sha do commit, gravado pelo processo de build
# (ADR-003: "o build grava o hash em arquivo somente leitura"). A geração deste
# arquivo é responsabilidade da frente de infraestrutura de imagem — esta
# camada apenas o lê se existir.
BUILD_COMMIT_FILE = Path("/app/.build-commit")


def resolve_commit() -> str | None:
    """Resolve o commit em execução: checkout git > arquivo de build > None.

    Ordem de resolução:
    1. `git rev-parse HEAD` no diretório de trabalho atual (funciona em
       checkout local com `.git` presente).
    2. Conteúdo de BUILD_COMMIT_FILE, se existir (imagem Docker sem `.git`
       - ver ADR-003, "Riscos": "checkout sem `.git` não fornece commit
       [...] o build grava o hash em arquivo somente leitura").
    3. None se nenhuma das duas fontes produzir um valor - NUNCA infira
       sucesso; o chamador deve tratar None como evidência incompleta.

    Falhas do subprocess git (não é repo, git não instalado, timeout) são
    capturadas e tratadas como "fonte 1 indisponível", sem levantar
    exceção - a função sempre retorna str ou None.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            if commit:
                return commit
    except Exception:
        # subprocess.TimeoutExpired, FileNotFoundError, etc. — fonte 1
        # indisponível; cai para a fonte 2.
        pass

    if BUILD_COMMIT_FILE.exists():
        content = BUILD_COMMIT_FILE.read_text().strip()
        if content:
            return content

    return None


def resolve_environment() -> str | None:
    """Lê PIPE_ENVIRONMENT do processo. None se ausente/vazia.

    ADR-003: "PIPE_ENVIRONMENT é obrigatório no runtime de produção".
    Esta função não decide obrigatoriedade - apenas lê e normaliza vazio
    para None; quem decide se a ausência bloqueia a evidência é o
    chamador (rollout_evidence em __main__.py).
    """
    value = os.environ.get("PIPE_ENVIRONMENT", "").strip()
    return value or None
