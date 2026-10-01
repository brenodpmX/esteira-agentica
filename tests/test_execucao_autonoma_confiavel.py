"""Casos de teste — Execução autônoma confiável (issue #303).

ESPECIFICAÇÃO (etapa "Casos de Teste"), já reconciliada com o escopo fechado
pelo planejamento em revisar-escopo (2026-10-01). Este arquivo é o esqueleto que
o desenvolvimento deve implementar na issue #303. Cada teste está vinculado a um
critério de aceitação (CA) via o caso de teste CT-NN documentado em
`doc/quality/execucao-autonoma-confiavel/test-cases.md`.

Decisões de escopo incorporadas (ver cabeçalho do test-cases.md):

- Grupo A: a classificação de sucesso/falha considera APENAS canais estruturados
  (exit-code != 0, [TIMEOUT], [ERRO], saída de erro estruturada). A narrativa
  (texto livre) NUNCA classifica. Ausência de sinal estruturado = SUCESSO. O
  canal "ausência de resumo normal => falha" foi REMOVIDO do escopo (não há mais
  CT-06). A suíte congelada que codifica o falso positivo (narrativa => falha)
  é reescrita nesta entrega — #303 prevalece (ver CT-05b no test-cases.md;
  reescrita feita em tests/test_agent_failure_detection.py pelo desenvolvimento).
- Grupo D: recuperação alinhada à ADR retry-kiro-cli SEM a fronteira idempotente
  da seção 4 (fora de escopo). UNKNOWN_OUTCOME é fail-closed (uma única
  invocação, sem retry inline, preserva evidências); retry inline com backoff
  SOMENTE para DEFINITE_NOT_STARTED (não-inicialização comprovada). Removidos os
  parâmetros retry.retomar_sessao e retry.idempotencia_ativa.

Convenção (mesmo padrão test-first de `tests/test_error_classification.py` e
`tests/test_sanitize_relations.py`):

- Testes com `@pytest.mark.skip(reason="#303 ...")` descrevem comportamento AINDA
  NÃO implementado (retry/classificação UNKNOWN_OUTCOME/DEFINITE_NOT_STARTED,
  resolução de caminhos de apoio, validação `retry.*`, guarda de doc). O
  desenvolvimento deve: (1) implementar, (2) remover o `skip`, (3) completar o
  corpo conforme o docstring (contrato — não enfraquecer a asserção).
- Testes `xfail(strict=True)` (CT-01, CT-05) são o coração da correção: hoje
  `_detect_failure` escaneia a narrativa; viram XPASS com a classificação
  só-por-canais, sinalizando a entrega.
- Testes SEM marca exercitam código já existente e fixam a fronteira correta;
  devem passar hoje.
"""

import sys
from pathlib import Path

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

    @pytest.mark.xfail(strict=True, reason="#303: hoje _detect_failure escaneia "
                       "a narrativa (texto livre: 'Kiro is having trouble "
                       "responding' em _FAILURE_MARKERS). Deve passar após a "
                       "correção (só canais estruturados). XPASS sinaliza a "
                       "entrega (CT-01).")
    def test_ct01_narrativa_cita_erro_sem_sinal_estruturado_e_sucesso(self, adapter):
        """CT-01: narrativa cita frase(s) de erro conhecida(s) mas NÃO há sinal
        estruturado (sem [exit-code: N!=0], sem [TIMEOUT], sem [ERRO]) →
        _detect_failure retorna None (sucesso).

        É o coração da correção: hoje 'Kiro is having trouble responding' consta
        em _FAILURE_MARKERS e dispara falso positivo mesmo citado pela narrativa.
        O desenvolvimento deve parar de escanear texto livre e remover termos de
        prosa dos marcadores de classificação.
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

        Fixa a decisão de escopo: o canal 'ausência de resumo normal => falha'
        foi removido. Coerente com os testes de sucesso da suíte congelada
        (test_output_vazio_nao_e_falha / test_output_normal_nao_e_falha), que
        permanecem válidos.
        """
        assert adapter._detect_failure("") is None
        assert adapter._detect_failure("  \n \n") is None
        assert adapter._detect_failure("Pronto. 3 arquivos alterados.\n") is None

    @pytest.mark.xfail(strict=True, reason="#303: regressão do falso positivo "
                       "histórico. Falha com a detecção antiga (escaneia a "
                       "narrativa); deve passar após a correção. XPASS sinaliza "
                       "a entrega (CT-05).")
    def test_ct05_regressao_falso_positivo_narrativa_nao_recorre(self, adapter):
        """CT-05 (regressão): reproduz o falso positivo histórico — execução
        bem-sucedida cuja narrativa contém o termo de erro, SEM sinal estruturado
        — e comprova que NÃO recorre. Falha na implementação antiga (escaneava
        texto); passa na nova (só canais estruturados).
        """
        output = (
            "Resumo do que fiz: tratei o caso em que a API devolve "
            "'Kiro is having trouble responding right now' e 'temporarily "
            "unavailable'. Nenhum erro ocorreu nesta execução.\n"
            "Concluído em 12s.\n"
        )
        assert adapter._detect_failure(output) is None

    # CT-05b (precedência de contrato) é executado na suíte congelada
    # tests/test_agent_failure_detection.py: o desenvolvimento reescreve os
    # testes que codificam o falso positivo (narrativa => falha) para
    # classificação por canal estruturado, e preserva os testes de sucesso.
    # Ver o detalhamento em doc/quality/execucao-autonoma-confiavel/test-cases.md.


