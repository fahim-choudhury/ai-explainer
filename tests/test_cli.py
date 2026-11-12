"""The xv command line itself: help, version, errors, exit codes, JSON, stdout vs stderr."""
import json, os, subprocess
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent
PY = REPO / ".venv/bin/python"


def xv(*args, ws=None):
    env = {**os.environ, "NO_COLOR": "1"}
    if ws:
        env["XV_WORKSPACE"] = str(ws)
    return subprocess.run([PY, REPO / "lib/xv.py", *map(str, args)], capture_output=True, text=True, env=env)


def test_no_args_shows_help():
    r = xv()
    assert r.returncode == 0 and "Commands:" in r.stdout and "Exit codes" in r.stdout


@pytest.mark.parametrize("args", [["--help"], ["-h"], ["help"], ["help", "commit"], ["commit", "--help"], ["commit", "-h"]])
def test_help_forms(args):
    r = xv(*args)
    assert r.returncode == 0 and "usage: xv" in r.stdout


def test_subcommand_help_has_examples():
    assert "Examples:" in xv("help", "gate").stdout


def test_version():
    r = xv("--version")
    assert r.returncode == 0 and r.stdout.startswith("xv ")


def test_typo_suggests_command():
    r = xv("stauts", "x")
    assert r.returncode == 2 and "status" in r.stderr


def test_unknown_project_is_exit_1_with_hint(tmp_path):
    r = xv("status", "nope", ws=tmp_path)
    assert r.returncode == 1 and "xv: error:" in r.stderr and r.stdout == ""


def test_status_json_and_global_flags_after_command(project):
    r = xv("status", project.name, "--json", "-q", ws=project.parent)
    assert r.returncode == 0 and json.loads(r.stdout)["current_gate"] == "0"


def test_workspace_flag(project, tmp_path):
    r = xv("--workspace", project.parent, "list", "--json", ws=tmp_path)
    assert [p["project"] for p in json.loads(r.stdout)["projects"]] == [project.name]


def test_lint_json_and_exit_code(project):
    f = project / "script/script.json"
    s = json.loads(f.read_text()); s["scenes"][0]["lines"][0] = "It costs 8 dollars."
    f.write_text(json.dumps(s))
    r = xv("lint", project.name, "--json", ws=project.parent)
    d = json.loads(r.stdout)
    assert r.returncode == 1 and d["errors"] >= 1 and d["findings"][0]["rule"] == "digits"


def test_feedback_cycle_and_hints_on_stderr(project):
    r = xv("feedback", project.name, "add", "shorter intro", ws=project.parent)
    assert r.stdout.strip() == "1. shorter intro"
    r = xv("gate", project.name, "0", ws=project.parent)
    assert r.returncode == 1 and "--force" in r.stderr
    r = xv("gate", project.name, "0", "--dry-run", "--force", ws=project.parent)
    assert r.returncode == 0 and r.stdout.startswith("would commit: gate 0 approved")


def test_commit_kind_choices(project):
    r = xv("commit", project.name, "scirpt", "x", ws=project.parent)
    assert r.returncode == 2 and "script" in r.stderr
