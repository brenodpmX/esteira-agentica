"""Adapter kiro-cli - execução de agentes via kiro-cli."""

import os
import re
import subprocess
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path

from src.core.agent import AgentPort, AgentParams
from src.core.log import log
from src.core.session import SessionIndex
from src.core.context_generator import CONTEXT_FILE, AGENT_FILE

_tz = timezone(timedelta(hours=-3))

# Timeout máximo de uma execução do agente (segundos).
_TIMEOUT = 3600

# Remove sequências ANSI/escape do output capturado.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\].*?(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")

# UUID de sessão do kiro-cli (formato canônico 8-4-4-4-12).
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# request_id / Request ID do bloco de erro estruturado do kiro-cli. A vírgula e
# o espaço ficam fora da captura porque o padrão real é
# "request_id: <id>,\n      error: dispatch failure ...".
_REQUEST_ID = re.compile(
    r"request[_ ]?id\s*[:=]\s*([0-9A-Za-z][0-9A-Za-z._-]*)", re.IGNORECASE
)

# ══════════════════════════════════════════════════════════════════════════════
# Política fail-closed para abort transitório do kiro-cli
# ══════════════════════════════════════════════════════════════════════════════
# Definição normativa: doc/architecture/retry-kiro-cli/idempotencia.md
# (ADR aceita na resolução do débito #217; implementação na issue #208).
#
# O kiro-cli aborta o turno no meio (`dispatch failure`, `InternalServerError`)
# sem rollback — bug upstream kirodotdev/Kiro#6065, fechado como "not planned".
# O abort pode ocorrer DEPOIS de o agente já ter feito `git commit`, `git push`
# ou movido os arquivos da issue de coluna (evidência: execução de #175 no
# incidente #203). Nem o output parcial nem o `--resume-id` provam ausência de
# efeitos: o stream pode quebrar entre o efeito e a recepção do evento.
#
# Logo, esses resultados são AMBÍGUOS e a política é fail-closed: uma única
# invocação do subprocesso por entrega, evidência preservada, nenhum
# retry/backoff inline. A reentrega ocorre pelo loop normal, depois da
# reconciliação de filesystem/git/board e respeitando `rerun_cooldown`.

# Invocações do `kiro-cli chat` permitidas por entrega ao agente.
_MAX_INVOCATIONS = 1

# Saída sintética do adapter quando o binário não está no PATH.
_KIRO_NOT_FOUND = "[ERRO] kiro-cli não encontrado no PATH"


class Outcome(str, Enum):
    """Estado terminal de uma execução do agente (ADR, seção 5).

    - ``SUCCEEDED``: execução concluída sem falha detectada.
    - ``DEFINITE_NOT_STARTED``: há evidência positiva e estruturada de que o
      subprocesso não chegou a executar. Único estado que admitiria retry.
    - ``UNKNOWN_OUTCOME``: resultado ambíguo (`dispatch failure`,
      `InternalServerError`, timeout ou qualquer falha sem prova de
      não-inicialização). Encerra a entrega sem retry inline.
    """

    SUCCEEDED = "SUCCEEDED"
    DEFINITE_NOT_STARTED = "DEFINITE_NOT_STARTED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


class SingleInvocationViolation(RuntimeError):
    """Tentativa de invocar o kiro-cli mais de uma vez na mesma entrega."""


class _DeliveryBudget:
    """Orçamento de invocações do `kiro-cli chat` em uma entrega ao agente.

    Existe para que a política deixe de ser "ausência de código de retry" e
    passe a ser uma restrição explícita: se alguém reintroduzir retry/backoff
    dentro de `_run` — por exemplo lendo apenas o título histórico da issue
    #208 —, a segunda invocação falha alto em vez de duplicar silenciosamente
    um commit, um push ou uma movimentação de coluna já aplicados.
    """

    max_calls = _MAX_INVOCATIONS

    def __init__(self) -> None:
        self.calls = 0

    def spend(self) -> None:
        if self.calls >= self.max_calls:
            raise SingleInvocationViolation(
                "política fail-closed: o kiro-cli pode ser invocado apenas "
                f"{self.max_calls}x por entrega — retry/backoff inline é "
                "proibido porque o abort pode ter ocorrido após efeitos "
                "colaterais já aplicados (ver "
                "doc/architecture/retry-kiro-cli/idempotencia.md)"
            )
        self.calls += 1


