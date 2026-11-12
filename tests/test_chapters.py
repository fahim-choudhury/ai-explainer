from conftest import set_timings
from package import chapters


def test_chapters_and_folding(project):
    set_timings(project, [("hook", [(0, 15)]), ("main", [(16, 70)]), ("close", [(71, 120)]), ("outro", [(121, 126)])])
    text, warn = chapters(project, {"hook": "Intro", "main": "How it works", "close": "Which fits", "outro": ""})
    assert text.splitlines() == ["0:00 Intro", "0:16 How it works", "1:11 Which fits"]
    assert warn == []


def test_short_chapter_warns(project):
    set_timings(project, [("hook", [(0, 15)]), ("main", [(16, 70)]), ("outro", [(71, 76)])])
    _, warn = chapters(project, {"hook": "Intro", "main": "Main", "outro": "Sources"})
    assert any("under 10 s" in w for w in warn)


def test_missing_and_unknown_titles_warn(project):
    set_timings(project, [("hook", [(0, 15)]), ("main", [(16, 70)]), ("end", [(71, 120)])])
    _, warn = chapters(project, {"hook": "Intro", "main": "Main", "typo": "x"})
    assert any("no entry for scene 'end'" in w for w in warn) and any("unknown scene 'typo'" in w for w in warn)
