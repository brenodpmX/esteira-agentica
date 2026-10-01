"""Config core - carrega e valida pipe.yml."""

from pathlib import Path
from dataclasses import dataclass
import os
import yaml

PIPE_FILE = Path("pipe.yml")
SSH_KEY_ENV = "PIPE_SSH_KEY_FILE"


class ConfigError(Exception):
    """Erro de configuração do pipe.yml."""
    pass


def _require(data: dict, key: str, context: str):
    if key not in data:
        raise ConfigError(f"{context}: campo '{key}' é obrigatório")
    return data[key]


def _validate_env():
    key_path = os.environ.get(SSH_KEY_ENV, "").strip()
    if not key_path:
        raise ConfigError(
            "✗ SSH  variável PIPE_SSH_KEY_FILE não definida ou vazia\n"
            "    Causa:  o clone via SSH no arranque precisa saber onde está a chave privada.\n"
            "    Ação:   defina PIPE_SSH_KEY_FILE no serviço apontando para o secret montado.\n"
            "            ex.: PIPE_SSH_KEY_FILE=/run/secrets/ssh_key\n"
            "    Onde:   monte a chave como Docker secret (ver docker-compose / runbook)."
        )
    if not Path(key_path).expanduser().exists():
        raise ConfigError(
            f"✗ SSH  arquivo de chave não encontrado em {key_path}\n"
            "    Causa:  PIPE_SSH_KEY_FILE aponta para um caminho que não existe no container.\n"
            "    Ação:   confira se o secret/volume da chave está montado nesse caminho.\n"
            "    Onde:   seção 'secrets' do docker-compose (ver runbook)."
        )


def _validate_git(git: dict):
    _require(git, "repo", "git")
    _require(git, "flow", "git")
    
    flow = git["flow"]
    _require(flow, "base", "git.flow")
    
    for flow_id, flow_cfg in flow.items():
        if flow_id == "base":
            continue
        if "name" not in flow_cfg and "prefix" not in flow_cfg:
            raise ConfigError(f"git.flow.{flow_id}: requer 'name' ou 'prefix'")
        # E1 (F1.1): branch_pattern por flow — template legível do nome da branch,
        # no formato `<prefix>/<id>-<slug>`. OBRIGATÓRIO em todo flow (exceto
        # 'base'): o agent.py não monta mais o nome; passa o padrão como
        # instrução e o agente cria a branch conforme (E3). Deve ser string
        # não-vazia.
        if "branch_pattern" not in flow_cfg:
            raise ConfigError(
                f"git.flow.{flow_id}: campo 'branch_pattern' é obrigatório "
                f"(template legível do nome da branch, ex.: 'story/{{id}}-{{slug}}')"
            )
        bp = flow_cfg["branch_pattern"]
        if not isinstance(bp, str) or not bp.strip():
            raise ConfigError(
                f"git.flow.{flow_id}.branch_pattern: deve ser uma string não-vazia "
                f"(template do nome da branch, ex.: 'story/{{id}}-{{slug}}')"
            )


CONTEXTS_DIR = Path("contexts")


def _validate_agents(agents: dict):
    missing = []
    empty = []
    for platform_id, platform in agents.items():
        for agent_id, agent_cfg in platform.items():
            _require(agent_cfg, "name", f"agents.{platform_id}.{agent_id}")
            # P1.5 (F0.9): a esteira NÃO cria mais o arquivo de contexto (persona).
            # Ele é insumo do operador (versionado no repo PIPE, montado readonly).
            # Aqui apenas validamos e orientamos — nunca escrevemos.
            ctx_file = CONTEXTS_DIR / platform_id / f"{agent_id}.md"
            if not ctx_file.exists():
                missing.append(str(ctx_file))
            elif not ctx_file.read_text(encoding="utf-8").strip():
                empty.append(str(ctx_file))
    if missing or empty:
        parts = []
        if missing:
            parts.append("Arquivos de contexto ausentes (crie e preencha):\n  - "
                         + "\n  - ".join(missing))
        if empty:
            parts.append("Arquivos de contexto vazios (preencha antes de executar):\n  - "
                         + "\n  - ".join(empty))
        raise ConfigError("\n".join(parts))


