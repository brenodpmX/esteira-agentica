"""Casos de teste — Execução autônoma confiável (issue #303).

ESPECIFICAÇÃO (etapa "Casos de Teste"). Este arquivo é o esqueleto que o
desenvolvimento deve implementar na issue #303. Cada teste está vinculado a um
critério de aceitação (CA) via o caso de teste CT-NN documentado em
`doc/quality/execucao-autonoma-confiavel/test-cases.md`.

Convenção (mesmo padrão test-first de `tests/test_error_classification.py` e
`tests/test_sanitize_relations.py`):

- Testes marcados com `@pytest.mark.skip(reason="#303 ...")` descrevem
  comportamento AINDA NÃO implementado no repositório (retry, resolução de
  caminhos de apoio, validação `retry.*`). O desenvolvimento deve: (1) implementar
  o comportamento, (2) remover o `skip` e (3) completar o corpo do teste conforme
  o docstring. O docstring é contrato — não enfraquecer a asserção.
- Testes SEM `skip` exercitam código já existente
  (`KiroCliAgent._detect_failure`) e fixam a fronteira correta
  (canais estruturados × narrativa). Esses devem passar; se a detecção ainda
  escaneia texto livre, falham de propósito até a correção.

ATENÇÃO (conflito arquitetural): o Grupo D (retry) depende da fronteira
idempotente da ADR `doc/architecture/retry-kiro-cli/idempotencia.md` (seção 4).
Ver o aviso no topo do documento de casos de teste. A idempotência é invariante,
não opção.
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
# (exit-code, timeout, erro interno, ausência de resumo final normal, saída de
# erro estruturada). A narrativa (texto livre) do agente NUNCA classifica.
# ══════════════════════════════════════════════════════════════════════════

class TestDeteccaoFalhaCanaisEstruturados:

    @pytest.mark.xfail(strict=True, reason="#303: hoje _detect_failure escaneia "
                       "a narrativa (texto livre). Deve passar após a correção "
                       "(só canais estruturados). XPASS sinaliza a entrega (CT-01).")
    def test_ct01_narrativa_cita_erro_com_resumo_normal_e_sucesso(self, adapter):
        """CT-01: narrativa cita frase de erro conhecida mas o resumo final é
        normal e exit-code 0 → _detect_failure retorna None (sucesso).

        É o coração da correção: hoje "Kiro is having trouble responding" em
        _FAILURE_MARKERS dispara falso positivo mesmo citado pela narrativa.
        O desenvolvimento deve parar de escanear texto livre e considerar apenas
        canais estruturados (incl. presença do bloco final de resumo normal).
        """
        output = (
            "Analisei a issue e implementei o tratamento para quando o modelo "
            "responde 'Kiro is having trouble responding right now'.\n"
            "Também cobri 'InternalServerError' e mensagens 'error:' do servidor.\n"
            # Bloco final de resumo NORMAL (crédito/tempo) — formato real a ser
            # fixado pelo desenvolvimento. Exit-code 0 (ausência de [exit-code: N]).
            "<<RESUMO_FINAL_NORMAL: crédito/tempo>>\n"
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

        Diferente do CT-01: aqui o sinal é ESTRUTURADO (marcador/seção de erro
        de dispatch), não texto livre do agente. O desenvolvimento define quais
        marcadores constituem 'canal estruturado' de transporte.
        """
        output = (
            "iniciando\n"
            "[ERRO] dispatch failure: stream da resposta interrompido\n"
        )
        error = adapter._detect_failure(output)
        assert error is not None
        assert "dispatch failure" in error or "ERRO" in error

    @pytest.mark.xfail(strict=True, reason="#303: regressão do falso positivo "
                       "histórico. Falha com a detecção antiga (escaneia texto); "
                       "deve passar após a correção. XPASS sinaliza a entrega (CT-05).")
    def test_ct05_regressao_falso_positivo_narrativa_nao_recorre(self, adapter):
        """CT-05 (regressão): reproduz o falso positivo histórico — execução
        bem-sucedida cuja narrativa contém o termo de erro — e comprova que NÃO
        recorre. Falha na implementação antiga (escaneava texto); passa na nova.
        """
        output = (
            "Resumo do que fiz: tratei o caso em que a API devolve "
            "'Kiro is having trouble responding right now' e 'temporarily "
            "unavailable'. Nenhum erro ocorreu nesta execução.\n"
            "<<RESUMO_FINAL_NORMAL: crédito/tempo>>\n"
        )
        assert adapter._detect_failure(output) is None

    @pytest.mark.skip(reason="#303: reconhecedor do 'bloco final de resumo "
                             "normal' a implementar (CT-06).")
    def test_ct06_ausencia_de_resumo_final_normal_e_falha(self, adapter):
        """CT-06: output sem o bloco final de resumo normal (execução cortada no
        meio, sem exit-code) → falha. A ausência do resumo é canal estruturado.

        Par com CT-01: narrativa+resumo normal = sucesso; sem resumo = falha.
        O desenvolvimento define o reconhecedor estrutural do resumo final.
        """
        output = (
            "iniciando a tarefa\n"
            "editando arquivos...\n"
            # Sem bloco final de resumo normal, sem exit-code, sem marcador.
        )
        assert adapter._detect_failure(output) is not None


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
# Grupo D — Recuperação de interrupção transitória com retry idempotente
# PRÉ-REQUISITO: fronteira idempotente da ADR retry-kiro-cli (seção 4).
# Observabilidade exigida em todos: causa real + origem (canal) + operações
# puladas por já estarem aplicadas. time.sleep SEMPRE mockado.
# ══════════════════════════════════════════════════════════════════════════

