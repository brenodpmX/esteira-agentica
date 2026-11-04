import pytest

from src.core.config import ConfigError
from src.core.sync_circuit_breaker import (
    DEFAULT_ESCALATION_AGENT, resolve_config, validate_sync_circuit_breaker,
)


def cfg(block):
    return {"sync": {"circuit_breaker": block}}


class TestDefaults:
    @pytest.mark.parametrize("config", [
        {},
        {"sync": {}},
        {"sync": {"max_attempts": 3}},
        cfg({}),
        cfg({"issue": {"max_failures": 7}}),
        cfg({"issue": {}, "platform": {}, "half_open": {}}),
        cfg({"issue": {"max_failures": 2}, "half_open": {"success_threshold": 4}}),
    ])
    def test_ct17_ausencia_aceita_e_aplica_defaults(self, config):
        validate_sync_circuit_breaker(config)
        resolved = resolve_config(config)
        assert resolved.persistence == "file"
        assert resolved.escalation_agent == DEFAULT_ESCALATION_AGENT
        assert resolved.issue_block_duration == 300
        assert resolved.issue_max_blocks == 3
        assert resolved.platform_max_blocked_issues == 5
        assert resolved.platform_block_window == 600
        assert resolved.platform_block_duration == 900

    def test_valores_default_sem_bloco(self):
        resolved = resolve_config({})
        assert resolved.issue_max_failures == 3
        assert resolved.half_open_success_threshold == 2

    def test_valores_presentes_sao_respeitados(self):
        resolved = resolve_config(cfg({
            "persistence": "memory",
            "escalation_agent": "x",
            "issue": {"max_failures": 7, "block_duration": 11, "max_blocks": 2},
            "platform": {"max_blocked_issues": 9, "block_window": 8,
                         "block_duration": 7},
            "half_open": {"success_threshold": 5},
        }))
        assert (resolved.persistence, resolved.escalation_agent) == ("memory", "x")
        assert (resolved.issue_max_failures, resolved.issue_block_duration,
                resolved.issue_max_blocks) == (7, 11, 2)
        assert (resolved.platform_max_blocked_issues, resolved.platform_block_window,
                resolved.platform_block_duration) == (9, 8, 7)
        assert resolved.half_open_success_threshold == 5


class TestInvalid:
    @pytest.mark.parametrize("block,path", [
        ({"issue": {"max_failures": 0}}, "sync.circuit_breaker.issue.max_failures"),
        ({"issue": {"max_failures": True}}, "sync.circuit_breaker.issue.max_failures"),
        ({"issue": {"block_duration": -1}}, "sync.circuit_breaker.issue.block_duration"),
        ({"issue": {"max_blocks": 0}}, "sync.circuit_breaker.issue.max_blocks"),
        ({"platform": {"max_blocked_issues": 0}},
         "sync.circuit_breaker.platform.max_blocked_issues"),
        ({"platform": {"block_window": 0}}, "sync.circuit_breaker.platform.block_window"),
        ({"platform": {"block_duration": 0}},
         "sync.circuit_breaker.platform.block_duration"),
        ({"half_open": {"success_threshold": 0}},
         "sync.circuit_breaker.half_open.success_threshold"),
        ({"persistence": "disk"}, "sync.circuit_breaker.persistence"),
        ({"issue": {"foo": 1}}, "sync.circuit_breaker.issue.foo"),
        ({"foo": 1}, "sync.circuit_breaker.foo"),
        ({"issue": 3}, "sync.circuit_breaker.issue"),
        ({"escalation_agent": ""}, "sync.circuit_breaker.escalation_agent"),
    ])
    def test_ct17b_rejeita_citando_o_caminho(self, block, path):
        with pytest.raises(ConfigError, match=path.replace(".", r"\.")):
            validate_sync_circuit_breaker(cfg(block))

    def test_bloco_nao_mapa_e_rejeitado(self):
        with pytest.raises(ConfigError, match=r"sync\.circuit_breaker"):
            validate_sync_circuit_breaker(cfg([1]))

    def test_agente_de_escalacao_precisa_existir_em_agents(self, tmp_path, monkeypatch):
        from src.core import config as config_module
        monkeypatch.setattr(config_module, "_validate_env", lambda: None)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "contexts" / "kiro-cli").mkdir(parents=True)
        (tmp_path / "contexts" / "kiro-cli" / "dev.md").write_text("persona", encoding="utf-8")

        def write(agent):
            raw = (
                "sleep: 1\n"
                f"sync:\n  circuit_breaker:\n    escalation_agent: {agent}\n"
                "project:\n  name: p\n  summary: s\n"
                "git:\n  repo:\n    main: git@github.com:u/r.git\n"
                "  flow:\n    base: main\n    feature:\n      prefix: feature/\n"
                "      branch_pattern: feature/{id}\n"
                "agents:\n  kiro-cli:\n    dev:\n      name: dev\n      model: m\n"
                "boards:\n  platform: github\n  b:\n    name: B\n    columns:\n"
                "      todo:\n        name: Todo\n"
            )
            (tmp_path / "pipe.yml").write_text(raw, encoding="utf-8")

        write("dev")
        assert config_module.check_config()["sync"]["circuit_breaker"][
            "escalation_agent"] == "dev"

        write("inexistente")
        with pytest.raises(ConfigError, match=r"sync\.circuit_breaker\.escalation_agent"):
            config_module.check_config()
