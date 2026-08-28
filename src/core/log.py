"""Log core - terminal (resumo colorido) + arquivo (detalhe com extras/trace)."""

import logging
import re
import traceback
from datetime import date, datetime
from pathlib import Path

_DEFAULT_DIR = "logs"
_DEFAULT_TTL = 10

# Nível TRACE: abaixo de DEBUG (5 < 10). Só vai para arquivo, não para terminal.
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

_RESET = "\033[0m"
_BOLD = "\033[1m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_WHITE = "\033[37m"
_DIM = "\033[2m"

_LEVEL_COLOR = {
    TRACE: _DIM,
    logging.INFO: _BOLD,
    logging.WARNING: _YELLOW,
    logging.ERROR: _RED,
}

_BRACKET = re.compile(r"\[([^\]]+)\]")

# Chaves de kwargs de log consideradas sensíveis. Superconjunto conservador do
# que os eventos estruturados da story #246 (e das stories #241/#244/#245)
# utilizam. A garantia é por NOME de campo/disciplina de call site, não por
# scanner de conteúdo - detectar segredo por valor exigiria heurística frágil
# (mesma decisão registrada no README sobre não escanear corpo de resposta
# em busca de "rate limit").
FORBIDDEN_LOG_KWARGS = {"token", "ssh_key", "body", "gh_token", "kiro_api_key"}


def assert_no_sensitive_kwargs(extra: dict) -> None:
    """Levanta ValueError se `extra` contiver alguma chave proibida.

    Chaves proibidas (comparação exata, case-insensitive): token, ssh_key,
    body, gh_token, kiro_api_key - superconjunto conservador do que os
    eventos desta story usam. Não inspeciona valores (apenas chaves) -
    detectar segredo por conteúdo de string exigiria heurística frágil;
    a garantia real é de disciplina de nomes de campo nos call sites,
    verificada também pelos testes desta task por inspeção de código.

    Não chamada automaticamente por Log._log (mudaria o comportamento de
    todo log existente na base, fora do escopo desta story) - é uma
    ferramenta de teste/asserção usada pela suíte de conformidade e,
    opcionalmente, pelos call sites desta story antes de logar.
    """
    lower_keys = {k.lower() for k in extra}
    hit = lower_keys & FORBIDDEN_LOG_KWARGS
    if hit:
        raise ValueError(f"kwargs de log contêm chave(s) proibida(s): {sorted(hit)}")


class Log:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._log_dir = Path(_DEFAULT_DIR)
            cls._instance._ttl = _DEFAULT_TTL
            cls._instance._level = logging.INFO
            cls._instance._file = None
            cls._instance._setup()
        return cls._instance

    def configure(self, config: dict):
        """Aplica configuração de log do pipe.yml."""
        log_cfg = config.get("log", {})
        new_dir = Path(log_cfg.get("dir", _DEFAULT_DIR))
        self._ttl = log_cfg.get("ttl", _DEFAULT_TTL)
        level_str = log_cfg.get("level", "INFO").upper()
        if level_str == "TRACE":
            self._level = TRACE
        else:
            self._level = getattr(logging, level_str, logging.INFO)
        if new_dir != self._log_dir:
            self._log_dir = new_dir
            if self._file:
                self._file.close()
            self._setup()

    def _setup(self):
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self._log_dir / f"{date.today().strftime('%Y-%m-%d')}.json"
        self._file = open(log_file, "a", encoding="utf-8")

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    def cleanup(self):
        """Remove arquivos de log com mais de ttl dias."""
        if not self._log_dir.exists():
            return
        now = date.today()
        for path in sorted(self._log_dir.rglob("*")):
            if path.is_file():
                age = (now - date.fromtimestamp(path.stat().st_mtime)).days
                if age > self._ttl:
                    path.unlink()
        for path in sorted(self._log_dir.rglob("*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()

    def separator(self):
        """Escreve linha em branco no arquivo para demarcar início de execução."""
        self._file.write("\n")
        self._file.flush()

    def info(self, module: str, msg: str, *args, **extra):
        self._log("INFO", module, msg, args, extra)

    def warning(self, module: str, msg: str, *args, **extra):
        self._log("WARNING", module, msg, args, extra)

    def error(self, module: str, msg: str, *args, exc: BaseException = None, **extra):
        self._log("ERROR", module, msg, args, extra, exc=exc)

    def trace(self, module: str, msg: str, *args, **extra):
        self._log("TRACE", module, msg, args, extra)

    def _log(self, level: str, module: str, msg: str, args: tuple, extra: dict, exc: BaseException = None):
        formatted = msg % args if args else msg

        now = datetime.now()
        level_num = getattr(logging, level, None) or TRACE

        # Terminal: hora + resumo colorido (só se nível >= configurado)
        if level_num >= self._level:
            color = _LEVEL_COLOR.get(level_num, _BOLD)
            terminal_msg = f"[{module}] {formatted}"
            terminal_msg = _BRACKET.sub(f"{color}[\\1]{_RESET}", terminal_msg)
            print(f"{now.strftime('%H:%M:%S')} {terminal_msg}")

        # Arquivo: timestamp - level - module - message + extras (sempre grava)
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        file_line = f"{ts} - {level} - {module} - {formatted}"
        if extra:
            file_line += f" | {extra}"
        if exc:
            file_line += f"\n{traceback.format_exception(type(exc), exc, exc.__traceback__)[-1].rstrip()}"
            file_line += f"\n{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))}"
        self._file.write(file_line + "\n")
        self._file.flush()


log = Log()