class TestRecuperacaoInterrupcao:

    @pytest.mark.skip(reason="#303: retry inline + backoff + retomada de sessão "
                             "a implementar (CT-10). Depende da fronteira "
                             "idempotente da ADR seção 4.")
    def test_ct10_sem_efeito_aplicado_retoma_com_backoff_ate_sucesso(self, monkeypatch):
        """CT-10: interrupção transitória sem efeito colateral já aplicado →
        a execução é retomada automaticamente (sem intervenção humana) com
        backoff crescente (backoff_inicial_seg * backoff_fator^n) e retomada de
        sessão (--resume-id), até sucesso dentro de max_tentativas.

        time.sleep mockado: asserir os ARGUMENTOS de backoff, não esperar tempo.
        Fronteira idempotente registra 0 operações de escrita efetivadas.
        """
        # sleeps = []
        # monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
        # adapter falha transitório 1x, depois sucesso.
        # chamar call_agent(config, task) com retry habilitado.
        # assert sleeps == [30]  (backoff_inicial; 1 retry)
        # assert sessao_retomada is True
        # assert resultado == "sucesso"
        pytest.fail("implementar: retry com backoff + resume até sucesso")

    @pytest.mark.skip(reason="#303: idempotência (não repetir efeitos aplicados) "
                             "a implementar (CT-11). ADR seção 4.")
    def test_ct11_apos_efeito_aplicado_nao_repete_e_loga_puladas(self, monkeypatch):
        """CT-11: interrupção após commit/push/movimento de coluna já EFETIVADOS
        → nenhuma dessas operações é repetida no retry; o log lista
        explicitamente quais foram PULADAS por já estarem aplicadas.

        Testar as TRÊS operações (commit, push, movimento de coluna). A
        verificação de pós-condição confirma o estado desejado (operações
        declarativas: reaplicar = no-op).
        """
        # journal marca commit/push/move como applied/verified
        # disparar interrupção + retry
        # assert nenhuma reexecução de commit/push/move
        # assert "puladas" / "já aplicadas" presente no log, nomeando as ops
        pytest.fail("implementar: idempotência + log de operações puladas")

    @pytest.mark.skip(reason="#303: limite de tentativas e falha persistente a "
                             "implementar (CT-12).")
    def test_ct12_interrupcao_persistente_encerra_em_max_tentativas(self, monkeypatch):
        """CT-12: interrupção que persiste → ao atingir retry.max_tentativas a
        recuperação encerra, a execução é classificada como FALHA PERSISTENTE e
        o reprocessamento para (sem laço infinito). O log registra o total de
        tentativas e a última causa.

        Confirmar com o desenvolvimento a semântica de 'tentativas' (ver CT-14):
        o teste deve travar a semântica escolhida (ex.: max_tentativas=3 ⇒ 3
        invocações do subprocesso).
        """
        # adapter falha transitório sempre; max_tentativas=3; sleep mockado
        # chamar call_agent com retry
        # assert numero_de_invocacoes == 3
        # assert classificacao == "falha persistente"
        # assert log contém total de tentativas e última causa
        pytest.fail("implementar: limite de tentativas sem laço infinito")

    @pytest.mark.skip(reason="#303: observabilidade (causa + origem do canal) "
                             "no retry a implementar (CT-13).")
    def test_ct13_log_registra_causa_e_origem_do_canal(self, monkeypatch):
        """CT-13: todo retry e toda classificação de falha registram no log a
        causa real E a origem/canal estruturado (ex.: campo que diferencie
        exit-code / timeout / transporte). A narrativa do agente nunca é a
        origem registrada.
        """
        # capturar registros de log de um retry/classificação
        # assert causa_real in registro
        # assert origem_canal in registro  (ex.: "exit-code" | "timeout" | "transporte")
        pytest.fail("implementar: log com causa + origem do canal")


