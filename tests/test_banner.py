"""Regressão: o banner da esteira (locomotiva ASCII) não deve ser substituído.

Contexto (perda no merge `c27f813`): o banner é uma escolha deliberada de
identidade visual da esteira, ajustada manualmente em `7ed7bf0` e `45c8b14`. O
merge de `epic` em `main` resolveu o conflito de `src/__main__.py` adotando o
lado `epic`, que trazia um banner genérico de texto — descartando a locomotiva.

Foi justamente essa troca visível que revelou o incidente: as perdas silenciosas
(`rerun_cooldown`, descoberta local global, `create-up` de slug em underscore)
não davam sinal nenhum na saída do programa.

Este teste trava os elementos que caracterizam a locomotiva. Não compara o
banner inteiro caractere a caractere de propósito: ajustes finos de espaçamento
são legítimos, trocar o desenho por outro não é.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.__main__ import _BANNER


class TestBannerLocomotiva:
    """O banner deve ser a locomotiva ASCII, não um wordmark genérico."""

    def test_banner_nao_e_vazio(self):
        assert _BANNER.strip(), "o banner não pode ser vazio"

    def test_tem_a_cabine_da_locomotiva(self):
        """`TS__[O]` é a cabine — marca inconfundível do desenho."""
        assert "TS__[O]" in _BANNER, (
            "cabine da locomotiva ausente: o banner foi substituído"
        )

    def test_tem_a_fumaca(self):
        """`o O O` é a fumaça saindo da chaminé."""
        assert "o O O" in _BANNER, "fumaça da locomotiva ausente"

    def test_tem_os_vagoes(self):
        """Os vagões são formados pela cerca `|_|*****|_|`."""
        assert "|_|*****|_|" in _BANNER, "vagões da locomotiva ausentes"

    def test_tem_os_trilhos_e_rodas(self):
        """A base `./o--000` são as rodas dianteiras sobre os trilhos."""
        assert "./o--000" in _BANNER, "rodas/trilhos da locomotiva ausentes"

    def test_tem_altura_de_locomotiva(self):
        """O desenho ocupa 6 linhas; um wordmark de texto ocupa ~5."""
        linhas = [l for l in _BANNER.split("\n") if l.strip()]
        assert len(linhas) == 6, (
            f"esperadas 6 linhas de desenho, encontradas {len(linhas)} — "
            "provável substituição do banner"
        )

    def test_nao_e_o_wordmark_generico_do_epic(self):
        """Regressão direta: o banner de texto puro que o merge introduziu.

        O lado `epic` renderizava 'ESTEIRA' em figlet padrão, cuja assinatura é
        a sequência `|_____|____/` na última linha.
        """
        assert "|_____|____/" not in _BANNER, (
            "o banner voltou ao wordmark genérico introduzido pelo merge c27f813"
        )

    def test_banner_e_impresso_no_startup(self):
        """O banner precisa chegar ao terminal — senão a regressão passa muda."""
        fonte = (ROOT / "src" / "__main__.py").read_text(encoding="utf-8")
        assert "print(_BANNER)" in fonte, (
            "main() deve imprimir o banner no arranque"
        )

    def test_banner_e_raw_string(self):
        """O desenho usa `\\` e backticks; sem raw string vira escape acidental."""
        fonte = (ROOT / "src" / "__main__.py").read_text(encoding="utf-8")
        assert '_BANNER = r"""' in fonte, (
            "o banner deve ser declarado como raw string (r\"\"\")"
        )
