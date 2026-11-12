import json, subprocess
import pytest
from conftest import set_script, set_timings
import state


def log(proj):
    return subprocess.run(["git", "log", "--format=%s"], cwd=proj, capture_output=True, text=True).stdout.splitlines()


def touch(proj, text):
    with open(proj / "brief.md", "a") as f:
        f.write(text + "\n")


def test_commit_numbers_versions_from_history(project):
    touch(project, "a"); state.cmd_commit(project, ["brief", "first"])
    touch(project, "b"); state.cmd_commit(project, ["brief", "second"])
    touch(project, "c"); state.cmd_commit(project, ["script", "draft"])
    assert log(project)[:3] == ["script v1: draft", "brief v2: second", "brief v1: first"]
    assert "(script v1 awaiting review)" in state.Status(project).stage()


def test_commit_has_no_trailer(project):
    touch(project, "a"); state.cmd_commit(project, ["brief", "x"])
    body = subprocess.run(["git", "log", "-1", "--format=%B"], cwd=project, capture_output=True, text=True).stdout
    assert body.strip() == "brief v1: x"


def test_maintenance_commit_keeps_stage(project):
    before = state.Status(project).stage()
    touch(project, "a"); state.cmd_commit(project, ["maintenance", "tidy"])
    assert log(project)[0] == "maintenance: tidy" and state.Status(project).stage() == before


def test_gate_refuses_with_open_feedback(project):
    state.cmd_feedback(project, ["add", "shorter intro", "fix colour"])
    with pytest.raises(SystemExit):
        state.cmd_gate(project, ["0"])
    state.cmd_feedback(project, ["done", "1", "2"])
    state.cmd_gate(project, ["0"])
    st = state.Status(project)
    assert st.gates()["0"][1] == "approved" and st.stage() == "1-2 research and script"
    assert log(project)[0] == "gate 0 approved"


def test_skip_gate(project):
    state.cmd_gate(project, ["7", "--skip", "YouTube only"])
    assert state.Status(project).gates()["7"][1] == "skipped"
    assert log(project)[0] == "gate 7 skipped: YouTube only"


def test_decision_appends(project):
    state.cmd_decision(project, ["Voice", "speed", "1.05"])
    assert any(t == "Voice speed 1.05" for _, t in state.Status(project).items("Decisions"))


def test_script_md_staleness_is_content_based(project):
    from xv import script_md_text
    (project / "script/script.md").write_text(script_md_text(project))
    assert not any("script.md" in s for s in state.stale(project))
    set_script(project, [("intro", ["A new line."])])
    assert any("script.md" in s for s in state.stale(project))


def test_changed_lines_reports_new_timestamps(project):
    set_script(project, [("intro", ["First line.", "Second line."])])
    subprocess.run(["git", "commit", "-qam", "script v1"], cwd=project, check=True)
    set_script(project, [("intro", ["First line.", "Second line, edited."])])
    set_timings(project, [("intro", [(0.5, 2.0), (2.4, 5.6)])])
    rows, removed = state.changed_lines(project, "HEAD")
    assert len(rows) == 1 and rows[0].startswith("0:02-0:06") and "Second line, edited." in rows[0]


def test_voice_only_change_is_labelled(project):
    set_script(project, [("intro", ["The control plane."])])
    subprocess.run(["git", "commit", "-qam", "v1"], cwd=project, check=True)
    set_script(project, [("intro", ["The control plane."])], say={"\\bcontrol plane\\b": "control-plane"})
    set_timings(project, [("intro", [(0.5, 2.0)])])
    rows, _ = state.changed_lines(project, "HEAD")
    assert "[voice only]" in rows[0]
