from pathlib import Path
from conftest import set_script
import lint


def run_narration(proj):
    r = lint.Report(proj)
    lint.narration(proj, r)
    return r


def rules(r, level):
    return [row.split(f" {level} ")[1].split(":")[0] for row in r.rows if f" {level} " in row]


def test_clean_line_passes(project):
    set_script(project, [("intro", ["Each device keeps its own private key."])])
    assert run_narration(project).rows == []


def test_line_over_25_words_is_an_error(project):
    set_script(project, [("intro", [" ".join(["word"] * 26) + "."])])
    assert "line-length" in rules(run_narration(project), "E")


def test_numbers_must_be_words(project):
    set_script(project, [("intro", ["It costs 8 dollars."])])
    assert "digits" in rules(run_narration(project), "E")


def test_digits_inside_a_name_only_warn(project):
    set_script(project, [("intro", ["The interface is called wg0 here."])])
    r = run_narration(project)
    assert "digits" in rules(r, "W") and r.errors == 0


def test_symbols_and_urls_are_errors(project):
    set_script(project, [("intro", ["Visit https://example.com (now)."])])
    e = rules(run_narration(project), "E")
    assert "url" in e and "symbol" in e


def test_em_dash_in_narration_is_an_error(project):
    set_script(project, [("intro", ["One idea — then another."])])
    assert "unicode" in rules(run_narration(project), "E")


def test_undeclared_acronym_warns(project):
    set_script(project, [("intro", ["Peers use STUN to find their address."])])
    assert "acronym" in rules(run_narration(project), "W")


def test_declared_acronym_needs_expansion_nearby(project):
    set_script(project, [("intro", ["Peers use STUN.", "Nothing else here.", "Still nothing."])],
               acronyms={"STUN": "Session Traversal Utilities for NAT"}, acronyms_known=["NAT"])
    assert "acronym" in rules(run_narration(project), "E")


def test_declared_acronym_with_expansion_in_next_line_passes(project):
    set_script(project, [("intro", ["Peers ask a STUN server.", "STUN is short for Session Traversal Utilities for NAT."])],
               acronyms={"STUN": "Session Traversal Utilities for NAT"}, acronyms_known=["NAT"])
    assert run_narration(project).rows == []


def test_known_acronyms_and_plurals_pass(project):
    set_script(project, [("intro", ["Both use UDP and assign IPs to each device."])])
    assert run_narration(project).rows == []


def test_prose_rules(tmp_path):
    f = tmp_path / "copy.md"
    r = lint.Report(tmp_path)
    lint.check_prose(f, ["A robust tool — truly.", "## Why it matters", "It's worth noting the cost."], r)
    joined = "\n".join(r.rows)
    assert " E unicode" in joined and "whip-word: robust" in joined and "wh-heading" in joined and "whip-phrase" in joined


def test_code_spans_are_exempt(tmp_path):
    r = lint.Report(tmp_path)
    lint.check_prose(tmp_path / "x.md", ["Run `robust --leverage` now."], r)
    assert r.rows == []