# ══════════════════════════════════════════════════════════════════════════
# Grupo B — Resolução dos caminhos de apoio
# Fonte válida de templates: contexts/templates/ (ex.: docs/test-cases.md).
# Resolução por item (isolar ausência) — NÃO cancelar o lote.
# ══════════════════════════════════════════════════════════════════════════

class TestCaminhosDeApoio:

    @pytest.mark.skip(reason="#303: resolução/validação por item dos caminhos de "
                             "apoio a implementar (CT-07).")
    def test_ct07_caminho_inexistente_nao_cancela_lote(self, tmp_path):
        """CT-07: um lote com caminhos de apoio válidos + um inexistente. Os
        válidos resolvem/executam; o ausente é sinalizado ISOLADAMENTE (por
        item), sem exceção que cancele o lote inteiro.

        O desenvolvimento define o ponto de interceptação (ex.: resolver antes
        de montar o lote de ferramentas); o teste fixa a invariante:
        1 caminho ausente != cancelar os válidos.
        """
        valido = tmp_path / "contexts" / "templates" / "docs" / "test-cases.md"
        valido.parent.mkdir(parents=True)
        valido.write_text("# template\n", encoding="utf-8")
        ausente = tmp_path / "contexts" / "templates" / "issues" / "nao-existe.md"
        # resultado = resolve_support_paths([valido, ausente])
        # assert resultado.resolvidos == [valido]
        # assert resultado.ausentes == [ausente]
        # assert resultado.cancelou_lote is False
        pytest.fail("implementar: resolução por item sem cancelar o lote")

    @pytest.mark.skip(reason="#303: fonte única de templates (config == código) "
                             "a implementar (CT-08).")
    def test_ct08_config_e_codigo_apontam_para_mesma_fonte_valida(self, tmp_path):
        """CT-08: os caminhos de apoio referenciados pela CONFIGURAÇÃO e os
        gerados por CÓDIGO apontam para o mesmo diretório-fonte válido
        (contexts/templates/…) e todos existem no ambiente.

        Detecta o anti-padrão de config e código apontando para pastas
        diferentes. O desenvolvimento centraliza a constante da fonte.
        """
        # fonte_codigo = support_paths_from_code()
        # fonte_config = support_paths_from_config(config)
        # assert fonte_codigo == fonte_config
        # assert all(p.exists() for p in fonte_codigo)
        pytest.fail("implementar: fonte única e existência garantida")


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
        # Tabela de boards/colunas com dados reais
        assert "| `casos-de-teste` | Casos de Teste | quality |" in content
        assert "| `desenvolvimento` | Desenvolvimento | engineering-pl |" in content
        # Tabela de flow/branches preenchida
        assert "| `feature` | `feature` | `main` | `main` |" in content
        assert "Branch base: `main`" in content

    def test_ct09_sem_aviso_de_conflito_no_caminho_feliz(self, tmp_path, monkeypatch):
        """CT-09: quando o steering já reflete a config vigente,
        ensure_steering_integrity NÃO acusa divergência (retorna False) — ou
        seja, nenhum 'aviso de conflito de contexto' é emitido no caminho feliz.
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
        # Artefato congelado: tabelas vazias (cabeçalho sem linhas de dados).
        steering.write_text(
            "---\ninclusion: always\n---\n\n## Boards e colunas\n\n"
            "| Coluna (id) | Nome | Agente |\n|---|---|---|\n", encoding="utf-8")
        monkeypatch.setattr(cg, "STEERING_FILE", steering)

        diverged = cg.ensure_steering_integrity(self._config())
        assert diverged is True
        content = steering.read_text(encoding="utf-8")
        assert "| `casos-de-teste` | Casos de Teste | quality |" in content

    @pytest.mark.skip(reason="#303: garantir que nenhum pipe_context.json legado "
                             "sombreie o steering vigente (CT-09b, 2ª camada).")
    def test_ct09b_pipe_context_legado_nao_sombreia_steering(self, tmp_path):
        """CT-09b (2ª camada): se existir um .kiro/agents/pipe_context.json
        legado com tabelas vazias, ele NÃO pode sombrear o steering vigente. O
        desenvolvimento garante que o contexto efetivo é sempre o derivado da
        config (remoção/regeneração do artefato legado).
        """
        pytest.fail("implementar: artefato legado pipe_context.json sem precedência")


# ══════════════════════════════════════════════════════════════════════════
# Grupo D — Tratamento seguro de interrupção transitória (ADR #217)
# SEM a fronteira idempotente da seção 4 (fora de escopo).
# - UNKNOWN_OUTCOME: fail-closed (1 invocação, sem retry inline, preserva
#   output/request ID/causa/session_id; reconciliação pelo loop normal).
# - DEFINITE_NOT_STARTED: retry inline com backoff e limite.
# Observabilidade exigida: causa real + origem (canal). time.sleep SEMPRE mockado.
# ══════════════════════════════════════════════════════════════════════════

class TestRecuperacaoInterrupcao:

    @pytest.mark.skip(reason="#303: classificação UNKNOWN_OUTCOME fail-closed a "
                             "implementar (CT-10).")
    def test_ct10_unknown_outcome_fail_closed_uma_invocacao_preserva(self, monkeypatch):
        """CT-10: aborto transitório ambíguo (dispatch failure /
        InternalServerError após output parcial / timeout) → UNKNOWN_OUTCOME.

        - subprocesso invocado EXATAMENTE UMA VEZ (sem retry inline, sem backoff);
        - resultado marcado como ambíguo (NÃO sucesso, NÃO falha definitiva);
        - output, request ID (quando disponível), causa e session_id PRESERVADOS
          para auditoria/continuidade.

        A reconciliação (fs/git/board) e a eventual retomada via --resume-id
        ficam a cargo do LOOP NORMAL — não há retry inline aqui.
        """
        # invocacoes = []
        # monkeypatch no adapter para registrar cada invocação e devolver um
        # resultado ambíguo (output parcial + 'dispatch failure').
        # sleeps = []
        # monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
        # resultado = call_agent(config, task)
        # assert len(invocacoes) == 1
        # assert sleeps == []            # nenhum backoff
        # assert resultado.classe == "UNKNOWN_OUTCOME"
        # assert resultado.output and resultado.causa and resultado.session_id
        pytest.fail("implementar: UNKNOWN_OUTCOME fail-closed (1 invocação + preserva)")

    @pytest.mark.skip(reason="#303: retry inline + backoff para DEFINITE_NOT_STARTED "
                             "a implementar (CT-11).")
    def test_ct11_definite_not_started_retry_com_backoff_ate_sucesso_ou_limite(self, monkeypatch):
        """CT-11: não-inicialização comprovada mecanicamente
        (DEFINITE_NOT_STARTED, ex.: kiro-cli ausente no PATH) → retry inline com
        backoff crescente (backoff_inicial_seg * backoff_fator^n) até sucesso ou
        até max_tentativas.

        Sub-caso A (retoma até sucesso): falha DEFINITE_NOT_STARTED 1x, depois
        sucesso → reexecuta com backoff e conclui em sucesso; time.sleep chamado
        com backoff_inicial_seg na 1ª espera.

        Sub-caso B (esgota o limite): falha DEFINITE_NOT_STARTED sempre →
        exatamente max_tentativas invocações (SEM laço infinito); backoff cresce
        por backoff_fator (ex.: [30, 60] para max_tentativas=3); resultado =
        FALHA PERSISTENTE; log registra total de tentativas + última causa.

        time.sleep mockado: asserir os ARGUMENTOS de backoff, não esperar tempo.
        """
        # sleeps = []
        # monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
        # Sub-caso B: adapter sinaliza DEFINITE_NOT_STARTED sempre; max=3
        # resultado = call_agent(config, task)
        # assert numero_de_invocacoes == 3
        # assert sleeps == [30, 60]      # backoff_inicial=30, fator=2.0
        # assert resultado.classe == "falha persistente"
        # assert "tentativas" in log and "última causa" in log
        pytest.fail("implementar: retry DEFINITE_NOT_STARTED com backoff + limite")

    @pytest.mark.skip(reason="#303: garantir que UNKNOWN_OUTCOME NÃO dispara retry "
                             "inline nem backoff (CT-12).")
    def test_ct12_unknown_outcome_nao_dispara_retry_nem_backoff(self, monkeypatch):
        """CT-12: resultado ambíguo (UNKNOWN_OUTCOME) → NÃO há retry inline nem
        backoff na mesma execução (par explícito de CT-11).

        Garante que o retry inline é EXCLUSIVO de DEFINITE_NOT_STARTED. Impede a
        regressão do 'retry cego' vedado pela ADR #217.
        """
        # sleeps = []
        # monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
        # adapter devolve UNKNOWN_OUTCOME; retry.max_tentativas > 1
        # resultado = call_agent(config, task)
        # assert numero_de_invocacoes == 1
        # assert sleeps == []            # nenhum backoff
        # assert resultado.classe == "UNKNOWN_OUTCOME"
        pytest.fail("implementar: UNKNOWN_OUTCOME sem retry inline/backoff")

    @pytest.mark.skip(reason="#303: observabilidade (causa + origem do canal; "
                             "UNKNOWN_OUTCOME acionável) a implementar (CT-13).")
    def test_ct13_log_registra_causa_e_origem_do_canal(self, monkeypatch):
        """CT-13: toda classificação de falha e todo retry seguro registram no
        log a causa real E a origem/canal estruturado (campo que diferencie
        exit-code / timeout / erro interno). O UNKNOWN_OUTCOME é registrado de
        forma acionável (causa + evidência preservada), distinto de sucesso e de
        falha definitiva. A narrativa do agente NUNCA é a origem registrada.
        """
        # capturar registros de log de: (a) falha por canal, (b) UNKNOWN_OUTCOME,
        # (c) retry DEFINITE_NOT_STARTED.
        # assert causa_real in registro
        # assert origem_canal in registro  (ex.: "exit-code" | "timeout" | "erro interno")
        # assert registro_unknown distinto de sucesso e de falha definitiva
        pytest.fail("implementar: log com causa + origem do canal; UNKNOWN acionável")


# ══════════════════════════════════════════════════════════════════════════
# Grupo D (config) — Validação e defaults dos parâmetros retry.*
# Padrão: espelhar validate_max_attempts/resolve_max_attempts de config.py.
# Aplicáveis SÓ ao caso seguro DEFINITE_NOT_STARTED. Sem retomar_sessao nem
# idempotencia_ativa (removidos do escopo).
# ══════════════════════════════════════════════════════════════════════════

class TestRetryConfig:

    @pytest.mark.skip(reason="#303: validate_retry/resolve_retry a implementar "
                             "em config.py (CT-14).")
    def test_ct14_defaults_quando_ausente(self):
        """CT-14.1: sem a chave 'retry', aplica defaults: max_tentativas=3,
        backoff_inicial_seg=30, backoff_fator=2.0."""
        # from src.core.config import resolve_retry
        # r = resolve_retry({})
        # assert r.max_tentativas == 3
        # assert r.backoff_inicial_seg == 30
        # assert r.backoff_fator == 2.0
        pytest.fail("implementar: defaults de retry.*")

    @pytest.mark.skip(reason="#303: validate_retry a implementar (CT-14).")
    @pytest.mark.parametrize("valor", [0, -1, True, 2.5, "3"])
    def test_ct14_max_tentativas_invalido_levanta_configerror(self, valor):
        """CT-14.2: max_tentativas inválido (0, negativo, bool, float, string)
        → ConfigError identificando a chave 'retry.max_tentativas'."""
        # from src.core.config import validate_retry, ConfigError
        # with pytest.raises(ConfigError, match="retry.max_tentativas"):
        #     validate_retry({"retry": {"max_tentativas": valor}})
        pytest.fail("implementar: validação de retry.max_tentativas")

    @pytest.mark.skip(reason="#303: validate_retry a implementar (CT-14).")
    @pytest.mark.parametrize("valor", [-1, True, "0"])
    def test_ct14_backoff_inicial_invalido_levanta_configerror(self, valor):
        """CT-14.3: backoff_inicial_seg < 0 (ou bool/não-inteiro) → ConfigError
        nomeando 'retry.backoff_inicial_seg'."""
        pytest.fail("implementar: validação de retry.backoff_inicial_seg >= 0")

    @pytest.mark.skip(reason="#303: validate_retry a implementar (CT-14).")
    @pytest.mark.parametrize("valor", [0.5, 0, True, "2.0"])
    def test_ct14_backoff_fator_invalido_levanta_configerror(self, valor):
        """CT-14.4: backoff_fator < 1.0 (ou bool/não-numérico) → ConfigError
        nomeando 'retry.backoff_fator'."""
        pytest.fail("implementar: validação de retry.backoff_fator >= 1.0")

    @pytest.mark.skip(reason="#303: validate_retry a implementar (CT-14).")
    def test_ct14_valores_validos_sao_aceitos(self):
        """CT-14.5: valores válidos (max_tentativas=5, backoff_inicial_seg=10,
        backoff_fator=1.5) → aceitos e resolvidos corretamente."""
        # from src.core.config import resolve_retry
        # r = resolve_retry({"retry": {"max_tentativas": 5,
        #                              "backoff_inicial_seg": 10,
        #                              "backoff_fator": 1.5}})
        # assert (r.max_tentativas, r.backoff_inicial_seg, r.backoff_fator) \
        #        == (5, 10, 1.5)
        pytest.fail("implementar: aceitação de valores válidos de retry.*")


# ══════════════════════════════════════════════════════════════════════════
# Grupo E — Higiene de documentação
# ══════════════════════════════════════════════════════════════════════════

class TestHigieneDocumentacao:

    @pytest.mark.skip(reason="#303: definir lista de modelos válidos e corrigir a "
                             "doc de exemplo; teste de guarda (CT-15).")
    def test_ct15_doc_exemplo_sem_identificador_de_modelo_invalido(self):
        """CT-15: nenhuma referência a identificador de modelo inválido/
        inexistente permanece na doc de exemplo do produto (ex.: README.md).

        Identificadores válidos vigentes: 'claude-sonnet-5', 'auto',
        'claude-haiku-4.5'. Hoje README.md traz 'model: claude-sonnet-4-20250514'
        (inválido). Teste de guarda: varrer 'model:' na doc de exemplo e exigir
        que cada valor esteja na lista de válidos (impede reintrodução).
        """
        # import re
        # MODELOS_VALIDOS = {"claude-sonnet-5", "auto", "claude-haiku-4.5"}
        # readme = (ROOT / "README.md").read_text(encoding="utf-8")
        # modelos = re.findall(r"model:\s*([\w.\-]+)", readme)
        # invalidos = [m for m in modelos if m not in MODELOS_VALIDOS]
        # assert invalidos == [], f"identificadores inválidos na doc: {invalidos}"
        pytest.fail("implementar: guarda de identificadores de modelo na doc")
