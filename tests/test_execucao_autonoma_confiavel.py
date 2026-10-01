"""Casos de teste — Execução autônoma confiável (issue #303).

Implementado pelo desenvolvimento a partir do esqueleto test-first especificado
pela QA, já reconciliado com o escopo fechado no revisar-escopo (2026-10-01).
Cada teste está vinculado a um critério de aceitação (CA) via o caso CT-NN
documentado em `doc/quality/execucao-autonoma-confiavel/test-cases.md`.

Decisões de escopo incorporadas:

- Grupo A: a classificação de sucesso/falha considera APENAS canais estruturados
  (exit-code != 0, [TIMEOUT], [ERRO], saída de erro estruturada). A narrativa
  (texto livre) NUNCA classifica. Ausência de sinal estruturado = SUCESSO. A
  suíte congelada que codificava o falso positivo (narrativa => falha) foi
  reescrita nesta entrega — #303 prevalece (ver CT-05b: reescrita em
  tests/test_agent_failure_detection.py).
- Grupo D: recuperação alinhada à ADR retry-kiro-cli SEM a fronteira idempotente
  da seção 4 (fora de escopo). UNKNOWN_OUTCOME é fail-closed (uma única
  invocação, sem retry inline, preserva evidências); retry inline com backoff
  SOMENTE para DEFINITE_NOT_STARTED (não-inicialização comprovada).
"""

import re
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.kiro_cli_agent import KiroCliAgent


@pytest.fixture
def adapter():
    return KiroCliAgent()


# ══════════════════════════════════════════════════════════════════════════
# Grupo A — Detecção de falha por canais estruturados
# Alvo: KiroCliAgent._detect_failure. Regra: só canais estruturados classificam
# (exit-code != 0, [TIMEOUT], [ERRO], saída de erro estruturada). A narrativa
# (texto livre) do agente NUNCA classifica. Ausência de sinal = SUCESSO.
# ══════════════════════════════════════════════════════════════════════════

class TestDeteccaoFalhaCanaisEstruturados:

    def test_ct01_narrativa_cita_erro_sem_sinal_estruturado_e_sucesso(self, adapter):
        """CT-01: narrativa cita frase(s) de erro conhecida(s) mas NÃO há sinal
        estruturado (sem [exit-code: N!=0], sem [TIMEOUT], sem [ERRO]) →
        _detect_failure retorna None (sucesso).

        É o coração da correção: antes 'Kiro is having trouble responding'
        constava em _FAILURE_MARKERS e disparava falso positivo mesmo citado
        pela narrativa. A classificação passou a ser só por canais estruturados.
        """
        output = (
            "Analisei a issue e implementei o tratamento para quando o modelo "
            "responde 'Kiro is having trouble responding right now'.\n"
            "Também cobri 'InternalServerError' e mensagens 'error:' do servidor.\n"
            "Pronto. 2 arquivos alterados.\n"
        )
        assert adapter._detect_failure(output) is None

    def test_ct02_exit_code_nao_zero_e_falha_com_causa_estruturada(self, adapter):
        """CT-02: exit-code != 0 → falha, com causa extraída do canal
        estruturado (não da narrativa), em uma única linha."""
        output = (
            "trabalhando normalmente\n"
            "error: comando git retornou status não-zero\n"
            "[exit-code: 2]\n"
        )
        error = adapter._detect_failure(output)
        assert error is not None
        assert "\n" not in error

    def test_ct02b_exit_code_zero_nao_e_falha(self, adapter):
        """CT-02 (complemento): [exit-code: 0] NÃO é falha — só N != 0 classifica."""
        output = "trabalho concluído\n[exit-code: 0]\n"
        assert adapter._detect_failure(output) is None

    def test_ct03_marcador_timeout_e_falha(self, adapter):
        """CT-03: marcador de timeout → falha."""
        output = "iniciando tarefa\n[TIMEOUT] Agente excedeu 3600s\n"
        assert adapter._detect_failure(output) is not None

    def test_ct04_erro_transporte_estruturado_e_falha(self, adapter):
        """CT-04: erro de transporte reportado em canal estruturado → falha,
        com a causa real extraída do canal.

        Diferente do CT-01: aqui o sinal é ESTRUTURADO (marcador [ERRO] / seção
        de erro de dispatch), não texto livre do agente.
        """
        output = (
            "iniciando\n"
            "[ERRO] dispatch failure: stream da resposta interrompido\n"
        )
        error = adapter._detect_failure(output)
        assert error is not None
        assert "dispatch failure" in error or "ERRO" in error

    def test_ct04b_output_vazio_ou_normal_sem_marcador_e_sucesso(self, adapter):
        """CT-04b: output vazio ou normal, SEM qualquer marcador estruturado →
        sucesso. A ausência de sinal estruturado NUNCA é falha.
        """
        assert adapter._detect_failure("") is None
        assert adapter._detect_failure("  \n \n") is None
        assert adapter._detect_failure("Pronto. 3 arquivos alterados.\n") is None

    def test_ct05_regressao_falso_positivo_narrativa_nao_recorre(self, adapter):
        """CT-05 (regressão): reproduz o falso positivo histórico — execução
        bem-sucedida cuja narrativa contém o termo de erro, SEM sinal estruturado
        — e comprova que NÃO recorre.
        """
        output = (
            "Resumo do que fiz: tratei o caso em que a API devolve "
            "'Kiro is having trouble responding right now' e 'temporarily "
            "unavailable'. Nenhum erro ocorreu nesta execução.\n"
            "Concluído em 12s.\n"
        )
        assert adapter._detect_failure(output) is None

    # CT-05b (precedência de contrato) é executado na suíte congelada
    # tests/test_agent_failure_detection.py: os testes que codificavam o falso
    # positivo (narrativa => falha) foram reescritos para classificação por
    # canal estruturado, e os testes de sucesso foram preservados.