def validate_column_migrations(board_id: str, board_cfg: dict) -> None:
    """Valida a chave opcional `boards.<board>.column-migrations` (issue #305).

    Validação de FORMA apenas (a validação semântica — destino existir no mesmo
    board, ser diferente da origem e não ser outra coluna também em retirada no
    ciclo — é feita em tempo de reconciliação pelo núcleo de decisão).

    Regras (cada violação levanta ConfigError citando o caminho e a entrada):
    - quando presente, deve ser um mapa (dict);
    - cada chave (origem) e cada valor (destino) deve ser string não-vazia após
      remoção de espaços; tipo diferente, nulo ou vazio é rejeitado.

    A ausência da chave é configuração válida (declaração opcional).
    """
    path = f"boards.{board_id}.column-migrations"
    if "column-migrations" not in board_cfg:
        return
    migrations = board_cfg["column-migrations"]
    if not isinstance(migrations, dict):
        raise ConfigError(
            f"{path}: deve ser um mapa (origem -> destino) "
            f"(valor recebido: {migrations!r})"
        )
    for source, destination in migrations.items():
        if not isinstance(source, str) or not source.strip():
            raise ConfigError(
                f"{path}: chave de origem inválida — deve ser string não-vazia "
                f"(entrada: {source!r})"
            )
        if not isinstance(destination, str) or not destination.strip():
            raise ConfigError(
                f"{path}: destino inválido para '{source.strip()}' — deve ser "
                f"string não-vazia (entrada: {destination!r})"
            )


def _validate_boards(boards: dict, known_agents: set[str] | None = None):
    known_agents = known_agents or set()
    _require(boards, "platform", "boards")

    # boards.rerun_cooldown (opcional): tempo mínimo, em segundos, antes de
    # reexecutar a mesma issue (mesmo board, coluna e id). 0 desabilita.
    cooldown = boards.get("rerun_cooldown")
    if cooldown is not None and (
        isinstance(cooldown, bool) or not isinstance(cooldown, int) or cooldown < 0
    ):
        raise ConfigError("boards.rerun_cooldown: deve ser inteiro >= 0 (segundos)")

    for board_id, board in boards.items():
        if board_id == "platform":
            continue
        # Chaves escalares de configuração (ex.: rerun_cooldown) convivem com os
        # boards dentro de 'boards'; só validamos entradas que são boards (dict).
        if not isinstance(board, dict):
            continue
        _require(board, "name", f"boards.{board_id}")
        columns = _require(board, "columns", f"boards.{board_id}")

        # Validação de forma do mapa opcional de destinos de migração (#305).
        validate_column_migrations(board_id, board)
        
        for col_id, col in columns.items():
            _require(col, "name", f"boards.{board_id}.columns.{col_id}")
            for ev in ("on_in", "on_out"):
                if ev in col and not isinstance(col[ev], list):
                    raise ConfigError(
                        f"boards.{board_id}.columns.{col_id}.{ev}: deve ser uma lista"
                    )

            # allowed-commands (#308): lista opcional de comandos de anotação
            # `@---` permitidos na etapa. Deriva o gate de referência sob demanda
            # (manual @---). Quando ausente, assume o conjunto completo. Quando
            # presente, deve ser uma lista de strings.
            if "allowed-commands" in col:
                ac = col["allowed-commands"]
                if not isinstance(ac, list) or not all(
                    isinstance(x, str) for x in ac
                ):
                    raise ConfigError(
                        f"boards.{board_id}.columns.{col_id}.allowed-commands: "
                        f"deve ser uma lista de strings (nomes de comando)"
                    )

            ctx = f"boards.{board_id}.columns.{col_id}"

            # Agente default da coluna deve existir
            agent = col.get("agent")
            if agent and known_agents and agent not in known_agents:
                raise ConfigError(f"{ctx}.agent: agente '{agent}' não definido em 'agents'")

            # agent-hub: mapa <valor> → agente (roteamento por hub)
            override = col.get("agent-hub")
            if override is not None:
                if not isinstance(override, dict):
                    raise ConfigError(f"{ctx}.agent-hub: deve ser um mapa <valor>: <agente>")
                if not col.get("agent"):
                    raise ConfigError(
                        f"{ctx}.agent-hub: requer um 'agent' default na coluna"
                    )
                for value, ov_agent in override.items():
                    if known_agents and ov_agent not in known_agents:
                        raise ConfigError(
                            f"{ctx}.agent-hub.{value}: agente '{ov_agent}' não definido em 'agents'"
                        )


