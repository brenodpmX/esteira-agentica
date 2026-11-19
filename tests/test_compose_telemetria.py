import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
OVERRIDE = ROOT / "compose.telemetria.yml"
BASE = ROOT / "docker-compose.yml"
DOCKERFILE = ROOT / "Dockerfile"
VERSIONS_ENV = ROOT / "docker" / "versions.env"


def _docker_ok() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "compose", "version"], capture_output=True,
                              timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


DOCKER_SKIP = pytest.mark.skipif(not _docker_ok(), reason="docker compose indisponível")


def _versions() -> dict:
    out = {}
    for line in VERSIONS_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


@pytest.mark.parametrize("pacote,chave", [
    ("opentelemetry-sdk", "OPENTELEMETRY_SDK_VERSION"),
    ("opentelemetry-exporter-otlp", "OPENTELEMETRY_EXPORTER_OTLP_VERSION"),
])
def test_ct_infra_01_dependencias_otel_pinadas(pacote, chave):
    texto = DOCKERFILE.read_text(encoding="utf-8")
    m = re.search(rf"pip install --no-cache-dir [^\n]*\b{re.escape(pacote)}==(\d+\.\d+\.\d+)\b",
                  texto)
    assert m, f"{pacote} sem versão exata no Dockerfile"
    assert not re.search(rf"{re.escape(pacote)}\s*(>=|~=|<)", texto)
    assert _versions().get(chave) == m.group(1)


def test_ct_infra_02_override_declara_rede_externa_no_dind():
    data = yaml.safe_load(OVERRIDE.read_text(encoding="utf-8"))
    rede = data["networks"]["esteira-telemetria"]
    assert rede["external"] is True
    assert rede.get("name", "esteira-telemetria") == "esteira-telemetria"
    redes_dind = data["services"]["dind"]["networks"]
    assert "esteira-telemetria" in redes_dind
    assert "default" in redes_dind
    assert set(data["services"]) == {"dind"}


def test_ct_infra_04_base_nao_cita_a_rede():
    assert "esteira-telemetria" not in BASE.read_text(encoding="utf-8")


def _config(tmp_path, *arquivos):
    for nome in ("docker-compose.yml", "compose.telemetria.yml"):
        shutil.copy(ROOT / nome, tmp_path / nome)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    (tmp_path / "k").write_text("", encoding="utf-8")
    cmd = ["docker", "compose"]
    for a in arquivos:
        cmd += ["-f", a]
    return subprocess.run(cmd + ["config"], cwd=tmp_path, capture_output=True, text=True,
                          timeout=60, env={"PATH": "/usr/local/bin:/usr/bin:/bin",
                                           "SSH_KEY_FILE_HOST": str(tmp_path / "k")})


@DOCKER_SKIP
def test_ct_infra_02_compose_config_com_override(tmp_path):
    out = _config(tmp_path, "docker-compose.yml", "compose.telemetria.yml")
    assert out.returncode == 0, out.stderr
    data = yaml.safe_load(out.stdout)
    assert "esteira-telemetria" in data["services"]["dind"]["networks"]
    assert data["networks"]["esteira-telemetria"]["external"] is True
    assert data["services"]["pipe"]["network_mode"] == "service:dind"


@DOCKER_SKIP
def test_ct_infra_04_compose_base_sem_override(tmp_path):
    out = _config(tmp_path, "docker-compose.yml")
    assert out.returncode == 0, out.stderr
    assert "esteira-telemetria" not in out.stdout