# ══════════════════════════════════════════════════════════════════════════
# Grupo D (config) — Validação e defaults dos parâmetros retry.*
# Padrão: espelhar validate_max_attempts/resolve_max_attempts de config.py.
# ══════════════════════════════════════════════════════════════════════════

class TestRetryConfig:

    @pytest.mark.skip(reason="#303: validate_retry/resolve_retry a implementar "
                             "em config.py (CT-14).")
    def test_ct14_defaults_quando_ausente(self):
        """CT-14.1: sem a chave 'retry', aplica defaults: max_tentativas=3,
        backoff_inicial_seg=30, backoff_fator=2.0, retomar_sessao=True,
        idempotencia_ativa=True."""
        # from src.core.config import resolve_retry
        # r = resolve_retry({})
        # assert r.max_tentativas == 3 and r.backoff_inicial_seg == 30
        # assert r.backoff_fator == 2.0 and r.retomar_sessao is True
        # assert r.idempotencia_ativa is True
        pytest.fail("implementar: defaults de retry.*")

    @pytest.mark.skip(reason="#303: validate_retry a implementar (CT-14).")
    @pytest.mark.parametrize("valor", [0, -1, True, 2.5, "3"])
    def test_ct14_max_tentativas_invalido_levanta_configerror(self, valor):
        """CT-14.2: max_tentativas inválido (0, negativo, bool, float, string)
        → ConfigError identificando a chave."""
        # from src.core.config import validate_retry, ConfigError
        # with pytest.raises(ConfigError, match="retry.max_tentativas"):
        #     validate_retry({"retry": {"max_tentativas": valor}})
        pytest.fail("implementar: validação de retry.max_tentativas")

    @pytest.mark.skip(reason="#303: validate_retry a implementar (CT-14).")
    def test_ct14_backoff_inicial_negativo_levanta_configerror(self):
        """CT-14.3: backoff_inicial_seg < 0 → ConfigError."""
        pytest.fail("implementar: validação de retry.backoff_inicial_seg >= 0")

    @pytest.mark.skip(reason="#303: validate_retry a implementar (CT-14).")
    def test_ct14_backoff_fator_menor_que_um_levanta_configerror(self):
        """CT-14.4: backoff_fator < 1.0 → ConfigError."""
        pytest.fail("implementar: validação de retry.backoff_fator >= 1.0")

    @pytest.mark.skip(reason="#303: validate_retry a implementar (CT-14).")
    @pytest.mark.parametrize("campo", ["retomar_sessao", "idempotencia_ativa"])
    def test_ct14_booleanos_invalidos_levantam_configerror(self, campo):
        """CT-14.5: retomar_sessao / idempotencia_ativa não-booleanos →
        ConfigError."""
        pytest.fail("implementar: validação dos booleanos de retry.*")


# ══════════════════════════════════════════════════════════════════════════
# Grupo E — Higiene de documentação
# ══════════════════════════════════════════════════════════════════════════

class TestHigieneDocumentacao:

    @pytest.mark.skip(reason="#303: definir lista de modelos válidos e corrigir a "
                             "doc de exemplo; teste de guarda opcional (CT-15).")
    def test_ct15_doc_exemplo_sem_identificador_de_modelo_invalido(self):
        """CT-15: nenhuma referência a identificador de modelo inválido/
        inexistente permanece na doc de exemplo do produto (ex.: README.md).

        O desenvolvimento define MODELOS_VALIDOS (ex.: 'claude-sonnet-5',
        'auto', 'claude-haiku-4.5') e corrige as referências. Teste de guarda:
        varrer 'model:' na doc de exemplo e exigir que cada valor esteja na
        lista de válidos (impede reintrodução).
        """
        # import re
        # readme = (ROOT / "README.md").read_text(encoding="utf-8")
        # modelos = re.findall(r"model:\s*([\w.\-]+)", readme)
        # invalidos = [m for m in modelos if m not in MODELOS_VALIDOS]
        # assert invalidos == [], f"identificadores inválidos na doc: {invalidos}"
        pytest.fail("implementar: guarda de identificadores de modelo na doc")
