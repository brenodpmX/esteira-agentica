"""Gate de referência sob demanda do manual `@---` (CA-8).

CT-15 — etapa SEM comando de anotação não carrega o manual
CT-16 — etapa COM comando de anotação disponibiliza o manual
CT-17 — a inclusão é derivada determinística dos comandos permitidos
"""

from src.core import composition
from tests._composicao_helpers import canonical_config, make_task, prompt_for


_POINTER_HEADER = "## Anotações no body (comandos `@---`)"


class TestManualArroba:

    def test_etapa_sem_comando_nao_carrega(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, col_overrides={"allowed-commands": []})
        prompt = prompt_for(tmp_path, config, task)
        assert _POINTER_HEADER not in prompt
        refs = composition.on_demand_references(task["column"])
        assert composition.REF_MANUAL_ARROBA not in refs

    def test_etapa_com_comando_carrega(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, col_overrides={"allowed-commands": ["labels"]})
        prompt = prompt_for(tmp_path, config, task)
        assert _POINTER_HEADER in prompt
        refs = composition.on_demand_references(task["column"])
        assert composition.REF_MANUAL_ARROBA in refs

    def test_etapa_default_carrega_sob_demanda(self, tmp_path):
        # Sem a chave allowed-commands, assume o conjunto completo → manual entra.
        config = canonical_config()
        task = make_task(tmp_path)
        prompt = prompt_for(tmp_path, config, task)
        assert _POINTER_HEADER in prompt


class TestGateDerivado:

    def test_inclusao_e_funcao_dos_comandos_permitidos(self):
        com = composition.on_demand_references({"allowed-commands": ["archive"]})
        sem = composition.on_demand_references({"allowed-commands": []})
        assert composition.REF_MANUAL_ARROBA in com
        assert composition.REF_MANUAL_ARROBA not in sem

    def test_subconjunto_sem_anotacao_nao_inclui(self):
        # Um comando desconhecido/não-anotação não abre o gate.
        refs = composition.on_demand_references({"allowed-commands": ["foo-bar"]})
        assert composition.REF_MANUAL_ARROBA not in refs

    def test_determinismo(self):
        col = {"allowed-commands": ["blocked_by"]}
        assert composition.on_demand_references(col) == composition.on_demand_references(col)