# ══════════════════════════════════════════════════════════════════════════
# Grupo B — Resolução dos caminhos de apoio
# Fonte válida de templates: contexts/templates/ (ex.: docs/test-cases.md).
# Resolução por item (isolar ausência) — NÃO cancelar o lote.
# ══════════════════════════════════════════════════════════════════════════

class TestCaminhosDeApoio:

    def test_ct07_caminho_inexistente_nao_cancela_lote(self, tmp_path):
        """CT-07: um lote com caminhos de apoio válidos + um inexistente. Os
        válidos resolvem; o ausente é sinalizado ISOLADAMENTE (por item), sem
        exceção que cancele o lote inteiro.
        """
        from src.core.support_paths import resolve_support_paths

        valido = tmp_path / "contexts" / "templates" / "docs" / "test-cases.md"
        valido.parent.mkdir(parents=True)
        valido.write_text("# template\n", encoding="utf-8")
        ausente = tmp_path / "contexts" / "templates" / "issues" / "nao-existe.md"

        resultado = resolve_support_paths([valido, ausente])
        assert resultado.resolvidos == [valido]
        assert resultado.ausentes == [ausente]
        assert resultado.cancelou_lote is False

    def test_ct08_config_e_codigo_apontam_para_mesma_fonte_valida(self, tmp_path):
        """CT-08: os caminhos de apoio referenciados pela CONFIGURAÇÃO e os
        gerados por CÓDIGO apontam para o mesmo diretório-fonte válido
        (contexts/templates/…) e todos existem no ambiente.
        """
        from src.core.support_paths import (
            support_paths_from_code, support_paths_from_config,
        )

        # Ambiente com a fonte única presente (contexts/templates/docs/...).
        templates = tmp_path / "contexts" / "templates"
        doc = templates / "docs" / "test-cases.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# template\n", encoding="utf-8")

        config = {"boards": {"platform": "github"}}
        fonte_codigo = support_paths_from_code(templates)
        fonte_config = support_paths_from_config(config, templates)

        assert fonte_codigo == fonte_config
        assert fonte_codigo  # não vazio
        assert all(p.exists() for p in fonte_codigo)

    def test_ct08_fonte_unica_do_repo_existe(self):
        """CT-08 (complemento): a fonte única canônica do repo
        (contexts/templates/) existe e aponta para o mesmo lugar em código e
        config, sem argumento de override.
        """
        from src.core.support_paths import (
            TEMPLATES_DIR, support_paths_from_code, support_paths_from_config,
        )
        assert TEMPLATES_DIR == Path("contexts") / "templates"
        codigo = support_paths_from_code()
        config = support_paths_from_config({})
        assert codigo == config


# ══════════════════════════════════════════════════════════════════════════
# Grupo C — Contexto derivado da configuração vigente
# Alvo: src/core/context_generator.py + call_agent (ensure_steering_integrity).
# ══════════════════════════════════════════════════════════════════════════