class KiroCliAgent(AgentPort):
    """Adapter de agente para kiro-cli."""

    def __init__(self) -> None:
        # Evidência da última entrega, para observabilidade e continuidade.
        self._last_session_id: str | None = None
        self._invocations = 0

    def execute(self, params: AgentParams) -> None:
        self._last_session_id = None
        self._invocations = 0
        log_path = self._create_log(params)
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
            output, returncode = self._run(params, work_dir)
            self._append_log(log_path, self._strip_ansi(output) + "\n")
            # O exit-code do kiro-cli nem sempre reflete a falha: erros de
            # modelo/servidor voltam como texto no output com exit 0. Sem esta
            # análise, uma execução quebrada era logada como "concluída".
            error = self._detect_failure(output, returncode)
            outcome = self._classify(output, returncode, error)
            request_id = self._extract_request_id(output)
            marker = self._ambiguous_marker(output) if error else None
            self._append_outcome(log_path, outcome, returncode, request_id,
                                 error, marker)
            if error:
                log.error("Kiro", f"[{params.board_id}] #{params.issue_id} "
                          f"falhou: {error}", log=str(log_path),
                          **self._evidence(outcome, request_id, marker))
            else:
                log.info("Kiro", f"[{params.board_id}] #{params.issue_id} "
                         f"execução concluída: {self._last_meaningful_line(output)}",
                         log=str(log_path))
        except Exception as e:
            # Exceção antes da invocação prova não-inicialização; depois dela, o
            # resultado é ambíguo (o subprocesso pode ter aplicado efeitos).
            outcome = (Outcome.DEFINITE_NOT_STARTED if self._invocations == 0
                       else Outcome.UNKNOWN_OUTCOME)
            self._append_log(log_path, f"\n**ERRO**: {e}\n")
            log.error("Kiro", f"[{params.board_id}] #{params.issue_id} "
                      f"erro: {self._last_meaningful_line(str(e))}",
                      log=str(log_path), **self._evidence(outcome, None))
            raise

    def _run(self, params: AgentParams, work_dir: Path) -> tuple[str, int | None]:
        """Executa kiro-cli chat em modo headless DENTRO de repo/<repo_id>.

        Retorna (output, returncode). returncode é None quando o processo não
        chegou a finalizar normalmente (TimeoutExpired, FileNotFoundError).

        O cwd do processo é o clone do repositório alvo, garantindo que toda
        operação git/arquivos do agente fique confinada ao repo — nunca no
        diretório da esteira.

        Sessão: se houver um session_id conhecido para (board, issue, agente) e
        ele ainda existir no kiro-cli, retoma via `--resume-id` (o agente
        recupera o raciocínio da execução anterior). Após executar, captura o id
        da sessão (mais recente do cwd) e grava no índice. A esteira não gerencia
        o ciclo de vida das sessões — o kiro-cli cuida disso.

        Política fail-closed (ADR doc/architecture/retry-kiro-cli/idempotencia.md):
        o subprocesso é invocado no máximo `_MAX_INVOCATIONS` vez por entrega.
        Não há retry nem backoff aqui — um abort transitório pode ter ocorrido
        depois de efeitos já aplicados (commit, push, movimentação de coluna) e
        reexecutar duplicaria esses efeitos. A nova tentativa é responsabilidade
        do loop, após reconciliar filesystem/git/board.
        """
        # Sem cor nos logs do kiro-cli (facilita parsing/limpeza).
        # KIRO_HOME: aponta o kiro-cli para o diretório .kiro da esteira.
        # O kiro-cli é executado com cwd=repo/<repo_id>, onde buscaria agentes
        # locais em repo/<repo_id>/.kiro/agents/ — diretório diferente do gerado
        # no startup. Com KIRO_HOME=<esteira>/.kiro, o kiro-cli encontra
        # <KIRO_HOME>/agents/pipe_context.json como agente global.
        #
        # AGENT_FILE é relativo no módulo (Path(".kiro/agents/pipe_context.json")),
        # por isso usamos .resolve() para obter o path absoluto antes de subir
        # ao diretório pai (.kiro). Sem .resolve(), .parent.parent em path relativo
        # resultaria em "." — que o subprocess resolveria contra seu próprio cwd
        # (o repo), apontando para o lugar errado.
        kiro_home = str(AGENT_FILE.resolve().parent.parent)  # <esteira>/.kiro
        env = {**os.environ, "KIRO_LOG_NO_COLOR": "1", "KIRO_HOME": kiro_home}

        cmd = [
            "kiro-cli", "chat",
            "--no-interactive",
            "--trust-all-tools",
        ]
        if params.model:
            cmd += ["--model", params.model]

        # Injeta o contexto do sistema via --agent (quando CONTEXT.md existe).
        # O arquivo .kiro/agents/pipe_context.json foi gerado pelo startup a
        # partir do pipe.yml e contém as instruções explícitas para o agente.
        if CONTEXT_FILE.exists():
            cmd += ["--agent", "pipe_context"]

        # Retoma a sessão anterior se ainda existir.
        index = SessionIndex()
        known_id = index.get(params.board_id, params.issue_id, params.agent_id)
        if known_id and self._session_exists(known_id, work_dir, env):
            cmd += ["--resume-id", known_id]
            self._last_session_id = known_id
            log.info("Kiro", f"[{params.board_id}] #{params.issue_id} "
                     f"retomando sessão {known_id}",
                     session_id=known_id, agent=params.agent_id)

        cmd.append(self._compose_input(params))

        # Uma única invocação por entrega — sem retry/backoff inline.
        budget = _DeliveryBudget()
        budget.spend()
        self._invocations = budget.calls
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
            # Timeout é UNKNOWN_OUTCOME: o processo pode ter produzido efeitos
            # antes de exceder o limite. A sessão é capturada para que a
            # reentrega pelo loop retome o raciocínio de onde parou.
            self._capture_session(index, params, work_dir, env)
            return f"[TIMEOUT] Agente excedeu {_TIMEOUT}s", None
        except FileNotFoundError:
            # kiro-cli ausente do PATH: evidência positiva de não-inicialização.
            # Nada executou, então não há sessão nova a capturar.
            return _KIRO_NOT_FOUND, None

        # Captura o id da sessão recém-usada (mais recente do cwd) e persiste.
        # O loop da esteira é sequencial, então a sessão do topo é a desta
        # execução (mesma quando retomada por id, nova quando criada agora).
        self._capture_session(index, params, work_dir, env)

        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            output += f"\n[exit-code: {result.returncode}]"
        return output, result.returncode

    def _capture_session(self, index: SessionIndex, params: AgentParams,
                         work_dir: Path, env: dict) -> None:
        """Persiste o session_id da execução recém-encerrada, se houver.

        Roda independentemente do resultado (sucesso, abort ou timeout): a
        continuidade do raciocínio é justamente o que permite a reentrega
        posterior retomar com `--resume-id`.
        """
        current_id = self._latest_session_id(work_dir, env)
        if current_id:
            self._last_session_id = current_id
            index.set(params.board_id, params.issue_id, params.agent_id, current_id)

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

    def _compose_input(self, params: AgentParams) -> str:
        """Monta o input do agente: contexto do papel + prompt da tarefa."""
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

    # Marcadores que indicam que a execução do kiro-cli falhou.
    # Buscados apenas nos canais estruturados (tail do output ou saída
    # sintética do adapter), nunca no corpo/narrativa inteiro do agente.
    _FAILURE_MARKERS = (
        "[exit-code:",
        "[TIMEOUT]",
        "[ERRO]",
        "Kiro is having trouble responding",
    )

    # Trechos que identificam a linha do erro real dentro do output.
    _ERROR_HINTS = (
        "Kiro is having trouble responding",
        "temporarily unavailable",
        "unavailable",
        "InternalServerError",
        "Request ID:",
        "request_id:",
        "error:",
        "Error:",
        "ERRO",
        "Location:",
        "[exit-code:",
        "[TIMEOUT]",
    )

    # Indicador de sucesso do kiro-cli: impresso como última linha útil quando
    # a execução completa normalmente. Presença desta linha no epilogo indica
    # que qualquer marcador de falha no corpo é narrativa do agente, não erro
    # estruturado do processo.
    _SUCCESS_INDICATOR = "\u25b8 Credits:"

    # Quantidade de linhas finais (não-vazias) consideradas como canal
    # estruturado do kiro-cli quando returncode == 0 e não há indicador de
    # sucesso. O bloco de erro do kiro-cli é impresso imediatamente antes do
    # processo encerrar.
    _TAIL_LINES = 30

    # Marcadores de abort **ambíguo** do kiro-cli: o turno quebrou no meio, sem
    # rollback. Não provam que nada executou — pelo contrário, na evidência de
    # #175 o commit e o push já haviam sido aplicados quando o abort ocorreu.
    _AMBIGUOUS_MARKERS = (
        "dispatch failure",
        "InternalServerError",
        "[TIMEOUT]",
    )

    # Evidência positiva e estruturada de que o subprocesso não chegou a rodar.
    # Só isso autoriza DEFINITE_NOT_STARTED (ADR, seção 5): ausência de tool
    # call em output parcial não é evidência.
    _NOT_STARTED_MARKERS = (
        _KIRO_NOT_FOUND,
    )

    def _detect_failure(self, output: str, returncode: int | None = None) -> str | None:
        """Detecta falha na execução do kiro-cli usando canais estruturados.

        A decisão de falha é baseada exclusivamente em:
        1. Saída sintética do adapter (timeout, kiro-cli ausente): o output
           inteiro É o canal estruturado.
        2. returncode != 0: falha confirmada pelo processo; extrai causa do
           tail do output.
        3. returncode == 0: se a última linha significativa é o indicador de
           sucesso do kiro-cli (`▸ Credits: ...`), a execução é bem-sucedida
           independente do que o agente narrou. Se NÃO há indicador de sucesso,
           busca marcadores de falha no tail (erros de modelo/servidor com
           exit 0 que o kiro-cli reporta no encerramento sem imprimir Credits).

        Retorna mensagem de uma linha com o erro real (linhas relevantes
        unidas por ' | '), ou None se a execução foi bem-sucedida.
        """
        clean = self._strip_ansi(output)
        non_empty = [l.strip() for l in clean.splitlines() if l.strip()]
        if not non_empty:
            return None

        # Caso 1: saída sintética do adapter (processo não executou/completou).
        # O output inteiro é o canal estruturado — usa-o diretamente.
        if returncode is None:
            if any(m in clean for m in self._FAILURE_MARKERS):
                return self._extract_error(non_empty, non_empty)
            return None

        # Caso 2: processo encerrou com exit-code != 0.
        # Falha confirmada; extrai causa do tail.
        if returncode != 0:
            tail = non_empty[-self._TAIL_LINES:]
            return self._extract_error(tail, non_empty)

        # Caso 3: returncode == 0.
        # Se o kiro-cli imprimiu seu indicador de sucesso como última linha
        # significativa, a execução completou normalmente — qualquer marcador
        # no corpo é narrativa do agente (falso positivo que queremos evitar).
        if any(self._SUCCESS_INDICATOR in line for line in non_empty[-3:]):
            return None

        # Sem indicador de sucesso e returncode == 0: possível erro de
        # modelo/servidor reportado no encerramento. Busca marcadores apenas
        # no tail (onde o kiro-cli imprime o bloco de erro).
        tail = non_empty[-self._TAIL_LINES:]
        tail_text = "\n".join(tail)
        if not any(m in tail_text for m in self._FAILURE_MARKERS):
            return None

        return self._extract_error(tail, non_empty)

    def _extract_error(self, search_lines: list[str], all_lines: list[str]) -> str | None:
        """Extrai as linhas relevantes de erro de search_lines.

        Procura linhas que casam com _ERROR_HINTS em search_lines. Se nenhuma
        casar, usa as últimas 3 linhas de all_lines como contexto.
        """
        relevant: list[str] = []
        for line in search_lines:
            if any(hint in line for hint in self._ERROR_HINTS):
                if line not in relevant:
                    relevant.append(line)

        if not relevant:
            relevant = all_lines[-3:]

        return " | ".join(relevant) if relevant else None

    # ── Classificação do resultado (ADR retry-kiro-cli/idempotencia.md) ──────

    def _classify(self, output: str, returncode: int | None,
                  error: str | None) -> Outcome:
        """Classifica o resultado da execução na máquina de estados da ADR.

        - Sem falha detectada → ``SUCCEEDED``.
        - Falha com evidência positiva de não-inicialização →
          ``DEFINITE_NOT_STARTED`` (único estado que admitiria retry).
        - Qualquer outra falha → ``UNKNOWN_OUTCOME`` (fail-closed). Inclui
          `dispatch failure`, `InternalServerError` e timeout: o abort ocorre no
          meio do turno, sem rollback, e o output parcial não prova ausência de
          efeitos porque o stream pode quebrar entre o efeito e a recepção do
          evento.

        O default ambíguo é deliberado: classificar como "não executou" sem
        prova permitiria retry sobre um turno que já fez commit/push.
        """
        if not error:
            return Outcome.SUCCEEDED
        clean = self._strip_ansi(output)
        if any(marker in clean for marker in self._NOT_STARTED_MARKERS):
            return Outcome.DEFINITE_NOT_STARTED
        return Outcome.UNKNOWN_OUTCOME

    def _ambiguous_marker(self, output: str) -> str | None:
        """Retorna o marcador de abort ambíguo presente no output, se houver.

        Serve à observabilidade: nomeia no log qual dos aborts conhecidos de
        #203 ocorreu, sem alterar a classificação (que já é ambígua por
        default).
        """
        clean = self._strip_ansi(output).lower()
        for marker in self._AMBIGUOUS_MARKERS:
            if marker.lower() in clean:
                return marker
        return None

    def _extract_request_id(self, output: str) -> str | None:
        """Extrai o request ID do bloco de erro estruturado do kiro-cli.

        Cobre `request_id: <id>` (abort de dispatch) e `Request ID: <id>`
        (erro de servidor). É a chave para correlacionar o abort com o upstream.
        """
        match = _REQUEST_ID.search(self._strip_ansi(output))
        return match.group(1) if match else None

    def _evidence(self, outcome: Outcome, request_id: str | None,
                  marker: str | None = None) -> dict:
        """Extras de log com a evidência da entrega (omite campos ausentes)."""
        extra = {"outcome": outcome.value, "invocations": self._invocations}
        if request_id:
            extra["request_id"] = request_id
        if marker:
            extra["marker"] = marker
        if self._last_session_id:
            extra["session_id"] = self._last_session_id
        return extra

    def _append_outcome(self, log_path: Path, outcome: Outcome,
                        returncode: int | None, request_id: str | None,
                        error: str | None, marker: str | None = None) -> None:
        """Registra o bloco de resultado no log de execução (auditoria).

        O output integral já foi gravado antes; este bloco é o resumo
        estruturado que permite auditar o turno abortado sem reler o chat.
        """
        lines = [
            "", "---", "", "## Resultado", "",
            f"- **classificação**: {outcome.value}",
            f"- **invocações do kiro-cli**: {self._invocations}",
            f"- **exit-code**: "
            f"{returncode if returncode is not None else '(não finalizou)'}",
        ]
        if request_id:
            lines.append(f"- **request_id**: {request_id}")
        if self._last_session_id:
            lines.append(f"- **session_id**: {self._last_session_id}")
        if marker:
            lines.append(f"- **marcador**: {marker}")
        if error:
            lines.append(f"- **erro**: {error}")
        if outcome is Outcome.UNKNOWN_OUTCOME:
            lines += [
                "",
                "> Resultado ambíguo: o turno pode ter aplicado efeitos "
                "(commit, push, movimentação de coluna) antes do abort. Sem "
                "retry inline — a reentrega ocorre pelo loop normal, após a "
                "reconciliação e respeitando `rerun_cooldown`, retomando a "
                "sessão quando ela existir.",
            ]
        self._append_log(log_path, "\n".join(lines) + "\n")

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
        lines.append(f"- **participation_intent**: {params.participation_intent or '(ausente)'}")
        lines.append(f"- **issue**: #{params.issue_id}")
        if params.repo_id:
            lines.append(f"- **repo**: {params.repo_id}")
        if params.work_dir:
            lines.append(f"- **work_dir**: {params.work_dir}")
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
