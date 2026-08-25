"""Adapter kiro-cli - execução de agentes via kiro-cli."""

import os
import re
import subprocess
from datetime import datetime, timezone, timedelta
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


class KiroCliAgent(AgentPort):
    """Adapter de agente para kiro-cli."""

    def execute(self, params: AgentParams) -> None:
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
            if error:
                log.error("Kiro", f"[{params.board_id}] #{params.issue_id} "
                          f"falhou: {error}", log=str(log_path))
            else:
                log.info("Kiro", f"[{params.board_id}] #{params.issue_id} "
                         f"execução concluída: {self._last_meaningful_line(output)}",
                         log=str(log_path))
        except Exception as e:
            self._append_log(log_path, f"\n**ERRO**: {e}\n")
            log.error("Kiro", f"[{params.board_id}] #{params.issue_id} "
                      f"erro: {self._last_meaningful_line(str(e))}",
                      log=str(log_path))
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
            log.info("Kiro", f"[{params.board_id}] #{params.issue_id} "
                     f"retomando sessão {known_id}",
                     session_id=known_id, agent=params.agent_id)

        cmd.append(self._compose_input(params))

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
            return f"[TIMEOUT] Agente excedeu {_TIMEOUT}s", None
        except FileNotFoundError:
            return "[ERRO] kiro-cli não encontrado no PATH", None

        # Captura o id da sessão recém-usada (mais recente do cwd) e persiste.
        # O loop da esteira é sequencial, então a sessão do topo é a desta
        # execução (mesma quando retomada por id, nova quando criada agora).
        current_id = self._latest_session_id(work_dir, env)
        if current_id:
            index.set(params.board_id, params.issue_id, params.agent_id, current_id)

        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            output += f"\n[exit-code: {result.returncode}]"
        return output, result.returncode

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