def _validate_project(project: dict):
    """Valida a seção `project` do pipe.yml (E — 'Visão geral').

    `name` e `summary` são OBRIGATÓRIOS (strings não-vazias). `humans` é
    OPCIONAL: se presente, deve ser lista de mapas com `name`/`role` não-vazios.
    O gerador de contexto (context_generator) injeta esses valores nas seções
    'Projeto' e 'Papéis humanos' do steering.
    """
    if not isinstance(project, dict):
        raise ConfigError("project: deve ser um mapa com 'name' e 'summary'")
    for key in ("name", "summary"):
        value = project.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(
                f"project.{key}: campo obrigatório (string não-vazia)"
            )
    humans = project.get("humans")
    if humans is not None:
        if not isinstance(humans, list):
            raise ConfigError("project.humans: deve ser uma lista de {name, role}")
        for i, human in enumerate(humans):
            if not isinstance(human, dict):
                raise ConfigError(
                    f"project.humans[{i}]: deve ser um mapa com 'name' e 'role'"
                )
            for key in ("name", "role"):
                value = human.get(key)
                if not isinstance(value, str) or not value.strip():
                    raise ConfigError(
                        f"project.humans[{i}].{key}: campo obrigatório (string não-vazia)"
                    )


def _validate_log(log_cfg: dict):
    ttl = log_cfg.get("ttl")
    if ttl is not None and (not isinstance(ttl, int) or ttl < 1):
        raise ConfigError("log.ttl: deve ser inteiro >= 1")


def _validate_sleep(sleep_val):
    """Valida campo sleep (segundos entre ciclos quando ocioso)."""
    if not isinstance(sleep_val, (int, float)) or sleep_val <= 0:
        raise ConfigError("sleep: deve ser número > 0 (segundos)")


DEFAULT_MAX_ATTEMPTS = 3


def validate_max_attempts(config: dict) -> None:
    """Valida a chave opcional sync.max_attempts do pipe.yml.

    Se presente, deve ser um int >= 1 (rejeita 0, negativos, floats e
    strings não numéricas). Levanta ConfigError identificando a chave.
    """
    sync_cfg = config.get("sync") or {}
    if "max_attempts" not in sync_cfg:
        return
    value = sync_cfg["max_attempts"]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigError(
            f"sync.max_attempts: deve ser inteiro >= 1 (valor recebido: {value!r})"
        )


def resolve_max_attempts(config: dict) -> int:
    """Retorna o limite de tentativas configurado (sync.max_attempts).

    Default seguro de DEFAULT_MAX_ATTEMPTS quando a chave está ausente.
    Não valida — assume que validate_max_attempts já rodou em check_config.
    """
    sync_cfg = config.get("sync") or {}
    return sync_cfg.get("max_attempts", DEFAULT_MAX_ATTEMPTS)


# ── retry.* (issue #303) ──────────────────────────────────────────────────────
# Parâmetros do retry inline SEGURO, aplicáveis SOMENTE ao caso
# DEFINITE_NOT_STARTED (não-inicialização comprovada mecanicamente, ex.:
# kiro-cli ausente no PATH). NÃO se aplicam ao UNKNOWN_OUTCOME (fail-closed, sem
# retry inline — ver ADR doc/architecture/retry-kiro-cli/idempotencia.md).
DEFAULT_RETRY_MAX_TENTATIVAS = 3
DEFAULT_RETRY_BACKOFF_INICIAL_SEG = 30
DEFAULT_RETRY_BACKOFF_FATOR = 2.0


