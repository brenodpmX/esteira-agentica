"""Adapter kiro-cli - execução de agentes via kiro-cli."""

import json
import os
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.core.agent import AgentPort, AgentParams
from src.core.log import log
from src.core.session import SessionIndex
from src.core.context_generator import STEERING_FILE
from src.core.execution_record import Consumo
from src.core.execution import (
    ExecutionResult, SUCEDIDO, FALHA, UNKNOWN_OUTCOME, DEFINITE_NOT_STARTED,
)

_tz = timezone(timedelta(hours=-3))

# Timeout máximo de uma execução do agente (segundos).
_TIMEOUT = 3600

# Remove sequências ANSI/escape do output capturado.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\].*?(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")

# UUID de sessão do kiro-cli (formato canônico 8-4-4-4-12).
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# Request ID do servidor (preservado para auditoria — ADR #217 §2).
_REQUEST_ID = re.compile(r"[Rr]equest[ _][Ii][Dd]:\s*([^\s|]+)")

# Marcador emitido por _run quando o subprocesso NÃO iniciou (FileNotFoundError:
# kiro-cli ausente no PATH). É a ÚNICA evidência estrutural de não-inicialização
# comprovada mecanicamente (DEFINITE_NOT_STARTED) — único caso com retry inline.
_NOT_STARTED_MARKER = "[ERRO] kiro-cli não encontrado no PATH"

# Trechos que indicam interrupção transitória AMBÍGUA (UNKNOWN_OUTCOME): o
# subprocesso iniciou e pode ter aplicado efeitos antes de abortar. Fail-closed
# (sem retry inline). O timeout entra por marcador próprio (ver _classify).
_AMBIGUOUS_HINTS = (
    "dispatch failure",
    "InternalServerError",
)


