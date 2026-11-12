"""Where everything lives. The workspace (video projects) is separate from this repository.

Workspace, first match wins (flags, then environment, then project config, then user config):
  1. --workspace DIR
  2. $XV_WORKSPACE
  3. `workspace = "..."` in <repo>/xv.toml (copy xv.toml.example)
  4. `workspace = "..."` in $XDG_CONFIG_HOME/xv/config.toml (default ~/.config/xv/config.toml)
  5. <repo>/workspace
"""
import os, tomllib
from pathlib import Path

LIB = Path(__file__).resolve().parent
REPO = LIB.parent
PY = REPO / ".venv/bin/python"
MODELS = REPO / "models"
STAMP = REPO / ".xv-verified"
OVERRIDE = None  # set from --workspace


def user_config_file():
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "xv/config.toml"


def config():
    """Repository xv.toml over the user config file."""
    merged = {}
    for f in (user_config_file(), REPO / "xv.toml"):
        if f.exists():
            merged.update(tomllib.loads(f.read_text()))
    return merged


def workspace():
    ws = OVERRIDE or os.environ.get("XV_WORKSPACE") or config().get("workspace") or str(REPO / "workspace")
    return Path(os.path.expanduser(ws)).resolve()


def model(name):
    """Path of a file listed in deps/models.json, e.g. model("kokoro/kokoro-v1.0.onnx")."""
    return MODELS / name


def version():
    return tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]
