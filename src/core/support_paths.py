"""Resolução dos caminhos de apoio (templates de documento/issue) — issue #303.

Fragilidade tratada: a configuração e os contextos de agente referenciam modelos
de documento/issue em um diretório de apoio que pode não estar resolvido no
ambiente de execução. Como a ferramenta de execução valida o lote de chamadas de
ferramenta em BLOCO, um único caminho inexistente cancelava TODAS as ferramentas
do lote — inclusive as válidas —, desperdiçando turnos e crédito.

Correção (#303):
- `resolve_support_paths` resolve cada caminho POR ITEM: separa os existentes
  (`resolvidos`) dos ausentes (`ausentes`) e NUNCA cancela o lote
  (`cancelou_lote` é sempre False). A ausência é sinalizada isoladamente.
- Fonte única de templates: `contexts/templates/`. Os caminhos dirigidos por
  configuração (`support_paths_from_config`) e os gerados por código
  (`support_paths_from_code`) apontam para o MESMO diretório-fonte, evitando o
  anti-padrão de config e código divergirem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Fonte ÚNICA e válida dos modelos de apoio (templates de doc/issue). Config e
# código devem sempre apontar para cá — nunca para pastas diferentes.
TEMPLATES_DIR: Path = Path("contexts") / "templates"


@dataclass
class SupportPathResolution:
    """Resultado da resolução POR ITEM de um lote de caminhos de apoio.

    - `resolvidos`: caminhos que existem no ambiente (prontos para uso).
    - `ausentes`: caminhos inexistentes, sinalizados ISOLADAMENTE.
    - `cancelou_lote`: SEMPRE False — a ausência de um item nunca cancela os
      demais (invariante central do #303). Mantido explícito para o chamador
      afirmar a garantia sem inferir.
    """

    resolvidos: list[Path] = field(default_factory=list)
    ausentes: list[Path] = field(default_factory=list)
    cancelou_lote: bool = False


def resolve_support_paths(paths) -> SupportPathResolution:
    """Resolve um lote de caminhos de apoio POR ITEM, sem cancelar o lote.

    Para cada caminho, verifica a existência no ambiente: existentes vão para
    `resolvidos`, ausentes para `ausentes`. Um caminho ausente NÃO levanta
    exceção nem descarta os válidos — `cancelou_lote` permanece False.

    Aceita qualquer iterável de `str`/`Path`.
    """
    resolution = SupportPathResolution()
    for raw in paths:
        path = Path(raw)
        if path.exists():
            resolution.resolvidos.append(path)
        else:
            resolution.ausentes.append(path)
    return resolution


def support_paths_from_code(templates_dir: Path | None = None) -> list[Path]:
    """Caminhos de apoio GERADOS por código, a partir da fonte única.

    Enumera os templates sob `contexts/templates/` (recursivamente). É a mesma
    fonte usada por `support_paths_from_config`, garantindo que código e
    configuração nunca divirjam (CT-08).
    """
    base = templates_dir or TEMPLATES_DIR
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*") if p.is_file())


def support_paths_from_config(config: dict, templates_dir: Path | None = None) -> list[Path]:
    """Caminhos de apoio dirigidos pela CONFIGURAÇÃO, a partir da fonte única.

    A configuração não define um diretório de templates próprio: a esteira
    centraliza a fonte em `contexts/templates/` (constante `TEMPLATES_DIR`),
    de modo que os caminhos derivados da config apontem para o MESMO lugar que
    os gerados por código. Isso elimina o anti-padrão de duas fontes
    divergentes (config vs. código).

    O parâmetro `config` é aceito para extensibilidade futura (ex.: um board
    sobrescrever a fonte), mas hoje a fonte é única e canônica.
    """
    return support_paths_from_code(templates_dir)