class KiroCliAgent(AgentPort):
    """Adapter de agente para kiro-cli."""

    def execute(self, params: AgentParams) -> ExecutionResult:
        """Executa o agente e retorna o resultado CLASSIFICADO (issue #303).

        A classificação segue a ADR #217 (máquina de estados da seção 5):
        SUCEDIDO / FALHA / UNKNOWN_OUTCOME (ambíguo, fail-closed) /
        DEFINITE_NOT_STARTED (não-inicialização comprovada — único caso com
        retry inline, decidido por call_agent).

        Observabilidade (CT-13): toda falha/ambiguidade registra no log a causa
        real E a origem (canal estruturado) — nunca a narrativa do agente. O
        UNKNOWN_OUTCOME é logado de forma acionável, distinto de sucesso e de
        falha definitiva, com as evidências preservadas (output/request
        ID/causa/session_id).

        Mantém a interface antiga (callers que ignoram o retorno seguem válidos)
        e o contrato de logging da suíte congelada.
        """
        log_path = self._create_log(params)
        # Consumo medido nesta execução (preenchido por _run ao parsear o
        # stream-json). Reset por execução para não vazar valor de uma anterior.
        self._last_consumo = None
        title_part = f" {params.title}" if params.title else ""
        col_part = f" [{params.col_name}]" if params.col_name else ""
        log.info("Kiro", f"[{params.board_id}]{col_part} #{params.issue_id}{title_part}"
                          f" - By: {params.agent_name} - {log_path}")
        try:
            work_dir = Path(params.work_dir)
            if not work_dir.is_dir():
                raise FileNotFoundError(
                    f"Diretório de trabalho (repo) não encontrado: {work_dir}"
                )
            output = self._run(params, work_dir)
            self._append_log(log_path, self._strip_ansi(output) + "\n")

            result = self._classify(params, output)
            result.consumo = self._last_consumo
            self._log_outcome(params, result, log_path)
            return result
        except Exception as e:
            self._append_log(log_path, f"\n**ERRO**: {e}\n")
            log.error("Kiro", f"[{params.board_id}] #{params.issue_id} "
                      f"erro: {self._last_meaningful_line(str(e))}",
                      log=str(log_path))
            raise

    def _classify(self, params: AgentParams, output: str) -> ExecutionResult:
        """Classifica o output em uma das classes da ADR #217 (seção 5).

        Ordem de precedência:
        1. DEFINITE_NOT_STARTED — marcador de não-inicialização comprovada
           (kiro-cli ausente no PATH): nenhum efeito pôde ter sido aplicado.
        2. UNKNOWN_OUTCOME — interrupção transitória ambígua: `[TIMEOUT]` ou
           `dispatch failure`/`InternalServerError` (o subprocesso iniciou e
           pode ter aplicado efeitos). Fail-closed.
        3. FALHA — demais falhas por canal estruturado (exit-code != 0, saída
           de erro). Falha definitiva.
        4. SUCEDIDO — nenhum sinal estruturado de falha.
        """
        clean = self._strip_ansi(output)
        session_id = self._current_session(params)
        request_id = self._extract_request_id(clean)

        # 1. Não-inicialização comprovada mecanicamente.
        if _NOT_STARTED_MARKER in clean:
            return ExecutionResult(
                classe=DEFINITE_NOT_STARTED, output=output,
                causa=_NOT_STARTED_MARKER, origem="erro interno",
                session_id=session_id, request_id=request_id,
            )

        error = self._detect_failure(output)
        if error is None:
            return ExecutionResult(
                classe=SUCEDIDO, output=output,
                session_id=session_id, request_id=request_id,
            )

        origem = self._structured_channel(output)

        # 2. Interrupção transitória ambígua (fail-closed).
        if "[TIMEOUT]" in clean:
            return ExecutionResult(
                classe=UNKNOWN_OUTCOME, output=output, causa=error,
                origem="timeout", session_id=session_id, request_id=request_id,
            )
        if any(hint in clean for hint in _AMBIGUOUS_HINTS):
            return ExecutionResult(
                classe=UNKNOWN_OUTCOME, output=output, causa=error,
                origem="dispatch failure", session_id=session_id,
                request_id=request_id,
            )

        # 3. Falha definitiva por canal estruturado.
        return ExecutionResult(
            classe=FALHA, output=output, causa=error, origem=origem,
            session_id=session_id, request_id=request_id,
        )

    def _log_outcome(self, params: AgentParams, result: ExecutionResult,
                     log_path: Path) -> None:
        """Observabilidade (CT-13): registra o resultado com causa + origem.

        - SUCEDIDO: info de conclusão (contrato da suíte congelada preservado).
        - FALHA: error com causa real + origem do canal estruturado.
        - UNKNOWN_OUTCOME: error ACIONÁVEL, distinto de sucesso e de falha
          definitiva, com evidências preservadas (request ID/session_id).
        - DEFINITE_NOT_STARTED: error com causa + origem (o retry é decidido
          por call_agent, que loga as tentativas).
        """
        prefix = f"[{params.board_id}] #{params.issue_id}"
        if result.classe == SUCEDIDO:
            log.info("Kiro", f"{prefix} execução concluída: "
                     f"{self._last_meaningful_line(result.output)}",
                     log=str(log_path))
            return
        if result.classe == UNKNOWN_OUTCOME:
            log.error(
                "Kiro",
                f"{prefix} resultado ambíguo (UNKNOWN_OUTCOME) - fail-closed: "
                f"{result.causa}",
                log=str(log_path), classe=UNKNOWN_OUTCOME, origem=result.origem,
                causa=result.causa, request_id=result.request_id,
                session_id=result.session_id,
            )
            return
        # FALHA e DEFINITE_NOT_STARTED.
        log.error("Kiro", f"{prefix} falhou: {result.causa}",
                  log=str(log_path), classe=result.classe, origem=result.origem,
                  causa=result.causa)

    def _extract_request_id(self, clean: str) -> str | None:
        """Extrai o request ID do servidor do output, se presente."""
        m = _REQUEST_ID.search(clean)
        return m.group(1) if m else None

    def _current_session(self, params: AgentParams) -> str | None:
        """Lê o session_id persistido para (issue, coluna), se houver.

        _run grava no índice após a chamada; aqui apenas lemos para preservar
        a evidência no ExecutionResult (ADR #217 §2). Falhas de leitura do
        índice não devem derrubar a classificação.
        """
        try:
            return SessionIndex().get(params.issue_id, params.col_id)
        except Exception:
            return None

    def _run(self, params: AgentParams, work_dir: Path) -> str:
        """Executa kiro-cli chat em modo headless DENTRO de repo/<repo_id>.

        O cwd do processo é o clone do repositório alvo, garantindo que toda
        operação git/arquivos do agente fique confinada ao repo — nunca no
        diretório da esteira.

        Sessão: se houver um session_id conhecido para (board, issue, agente) e
        ele ainda existir no kiro-cli, retoma via `--resume-id` (o agente
        recupera o raciocínio da execução anterior). Após executar, captura o id
        da sessão (mais recente do cwd) e grava no índice. A esteira não gerencia
        o ciclo de vida das sessões — o kiro-cli cuida disso.
        """
        # Sem cor nos logs do kiro-cli (facilita parsing/limpeza).
        # KIRO_HOME: aponta o kiro-cli para o diretório .kiro da esteira, onde
        # vive o steering (.kiro/steering/esteira.md). O default agent do
        # kiro-cli auto-carrega o steering resolvido por KIRO_HOME — não usamos
        # mais `--agent` (Caminho B / P1.1(b)).
        #
        # STEERING_FILE é relativo no módulo (.kiro/steering/esteira.md), por
        # isso usamos .resolve() para obter o path absoluto antes de subir aos
        # diretórios pais até .kiro. Sem .resolve(), .parent em path relativo
        # apontaria para o cwd do subprocess (o repo), lugar errado.
        kiro_home = str(STEERING_FILE.resolve().parent.parent)  # <esteira>/.kiro
        env = {**os.environ, "KIRO_LOG_NO_COLOR": "1", "KIRO_HOME": kiro_home}

        cmd = [
            "kiro-cli", "chat",
            "--no-interactive",
            "--trust-all-tools",
            # Formato estruturado (JSON Lines / eventos ACP): única forma, desde
            # o kiro-cli 2.27.x, de obter o consumo (meteringUsage) por execução.
            # O modo texto deixou de imprimir a linha-resumo de créditos/tempo.
            "--output-format", "stream-json",
        ]
        if params.model:
            cmd += ["--model", params.model]

        # O contexto de sistema é carregado como steering (default agent) via
        # KIRO_HOME — não passamos `--agent`.

        # Retoma a sessão anterior se ainda existir.
        # Chave por (issue, coluna) — E10 (não depende do agente).
        index = SessionIndex()
        known_id = index.get(params.issue_id, params.col_id)
        resuming = bool(known_id and self._session_exists(known_id, work_dir, env))
        if resuming:
            cmd += ["--resume-id", known_id]
            log.info("Kiro", f"[{params.board_id}] #{params.issue_id} "
                     f"retomando sessão {known_id} (continuação)",
                     session_id=known_id, col_id=params.col_id)

        # GUARDA anti-delírio (E10): só usa o prompt de continuação quando a
        # sessão foi CONFIRMADA (known_id + _session_exists). Sem sessão →
        # prompt de execução completo.
        cmd.append(self._compose_input(params, resuming=resuming))

        try:
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                env=env,
            )
        except subprocess.TimeoutExpired:
            self._last_consumo = Consumo.indisponivel(origem=params.platform)
            return f"[TIMEOUT] Agente excedeu {_TIMEOUT}s"
        except FileNotFoundError:
            self._last_consumo = Consumo.indisponivel(origem=params.platform)
            return "[ERRO] kiro-cli não encontrado no PATH"

        # Captura o id da sessão recém-usada (mais recente do cwd) e persiste.
        # O loop da esteira é sequencial, então a sessão do topo é a desta
        # execução (mesma quando retomada por id, nova quando criada agora).
        current_id = self._latest_session_id(work_dir, env)
        if current_id:
            index.set(params.issue_id, params.col_id, current_id)

        # Reconstrói um transcript legível a partir dos eventos ACP (stdout) e
        # extrai o consumo (meteringUsage). O stderr é anexado cru: pode conter
        # diagnósticos/erros de transporte cujos trechos a classificação usa.
        transcript, valor, unidade = self._parse_stream_json(result.stdout or "")
        stderr = (result.stderr or "").strip()
        if stderr:
            transcript = f"{transcript}\n{stderr}" if transcript else stderr

        if valor is not None:
            self._last_consumo = Consumo.reportado(
                valor, unidade or "credit", params.platform
            )
        else:
            self._last_consumo = Consumo.indisponivel(origem=params.platform)

        output = transcript
        if result.returncode != 0:
            output += f"\n[exit-code: {result.returncode}]"
        return output

    def _parse_stream_json(self, raw: str) -> tuple[str, float | None, str | None]:
        """Converte os eventos ACP (JSON Lines) em transcript + consumo.

        Retorna ``(transcript, valor_consumo, unidade_consumo)``:
        - ``transcript``: reconstrução legível (prosa do agente, linhas
          ``[tool] ...``, erros de ``runFinished``), encerrada por uma linha-
          resumo ``▸ Credits: X • Time: Ys`` quando há medição — restaurando o
          resumo que o kiro-cli deixou de imprimir no modo texto.
        - ``valor_consumo``/``unidade_consumo``: soma do ``meteringUsage`` do
          metadata final do turno (``None`` quando a ferramenta não reportou).

        Robustez: linhas não-JSON são preservadas cruas (nada é perdido); tipos
        de evento desconhecidos (ex.: erro de transporte) são anexados crus para
        que a classificação por canal estruturado continue enxergando os
        trechos relevantes. Degrada para ``("", None, None)`` em entrada vazia.
        """
        valor: float | None = None
        unidade: str | None = None
        turn_ms: int | None = None
        status: str | None = None
        stop_reason: str | None = None
        final_text: str | None = None

        lines: list[str] = []
        msg_buf: list[str] = []

        def _flush_msg() -> None:
            if msg_buf:
                texto = "".join(msg_buf).strip()
                if texto:
                    lines.append(texto)
                msg_buf.clear()

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                _flush_msg()
                lines.append(line)  # preserva saída não estruturada
                continue
            if not isinstance(evt, dict):
                continue
            etype = evt.get("type")
            data = evt.get("data") or {}

            if etype == "metadata":
                mu = data.get("meteringUsage")
                if isinstance(mu, list) and mu:
                    total = 0.0
                    uni = None
                    for seg in mu:
                        if not isinstance(seg, dict):
                            continue
                        try:
                            total += float(seg.get("value") or 0)
                        except (TypeError, ValueError):
                            pass
                        uni = uni or seg.get("unit")
                    valor = total
                    unidade = uni
                if data.get("turnDurationMs") is not None:
                    turn_ms = data.get("turnDurationMs")
                continue

            if etype == "sessionUpdate":
                upd = data.get("update") or {}
                kind = upd.get("sessionUpdate")
                if kind == "agent_message_chunk":
                    txt = (upd.get("content") or {}).get("text")
                    if txt:
                        msg_buf.append(txt)
                elif kind == "tool_call":
                    _flush_msg()
                    title = upd.get("title")
                    if title:
                        lines.append(f"[tool] {title}")
                elif kind == "tool_call_update":
                    st = upd.get("status")
                    if st:
                        lines.append(f"[tool] status: {str(st).capitalize()}")
                # agent_thought_chunk (raciocínio) é omitido do transcript.
                continue

            if etype == "runFinished":
                status = data.get("status")
                stop_reason = data.get("stopReason")
                final_text = data.get("finalText")
                continue

            if etype == "runStarted":
                continue

            # Evento desconhecido (ex.: erro de transporte): preserva cru para a
            # classificação por canal estruturado.
            _flush_msg()
            lines.append(line)

        _flush_msg()

        # Falha não-sucesso: anexa evidência acionável (status/causa) preservando
        # trechos reconhecidos pelos _ERROR_HINTS/_AMBIGUOUS_HINTS.
        if status is not None and status != "success":
            detalhe = f"[ERRO] runFinished status={status}"
            if stop_reason:
                detalhe += f" stopReason={stop_reason}"
            if final_text:
                detalhe += f": {final_text}"
            lines.append(detalhe)

        # Linha-resumo final (restaura o antigo "▸ Credits: X • Time: Ys").
        if valor is not None:
            resumo = f"▸ Credits: {valor:.2f}"
            if turn_ms is not None:
                secs = int(turn_ms // 1000)
                resumo += f" • Time: {secs // 60}m {secs % 60}s"
            lines.append(resumo)

        return "\n".join(lines), valor, unidade

    def _list_session_ids(self, work_dir: Path, env: dict) -> list[str]:
        """Lista os session_ids do cwd (mais recente primeiro) via kiro-cli."""
        try:
            result = subprocess.run(
                ["kiro-cli", "chat", "--list-sessions"],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        if result.returncode != 0:
            return []
        return _UUID.findall(self._strip_ansi(result.stdout or ""))

    def _session_exists(self, session_id: str, work_dir: Path, env: dict) -> bool:
        """True se o session_id ainda existe no kiro-cli para este cwd."""
        return session_id in self._list_session_ids(work_dir, env)

    def _latest_session_id(self, work_dir: Path, env: dict) -> str | None:
        """Retorna o session_id mais recente do cwd (topo da listagem)."""
        ids = self._list_session_ids(work_dir, env)
        return ids[0] if ids else None

    def _compose_input(self, params: AgentParams, resuming: bool = False) -> str:
        """Monta o input do agente.

        Prioridade:
        1. remediation_prompt (E4): quando definido, contém os erros de sync.
           - COM sessão confirmada (resuming): envia só os erros — a sessão já
             carrega a persona e o contexto da tarefa.
           - SEM sessão (kiro-cli descartou a sessão): anexa persona + prompt de
             execução completo ANTES dos erros, para o agente não ficar sem
             contexto (mesma guarda anti-delírio da continuação — E10).
        2. resuming + continuation_prompt (E10): continuação em sessão confirmada.
        3. persona + prompt de execução completo (fallback anti-delírio).
        """
        if params.remediation_prompt and params.remediation_prompt.strip():
            rem = params.remediation_prompt.strip()
            if resuming:
                return rem
            # Sessão ausente: sem o fio anterior, o agente precisa do contexto
            # completo (persona + tarefa) além dos erros a corrigir.
            return f"{self._full_input(params)}\n\n---\n\n{rem}"
        if resuming and params.continuation_prompt and params.continuation_prompt.strip():
            return params.continuation_prompt.strip()
        return self._full_input(params)

    def _full_input(self, params: AgentParams) -> str:
        """Persona (se houver) + prompt de execução completo."""
        if params.context and params.context.strip():
            return f"{params.context.strip()}\n\n---\n\n{params.prompt}"
        return params.prompt

    def _strip_ansi(self, text: str) -> str:
        """Remove códigos ANSI do output."""
        return _ANSI.sub("", text)

    def _last_meaningful_line(self, output: str) -> str:
        """Retorna a última linha não-vazia do output (limpa ANSI).

        O kiro-cli tipicamente imprime um resumo na última linha com tempo
        e tokens consumidos. Em caso de erro, a última linha contém a mensagem.
        """
        clean = self._strip_ansi(output)
        lines = [l.strip() for l in clean.strip().splitlines() if l.strip()]
        return lines[-1] if lines else "(sem output)"

    # Marcadores ESTRUTURAIS da ferramenta de execução (kiro-cli / adapter) que
    # classificam uma execução como falha. #303: a classificação considera
    # APENAS canais estruturados — a narrativa (texto livre) do agente NUNCA
    # classifica, pelo mesmo motivo que a detecção de rate limit não escaneia o
    # corpo textual da resposta (evita falso positivo quando o agente apenas
    # CITA um termo de erro na sua prosa). Cada marcador é emitido pelo próprio
    # _run (exit-code/timeout/erro interno) ou pela ferramenta como seção de
    # erro reconhecível por marcador — nunca inferido de prosa.
    #
    # Mapeia marcador estrutural -> origem (canal) para observabilidade: o log
    # registra qual canal classificou a falha (CT-13), nunca a narrativa.
    _STRUCTURED_MARKERS: tuple[tuple[str, str], ...] = (
        ("[TIMEOUT]", "timeout"),
        ("[ERRO]", "erro interno"),
        ("[exit-code:", "exit-code"),
    )

    # Trechos que, QUANDO já há sinal estrutural presente, ajudam a extrair a
    # linha com a causa real dentro do output (não disparam falha sozinhos).
    _ERROR_HINTS = (
        "[TIMEOUT]",
        "[ERRO]",
        "[exit-code:",
        "dispatch failure",
        "InternalServerError",
        "temporarily unavailable",
        "unavailable",
        "Kiro is having trouble responding",
        "Request ID:",
        "request_id:",
        "error:",
        "Error:",
        "ERRO",
        "Location:",
    )

    def _structured_channel(self, output: str) -> str | None:
        """Retorna a ORIGEM (canal estruturado) que classifica a falha, ou None.

        Só considera marcadores estruturais (_STRUCTURED_MARKERS). A narrativa
        do agente nunca é origem. Usado pela observabilidade (CT-13) e por
        _detect_failure. Para exit-code, só classifica falha se N != 0.
        """
        clean = self._strip_ansi(output)
        for marker, origin in self._STRUCTURED_MARKERS:
            if marker not in clean:
                continue
            if marker == "[exit-code:":
                # Só é falha se o código for diferente de zero.
                if not self._nonzero_exit_code(clean):
                    continue
            return origin
        return None

    @staticmethod
    def _nonzero_exit_code(clean: str) -> bool:
        """True se houver um marcador [exit-code: N] com N != 0."""
        for m in re.finditer(r"\[exit-code:\s*(-?\d+)\]", clean):
            if int(m.group(1)) != 0:
                return True
        return False

    def _detect_failure(self, output: str) -> str | None:
        """Detecta falha na execução do kiro-cli SÓ por canais estruturados.

        #303: a classificação considera apenas os canais estruturados da
        ferramenta — código de saída != 0 (`[exit-code: N]`), marcador de
        timeout (`[TIMEOUT]`), marcador de erro interno (`[ERRO]`) e saída de
        erro estruturada reconhecível por marcador. A narrativa (texto livre)
        do agente NUNCA classifica: um agente pode legitimamente CITAR na sua
        prosa frases como "Kiro is having trouble responding" ou
        "InternalServerError" numa execução bem-sucedida — isso não é falha.
        (Mesmo princípio da detecção de rate limit, que não escaneia o corpo.)

        Ausência de sinal estruturado = SUCESSO (retorna None).

        Retorna uma mensagem de uma linha com a causa real extraída dos canais
        estruturados (linhas relevantes unidas por ' | '), ou None se não houve
        falha. O output completo continua gravado no arquivo de log da issue.
        """
        clean = self._strip_ansi(output)
        non_empty = [l.strip() for l in clean.splitlines() if l.strip()]
        if not non_empty:
            return None

        # Só classifica falha quando há um canal estruturado presente.
        if self._structured_channel(output) is None:
            return None

        relevant: list[str] = []
        for line in non_empty:
            if any(hint in line for hint in self._ERROR_HINTS):
                if line not in relevant:
                    relevant.append(line)

        # Falhou, mas sem padrão conhecido: usa as últimas linhas como contexto.
        if not relevant:
            relevant = non_empty[-3:]

        return " | ".join(relevant)

    def _append_log(self, log_path: Path, content: str) -> None:
        """Adiciona conteúdo ao final do log."""
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(content)

    def _create_log(self, params: AgentParams) -> Path:
        """Cria o arquivo de log de execução em markdown."""
        issue_dir = log.log_dir / str(params.issue_id)
        issue_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(_tz).strftime("%Y-%m-%d_%H-%M-%S")
        log_file = issue_dir / f"{timestamp}.md"

        content = self._build_log(params)
        log_file.write_text(content, encoding="utf-8")
        return log_file

    def _build_log(self, params: AgentParams) -> str:
        """Monta o conteúdo do log em markdown."""
        lines = []

        # Parâmetros
        lines.append("## Parâmetros")
        lines.append("")
        lines.append(f"- **plataforma**: {params.platform}")
        lines.append(f"- **agente**: {params.agent_name}")
        lines.append(f"- **model**: {params.model}")
        lines.append(f"- **board**: {params.board_id}")
        lines.append(f"- **coluna**: {params.col_id}")
        lines.append(f"- **issue**: #{params.issue_id}")
        if params.participation_intent:
            lines.append(f"- **participation_intent**: {params.participation_intent}")
        if params.origin_board:
            lines.append(f"- **origin_board**: {params.origin_board}")
        if params.repo_id:
            lines.append(f"- **repo**: {params.repo_id}")
        if params.work_dir:
            lines.append(f"- **work_dir**: {params.work_dir}")
        lines.append("")

        # Persona (P1.4): quando injetada via AgentParams.context, registra no
        # log para rastrear qual papel o agente assumiu nesta execução.
        if params.context and params.context.strip():
            lines.append("---")
            lines.append("")
            lines.append("## Persona")
            lines.append("")
            lines.append(params.context.strip())
            lines.append("")

        # Prompt
        lines.append("---")
        lines.append("")
        lines.append("## Prompt")
        lines.append("")
        lines.append(params.prompt)
        lines.append("")

        # Chat (preenchido durante execução)
        lines.append("---")
        lines.append("")
        lines.append("## Chat")
        lines.append("")

        return "\n".join(lines)
