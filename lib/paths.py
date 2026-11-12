"""Where everything lives. The workspace (video projects) is separate from this repository.

Workspace, first match wins:
  1. $XV_WORKSPACE
  2. `workspace = "..."` in <repo>/xv.toml (copy xv.toml.example)
  3. <repo>/workspace
"""
import os, tomllib
from pathlib import Path

LIB = Path(__file__).resolve().parent
REPO = LIB.parent
PY = REPO / ".venv/bin/python"
MODELS = REPO / "models"
STAMP = REPO / ".xv-verified"


def config():
    f = REPO / "xv.toml"
    return tomllib.loads(f.read_text()) if f.exists() else {}


def workspace():
    ws = os.environ.get("XV_WORKSPACE") or config().get("workspace") or str(REPO / "workspace")
    return Path(os.path.expanduser(ws)).resolve()


def model(name):
    """Path of a file listed in deps/models.lock, e.g. model("kokoro/kokoro-v1.0.onnx")."""
    return MODELS / name
