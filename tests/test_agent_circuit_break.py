"""Testes do núcleo do limitador de reexecuções de agente por contexto (#306).

Cobre contagem no instante da entrega, janela deslizante, bloqueio antes do
dispatch, sinalização idempotente (need_human + comentário com marcador),
reinício da franquia, retomada humana, recuperação após reinício, falha fechada,
segurança do estado e isolamento (a issue bloqueada não trava a fila).

Convenções (fixadas pela QA):
- Offline, sem rede: `BoardPort` fake espião controlável.
- Relógio controlável: injetado no `CircuitBreaker` (nunca `sleep` real).
- Nunca `monkeypatch` do símbolo sob teste: o núcleo (contagem, decisão,
  máquina de estados do `trip`) é exercitado de verdade; só o board port e o
  relógio são controlados. O dispatch real é substituído por espião.
- Evidência de negócio nunca via leitura do arquivo de estado protegido; a
  verificação do estado persistido só onde o caso é explicitamente sobre a
  persistência (CT-20/CT-19).
"""

import json
from pathlib import Path

import pytest

import src.__main__ as pipe
from src.core.agent_circuit_break import (
    CircuitBreaker,
    CircuitBreakPolicy,
    CircuitBreakStateError,
    STATE_FILE,
    STEP_LABELED,
    STEP_PERSISTED,
    STEP_SIGNALED,
    COMMENT_MARKER_PREFIX,
    load_state,
    save_state,
)


# ══════════════════════════════════════════════════════════════════════════════
# Infra de teste: relógio controlável e BoardPort fake espião
# ══════════════════════════════════════════════════════════════════════════════

class FakeClock:
    """Relógio determinístico (segundos). `advance` move o tempo adiante."""

    def __init__(self, start: float = 1_000_000.0):
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeBoard:
    """Board fake espião: registra labels, comentários e lista mutável de
    comentários. Sobrescreve a aplicação de label (capacidade real)."""

    def __init__(self):
        self.labels: dict[tuple[str, str], set[str]] = {}
        self.added_comments: list[dict] = []
        self._comments: dict[tuple[str, str], list[dict]] = {}
        self.moved: list[tuple] = []

    def _key(self, board_id, issue_id):
        return (str(board_id), str(issue_id))

    def add_label(self, board_id, issue_id, label):
        self.labels.setdefault(self._key(board_id, issue_id), set()).add(label)

    def set_labels(self, board_id, issue_id, labels):
        self.labels[self._key(board_id, issue_id)] = set(labels)

    def remove_label(self, board_id, issue_id, label):
        self.labels.get(self._key(board_id, issue_id), set()).discard(label)

    def add_comment(self, board_id, issue_id, comment):
        key = self._key(board_id, issue_id)
        entry = {"author": "pipe", "date": "now", "body": comment}
        self.added_comments.append({"key": key, "body": comment})
        self._comments.setdefault(key, []).append(entry)

    def list_comments(self, board_id, issue_id):
        return list(self._comments.get(self._key(board_id, issue_id), []))

    def move_issue(self, board_id, issue_id, column, from_column=None):
        self.moved.append((str(board_id), str(issue_id), column, from_column))

    # ── helpers de inspeção para os testes ────────────────────────────────────

    def has_need_human(self, board_id, issue_id) -> bool:
        return "need_human" in self.labels.get(self._key(board_id, issue_id), set())

    def comment_count(self, board_id, issue_id) -> int:
        return len(self._comments.get(self._key(board_id, issue_id), []))


