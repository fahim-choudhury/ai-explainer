"""Pronunciation check: transcribe each narration line with Whisper and compare it to the script.

Called by `xv asr <project> [--threshold 0.06] [--model small.en] [-o FILE]`.

Writes <project>/audio/asr-check.md listing lines whose transcript differs from the
spoken form of the script (lexicon applied) by more than the threshold
(character error rate on letters, ignoring spacing and punctuation). Flagged lines usually mean a
mispronounced acronym or name. Listen to the line, then either fix it with a lexicon
entry ("say" in script.json or lib/tts/lexicon.json) and re-run synth, or, if it
sounds right (NGINX -> "engine x"), add the term to "asr_accept" in script.json.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui
from synth import load_lexicon, spoken
import numpy as np
import soundfile as sf

NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"}
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def cardinal(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    for size, name in ((10**9, "billion"), (10**6, "million"), (1000, "thousand"), (100, "hundred")):
        if n >= size:
            q, r = divmod(n, size)
            return f"{cardinal(q)} {name}" + (f" {cardinal(r)}" if r else "")


def year(n):
    """2026 -> twenty twenty six, 2005 -> two thousand five, 1999 -> nineteen ninety nine."""
    hi, lo = divmod(n, 100)
    if lo == 0 or (2000 <= n < 2010):
        return cardinal(n)
    return f"{cardinal(hi)} {cardinal(lo)}"


def numbers_to_words(s, years=True):
    """Whisper writes numbers as digits and symbols; the script writes words. Spell the digits out."""
    s = re.sub(r"(\d),(\d{3})", r"\1\2", s)
    s = re.sub(r"\$(\d+)", r"\1 dollars", s)
    s = re.sub(r"€(\d+)", r"\1 euros", s)
    s = re.sub(r"£(\d+)", r"\1 pounds", s)
    s = re.sub(r"(\d+)\s?%", r"\1 percent", s)
    s = re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", s)
    def word(m):
        n = int(m.group(0))
        return f" {year(n) if years and len(m.group(0)) == 4 and 1100 <= n <= 2099 else cardinal(n)} "
    return re.sub(r"\d+", word, s)


def norm(s, years=True):
    """Letters only, spaces and punctuation dropped: 'wire guard' == 'WireGuard', 'A-W-S' == 'AWS'."""
    s = numbers_to_words(s, years)
    s = s.lower().replace("-", " ").replace("/", " ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\ba (hundred|thousand|million)\b", r"one \1", s)
    s = "".join(NUM.get(w, w) for w in s.split())
    return "".join(NUM.get(c, c) for c in s)  # digits inside tokens: "bsd3" == "bsd three"


def wer(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i in range(1, len(ref) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(hyp) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (ref[i - 1] != hyp[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(hyp)] / max(1, len(ref))


def check(proj, threshold=0.06, model_name="small.en", output=None):
    """Transcribe every line, write the report, return (flagged, total, report path)."""
    proj = Path(proj).resolve()
    timings = json.loads((proj / "audio/timings.json").read_text())
    sf_ = proj / "script/script.json"
    script = json.loads(sf_.read_text()) if sf_.exists() else {}
    lex = load_lexicon(script) if script else {}
    accept = {w.lower() for w in script.get("asr_accept", [])}
    audio, sr = sf.read(proj / "audio/narration.wav", dtype="float32")
    x16 = np.interp(np.arange(0, len(audio), sr / 16000), np.arange(len(audio)), audio).astype(np.float32)

    from faster_whisper import WhisperModel
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from paths import model as model_path
    local = model_path(f"whisper/{model_name}")
    model = WhisperModel(str(local) if local.exists() else model_name, device="cpu", compute_type="int8")
    rows, flagged = [], 0
    for sc in timings["scenes"]:
        for ln in sc["lines"]:
            seg = x16[int(ln["start"] * 16000): int(ln["end"] * 16000) + 1600]
            hyp = " ".join(s.text.strip() for s in model.transcribe(seg, language="en", beam_size=5, temperature=0.0, condition_on_previous_text=False)[0])
            said = spoken(ln["text"], lex)
            e = min(wer(norm(said), norm(hyp, years=y)) for y in (True, False))
            # acronyms and CamelCase names must be heard as written (catches "NGINX" -> "Engine X")
            missing = [w for w in re.findall(r"\b(?:[A-Z]{2,}[a-z]?|[A-Z][a-z]+[A-Z]\w*)\b", said)
                       if w.lower() not in accept and norm(w) not in norm(hyp)]
            bad = e > threshold or missing
            if bad:
                flagged += 1
                note = f", terms not heard as written: {', '.join(missing)}" if missing else ""
                rows.append(f"### {sc['id']} @ {ln['start']:.1f}s  (CER {e:.0%}{note})\n- script: {ln['text']}\n- heard:  {hyp}\n")
            ui.info(f"{'FLAG' if bad else ' ok '} {e:5.0%}  {ln['text'][:70]}{'  missing: ' + ','.join(missing) if missing else ''}")
    total = sum(len(s["lines"]) for s in timings["scenes"])
    report = f"# ASR pronunciation check\n\nModel `{model_name}`, threshold {threshold:.0%}. {flagged} of {total} lines flagged.\n\n" + ("\n".join(rows) or "No lines flagged.\n")
    out = Path(output) if output else proj / "audio/asr-check.md"
    out.write_text(report)
    ui.out(f"{out}  {flagged} of {total} lines flagged")
    return flagged, total, out
