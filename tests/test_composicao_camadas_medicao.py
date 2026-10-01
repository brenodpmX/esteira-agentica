"""Testes de medição da composição em camadas (#308).

Cobre:
  CT-01 — redução ≥40% do conteúdo estático do prompt dinâmico (CA-1)
  CT-02 — redução ≥20% do total sempre carregado (CA-2)
  CT-03 — redução real, não transferência entre camadas (RN-08)
  CT-05 — instrucoes_obrigatorias_carregadas == True (CA-4)
  CT-06 — sem instruções obrigatórias → agente NÃO é acionado (CA-5)
  CT-07 — falha sinalizada com False + motivo (CA-5)
  CT-32 — adapter sem tokens → tokens_entrada: null (CA-17)
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.core import composition
from src.core.context_generator import _build_content

from tests._composicao_helpers import (
    BASELINE, canonical_config, make_task, prompt_for, static_chars, normalize,
    FakeAdapterNoTokens, FakeAdapterWithTokens,
)


# ══════════════════════════════════════════════════════════════════════════════
# CT-01 — Estático do prompt dinâmico reduz ≥ 40%
# ══════════════════════════════════════════════════════════════════════════════

class TestReducaoEstatico:

    def test_estatico_reduz_pelo_menos_40_porcento(self, tmp_path):
        config = canonical_config()
        p1 = normalize(prompt_for(tmp_path, config, make_task(tmp_path, issue_id="308", slug="foo")), tmp_path)
        p2 = normalize(prompt_for(tmp_path, config, make_task(tmp_path, issue_id="999", slug="barbaz-other")), tmp_path)
        entregue = static_chars(p1, p2)
        base = BASELINE.prompt_dinamico_estatico_chars
        assert entregue <= 0.60 * base, (
            f"estático entregue={entregue} deveria ser <= 60% do base={base} "
            f"(ratio={entregue / base:.3f})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# CT-02 — Total sempre carregado reduz ≥ 20%
# ══════════════════════════════════════════════════════════════════════════════

class TestReducaoTotal:

    def test_total_sempre_carregado_reduz_pelo_menos_20(self, tmp_path):
        config = canonical_config()
        prompt = normalize(prompt_for(tmp_path, config, make_task(tmp_path)), tmp_path)
        steering = _build_content(config)
        entregue_total = len(prompt) + len(steering)
        base_total = BASELINE.total_sempre_carregado_chars
        assert entregue_total <= 0.80 * base_total, (
            f"total entregue={entregue_total} deveria ser <= 80% do base={base_total} "
            f"(ratio={entregue_total / base_total:.3f})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# CT-03 — Redução é real, não transferência entre camadas (RN-08)
# ══════════════════════════════════════════════════════════════════════════════

class TestReducaoNaoEhTransferencia:

    def test_aumento_de_camada_menor_que_reducao_da_outra(self, tmp_path):
        config = canonical_config()
        prompt = normalize(prompt_for(tmp_path, config, make_task(tmp_path)), tmp_path)
        steering = _build_content(config)

        prompt_base = BASELINE.prompt_dinamico_chars
        contexto_base = BASELINE.contexto_sempre_carregado_chars

        reducao_prompt = prompt_base - len(prompt)
        delta_contexto = len(steering) - contexto_base  # negativo se encolheu

        # O aumento (se houver) do contexto sempre carregado é ESTRITAMENTE menor
        # que a redução do prompt — prova de economia líquida real (RN-08).
        assert delta_contexto < reducao_prompt, (
            f"delta_contexto={delta_contexto} deveria ser < reducao_prompt={reducao_prompt}"
        )
        # Garantia extra: o total realmente caiu.
        assert len(prompt) + len(steering) < prompt_base + contexto_base


# ══════════════════════════════════════════════════════════════════════════════
# CT-05 / CT-06 / CT-07 — contrato de instruções obrigatórias (gate)
# ══════════════════════════════════════════════════════════════════════════════

def _write_steering(tmp_path: Path, content: str = "---\ninclusion: always\n---\n# ctx\n") -> Path:
    steering = tmp_path / ".kiro" / "steering" / "esteira.md"
    steering.parent.mkdir(parents=True, exist_ok=True)
    steering.write_text(content, encoding="utf-8")
    return steering


class TestInstrucoesObrigatorias:

    def test_carregadas_true(self, tmp_path):
        import src.__main__ as main
        steering = _write_steering(tmp_path)
        config = canonical_config()
        task = make_task(tmp_path)
        prompt = prompt_for(tmp_path, config, task)
        with patch("src.__main__.STEERING_FILE", steering):
            record = main.compose_execution_record(
                FakeAdapterNoTokens(), prompt, None, task["column"], task["issue"]
            )
        assert record["instrucoes_obrigatorias_carregadas"] is True

    def test_ausentes_nao_aciona(self, tmp_path, monkeypatch):
        """CT-06: sem instruções obrigatórias, call_agent NÃO despacha o agente."""
        import src.__main__ as main
        # steering inexistente
        steering = tmp_path / ".kiro" / "steering" / "esteira.md"
        config = canonical_config()
        task = make_task(tmp_path)

        dispatched = {"n": 0}

        def spy_dispatch(*a, **k):
            dispatched["n"] += 1
            return "DISPATCHED"

        monkeypatch.setattr(main, "STEERING_FILE", steering)
        monkeypatch.setattr(main, "_dispatch_with_recovery", spy_dispatch)
        monkeypatch.setattr(main, "ensure_steering_integrity", lambda c: False)
        monkeypatch.setattr(main, "build_prompt", lambda c, t: prompt_for(tmp_path, c, t))
        monkeypatch.setattr(main, "build_continuation_prompt", lambda c, t: "cont")
        monkeypatch.setattr(main, "build_remediation_prompt", lambda c, t, e: "rem")
        monkeypatch.setattr(main, "CONTEXTS_DIR", tmp_path / "contexts")

        with patch("src.__main__.KiroCliAgent", FakeAdapterNoTokens):
            result = main.call_agent(config, task)

        assert dispatched["n"] == 0, "o agente não deveria ser acionado (fail-closed)"
        assert result is None

    def test_ausentes_registra_motivo(self, tmp_path):
        """CT-07: registro contém False + motivo não-vazio."""
        import src.__main__ as main
        steering = tmp_path / ".kiro" / "steering" / "esteira.md"  # inexistente
        config = canonical_config()
        task = make_task(tmp_path)
        prompt = prompt_for(tmp_path, config, task)
        with patch("src.__main__.STEERING_FILE", steering):
            record = main.compose_execution_record(
                FakeAdapterNoTokens(), prompt, None, task["column"], task["issue"]
            )
        assert record["instrucoes_obrigatorias_carregadas"] is False
        assert record.get("motivo", "").strip() != ""


# ══════════════════════════════════════════════════════════════════════════════
# CT-32 — adapter sem tokens → tokens_entrada: null (sem falhar)
# ══════════════════════════════════════════════════════════════════════════════

class TestTokensAusentes:

    def test_adapter_sem_tokens_registra_null(self, tmp_path):
        import src.__main__ as main
        steering = _write_steering(tmp_path)
        config = canonical_config()
        task = make_task(tmp_path)
        prompt = prompt_for(tmp_path, config, task)
        with patch("src.__main__.STEERING_FILE", steering):
            record = main.compose_execution_record(
                FakeAdapterNoTokens(), prompt, None, task["column"], task["issue"]
            )
        assert record["tokens_entrada"] is None
        # Caracteres/palavras continuam preenchidos normalmente.
        assert record["prompt_dinamico"]["caracteres"] > 0
        assert record["prompt_dinamico"]["palavras"] > 0

    def test_adapter_com_tokens_preenche_int(self, tmp_path):
        import src.__main__ as main
        steering = _write_steering(tmp_path)
        config = canonical_config()
        task = make_task(tmp_path)
        prompt = prompt_for(tmp_path, config, task)
        with patch("src.__main__.STEERING_FILE", steering):
            record = main.compose_execution_record(
                FakeAdapterWithTokens(), prompt, None, task["column"], task["issue"]
            )
        assert isinstance(record["tokens_entrada"], int)