@dataclass
class RetryConfig:
    """Configuração resolvida do retry seguro (DEFINITE_NOT_STARTED)."""
    max_tentativas: int = DEFAULT_RETRY_MAX_TENTATIVAS
    backoff_inicial_seg: int = DEFAULT_RETRY_BACKOFF_INICIAL_SEG
    backoff_fator: float = DEFAULT_RETRY_BACKOFF_FATOR


def validate_retry(config: dict) -> None:
    """Valida a chave opcional `retry` do pipe.yml (issue #303).

    Restrições (cada violação levanta ConfigError nomeando a chave):
    - `retry.max_tentativas`: inteiro > 0 (rejeita 0, negativos, bool, float, str);
    - `retry.backoff_inicial_seg`: inteiro >= 0 (rejeita negativos, bool, float, str);
    - `retry.backoff_fator`: número >= 1.0 (rejeita < 1.0, bool, str).

    Ausência da chave `retry` (ou de qualquer subchave) é válida: os defaults
    são aplicados por `resolve_retry`. `bool` é rejeitado ANTES de int/number
    (True/False são instâncias de int em Python).
    """
    retry_cfg = config.get("retry") or {}

    if "max_tentativas" in retry_cfg:
        value = retry_cfg["max_tentativas"]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ConfigError(
                f"retry.max_tentativas: deve ser inteiro > 0 (valor recebido: {value!r})"
            )

    if "backoff_inicial_seg" in retry_cfg:
        value = retry_cfg["backoff_inicial_seg"]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ConfigError(
                f"retry.backoff_inicial_seg: deve ser inteiro >= 0 "
                f"(valor recebido: {value!r})"
            )

    if "backoff_fator" in retry_cfg:
        value = retry_cfg["backoff_fator"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 1.0:
            raise ConfigError(
                f"retry.backoff_fator: deve ser número >= 1.0 "
                f"(valor recebido: {value!r})"
            )


def resolve_retry(config: dict) -> RetryConfig:
    """Resolve os parâmetros `retry.*` com defaults seguros.

    Default quando a chave (ou subchave) está ausente:
    `max_tentativas=3`, `backoff_inicial_seg=30`, `backoff_fator=2.0`.
    Não valida — assume que `validate_retry` já rodou em `check_config`.
    """
    retry_cfg = config.get("retry") or {}
    return RetryConfig(
        max_tentativas=retry_cfg.get("max_tentativas", DEFAULT_RETRY_MAX_TENTATIVAS),
        backoff_inicial_seg=retry_cfg.get(
            "backoff_inicial_seg", DEFAULT_RETRY_BACKOFF_INICIAL_SEG),
        backoff_fator=retry_cfg.get("backoff_fator", DEFAULT_RETRY_BACKOFF_FATOR),
    )


def check_config() -> dict:
    """Valida e retorna configuração do pipe.yml."""
    _validate_env()
    
    if not PIPE_FILE.exists():
        raise ConfigError(f"Arquivo {PIPE_FILE} não encontrado")
    
    with open(PIPE_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    if not config:
        raise ConfigError("pipe.yml está vazio")
    
    if "log" in config:
        _validate_log(config["log"])
    
    _require(config, "sleep", "pipe.yml")
    _validate_sleep(config["sleep"])

    validate_max_attempts(config)
    validate_retry(config)

    project = _require(config, "project", "pipe.yml")
    _validate_project(project)

    git = _require(config, "git", "pipe.yml")
    _validate_git(git)
    
    agents = _require(config, "agents", "pipe.yml")
    _validate_agents(agents)
    
    known_agents = {
        agent_id
        for platform in agents.values()
        for agent_id in platform
    }
    boards = _require(config, "boards", "pipe.yml")
    _validate_boards(boards, known_agents)
    
    return config
