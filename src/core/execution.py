"""Classificação do resultado de uma execução de agente — issue #303 / ADR #217.

Alinhado à ADR `doc/architecture/retry-kiro-cli/idempotencia.md` (aceita). A
máquina de estados da seção 5 da ADR distingue:

- `SUCEDIDO`              — execução concluída sem sinal estruturado de falha;
- `FALHA`                 — falha definitiva por canal estruturado (exit-code,
                            saída de erro) que NÃO é interrupção transitória;
- `UNKNOWN_OUTCOME`       — resultado AMBÍGUO (dispatch failure /
                            InternalServerError após output parcial / timeout):
                            o subprocesso pode ter aplicado efeitos (commit,
                            push, movimento de coluna) antes de abortar. Política
                            fail-closed: UMA invocação por entrega, SEM retry
                            inline; evidências preservadas; reconciliação pelo
                            loop normal;
- `DEFINITE_NOT_STARTED`  — não-inicialização COMPROVADA mecanicamente (ex.:
                            kiro-cli ausente no PATH). Único caso que admite
                            retry inline com backoff e limite — nenhum efeito
                            pode ter sido aplicado.

A ausência de tool call em output parcial NÃO é evidência de não-inicialização
(seção 5 da ADR): é `UNKNOWN_OUTCOME`.
"""

from __future__ import annotations

from dataclasses import dataclass

# Classes de resultado (strings estáveis — usadas em logs e asserções).
SUCEDIDO = "sucedido"
FALHA = "falha"
UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
DEFINITE_NOT_STARTED = "DEFINITE_NOT_STARTED"
# Resultado terminal após esgotar o retry seguro de DEFINITE_NOT_STARTED.
FALHA_PERSISTENTE = "falha persistente"


@dataclass
class ExecutionResult:
    """Resultado classificado de uma execução de agente.

    - `classe`: uma das constantes acima.
    - `output`: output integral capturado (preservado para auditoria/retomada).
    - `causa`: causa real da falha extraída de canal estruturado (ou None).
    - `origem`: canal estruturado que classificou (ex.: 'exit-code', 'timeout',
      'erro interno', 'dispatch failure'); nunca a narrativa do agente.
    - `session_id`: id da sessão kiro-cli (preservado quando disponível).
    - `request_id`: request ID do servidor (preservado quando disponível).
    - `tentativas`: número de invocações do subprocesso nesta entrega.
    """

    classe: str
    output: str = ""
    causa: str | None = None
    origem: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    tentativas: int = 1

    @property
    def sucesso(self) -> bool:
        return self.classe == SUCEDIDO

    @property
    def ambiguo(self) -> bool:
        return self.classe == UNKNOWN_OUTCOME
