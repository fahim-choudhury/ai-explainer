"""Deterministic text checks for an explainer project (`xv lint`).

narration  every line in script/script.json: the narration rules in AGENTS.md
prose      every text deliverable: STYLE.md patterns that a regex can catch

Findings are errors (E), which block presenting, or warnings (W), which need a human look.
"""
import json, re, sys
from pathlib import Path

MAX_WORDS = 25

# Acronyms a technical audience reads without expansion. A project overrides with
# "acronyms" (expand these) and "acronyms_known" (never expand these) in script.json.
KNOWN = {"AI", "API", "CPU", "DNS", "GPU", "HTTP", "HTTPS", "ID", "IP", "OK", "PC", "QR", "RAM", "SSH", "TCP", "TLS", "TV", "UDP", "URL", "USB", "VPN"}

BANNED_WORDS = ["delve", "delves", "certainly", "utilize", "utilise", "utilizes", "robust", "streamline", "streamlines", "harness",
                "quietly", "deeply", "fundamentally", "remarkably", "arguably", "tapestry", "landscape", "paradigm", "synergy",
                "ecosystem", "load-bearing", "seamless", "seamlessly", "game-changer", "unlock", "unlocks", "supercharge"]
BANNED_PHRASES = ["it's worth noting", "it bears mentioning", "importantly,", "interestingly,", "notably,", "let's break",
                  "let's unpack", "let's explore", "let's dive", "dive in", "here's the thing", "here's the kicker",
                  "here's what", "but here's", "in conclusion", "to sum up", "in summary", "think of it as", "imagine a world",
                  "serves as", "stands as", "despite these challenges", "as we all know", "famously", "notoriously",
                  "the result?", "the answer?", "not just", "isn't just", "doesn't just"]
UNICODE = {"—": "em dash", "–": "en dash", "→": "unicode arrow", "←": "unicode arrow", "⇒": "unicode arrow",
           "“": "smart quote", "”": "smart quote", "‘": "smart quote", "’": "smart quote", "…": "ellipsis character"}
NARR_SYMBOLS = re.compile(r"[()\[\]{}/\\%$€£&@#*_<>=+~|\";]")


class Report:
    def __init__(self, proj):
        self.proj, self.findings = proj, []

    def add(self, f, line, level, rule, msg):
        rel = str(f.relative_to(self.proj)) if isinstance(f, Path) and f.is_relative_to(self.proj) else str(f)
        self.findings.append({"file": rel, "line": line, "level": level, "rule": rule, "message": msg})

    @property
    def errors(self):
        return sum(f["level"] == "E" for f in self.findings)

    @property
    def warnings(self):
        return sum(f["level"] == "W" for f in self.findings)

    @property
    def rows(self):
        return [f"{f['file']}:{f['line']}: {f['level']} {f['rule']}: {f['message']}" for f in self.findings]


def acronyms_in(text):
    return re.findall(r"\b[A-Z][A-Z0-9]*[A-Z][A-Z0-9]*s?\b", text)


def narration(proj, r):
    f = proj / "script/script.json"
    s = json.loads(f.read_text())
    raw = f.read_text().splitlines()
    expand = s.get("acronyms", {})
    known = KNOWN | set(s.get("acronyms_known", []))
    seen = set()
    flat = [(sc["id"], i, ln) for sc in s["scenes"] for i, ln in enumerate(sc["lines"])]

    def where(text):
        key = json.dumps(text, ensure_ascii=False)[1:-1][:40]
        return next((n for n, l in enumerate(raw, 1) if key in l), 0)

    for k, (sid, i, ln) in enumerate(flat):
        at = where(ln)
        tag = f"{sid}[{i}]"
        n = len(ln.split())
        if n > MAX_WORDS:
            r.add(f, at, "E", "line-length", f"{tag} has {n} words (max {MAX_WORDS}); split it")
        if re.search(r"(?<![A-Za-z])\d", ln):
            r.add(f, at, "E", "digits", f"{tag} write numbers as words: {ln!r}")
        elif re.search(r"\d", ln):
            r.add(f, at, "W", "digits", f"{tag} name with digits; check it has a spoken form in \"say\": {ln!r}")
        if re.search(r"https?://|www\.|\.\w{2,3}/", ln):
            r.add(f, at, "E", "url", f"{tag} no URLs in narration")
        for m in sorted(set(NARR_SYMBOLS.findall(ln))):
            r.add(f, at, "E", "symbol", f"{tag} symbol {m!r} in narration")
        for ch, name in UNICODE.items():
            if ch in ln:
                r.add(f, at, "E", "unicode", f"{tag} {name}")
        for a in acronyms_in(ln):
            base = a[:-1] if a.endswith("s") and len(a) > 2 and a[-2].isupper() else a
            if base in seen or base in known:
                continue
            seen.add(base)
            if base in expand:
                near = " ".join(x[2] for x in flat[max(0, k - 1):k + 2]).lower()
                if expand[base].lower() not in near:
                    r.add(f, at, "E", "acronym", f"{tag} first use of {base}: expansion {expand[base]!r} not in this or a neighbouring line")
            else:
                r.add(f, at, "W", "acronym", f"{tag} first use of {base}: add it to script.json \"acronyms\" (expand) or \"acronyms_known\"")
    for key in expand:
        if key not in seen:
            r.add(f, 0, "W", "acronym", f"\"acronyms\" lists {key}, which the narration never uses")


def prose_files(proj):
    out = [proj / p for p in ("brief.md", "research/findings.md", "script/storyboard.md",
                              "publish/youtube/description.txt", "publish/youtube/pinned-comment.txt")]
    out += sorted((proj / "publish/social").glob("*.md"))
    out += sorted((proj / "publish/social/shorts").glob("*.md"))
    return [f for f in out if f.exists() and f.name != "README.md"]


def check_prose(f, lines, r):
    for n, line in enumerate(lines, 1):
        text = re.sub(r"`[^`]*`", "", line)  # code spans are exempt
        low = text.lower()
        for ch, name in UNICODE.items():
            if ch in text:
                r.add(f, n, "E" if ch in "—→←⇒" else "W", "unicode", name)
        for w in BANNED_WORDS:
            if re.search(rf"\b{re.escape(w)}\b", low):
                r.add(f, n, "W", "whip-word", w)
        for p in BANNED_PHRASES:
            if p in low:
                r.add(f, n, "W", "whip-phrase", p)
        if re.search(r"\b(two|three|four|five|six|seven|eight|nine|ten) (things|reasons|ways|steps|questions|constraints|points)\b", low):
            r.add(f, n, "W", "counting", "names a count before a list")
        if re.match(r"#+ (what|why|where|how|when)\b", low):
            r.add(f, n, "W", "wh-heading", "heading built on a Wh-word")


def prose(proj, r):
    for f in prose_files(proj):
        check_prose(f, f.read_text().splitlines(), r)
    meta = proj / "publish/youtube/metadata.json"
    if meta.exists():
        m = json.loads(meta.read_text())
        check_prose(meta, [m.get("title", "")] + list(m.get("chapter_titles", {}).values()), r)


def run(proj, only=None):
    r = Report(proj)
    if only in (None, "narration"):
        narration(proj, r)
    if only in (None, "prose"):
        prose(proj, r)
    return r