class TestContextoDerivadoDaConfig:

    def _config(self):
        return {
            "project": {"name": "Esteira", "summary": "resumo"},
            "git": {
                "repo": {"main": "x"},
                "flow": {
                    "base": "main",
                    "feature": {"prefix": "feature",
                                "branch_pattern": "feature/{id}-{slug}",
                                "create": "main", "merge": "main"},
                },
            },
            "boards": {
                "platform": "github",
                "entrega": {
                    "name": "Entrega", "flow": "feature",
                    "columns": {
                        "casos-de-teste": {"name": "Casos de Teste",
                                           "agent": "quality"},
                        "desenvolvimento": {"name": "Desenvolvimento",
                                            "agent": "engineering-pl"},
                    },
                },
            },
        }

    def test_ct09_contexto_contem_tabelas_preenchidas(self):
        """CT-09: o contexto gerado a partir da config vigente contém a tabela
        de boards/colunas com linhas de dados reais e a tabela de flow/branches
        preenchida (prefixo/origem/merge/base) — não apenas cabeçalhos vazios.
        """
        from src.core import context_generator as cg
        content = cg._build_content(self._config())
        assert "| `casos-de-teste` | Casos de Teste | quality |" in content
        assert "| `desenvolvimento` | Desenvolvimento | engineering-pl |" in content
        assert "| `feature` | `feature` | `main` | `main` |" in content
        assert "Branch base: `main`" in content

    def test_ct09_sem_aviso_de_conflito_no_caminho_feliz(self, tmp_path, monkeypatch):
        """CT-09: quando o steering já reflete a config vigente,
        ensure_steering_integrity NÃO acusa divergência (retorna False).
        """
        from src.core import context_generator as cg
        steering = tmp_path / ".kiro" / "steering" / "esteira.md"
        monkeypatch.setattr(cg, "STEERING_FILE", steering)
        cg.ensure_steering_integrity(self._config())      # cria
        diverged = cg.ensure_steering_integrity(self._config())  # já íntegro
        assert diverged is False

    def test_ct09b_artefato_congelado_vazio_nao_tem_precedencia(self, tmp_path, monkeypatch):
        """CT-09b: um artefato congelado com tabelas vazias NÃO tem precedência:
        ensure_steering_integrity sobrescreve pelo conteúdo derivado da config
        vigente (tabelas preenchidas) e retorna True (divergiu).
        """
        from src.core import context_generator as cg
        steering = tmp_path / ".kiro" / "steering" / "esteira.md"
        steering.parent.mkdir(parents=True)
        steering.write_text(
            "---\ninclusion: always\n---\n\n## Boards e colunas\n\n"
            "| Coluna (id) | Nome | Agente |\n|---|---|---|\n", encoding="utf-8")
        monkeypatch.setattr(cg, "STEERING_FILE", steering)

        diverged = cg.ensure_steering_integrity(self._config())
        assert diverged is True
        content = steering.read_text(encoding="utf-8")
        assert "| `casos-de-teste` | Casos de Teste | quality |" in content

    def test_ct09b_pipe_context_legado_nao_sombreia_steering(self, tmp_path, monkeypatch):
        """CT-09b (2ª camada): se existir um .kiro/agents/pipe_context.json
        legado com tabelas vazias, ele NÃO pode sombrear o steering vigente. O
        desenvolvimento garante que o contexto efetivo é sempre o derivado da
        config (remoção do artefato legado).
        """
        from src.core import context_generator as cg
        steering = tmp_path / ".kiro" / "steering" / "esteira.md"
        legacy = tmp_path / ".kiro" / "agents" / "pipe_context.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text('{"tables": "vazias"}', encoding="utf-8")
        monkeypatch.setattr(cg, "STEERING_FILE", steering)

        cg.ensure_steering_integrity(self._config())

        # Artefato legado removido: não sombreia o steering vigente.
        assert not legacy.exists()
        # Contexto efetivo é o derivado da config (tabelas preenchidas).
        content = steering.read_text(encoding="utf-8")
        assert "| `casos-de-teste` | Casos de Teste | quality |" in content


# ══════════════════════════════════════════════════════════════════════════
# Grupo D — Tratamento seguro de interrupção transitória (ADR #217)
# SEM a fronteira idempotente da seção 4 (fora de escopo).
# - UNKNOWN_OUTCOME: fail-closed (1 invocação, sem retry inline, preserva
#   output/request ID/causa/session_id; reconciliação pelo loop normal).
# - DEFINITE_NOT_STARTED: retry inline com backoff e limite.
# Observabilidade exigida: causa real + origem (canal). time.sleep SEMPRE mockado.
# ══════════════════════════════════════════════════════════════════════════

