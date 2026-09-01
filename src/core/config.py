"""Config core - carrega e valida pipe.yml."""

from pathlib import Path
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


CONTEXTS_DIR = Path("contexts")


def _validate_agents(agents: dict):
    empty = []
    for platform_id, platform in agents.items():
        for agent_id, agent_cfg in platform.items():
            _require(agent_cfg, "name", f"agents.{platform_id}.{agent_id}")
            # Garantir que o arquivo de contexto existe
            ctx_file = CONTEXTS_DIR / platform_id / f"{agent_id}.md"
            ctx_file.parent.mkdir(parents=True, exist_ok=True)
            if not ctx_file.exists():
                ctx_file.write_text("", encoding="utf-8")
            if not ctx_file.read_text(encoding="utf-8").strip():
                empty.append(str(ctx_file))
    if empty:
        raise ConfigError(
            "Arquivos de contexto vazios (preencha antes de executar):\n  - "
            + "\n  - ".join(empty)
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
        
        for col_id, col in columns.items():
            _require(col, "name", f"boards.{board_id}.columns.{col_id}")
            for ev in ("on_in", "on_out"):
                if ev in col and not isinstance(col[ev], list):
                    raise ConfigError(
                        f"boards.{board_id}.columns.{col_id}.{ev}: deve ser uma lista"
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


CROSS_BOARD_LINKS_VALUES = {"enabled", "suspended"}


def validate_cross_board_parent_links(config: dict) -> None:
    """Valida a chave opcional safety.cross_board_parent_links do pipe.yml.

    Se presente, deve ser a string "enabled" ou "suspended". Levanta
    ConfigError com mensagem acionável para qualquer outro valor (inclusive
    tipos não-string, vazio ou variações de caixa). Ausência da chave ou de
    toda a seção `safety` é permitida e equivale a "enabled" (ver
    resolve_cross_board_parent_links).
    """
    safety_cfg = config.get("safety") or {}
    if "cross_board_parent_links" not in safety_cfg:
        return
    value = safety_cfg["cross_board_parent_links"]
    if value not in CROSS_BOARD_LINKS_VALUES:
        raise ConfigError(
            "safety.cross_board_parent_links: deve ser 'enabled' ou 'suspended' "
            f"(valor recebido: {value!r})"
        )


def resolve_cross_board_parent_links(config: dict) -> str:
    """Retorna o valor efetivo de safety.cross_board_parent_links.

    Default "enabled" quando a chave ou a seção `safety` estão ausentes.
    Não valida — assume que validate_cross_board_parent_links já rodou em
    check_config. Usada pelo gate de contingência (outra task) a cada
    tentativa de nova relação pai/filho, relendo o pipe.yml do disco por
    mtime a cada chamada (sem cache em memória do processo) — ver
    load_current_config.
    """
    return (config.get("safety") or {}).get("cross_board_parent_links", "enabled")


def load_current_config() -> dict:
    """Recarrega o pipe.yml do disco (sem validação completa).

    Usada pelo gate de contingência para reler safety.cross_board_parent_links
    a cada tentativa de nova relação pai/filho, sem exigir restart do
    processo — a config carregada uma única vez no startup (check_config)
    não reflete edições posteriores ao pipe.yml em disco.

    Levanta ConfigError se o arquivo não existir ou estiver vazio (mesmas
    mensagens de check_config). Não roda as demais validações (git, agents,
    boards) — é uma leitura leve para uma única chave de segurança, chamada
    potencialmente a cada relação pai/filho durante o loop principal;
    repetir a validação completa a cada chamada seria desproporcional ao
    propósito (reler uma chave), mesmo que o custo de I/O de um arquivo
    pequeno já seja aceitável.
    """
    if not PIPE_FILE.exists():
        raise ConfigError(f"Arquivo {PIPE_FILE} não encontrado")

    with open(PIPE_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config:
        raise ConfigError("pipe.yml está vazio")

    return config


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

    validate_cross_board_parent_links(config)

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
