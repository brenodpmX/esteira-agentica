"""Remoção do ponteiro do manual `@---` do prompt dinâmico (#325).

Esta entrega revoga a referência sob demanda que a #308 havia reintroduzido no
prompt dinâmico. O manual completo dos comandos `@---` passa a existir
exclusivamente no steering (origem única). O prompt dinâmico NÃO contém mais a
seção "## Anotações no body (comandos `@---`)" nem qualquer ponteiro ao manual,
em nenhuma coluna com agente e independentemente da chave `allowed-commands`.

CT-01 — coluna com `allowed-commands` presente não carrega o ponteiro
CT-02 — coluna sem `allowed-commands` (default) não carrega o ponteiro
CT-03 — coluna com `allowed-commands: []` não carrega o ponteiro
CT-05 — `allowed-commands` deixa de ser reconhecida pela validação
CT-06 — `allowed-commands` declarada não produz efeito no prompt
"""

from src.core import config as config_module
from tests._composicao_helpers import canonical_config, make_task, prompt_for


_POINTER_HEADER = "## Anotações no body (comandos `@---`)"


def _assert_sem_manual(prompt: str) -> None:
    """Garante ausência total de qualquer menção ao manual `@---` no prompt."""
    assert _POINTER_HEADER not in prompt
    assert "Anotações no body" not in prompt
    assert "manual completo dos" not in prompt
    assert "comandos `@---`" not in prompt


class TestManualArrobaRemovido:
    """CA-1 / CA-5 — o prompt dinâmico nunca contém a seção/ponteiro do manual
    `@---`, em qualquer coluna com agente."""

    def test_etapa_com_allowed_commands_nao_carrega(self, tmp_path):
        # CT-01: valor que, na versão anterior (#308), abriria o gate.
        config = canonical_config()
        task = make_task(
            tmp_path,
            col_overrides={"allowed-commands": ["labels", "blocked_by", "need_human"]},
        )
        prompt = prompt_for(tmp_path, config, task)
        _assert_sem_manual(prompt)

    def test_etapa_sem_allowed_commands_nao_carrega(self, tmp_path):
        # CT-02: default (sem a chave) — antes assumia o conjunto completo.
        config = canonical_config()
        task = make_task(tmp_path)
        prompt = prompt_for(tmp_path, config, task)
        _assert_sem_manual(prompt)

    def test_etapa_allowed_commands_vazio_nao_carrega(self, tmp_path):
        # CT-03: lista vazia — já não incluía antes; segue sem incluir.
        config = canonical_config()
        task = make_task(tmp_path, col_overrides={"allowed-commands": []})
        prompt = prompt_for(tmp_path, config, task)
        _assert_sem_manual(prompt)


class TestAllowedCommandsRemovida:
    """CA-3 — `allowed-commands` não é mais reconhecida pela validação e não
    produz efeito algum sobre o prompt dinâmico."""

    def test_chave_nao_reconhecida(self):
        # CT-05: validação não levanta o erro específico de forma antigo e não
        # trata `allowed-commands` como chave especial.
        config = canonical_config()
        config["boards"]["entrega"]["columns"]["desenvolvimento"][
            "allowed-commands"
        ] = ["labels"]
        # O schema de colunas aceita chaves desconhecidas: validar não deve
        # levantar nenhum erro relativo a `allowed-commands`.
        config_module._validate_boards(config["boards"], known_agents={"dev"})
        # Garante que a função de validação específica antiga sumiu do schema.
        assert not hasattr(config_module, "_validate_allowed_commands")

    def test_chave_sem_efeito_no_prompt(self, tmp_path):
        # CT-06: duas colunas idênticas exceto por `allowed-commands` produzem
        # prompts idênticos — a chave não produz diferença observável.
        config = canonical_config()
        sem = make_task(tmp_path, slug="zzaaa")
        com = make_task(
            tmp_path, slug="zzbbb",
            col_overrides={"allowed-commands": ["blocked_by", "need_human"]},
        )
        prompt_sem = prompt_for(tmp_path, config, sem)
        prompt_com = prompt_for(tmp_path, config, com)
        # Normaliza o slug (único token que legitimamente difere) para comparar
        # o restante do prompt.
        assert prompt_sem.replace("zzaaa", "SLUG") == prompt_com.replace("zzbbb", "SLUG")
        _assert_sem_manual(prompt_sem)
        _assert_sem_manual(prompt_com)