def _d_config(max_tentativas=3):
    """Config mínima com um agente resolvível e retry.* explícito."""
    return {
        "retry": {"max_tentativas": max_tentativas,
                  "backoff_inicial_seg": 30, "backoff_fator": 2.0},
        "git": {"repo": {"main": "git@github.com:u/r.git"},
                "flow": {"base": "main",
                         "feature": {"prefix": "feature",
                                     "branch_pattern": "feature/{id}-{slug}",
                                     "create": "main", "merge": "main"}}},
        "boards": {"platform": "github",
                   "entrega": {"name": "Entrega", "flow": "feature",
                               "columns": {"desenvolvimento": {
                                   "name": "Desenvolvimento", "agent": "dev",
                                   "gitevents": "no-branch",
                                   "change": {"advance": "execucao-testes"}}}}},
        "agents": {"kiro-cli": {"dev": {"name": "Dev", "model": "auto"}}},
    }


def _d_task(tmp_path):
    body = tmp_path / "303-x-body.md"
    body.write_text("# Uma tarefa\nconteúdo\n", encoding="utf-8")
    issue = {"id": "303", "column": "desenvolvimento", "status": "ok",
             "labels": [], "body_path": str(body)}
    board_cfg = _d_config()["boards"]["entrega"]
    return {"board_id": "entrega", "issue": issue,
            "column": board_cfg["columns"]["desenvolvimento"],
            "col_id": "desenvolvimento", "board": board_cfg}


class _FakeAdapter:
    """Adapter fake: registra cada invocação e devolve resultados pré-definidos.

    NÃO faz monkeypatch do próprio método sob teste (lição do incidente #106):
    é um dublê independente que o teste injeta no lugar de KiroCliAgent.
    """

    def __init__(self, resultados):
        # resultados: lista de ExecutionResult a devolver em ordem; o último
        # se repete se houver mais invocações que resultados.
        self._resultados = list(resultados)
        self.invocacoes = 0

    def execute(self, params):
        self.invocacoes += 1
        idx = min(self.invocacoes - 1, len(self._resultados) - 1)
        return self._resultados[idx]


def _run_call_agent(monkeypatch, tmp_path, config, resultados):
    """Dispara call_agent com um _FakeAdapter e time.sleep/guards mockados.

    Retorna (resultado, fake_adapter, sleeps, registros_log).
    """
    import src.__main__ as mod
    from src.core import context_generator as cg

    fake = _FakeAdapter(resultados)
    sleeps = []
    registros = []

    monkeypatch.setattr(mod, "KiroCliAgent", lambda: fake)
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(cg, "ensure_steering_integrity", lambda c: False)
    # Guards: no-op (isolam a lógica de recuperação; já cobertos por outra suíte).
    monkeypatch.setattr(mod, "SnapshotGuard", lambda *a, **k: _nullcm())
    import src.core.agent_guard as ag
    monkeypatch.setattr(ag, "AgentGuard", lambda *a, **k: _nullcm())
    for level in ("info", "warning", "error"):
        monkeypatch.setattr(
            mod.log, level,
            (lambda lvl: (lambda *a, **k: registros.append((lvl, a, k))))(level))

    resultado = mod.call_agent(config, _d_task(tmp_path))
    return resultado, fake, sleeps, registros


class _nullcm:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _result(classe, **kw):
    from src.core.execution import ExecutionResult
    return ExecutionResult(classe=classe, **kw)


