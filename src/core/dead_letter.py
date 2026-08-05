"""Dead Letter core - persistência de itens da fila que se esgotaram.

Persiste em .pipe/deadLetter.json um array de DeadLetterEntry, cada uma
descrevendo um item da fila de sincronismo (ChangeItem) que foi removido da
fila ativa por classificação "definitivo" ou por esgotar as tentativas
transitórias configuradas (ver classify_error em src/core/sync.py).

Segue o mesmo padrão de src/core/change_queue.py: arquivo JSON, lista de
entradas, escrita via json.dumps(..., indent=2, ensure_ascii=False), leitura
tolerante a campos desconhecidos.

.pipe/deadLetter.json é memória interna da esteira (ver PROTECTED_PATHS em
src/core/agent.py) — o agente de desenvolvimento não deve ler/escrever esse
arquivo diretamente.
"""

import json
import re
from dataclasses import asdict, dataclass, fields as dataclass_fields
from pathlib import Path

PIPE_DIR = Path(".pipe")
DEAD_LETTER_FILE = PIPE_DIR / "deadLetter.json"

# Mesmos padrões de src/core/agent.py (PROTECTED_PATHS), replicados aqui como
# strings simples (sem coringa fnmatch) para permitir substituição textual
# direta na mensagem de exceção. Mantidos em sincronia manualmente: qualquer
# novo padrão protegido deve ser adicionado também aqui se puder aparecer em
# mensagens de exceção do sync.
_PROTECTED_PATH_SUBSTRINGS = (
    ".pipe/boards/*/snapshot.json",
    ".pipe/changeQueue.json",
    ".pipe/throttle.json",
    ".pipe/throttle-*.json",
    ".pipe/deadLetter.json",
)

# Padrões de arquivo protegido com glob (ex.: snapshot.json de qualquer board,
# throttle-<escopo>.json) reconhecidos por regex sobre o caminho literal.
_PROTECTED_PATH_PATTERNS = [
    re.compile(r"\.pipe/boards/[^\s/]+/snapshot\.json"),
    re.compile(r"\.pipe/changeQueue\.json"),
    re.compile(r"\.pipe/throttle\.json"),
    re.compile(r"\.pipe/throttle-[^\s/]+\.json"),
    re.compile(r"\.pipe/deadLetter\.json"),
]

# Tokens de GitHub (ghp_, gho_, ghu_, ghs_, ghr_ etc.) - mascara qualquer
# sequência alfanumérica longa após o prefixo.
_TOKEN_PATTERN = re.compile(r"gh[a-z]_[A-Za-z0-9]{20,}")

# Header Authorization: Bearer <token> (mascara só o valor do token).
_BEARER_PATTERN = re.compile(r"(Authorization:\s*Bearer\s+)([A-Za-z0-9._~+/=-]+)", re.IGNORECASE)
_BEARER_ONLY_PATTERN = re.compile(r"(Bearer\s+)([A-Za-z0-9._~+/=-]+)", re.IGNORECASE)


def sanitize_reason(msg: str) -> str:
    """Remove/mascara conteúdo protegido e credenciais de uma mensagem de erro.

    Regras:
    - Caminhos de PROTECTED_PATHS são substituídos por '<arquivo interno>'.
    - Tokens do GitHub (ghp_/gho_/ghu_/ghs_/ghr_...) são mascarados com '***'.
    - Headers 'Authorization: Bearer <token>' (ou apenas 'Bearer <token>')
      têm o valor do token mascarado com '***', preservando o restante da
      mensagem legível.

    Função pura: não faz I/O nem loga.
    """
    result = msg
    for pattern in _PROTECTED_PATH_PATTERNS:
        result = pattern.sub("<arquivo interno>", result)
    result = _TOKEN_PATTERN.sub("***", result)
    result = _BEARER_PATTERN.sub(lambda m: f"{m.group(1)}***", result)
    result = _BEARER_ONLY_PATTERN.sub(lambda m: f"{m.group(1)}***", result)
    return result


@dataclass
class DeadLetterEntry:
    """Entrada de dead-letter (.pipe/deadLetter.json).

    Representa um ChangeItem que se esgotou (erro definitivo ou limite de
    tentativas transitórias atingido) e foi removido da fila ativa.
    """
    uuid: str
    board: str
    id: str
    identifier: str
    event: str
    category: str      # "definitivo" | "transitorio_esgotado"
    reason: str         # mensagem sanitizada (ver sanitize_reason)
    attempts: int
    isolated_at: str    # timestamp ISO 8601 UTC (mesmo padrão de ChangeItem.now())
    next_step: str      # ação recomendada, curta e acionável


class DeadLetterQueue:
    """Fila persistente de entradas de dead-letter.

    Únicos pontos de acesso ao arquivo: add(), list(), remove().
    """

    def _read(self) -> list[DeadLetterEntry]:
        if not DEAD_LETTER_FILE.exists():
            return []
        raw = json.loads(DEAD_LETTER_FILE.read_text(encoding="utf-8"))
        fields = {f.name for f in dataclass_fields(DeadLetterEntry)}
        return [
            DeadLetterEntry(**{k: v for k, v in entry.items() if k in fields})
            for entry in raw
        ]

    def _write(self, entries: list[DeadLetterEntry]) -> None:
        PIPE_DIR.mkdir(parents=True, exist_ok=True)
        data = [asdict(entry) for entry in entries]
        DEAD_LETTER_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def _same_target(a: DeadLetterEntry, b: DeadLetterEntry) -> bool:
        """Mesmo alvo: board + id (ou identifier, quando id é None) + event."""
        a_key = a.id if a.id is not None else a.identifier
        b_key = b.id if b.id is not None else b.identifier
        return a.board == b.board and a_key == b_key and a.event == b.event

    def add(self, entry: DeadLetterEntry) -> None:
        """Adiciona uma entrada. Idempotente por alvo (board+id/identifier+event):
        se já existir uma entrada equivalente, atualiza-a (novo motivo,
        tentativas, timestamp, categoria, next_step) em vez de duplicar.
        """
        entries = self._read()
        for i, existing in enumerate(entries):
            if self._same_target(existing, entry):
                entries[i] = entry
                self._write(entries)
                return
        entries.append(entry)
        self._write(entries)

    def list(self) -> list[DeadLetterEntry]:
        """Retorna todas as entradas."""
        return self._read()

    def remove(self, uuid: str) -> bool:
        """Remove a entrada com o uuid informado.

        Primitiva para uso futuro de limpeza operacional / replay manual —
        não é escopo desta camada expor replay automático.
        Retorna True se removeu, False se não encontrou.
        """
        entries = self._read()
        remaining = [e for e in entries if e.uuid != uuid]
        if len(remaining) == len(entries):
            return False
        self._write(remaining)
        return True
