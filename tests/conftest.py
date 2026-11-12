import json, os, shutil, subprocess, sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent
for sub in ("lib", "lib/tts", "lib/youtube"):
    sys.path.insert(0, str(REPO / sub))


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project made from template/, as a git repo with one commit. No models needed."""
    for k, v in {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
                 "GIT_COMMITTER_EMAIL": "t@example.com"}.items():
        monkeypatch.setenv(k, v)
    p = tmp_path / "explainer-test"
    shutil.copytree(REPO / "template", p)
    for f in p.rglob("*"):
        if f.is_file() and f.suffix in {".md", ".json", ".tsx", ".ts"}:
            f.write_text(f.read_text().replace("{{SLUG}}", "test").replace("{{TITLE}}", "Test").replace("{{DATE}}", "2026-01-01"))
    subprocess.run(["git", "init", "-q"], cwd=p, check=True)
    subprocess.run(["git", "add", "-A"], cwd=p, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=p, check=True)
    return p


def set_script(proj, scenes, **extra):
    f = proj / "script/script.json"
    s = json.loads(f.read_text())
    s["scenes"] = [{"id": i, "title": i, "lines": lines} for i, lines in scenes]
    s.update(extra)
    f.write_text(json.dumps(s, indent=2) + "\n")


def set_timings(proj, scenes):
    """scenes: [(id, [(start, end), ...]), ...]"""
    out, total = [], 0
    for sid, lines in scenes:
        out.append({"id": sid, "start": lines[0][0], "end": lines[-1][1],
                    "lines": [{"text": f"{sid} {i}", "start": a, "end": b} for i, (a, b) in enumerate(lines)]})
        total = lines[-1][1]
    (proj / "audio/timings.json").write_text(json.dumps({"fps": 30, "scenes": out, "total": total}))