class TestRecuperacaoInterrupcao:

    def test_ct10_unknown_outcome_fail_closed_uma_invocacao_preserva(self, monkeypatch, tmp_path):
        """CT-10: aborto transitório ambíguo → UNKNOWN_OUTCOME. Uma única
        invocação, sem backoff, resultado ambíguo, evidências preservadas.
        """
        from src.core.execution import UNKNOWN_OUTCOME
        res = _result(UNKNOWN_OUTCOME,
                      output="output parcial\n[ERRO] dispatch failure\n",
                      causa="dispatch failure: stream interrompido",
                      origem="dispatch failure", session_id="sess-abc",
                      request_id="req-123")
        resultado, fake, sleeps, _ = _run_call_agent(
            monkeypatch, tmp_path, _d_config(), [res])

        assert fake.invocacoes == 1
        assert sleeps == []                       # nenhum backoff
        assert resultado.classe == UNKNOWN_OUTCOME
        assert resultado.output and resultado.causa and resultado.session_id
        assert resultado.request_id == "req-123"

    def test_ct11_definite_not_started_retoma_ate_sucesso(self, monkeypatch, tmp_path):
        """CT-11 (sub-caso A): DEFINITE_NOT_STARTED 1x, depois sucesso → reexecuta
        com backoff e conclui em sucesso; 1ª espera = backoff_inicial_seg (30)."""
        from src.core.execution import DEFINITE_NOT_STARTED, SUCEDIDO
        resultados = [
            _result(DEFINITE_NOT_STARTED, causa="kiro-cli ausente", origem="erro interno"),
            _result(SUCEDIDO, output="pronto\n"),
        ]
        resultado, fake, sleeps, _ = _run_call_agent(
            monkeypatch, tmp_path, _d_config(max_tentativas=3), resultados)

        assert fake.invocacoes == 2
        assert sleeps == [30]
        assert resultado.classe == SUCEDIDO

    def test_ct11_definite_not_started_esgota_limite(self, monkeypatch, tmp_path):
        """CT-11 (sub-caso B): DEFINITE_NOT_STARTED sempre → exatamente
        max_tentativas invocações; backoff [30, 60] para max=3; resultado =
        falha persistente; log com total de tentativas e última causa.
        """
        from src.core.execution import DEFINITE_NOT_STARTED, FALHA_PERSISTENTE
        res = _result(DEFINITE_NOT_STARTED,
                      causa="[ERRO] kiro-cli não encontrado no PATH",
                      origem="erro interno")
        resultado, fake, sleeps, registros = _run_call_agent(
            monkeypatch, tmp_path, _d_config(max_tentativas=3), [res])

        assert fake.invocacoes == 3                 # sem laço infinito
        assert sleeps == [30, 60]                   # backoff_inicial=30, fator=2.0
        assert resultado.classe == FALHA_PERSISTENTE
        # Log registra total de tentativas + última causa.
        texto = " ".join(str(a) + str(k) for _, a, k in registros)
        assert "3" in texto
        assert "kiro-cli não encontrado no PATH" in texto

    def test_ct12_unknown_outcome_nao_dispara_retry_nem_backoff(self, monkeypatch, tmp_path):
        """CT-12: UNKNOWN_OUTCOME → NÃO há retry inline nem backoff, mesmo com
        max_tentativas > 1 (retry inline é exclusivo de DEFINITE_NOT_STARTED).
        """
        from src.core.execution import UNKNOWN_OUTCOME
        res = _result(UNKNOWN_OUTCOME, output="parcial\n", causa="InternalServerError",
                      origem="dispatch failure", session_id="s1")
        resultado, fake, sleeps, _ = _run_call_agent(
            monkeypatch, tmp_path, _d_config(max_tentativas=5), [res])

        assert fake.invocacoes == 1
        assert sleeps == []
        assert resultado.classe == UNKNOWN_OUTCOME

    def test_ct13_log_registra_causa_e_origem_do_canal(self, monkeypatch, tmp_path):
        """CT-13: observabilidade — falha por canal, UNKNOWN_OUTCOME e retry
        DEFINITE_NOT_STARTED registram causa real + origem (canal estruturado);
        UNKNOWN_OUTCOME é acionável e distinto de sucesso/falha definitiva; a
        narrativa nunca é a origem.
        """
        from src.core.execution import (UNKNOWN_OUTCOME, FALHA, DEFINITE_NOT_STARTED)

        # (a) falha definitiva por canal estruturado
        falha = _result(FALHA, output="x\n[exit-code: 2]\n",
                        causa="error: git falhou | [exit-code: 2]", origem="exit-code")
        _, _, _, reg_falha = _run_call_agent(monkeypatch, tmp_path, _d_config(), [falha])
        texto_falha = " ".join(f"{a} {k}" for _, a, k in reg_falha)
        assert "exit-code" in texto_falha and "git falhou" in texto_falha

        # (b) UNKNOWN_OUTCOME acionável, distinto de falha definitiva
        unk = _result(UNKNOWN_OUTCOME, output="parcial\n", causa="dispatch failure",
                      origem="dispatch failure", session_id="s", request_id="r")
        _, _, _, reg_unk = _run_call_agent(monkeypatch, tmp_path, _d_config(), [unk])
        texto_unk = " ".join(f"{a} {k}" for _, a, k in reg_unk)
        assert "UNKNOWN_OUTCOME" in texto_unk
        assert "dispatch failure" in texto_unk

        # (c) retry DEFINITE_NOT_STARTED loga causa + origem do canal
        dns = _result(DEFINITE_NOT_STARTED, causa="kiro-cli ausente", origem="erro interno")
        _, _, _, reg_dns = _run_call_agent(
            monkeypatch, tmp_path, _d_config(max_tentativas=2), [dns])
        texto_dns = " ".join(f"{a} {k}" for _, a, k in reg_dns)
        assert "kiro-cli ausente" in texto_dns

        # A narrativa do agente nunca é a origem registrada (origens válidas).
        for texto in (texto_falha, texto_unk, texto_dns):
            assert "Kiro is having trouble responding" not in texto


