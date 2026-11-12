import pytest
from asr_check import cardinal, year, norm, wer


@pytest.mark.parametrize("n,words", [(0, "zero"), (15, "fifteen"), (45, "forty five"), (100, "one hundred"),
                                     (2026, "two thousand twenty six"), (1420, "one thousand four hundred twenty")])
def test_cardinal(n, words):
    assert cardinal(n) == words


@pytest.mark.parametrize("n,words", [(2026, "twenty twenty six"), (2005, "two thousand five"), (1999, "nineteen ninety nine"), (2000, "two thousand")])
def test_year(n, words):
    assert year(n) == words


@pytest.mark.parametrize("script,heard", [
    ("as of November twenty twenty-six", "as of November 2026"),
    ("eight dollars per user", "$8 per user"),
    ("six euros", "€6"),
    ("one hundred machines", "100 machines"),
    ("one hundred machines", "a hundred machines"),
    ("forty-five pairs", "45 pairs"),
    ("WireGuard", "wire guard"),
])
def test_spoken_forms_match_transcripts(script, heard):
    assert min(wer(norm(script), norm(heard, years=y)) for y in (True, False)) == 0


def test_a_real_difference_still_counts():
    assert wer(norm("engine x"), norm("NGINX")) > 0.06