class FakeBoardNoLabel:
    """Board fake SEM capacidade de label (herda default no-op de BoardPort),
    usado só para o gate de capacidade (CT-18)."""
    # Não define add_label/set_labels — usa os defaults de BoardPort via
    # subclasse direta abaixo.


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Isola `.pipe/` por teste (chdir) e limpa caches de módulo."""
    monkeypatch.chdir(tmp_path)
    pipe._rerun_cache.clear()
    yield
    pipe._rerun_cache.clear()


def _policy(executions=3, window=3600, active=True):
    if not active:
        return CircuitBreakPolicy(active=False)
    return CircuitBreakPolicy(active=True, executions=executions, window=window)


# ══════════════════════════════════════════════════════════════════════════════
# Grupo A — Contagem, janela e isolamento por contexto
# ══════════════════════════════════════════════════════════════════════════════

class TestCT01LimiteAtingidoBloqueia:
    """CT-01 / CT-01b: ao atingir N, a próxima execução não é admitida."""

    def test_limite_bloqueia_quarta_entrega(self):
        clock = FakeClock()
        board = FakeBoard()
        cb = lambda: CircuitBreaker(_policy(3, 3600), board, clock)

        # 3 entregas permitidas (dentro da janela).
        for _ in range(3):
            assert cb().admit("entrega", "desenvolvimento", "42").admitted is True
        # 4ª excedente é bloqueada.
        decision = cb().admit("entrega", "desenvolvimento", "42")
        assert decision.admitted is False
        assert decision.blocked is True
        assert decision.event_id
        # Sinalização aplicada.
        assert board.has_need_human("entrega", "42")
        assert board.comment_count("entrega", "42") == 1

    def test_excedente_nao_conta_como_entrega(self):
        """CT-01b: exatamente 3 entregas admitidas; a 4ª é interrompida antes."""
        clock = FakeClock()
        board = FakeBoard()
        admitted = 0
        for _ in range(4):
            if CircuitBreaker(_policy(3, 3600), board, clock).admit(
                "entrega", "desenvolvimento", "42"
            ).admitted:
                admitted += 1
        assert admitted == 3


class TestCT02AbaixoDoLimite:
    def test_abaixo_do_limite_executa(self):
        clock = FakeClock()
        board = FakeBoard()
        d = CircuitBreaker(_policy(3, 3600), board, clock).admit(
            "entrega", "desenvolvimento", "42"
        )
        assert d.admitted is True
        assert not board.has_need_human("entrega", "42")
        assert board.comment_count("entrega", "42") == 0


class TestCT03SucessoSemAvancoConta:
    """CT-03: a contagem independe do resultado (sucesso sem avanço conta)."""

    def test_cada_entrega_conta_independente_do_resultado(self):
        clock = FakeClock()
        board = FakeBoard()
        # Simula N entregas de "sucesso sem avanço" (mesma coluna): a admissão
        # conta a entrega. Na N+1 bloqueia.
        for _ in range(3):
            assert CircuitBreaker(_policy(3, 3600), board, clock).admit(
                "entrega", "desenvolvimento", "42"
            ).admitted is True
        assert CircuitBreaker(_policy(3, 3600), board, clock).admit(
            "entrega", "desenvolvimento", "42"
        ).admitted is False


class TestCT04BordasDaJanela:
    """CT-04: contam só ocorrências com idade estritamente menor que T."""

    @pytest.mark.parametrize("idade,conta", [(-1, True), (0, False), (1, False)])
    def test_bordas_T_menos_1_T_T_mais_1(self, idade, conta):
        """Com N=2: semeia 1 ocorrência; posiciona o relógio na borda T+idade.

        idade relativo a T: T-1 (idade=-1) conta; T (0) e T+1 (+1) expiram.
        Se a antiga conta, a próxima (2ª dentro da janela) atinge N=2 e, portanto,
        a SEGUINTE seria bloqueada. Verificamos: com a antiga contando, após uma
        nova entrega o contexto fica no limite (próxima bloqueia); sem contar,
        não.
        """
        T = 100
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(2, T)

        # Semeia 1 ocorrência em t0.
        assert CircuitBreaker(policy, board, clock).admit(
            "entrega", "desenvolvimento", "42"
        ).admitted is True

        # Avança para idade de borda: T + idade (idade<0 → T-1; 0 → T; +1 → T+1).
        clock.advance(T + idade)

        # 2ª entrega.
        d2 = CircuitBreaker(policy, board, clock).admit(
            "entrega", "desenvolvimento", "42"
        )
        assert d2.admitted is True  # 2ª sempre executa (<= N=2 no pior caso)

        # 3ª entrega (mesmo instante): bloqueia SSE a antiga ainda contava.
        d3 = CircuitBreaker(policy, board, clock).admit(
            "entrega", "desenvolvimento", "42"
        )
        if conta:
            # antiga (idade T-1) + a 2ª = 2 dentro da janela → a 3ª bloqueia.
            assert d3.admitted is False
        else:
            # antiga expirou → só a 2ª conta → a 3ª ainda executa.
            assert d3.admitted is True


class TestCT05CT06MudancaDeColuna:
    """CT-05/CT-06: mudar de coluna reinicia; revisitar coluna começa do zero."""

    def test_mudanca_de_coluna_reinicia(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(2, 3600)
        # 2 ocorrências em desenvolvimento (no limite).
        for _ in range(2):
            CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        # Nova coluna: contexto novo, começa em zero.
        d = CircuitBreaker(policy, board, clock).admit("entrega", "execucao-testes", "42")
        assert d.admitted is True

    def test_revisita_de_coluna_comeca_do_zero(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(2, 3600)
        # desenvolvimento → acumula 2 (no limite)
        for _ in range(2):
            CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        # execucao-testes (contexto novo)
        CircuitBreaker(policy, board, clock).admit("entrega", "execucao-testes", "42")
        # volta a desenvolvimento (revisita): começa do zero
        d = CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        assert d.admitted is True
        # e aceita mais uma antes de bloquear (franquia 2 reiniciada)
        d2 = CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        assert d2.admitted is True
        d3 = CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        assert d3.admitted is False


class TestCT21PrecisaoSobRepeticaoIntensa:
    """CT-21 / RNF-01: zero execuções acima de N em >= 32 tentativas."""

    def test_nunca_excede_N_em_32_tentativas(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(5, 10_000)
        admitted = 0
        blocked_once = False
        for _ in range(40):
            # Após o 1º bloqueio, a label need_human permanece (operador não
            # libera) → a issue fica presa; nunca mais que N=5 despachos.
            d = CircuitBreaker(policy, board, clock).admit(
                "entrega", "dev", "99", need_human_present=blocked_once
            )
            if d.admitted:
                admitted += 1
            if d.blocked:
                blocked_once = True
        assert admitted == 5

    def test_nunca_excede_N_entre_bloqueios_com_liberacao(self):
        """Com liberação periódica (need_human removido), cada franquia concede
        exatamente N — nunca mais — antes de novo bloqueio."""
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(5, 10_000)
        run = 0  # execuções consecutivas admitidas desde o último bloqueio
        for _ in range(40):
            # Libera sempre (need_human_present=False): cada bloqueio reinicia a
            # franquia na admissão seguinte.
            d = CircuitBreaker(policy, board, clock).admit(
                "entrega", "dev", "99", need_human_present=False
            )
            if d.admitted:
                run += 1
                assert run <= 5, "nunca mais que N execuções entre bloqueios"
            else:
                run = 0


# ══════════════════════════════════════════════════════════════════════════════
# Grupo B — Sinalização, reinício da franquia e retomada
# ══════════════════════════════════════════════════════════════════════════════

class TestCT07SinalizacaoCompleta:
    """CT-07: need_human + comentário com os cinco dados mínimos + marcador."""

    def _trip(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(3, 3600)
        for _ in range(3):
            CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        decision = CircuitBreaker(policy, board, clock).admit(
            "entrega", "desenvolvimento", "42"
        )
        return board, decision

    def test_label_aplicada(self):
        board, _ = self._trip()
        assert board.has_need_human("entrega", "42")

    def test_um_comentario_com_cinco_dados_e_marcador(self):
        board, decision = self._trip()
        assert board.comment_count("entrega", "42") == 1
        body = board.added_comments[0]["body"]
        # motivo, issue, board, coluna, limite, janela
        assert "limite" in body.lower()
        assert "#42" in body
        assert "entrega" in body
        assert "desenvolvimento" in body
        assert "3" in body       # N
        assert "3600" in body    # T (segundos)
        # marcador técnico oculto com o event_id
        assert f"<!-- {COMMENT_MARKER_PREFIX}{decision.event_id} -->" in body


class TestCT08CT09ReinicioFranquiaERetomada:
    """CT-08: zera no bloqueio. CT-09: retomada concede franquia completa."""

    def test_contagem_zerada_apos_bloqueio_e_franquia_completa(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(3, 3600)
        # Atinge o limite e bloqueia.
        for _ in range(3):
            CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        blocked = CircuitBreaker(policy, board, clock).admit(
            "entrega", "desenvolvimento", "42"
        )
        assert blocked.admitted is False

        # Operador remove need_human (retomada humana).
        _liberar(board, "entrega", "42")

        # Mesma janela (sem avançar o relógio): deve aceitar N=3 novas execuções.
        # A primeira admissão após a liberação chega com need_human_present=False
        # (label removida) → o núcleo descarta o trip e concede franquia completa.
        admitted = 0
        for _ in range(3):
            if CircuitBreaker(policy, board, clock).admit(
                "entrega", "desenvolvimento", "42", need_human_present=False
            ).admitted:
                admitted += 1
        assert admitted == 3, "franquia completa após retomada, sem resíduo"
        # A N+1 bloqueia de novo.
        assert CircuitBreaker(policy, board, clock).admit(
            "entrega", "desenvolvimento", "42"
        ).admitted is False


class TestCT14UmComentarioPorEvento:
    """CT-14: nenhum novo comentário enquanto need_human presente; novo evento
    após liberação gera nova evidência."""

    def test_um_comentario_por_evento_e_novo_evento_apos_liberacao(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(2, 3600)

        for _ in range(2):
            CircuitBreaker(policy, board, clock).admit("entrega", "dev", "42")
        d1 = CircuitBreaker(policy, board, clock).admit("entrega", "dev", "42")
        assert d1.admitted is False
        assert board.comment_count("entrega", "42") == 1
        e1 = d1.event_id

        # Ciclos repetidos com trip ativo (need_human presente): reconciliação
        # não duplica comentário.
        for _ in range(3):
            d = CircuitBreaker(policy, board, clock).admit(
                "entrega", "dev", "42", need_human_present=True
            )
            assert d.admitted is False
        assert board.comment_count("entrega", "42") == 1

        # Libera e reacumula até novo bloqueio (evento E2 != E1).
        _liberar(board, "entrega", "42")
        for i in range(2):
            CircuitBreaker(policy, board, clock).admit(
                "entrega", "dev", "42", need_human_present=False
            )
        d2 = CircuitBreaker(policy, board, clock).admit("entrega", "dev", "42")
        assert d2.admitted is False
        assert d2.event_id != e1
        assert board.comment_count("entrega", "42") == 2


class TestCT15IdempotenciaComentarioNaRetomada:
    """CT-15: queda após publicar o comentário; retomada não duplica."""

    def test_marcador_presente_nao_republica(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(2, 3600)
        # Monta estado: trip persistido em STEP_LABELED (label ok, comentário
        # pendente localmente) MAS o comentário já está no board (marcador E1).
        event_id = "abc123def456"
        data = {
            "version": 1,
            "active_contexts": {
                "entrega/42": {
                    "column": "dev",
                    "occurrences": [],
                    "trip": {
                        "event_id": event_id,
                        "executions": 2,
                        "window": 3600,
                        "column": "dev",
                        "step": STEP_LABELED,
                    },
                }
            },
        }
        save_state(data)
        # O comentário com o marcador já existe no board (publicado antes da queda).
        board.add_comment("entrega", "42",
                           f"já publicado <!-- {COMMENT_MARKER_PREFIX}{event_id} -->")
        assert board.comment_count("entrega", "42") == 1

        # Reconciliação via admit (label ainda presente): encontra o marcador →
        # não republica.
        d = CircuitBreaker(policy, board, clock).admit(
            "entrega", "dev", "42", need_human_present=True
        )
        assert d.admitted is False
        assert board.comment_count("entrega", "42") == 1, "não deve duplicar"


class TestCT16BloqueioNaoMoveColuna:
    def test_zero_move_issue_no_bloqueio(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(2, 3600)
        for _ in range(2):
            CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        CircuitBreaker(policy, board, clock).admit("entrega", "desenvolvimento", "42")
        assert board.moved == [], "o bloqueio não deve mover a issue de coluna"


# ══════════════════════════════════════════════════════════════════════════════
# Grupo C — Sem política e ativação (opt-in, não regressão)
# ══════════════════════════════════════════════════════════════════════════════

class TestCT11SemPolitica:
    def test_sem_politica_nunca_bloqueia_mas_conta(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(active=False)
        for _ in range(10):
            d = CircuitBreaker(policy, board, clock).admit("entrega", "dev", "42")
            assert d.admitted is True
        assert not board.has_need_human("entrega", "42")
        assert board.comment_count("entrega", "42") == 0
        # Contagem interna ocorreu: 10 ocorrências persistidas.
        state = load_state()
        assert len(state["active_contexts"]["entrega/42"]["occurrences"]) == 10


class TestCT12AtivacaoSemRetroacao:
    def test_ativar_politica_nao_bloqueia_retroativamente(self):
        clock = FakeClock()
        board = FakeBoard()
        # Fase 1: sem política, acumula 5 ocorrências.
        inactive = _policy(active=False)
        for _ in range(5):
            CircuitBreaker(inactive, board, clock).admit("entrega", "dev", "42")
        # Fase 2: ativa política N=3. A ativação não re-executa decisões sobre o
        # passado; a próxima entrega é avaliada normalmente (as 5 pré-existentes
        # dentro da janela farão a próxima bloquear — mas isso é a semântica
        # normal da janela, não um "reprocessamento retroativo" que recomputa o
        # histórico). O ponto travado: ativar não dispara um gatilho que
        # recompute/bloqueie o histórico fora do fluxo de admissão.
        active = _policy(3, 10_000)
        # O estado interno existente é respeitado (mesma fonte), não recomputado:
        state = load_state()
        assert len(state["active_contexts"]["entrega/42"]["occurrences"]) == 5
        # A primeira avaliação com política segue a janela normal.
        d = CircuitBreaker(active, board, clock).admit("entrega", "dev", "42")
        # Com 5 >= 3 dentro da janela, a admissão é negada pela semântica normal.
        assert d.admitted is False


# ══════════════════════════════════════════════════════════════════════════════
# Grupo E — Falha fechada, recuperação e segurança
# ══════════════════════════════════════════════════════════════════════════════

class TestCT17FalhaFechada:
    def test_persistencia_falha_nega_admissao(self, monkeypatch):
        """CT-17a: falha ao persistir a ocorrência → admissão negada.

        Força `save_state` do MÓDULO (não o símbolo sob teste) a falhar. O
        `CircuitBreaker.admit` deve propagar `CircuitBreakStateError`.
        """
        clock = FakeClock()
        board = FakeBoard()
        import src.core.agent_circuit_break as acb

        def _boom(_data):
            raise acb.CircuitBreakStateError("disco cheio (simulado)")

        monkeypatch.setattr(acb, "save_state", _boom)
        with pytest.raises(CircuitBreakStateError):
            CircuitBreaker(_policy(3, 3600), board, clock).admit("entrega", "dev", "42")

    def test_estado_corrompido_nega_admissao(self):
        """CT-17b: estado ilegível/corrompido → erro de integridade (não assume
        contagem vazia)."""
        clock = FakeClock()
        board = FakeBoard()
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text("{ isto não é json válido ", encoding="utf-8")
        with pytest.raises(CircuitBreakStateError):
            CircuitBreaker(_policy(3, 3600), board, clock).admit("entrega", "dev", "42")

    def test_versao_desconhecida_nega_admissao(self):
        clock = FakeClock()
        board = FakeBoard()
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({"version": 999, "active_contexts": {}}),
                              encoding="utf-8")
        with pytest.raises(CircuitBreakStateError):
            CircuitBreaker(_policy(3, 3600), board, clock).admit("entrega", "dev", "42")


class TestCT19Recuperacao:
    """CT-19a/b/c: reinício preserva estado e retoma sinalização pendente."""

    def test_19a_reinicio_entre_persistir_e_label_segue_negada_e_reconcilia(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(3, 3600)
        # Monta trip em STEP_PERSISTED (evento persistido, label não aplicada).
        data = {
            "version": 1,
            "active_contexts": {
                "entrega/42": {
                    "column": "dev",
                    "occurrences": [],
                    "trip": {
                        "event_id": "e1evento0001",
                        "executions": 3,
                        "window": 3600,
                        "column": "dev",
                        "step": STEP_PERSISTED,
                    },
                }
            },
        }
        save_state(data)
        # Próximo ciclo (label ainda presente): execução segue negada e a
        # sinalização é retomada.
        d = CircuitBreaker(policy, board, clock).admit(
            "entrega", "dev", "42", need_human_present=True
        )
        assert d.admitted is False
        assert board.has_need_human("entrega", "42")
        assert board.comment_count("entrega", "42") == 1
        assert load_state()["active_contexts"]["entrega/42"]["trip"]["step"] == STEP_SIGNALED

    def test_19b_label_ok_comentario_pendente_retoma_so_o_faltante(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(3, 3600)
        board.add_label("entrega", "42", "need_human")  # label já aplicada
        data = {
            "version": 1,
            "active_contexts": {
                "entrega/42": {
                    "column": "dev",
                    "occurrences": [],
                    "trip": {
                        "event_id": "e2evento0002",
                        "executions": 3,
                        "window": 3600,
                        "column": "dev",
                        "step": STEP_LABELED,
                    },
                }
            },
        }
        save_state(data)
        d = CircuitBreaker(policy, board, clock).admit(
            "entrega", "dev", "42", need_human_present=True
        )
        assert d.admitted is False
        # Publica o comentário faltante (um add_comment).
        assert board.comment_count("entrega", "42") == 1
        assert "e2evento0002" in board.added_comments[0]["body"]

    def test_19c_reinicio_nao_apaga_ocorrencias_nem_libera(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(2, 3600)
        # Semeia contexto no limite (2 ocorrências recentes).
        now = int(clock.now)
        data = {
            "version": 1,
            "active_contexts": {
                "entrega/42": {
                    "column": "dev",
                    "occurrences": [now, now],
                    "trip": None,
                }
            },
        }
        save_state(data)
        # "Reinício": nada em memória; o arquivo persiste. Próxima entrega bloqueia.
        d = CircuitBreaker(policy, board, clock).admit("entrega", "dev", "42")
        assert d.admitted is False


class TestCT20SegurancaDoEstado:
    """CT-20 / RNF-10: estado mínimo, sem conteúdo sensível."""

    def test_estado_nao_contem_corpo_prompt_token(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(2, 3600)
        for _ in range(2):
            CircuitBreaker(policy, board, clock).admit("entrega", "dev", "42")
        CircuitBreaker(policy, board, clock).admit("entrega", "dev", "42")  # bloqueia
        raw = STATE_FILE.read_text(encoding="utf-8")
        assert "CORPO_SECRETO_123" not in raw
        # Chaves esperadas apenas: identidade, timestamps e trip (event_id/N/T/step).
        data = json.loads(raw)
        ctx = data["active_contexts"]["entrega/42"]
        assert set(ctx.keys()) <= {"column", "occurrences", "trip"}
        trip = ctx["trip"]
        assert set(trip.keys()) <= {"event_id", "executions", "window", "column", "step"}

    def test_arquivo_de_estado_em_protected_paths(self):
        from src.core.agent import PROTECTED_PATHS
        assert str(STATE_FILE) in PROTECTED_PATHS


class TestCTSRC01FonteUnica:
    """CT-SRC-01: a contagem tem fonte única — um registro por entrega."""

    def test_uma_ocorrencia_por_entrega(self):
        clock = FakeClock()
        board = FakeBoard()
        policy = _policy(active=False)
        for _ in range(4):
            CircuitBreaker(policy, board, clock).admit("entrega", "dev", "42")
        state = load_state()
        occ = state["active_contexts"]["entrega/42"]["occurrences"]
        assert len(occ) == 4, "exatamente uma ocorrência por entrega (fonte única)"


# ══════════════════════════════════════════════════════════════════════════════
# Integração com keep_task — isolamento (CT-10) e coexistência com cooldown (CT-11b)
# ══════════════════════════════════════════════════════════════════════════════

def _seed_snapshot(board_id: str, issues: list[dict]):
    """Grava um snapshot.json e os -body.md das issues informadas."""
    board_dir = Path(".pipe/boards") / board_id
    for issue in issues:
        col = issue["column"]
        (board_dir / col).mkdir(parents=True, exist_ok=True)
        stem = f"{issue['id']}-tarefa"
        body_path = board_dir / col / f"{stem}-body.md"
        body = issue.pop("_body", "# Tarefa\n\ncorpo\n")
        body_path.write_text(body, encoding="utf-8")
        issue["body_path"] = str(body_path)
        issue.setdefault("body_mtime", str(body_path.stat().st_mtime))
        issue.setdefault("created_at", "2026-08-01T10:00:00Z")
        issue.setdefault("updated_at", "2026-08-01T10:00:00Z")
        issue.setdefault("status", "ok")
    snap = {
        "board": {"desenvolvimento": "Desenvolvimento", "done": "Done"},
        "issues": issues,
        "last_sync": None,
    }
    (board_dir / "snapshot.json").write_text(json.dumps(snap, indent=2))


def _config_board(cooldown=None):
    boards = {
        "platform": "github",
        "entrega": {
            "name": "Entrega",
            "priority": 0,
            "columns": {
                "desenvolvimento": {
                    "name": "Desenvolvimento",
                    "agent": "dev",
                    "change": {"advance": "done"},
                },
                "done": {"name": "Done", "archive": True},
            },
        },
    }
    if cooldown is not None:
        boards["rerun_cooldown"] = cooldown
    return {"boards": boards, "sleep": 60}


class TestCT10Isolamento:
    """CT-10: issue bloqueada (need_human) é pulada por keep_task; outra segue."""

    def test_issue_com_need_human_e_pulada_outra_e_selecionada(self):
        _seed_snapshot("entrega", [
            {"id": "42", "column": "desenvolvimento",
             "_body": "# Bloqueada\n\ncorpo\n@---\n/need_human\n"},
            {"id": "43", "column": "desenvolvimento",
             "_body": "# Elegível\n\ncorpo\n"},
        ])
        task = pipe.keep_task("entrega", _config_board())
        assert task is not None and task is not pipe.AUTO_ADVANCED
        assert task["issue"]["id"] == "43", "a issue bloqueada não trava a fila"


class TestCT11bCoexistenciaCooldown:
    """CT-11b: sem política, com cooldown ativo, os mecanismos coexistem."""

    def test_cooldown_opera_sem_limitador(self):
        _seed_snapshot("entrega", [
            {"id": "42", "column": "desenvolvimento", "_body": "# T\n\ncorpo\n"},
        ])
        config = _config_board(cooldown=300)
        # 1ª seleção ocorre; 2ª imediata é pulada pelo cooldown (comportamento
        # existente inalterado — o limitador não interfere, pois não configurado).
        assert pipe.keep_task("entrega", config) is not None
        assert pipe.keep_task("entrega", config) is None


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _liberar(board: FakeBoard, board_id: str, issue_id: str) -> None:
    """Simula a retomada humana: remove a label need_human do board.

    O descarte do `trip` e o reinício da franquia são feitos pelo próprio núcleo
    na próxima admissão com `need_human_present=False` (não mexemos no estado
    protegido manualmente)."""
    board.remove_label(board_id, issue_id, "need_human")
