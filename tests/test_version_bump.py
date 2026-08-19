"""Testes de verificação do bump de versão — US-02 (preflight) + evolução.

Confirma que:
1. src/core/version.py contém VERSION semântica válida (>= 1.6.0 baseline US-02).
2. A versão segue o padrão semântico MAJOR.MINOR.PATCH.
3. O CONTEXT.md contém documentação de changelog da US-02 (preflight).
4. A versão é exibida no log de inicialização via __main__.

Histórico:
  - Bump original #36: 1.5.0 → 1.6.0 pela adição do preflight (US-02).
  - Evolução posterior: 1.6.0 → 1.7.0 → 1.8.0 → 1.8.1 → 1.8.2 → 1.8.3.
  - Atualizado em #165 para usar baseline >= 1.6.0 em vez de versão exata fixa.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION_FILE = ROOT / "src" / "core" / "version.py"
CONTEXT_FILE = ROOT / "CONTEXT.md"


# ─── Verificação de src/core/version.py ──────────────────────────────────────

class TestVersionFile:
    """Garante que src/core/version.py contém a versão correta após o bump."""

    def test_version_file_exists(self):
        """O arquivo src/core/version.py deve existir."""
        assert VERSION_FILE.exists(), (
            f"Arquivo de versão não encontrado: {VERSION_FILE}"
        )

    def test_version_importable(self):
        """VERSION deve ser importável de src.core.version."""
        from src.core.version import VERSION  # noqa: F401

    def test_version_is_string(self):
        """VERSION deve ser uma string."""
        from src.core.version import VERSION
        assert isinstance(VERSION, str), (
            f"VERSION deve ser str, mas é {type(VERSION).__name__}"
        )

    def test_version_semantic_format(self):
        """VERSION deve seguir o formato semântico MAJOR.MINOR.PATCH."""
        import re
        from src.core.version import VERSION
        pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(pattern, VERSION), (
            f"VERSION '{VERSION}' não segue o formato semântico MAJOR.MINOR.PATCH"
        )

    def test_version_is_target(self):
        """VERSION deve ser semântica válida >= 1.6.0 (baseline US-02 preflight)."""
        from src.core.version import VERSION
        parts = VERSION.split(".")
        assert len(parts) == 3, f"VERSION deve ser MAJOR.MINOR.PATCH, mas é '{VERSION}'"
        major, minor, _patch = int(parts[0]), int(parts[1]), int(parts[2])
        assert major >= 1, f"MAJOR deve ser >= 1. Atual: {major}"
        assert minor >= 6, f"MINOR deve ser >= 6 (baseline US-02). Atual: {minor}"

    def test_version_minor_incremented(self):
        """MINOR deve ser >= 6 (baseline após US-02 preflight)."""
        from src.core.version import VERSION
        parts = VERSION.split(".")
        assert len(parts) == 3, f"Formato inválido: '{VERSION}'"
        major, minor, _patch = int(parts[0]), int(parts[1]), int(parts[2])
        assert major == 1, f"MAJOR deve ser 1. Atual: {major}"
        assert minor >= 6, (
            f"MINOR deve ser >= 6 (bump de 5 pela adição do preflight em US-02). Atual: {minor}"
        )

    def test_version_patch_valid(self):
        """PATCH deve ser um inteiro não-negativo."""
        from src.core.version import VERSION
        parts = VERSION.split(".")
        assert len(parts) == 3, f"Formato inválido: '{VERSION}'"
        patch = int(parts[2])
        assert patch >= 0, (
            f"PATCH deve ser >= 0. Atual: {patch}"
        )


# ─── Verificação de CONTEXT.md ────────────────────────────────────────────────

class TestContextMD:
    """Confirma que CONTEXT.md contém a seção de changelog da v1.6.0."""

    def test_context_md_exists(self):
        """O arquivo CONTEXT.md deve existir."""
        assert CONTEXT_FILE.exists(), (
            f"CONTEXT.md não encontrado: {CONTEXT_FILE}"
        )

    def test_context_contains_v160_section(self):
        """CONTEXT.md deve conter seção de changelog para v1.6.0 — US-02."""
        content = CONTEXT_FILE.read_text(encoding="utf-8")
        assert "1.6.0" in content, (
            "CONTEXT.md deve mencionar v1.6.0 (seção de changelog da US-02 / preflight)"
        )

    def test_context_contains_preflight_section(self):
        """CONTEXT.md deve conter seção descrevendo o preflight de credenciais."""
        content = CONTEXT_FILE.read_text(encoding="utf-8")
        assert "Preflight de Credenciais" in content or "preflight" in content.lower(), (
            "CONTEXT.md deve conter seção sobre Preflight de Credenciais (US-02)"
        )

    def test_context_contains_us02_reference(self):
        """CONTEXT.md deve fazer referência à US-02."""
        content = CONTEXT_FILE.read_text(encoding="utf-8")
        assert "US-02" in content, (
            "CONTEXT.md deve referenciar US-02 na seção do preflight"
        )


# ─── Verificação de integração: versão no log de boot ────────────────────────

class TestVersionInBootLog:
    """Verifica que a versão importada pelo __main__ é a 1.6.0."""

    def test_main_imports_version(self):
        """src/__main__.py deve importar VERSION de src.core.version."""
        main_source = (ROOT / "src" / "__main__.py").read_text(encoding="utf-8")
        assert "from src.core.version import VERSION" in main_source, (
            "__main__.py deve importar VERSION de src.core.version"
        )

    def test_main_version_is_160(self):
        """VERSION importado por __main__ deve ser >= 1.6.0 (baseline US-02)."""
        import importlib
        import src.core.version as version_mod
        importlib.reload(version_mod)
        parts = version_mod.VERSION.split(".")
        assert len(parts) == 3, f"Formato inválido: '{version_mod.VERSION}'"
        major, minor, _patch = int(parts[0]), int(parts[1]), int(parts[2])
        assert major >= 1 and minor >= 6, (
            f"__main__ usará VERSION >= 1.6.0 (baseline US-02). Atual: '{version_mod.VERSION}'"
        )

    def test_version_log_message_format(self):
        """A mensagem de log de boot deve incluir a versão formatada."""
        main_source = (ROOT / "src" / "__main__.py").read_text(encoding="utf-8")
        assert "VERSION" in main_source, (
            "__main__.py deve usar VERSION na mensagem de inicialização"
        )
        # Verifica que o log exibe a versão no formato v{VERSION} (f-string)
        assert "v{VERSION}" in main_source, (
            "A mensagem de boot deve exibir a versão no formato v{VERSION}"
        )