# ══════════════════════════════════════════════════════════════════════════
# Grupo D (config) — Validação e defaults dos parâmetros retry.*
# ══════════════════════════════════════════════════════════════════════════

class TestRetryConfig:

    def test_ct14_defaults_quando_ausente(self):
        """CT-14.1: sem a chave 'retry', aplica defaults: max_tentativas=3,
        backoff_inicial_seg=30, backoff_fator=2.0."""
        from src.core.config import resolve_retry
        r = resolve_retry({})
        assert r.max_tentativas == 3
        assert r.backoff_inicial_seg == 30
        assert r.backoff_fator == 2.0

    @pytest.mark.parametrize("valor", [0, -1, True, 2.5, "3"])
    def test_ct14_max_tentativas_invalido_levanta_configerror(self, valor):
        """CT-14.2: max_tentativas inválido → ConfigError nomeando a chave."""
        from src.core.config import validate_retry, ConfigError
        with pytest.raises(ConfigError, match="retry.max_tentativas"):
            validate_retry({"retry": {"max_tentativas": valor}})

    @pytest.mark.parametrize("valor", [-1, True, "0", 2.5])
    def test_ct14_backoff_inicial_invalido_levanta_configerror(self, valor):
        """CT-14.3: backoff_inicial_seg < 0 (ou bool/não-inteiro) → ConfigError."""
        from src.core.config import validate_retry, ConfigError
        with pytest.raises(ConfigError, match="retry.backoff_inicial_seg"):
            validate_retry({"retry": {"backoff_inicial_seg": valor}})

    @pytest.mark.parametrize("valor", [0.5, 0, True, "2.0"])
    def test_ct14_backoff_fator_invalido_levanta_configerror(self, valor):
        """CT-14.4: backoff_fator < 1.0 (ou bool/não-numérico) → ConfigError."""
        from src.core.config import validate_retry, ConfigError
        with pytest.raises(ConfigError, match="retry.backoff_fator"):
            validate_retry({"retry": {"backoff_fator": valor}})

    def test_ct14_valores_validos_sao_aceitos(self):
        """CT-14.5: valores válidos → aceitos e resolvidos corretamente."""
        from src.core.config import resolve_retry, validate_retry
        cfg = {"retry": {"max_tentativas": 5, "backoff_inicial_seg": 10,
                         "backoff_fator": 1.5}}
        validate_retry(cfg)  # não levanta
        r = resolve_retry(cfg)
        assert (r.max_tentativas, r.backoff_inicial_seg, r.backoff_fator) == (5, 10, 1.5)


# ══════════════════════════════════════════════════════════════════════════
# Grupo E — Higiene de documentação
# ══════════════════════════════════════════════════════════════════════════

MODELOS_VALIDOS = {"claude-sonnet-5", "auto", "claude-haiku-4.5"}


class TestHigieneDocumentacao:

    def test_ct15_doc_exemplo_sem_identificador_de_modelo_invalido(self):
        """CT-15: nenhuma referência a identificador de modelo inválido/
        inexistente permanece na doc de exemplo do produto (README.md).

        Guarda de regressão: varre 'model:' no README e exige que cada valor
        esteja na lista de válidos.
        """
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        modelos = re.findall(r"model:\s*([\w.\-]+)", readme)
        assert modelos, "esperado ao menos um 'model:' na doc de exemplo"
        invalidos = [m for m in modelos if m not in MODELOS_VALIDOS]
        assert invalidos == [], f"identificadores inválidos na doc: {invalidos}"
