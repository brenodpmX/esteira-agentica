"""CT-04 — Inventário auditável sem regra duplicada entre camadas sempre
carregadas (CA-3 / RN-04)."""

from src.core import composition


class TestInventarioSemDuplicidade:

    def test_nenhuma_regra_em_mais_de_uma_camada_sempre_carregada(self):
        dups = composition.find_duplicated_rules()
        assert dups == {}, f"regras duplicadas entre camadas sempre carregadas: {dups}"

    def test_cada_regra_sempre_carregada_tem_camada_unica(self):
        from collections import Counter
        counts = Counter(r.rule_id for r in composition.always_loaded_inventory())
        repetidas = {rid: n for rid, n in counts.items() if n > 1}
        assert not repetidas, f"regra com origem múltipla: {repetidas}"

    def test_inventario_cobre_as_quatro_responsabilidades(self):
        responsabilidades = {r.responsabilidade for r in composition.layer_inventory()}
        assert set(composition.RESPONSABILIDADES) == responsabilidades

    def test_sempre_carregadas_sao_apenas_steering(self):
        for r in composition.always_loaded_inventory():
            assert r.camada == composition.CAMADA_STEERING

    def test_manual_arroba_tem_origem_unica_no_steering(self):
        manual = [r for r in composition.layer_inventory()
                  if r.rule_id == "manual_comandos_arroba"]
        assert len(manual) == 1
        assert manual[0].camada == composition.CAMADA_STEERING
