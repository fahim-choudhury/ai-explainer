"""Project state: STATUS.md, commits, review packages. Everything here is derived from files and git.

Functions return data and raise ui.XVError on expected failures; lib/xv.py turns them into commands and output.
"""
import difflib, hashlib, json, math, re, subprocess, sys
from pathlib import Path

from ui import XVError, USAGE

GATES = ["0", "1-2", "3", "4", "5", "6", "7"]
STAGE = {"0": "0 kickoff", "1-2": "1-2 research and script", "3": "3 narration and subtitles", "4": "4 visuals",
         "5": "5 render", "6": "6 YouTube package", "7": "7 social package"}
KINDS = {"maintenance": None, "brief": "0", "script": "1-2", "narration": "3", "styleframes": "4", "render": "5", "youtube": "6", "social": "7"}
GATE_RE = re.compile(r"^- \[( |x|-)\] (?:~~)?(\d(?:-\d)?)\b")


def git(proj, *args, check=True):
    return subprocess.run(["git", *args], cwd=proj, capture_output=True, text=True, check=check).stdout.strip()


# ---------------------------------------------------------------- hashes for staleness
def file_hash(*paths):
    h = hashlib.sha256()
    for p in paths:
        for f in sorted([p] if p.is_file() else p.rglob("*")):
            if f.is_file():
                h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()[:16]


def script_hash(proj):
    """Hash of everything the narration audio and subtitles depend on (not titles, acronyms or other metadata)."""
    s = json.loads((proj / "script/script.json").read_text())
    payload = [spoken_lines(s), s.get("voice"), s.get("speed"), s.get("lang"), s.get("gaps"), s.get("fps")]
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]


def visuals_hash(proj):
    return file_hash(proj / "audio/timings.json", proj / "video/src", Path(__file__).resolve().parent.parent / "remotion")


def stale(proj):
    out = []
    t = proj / "audio/timings.json"
    if t.exists():
        tj = json.loads(t.read_text())
        if tj.get("script_hash") and tj["script_hash"] != script_hash(proj):
            out.append("script.json or lexicon changed since the last synth: run `xv synth`, `xv asr`, `xv changed`")
    m = proj / "render/manifest.json"
    if m.exists() and json.loads(m.read_text()).get("visuals_hash") != visuals_hash(proj):
        out.append("timings or scene code changed since the last render: run `xv render`")
    sm = proj / "script/script.md"
    from xv import script_md_text
    if sm.exists() and sm.read_text() != script_md_text(proj):
        out.append("script.md does not match script.json: run `xv script-md`")
    return out


# ---------------------------------------------------------------- STATUS.md
class Status:
    def __init__(self, proj):
        self.f = proj / "STATUS.md"
        self.lines = self.f.read_text().splitlines()

    def save(self):
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(self.lines).rstrip("\n") + "\n")
        self.f.write_text(text)

    def gates(self):
        out = {}
        for i, l in enumerate(self.lines):
            m = GATE_RE.match(l)
            if m:
                out[m.group(2)] = (i, {" ": "open", "x": "approved", "-": "skipped"}[m.group(1)] if "~~" not in l else "skipped")
        return out

    def stage(self):
        return next((l[7:] for l in self.lines if l.startswith("Stage: ")), "?")

    def set_stage(self, text):
        for i, l in enumerate(self.lines):
            if l.startswith("Stage: "):
                self.lines[i] = f"Stage: {text}"

    def current_gate(self):
        g = self.gates()
        return next((k for k in GATES if g.get(k, (0, "open"))[1] == "open"), None)

    def section(self, name):
        start = next(i for i, l in enumerate(self.lines) if l.strip() == f"## {name}")
        end = next((i for i in range(start + 1, len(self.lines)) if self.lines[i].startswith("## ")), len(self.lines))
        return start, end

    def items(self, name):
        s, e = self.section(name)
        return [(i, self.lines[i][2:]) for i in range(s + 1, e) if self.lines[i].startswith("- ")]

    def append(self, name, text):
        s, e = self.section(name)
        while e > s + 1 and not self.lines[e - 1].strip():
            e -= 1
        self.lines.insert(e, f"- {text}")
        if e == s + 1 or not self.lines[e - 1].startswith("- "):
            self.lines.insert(e, "")


NEXT = {"0": "ask the kickoff questions, fill brief.md, `xv lint`, `xv commit <p> brief ...`, `xv review`",
        "1-2": "research -> sources.md, findings.md; script.json, storyboard.md; `xv script-md`, `xv lint`, `xv commit <p> script ...`, `xv review`",
        "3": "`xv synth`, `xv asr` until clean, `xv commit <p> narration ...`, `xv review`",
        "4": "scenes.tsx, `xv typecheck`, `xv stills` (+ --per-beat), inspect sheets, `xv commit <p> styleframes ...`, `xv review`",
        "5": "`xv render`, `xv stills`, `xv commit <p> render ...`, `xv review`",
        "6": "metadata.json, Thumbnail*.tsx, pinned-comment.txt; `xv thumbnail`, `xv youtube`, `xv lint`, `xv commit <p> youtube ...`, `xv review`",
        "7": "GUIDE.md social section -> publish/social/; `xv lint`, `xv commit <p> social ...`, `xv review`"}


def status(proj):
    """Everything `xv status` shows, as data."""
    st = Status(proj)
    gates = {k: st.gates().get(k, (0, "missing"))[1] for k in GATES}
    fb = [t for _, t in st.items("Open feedback")]
    g = st.current_gate()
    if fb:
        nxt = "address the open feedback, `xv feedback <p> done <n>` for each, commit, `xv review`"
    elif g:
        nxt = f"(gate {g}) {NEXT[g]}"
    else:
        nxt = "nothing: all gates approved or skipped; the owner uploads and posts"
    return {"project": proj.name, "path": str(proj), "stage": st.stage(), "gates": gates, "current_gate": g,
            "open_feedback": fb, "stale": stale(proj), "next": nxt.replace("<p>", proj.name)}


def commit(proj, kind, summary, dry_run=False):
    """git add -A and commit as "<kind> vN: <summary>". Returns the message."""
    if kind not in KINDS:
        raise XVError(f"unknown commit kind {kind!r}", f"use one of: {', '.join(KINDS)}", code=USAGE)
    if not summary.strip():
        raise XVError("the summary is empty", 'say what changed, e.g. xv commit <p> script "tighten intro"', code=USAGE)
    versions = [int(m.group(1)) for s in git(proj, "log", "--format=%s", check=False).splitlines()
                if (m := re.match(rf"{kind} v(\d+)\b", s))]
    v = max(versions, default=0) + 1
    msg = f"{kind} v{v}: {summary}" if KINDS[kind] else f"{kind}: {summary}"
    changes = git(proj, "status", "--porcelain")
    if not changes:
        raise XVError("nothing to commit", "change a file first; `git status` in the project shows the working tree")
    if dry_run:
        return msg, changes.splitlines()
    if KINDS[kind]:  # maintenance commits leave the stage alone and carry no version
        st = Status(proj)
        st.set_stage(f"{STAGE[KINDS[kind]]} ({kind} v{v} awaiting review)")
        st.save()
    git(proj, "add", "-A")
    git(proj, "commit", "-q", "-m", msg)
    return msg, changes.splitlines()


def gate(proj, key, skip=None, force=False, dry_run=False):
    """Approve (or skip) a gate, set the Stage line, commit. Returns (message, new stage)."""
    key = {"1": "1-2", "2": "1-2"}.get(key, key)
    st = Status(proj)
    g = st.gates()
    if key not in g:
        raise XVError(f"no gate {key!r} in STATUS.md", f"gates are: {', '.join(GATES)}", code=USAGE)
    if g[key][1] != "open":
        raise XVError(f"gate {key} is already {g[key][1]}", f"`xv status {proj.name}` shows every gate")
    fb = st.items("Open feedback")
    if fb and not skip and not force:
        raise XVError(f"{len(fb)} open feedback item(s) remain",
                      f"close them with `xv feedback {proj.name} done <n>`, or pass --force to approve anyway")
    i = g[key][0]
    label = re.sub(r"^- \[.\] (?:~~)?\S+ ?", "", st.lines[i]).split("~~")[0].strip()
    if skip:
        label = re.sub(r" approved.*$", "", label)
        st.lines[i] = f"- [-] {key} {label} skipped: {skip}"
    else:
        st.lines[i] = f"- [x] {key} {label}"
    nxt = st.current_gate()
    st.set_stage(STAGE[nxt] if nxt else "done (owner uploads and posts)")
    msg = f"gate {key} skipped: {skip}" if skip else f"gate {key} approved"
    if dry_run:
        return msg, st.stage()
    st.save()
    git(proj, "add", "-A")
    git(proj, "commit", "-q", "-m", msg)
    return msg, st.stage()


def feedback_list(proj):
    return [t for _, t in Status(proj).items("Open feedback")]


def feedback_add(proj, items):
    st = Status(proj)
    for t in items:
        if not t.strip():
            raise XVError("empty feedback item", code=USAGE)
        st.append("Open feedback", t.strip())
    st.save()
    return feedback_list(proj)


def feedback_done(proj, numbers):
    st = Status(proj)
    items = st.items("Open feedback")
    bad = [n for n in numbers if not 1 <= n <= len(items)]
    if bad:
        raise XVError(f"no open feedback item {', '.join(map(str, bad))}",
                      f"there are {len(items)}; `xv feedback {proj.name} list` numbers them", code=USAGE)
    for i in sorted({items[n - 1][0] for n in numbers}, reverse=True):
        del st.lines[i]
    st.save()
    return feedback_list(proj)


def decision(proj, text):
    if not text.strip():
        raise XVError("empty decision", code=USAGE)
    st = Status(proj)
    st.append("Decisions", text.strip())
    st.save()


# ---------------------------------------------------------------- changed narration lines
def mmss(x, up=False):
    s = math.ceil(x) if up else int(x)
    return f"{s // 60}:{s % 60:02d}"


def spoken_lines(script):
    sys.path.insert(0, str(Path(__file__).parent / "tts"))
    from synth import load_lexicon, spoken
    lex = load_lexicon(script)
    return [(sc["id"], ln, spoken(ln, lex)) for sc in script["scenes"] for ln in sc["lines"]]


def changed_lines(proj, ref):
    """Narration lines that differ from `ref`, with their timestamps in the current timings.json."""
    try:
        old = json.loads(git(proj, "show", f"{ref}:script/script.json"))
    except subprocess.CalledProcessError:
        raise XVError(f"git ref {ref!r} has no script/script.json", "pass --since <commit> with a commit that has one")
    new = json.loads((proj / "script/script.json").read_text())
    a, b = spoken_lines(old), spoken_lines(new)
    t = json.loads((proj / "audio/timings.json").read_text())
    times = [(ln["start"], ln["end"]) for sc in t["scenes"] for ln in sc["lines"]]
    rows, removed = [], []
    sm = difflib.SequenceMatcher(a=[x[1:] for x in a], b=[x[1:] for x in b], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ("replace", "insert"):
            for j in range(j1, j2):
                what = "voice only" if j - j1 < i2 - i1 and a[i1 + j - j1][1] == b[j][1] else ("text" if op == "replace" else "new")
                s, e = times[j] if j < len(times) else (0, 0)
                rows.append({"start": s, "end": e, "from": mmss(s), "to": mmss(e, True), "scene": b[j][0], "change": what, "text": b[j][1]})
        if op in ("replace", "delete") and (i2 - i1) > (j2 - j1 if op == "replace" else 0):
            removed += [a[i][1] for i in range(i1 + (j2 - j1 if op == "replace" else 0), i2)]
    return rows, removed


def format_row(r):
    return f"{r['from']}-{r['to']}  {r['scene']:10s} [{r['change']}] {r['text']}"


def default_ref(proj):
    if git(proj, "status", "--porcelain", "--", "script/script.json"):
        return "HEAD"
    last = git(proj, "log", "-n1", "--format=%H", "--", "script/script.json")
    return f"{last}~1"


def changed(proj, since=None):
    if not (proj / "audio/timings.json").exists():
        raise XVError("no audio/timings.json yet", f"run `xv synth {proj.name}` first")
    ref = since or default_ref(proj)
    rows, removed = changed_lines(proj, ref)
    return {"since": git(proj, "log", "-n1", "--format=%h %s", ref), "changed": rows, "removed": removed}


# ---------------------------------------------------------------- review package
def since_gate(proj):
    log = git(proj, "log", "--format=%s", check=False).splitlines()
    out = []
    for s in log:
        if s.startswith("gate "):
            break
        out.append(s)
    return out


def review(proj, gate_key=None):
    """The review package for a gate, as markdown."""
    from xv import slug_of
    slug = slug_of(proj)
    st = Status(proj)
    g = {"1": "1-2", "2": "1-2"}.get(gate_key, gate_key) if gate_key else st.current_gate()
    if g is None:
        raise XVError("every gate is approved or skipped", "pass a gate to review it again, e.g. `xv review <p> 6`")
    if g not in STAGE:
        raise XVError(f"no gate {g!r}", f"gates are: {', '.join(GATES)}", code=USAGE)
    P = lambda rel: f"`{proj / rel}`"
    out = [f"## Review: gate {g}, {STAGE.get(g, g)}\n"]
    commits = since_gate(proj)
    if commits:
        out.append("Versions since the last gate: " + "; ".join(f"`{c}`" for c in reversed(commits)) + "\n")
    files = []
    if g == "0":
        files = ["brief.md"]
    elif g == "1-2":
        files = ["script/script.md", "script/storyboard.md", "research/findings.md", "research/sources.md"]
        sm = (proj / "script/script.md")
        if sm.exists():
            out.append(sm.read_text().splitlines()[2] + "\n")
        n = sum(1 for l in (proj / "research/sources.md").read_text().splitlines() if re.match(r"\| \d+ \|", l))
        out.append(f"Sources logged: {n}. UNVERIFIED items in findings: "
                   f"{(proj / 'research/findings.md').read_text().count('UNVERIFIED')}\n")
    elif g == "3":
        files = ["audio/narration.wav", f"audio/{slug}.srt", "audio/asr-check.md"]
        t = json.loads((proj / "audio/timings.json").read_text())
        out.append(f"Narration length: {mmss(t['total'])} ({t['total']:.1f} s)\n")
        asr = proj / "audio/asr-check.md"
        if asr.exists():
            out.append(asr.read_text().splitlines()[2] + "\n")
    elif g == "4":
        files = sorted(str(f.relative_to(proj)) for f in (proj / "stills").glob("*sheet*.png")) + ["assets/ASSETS.md"]
    elif g == "5":
        files = [f"render/{slug}.mp4", f"render/{slug}.srt"]
        m = proj / "render/manifest.json"
        if m.exists():
            mj = json.loads(m.read_text())
            out.append(f"Duration {mmss(mj['duration'])} ({mj['duration']:.1f} s), {mj['size_mb']:.0f} MB, -14 LUFS\n")
    elif g == "6":
        pub = proj / "publish/youtube"
        files = ["publish/youtube/upload-sheet.md", "publish/youtube/description.txt", "publish/youtube/pinned-comment.txt"]
        files += sorted(str(f.relative_to(proj)) for f in pub.glob("thumbnail*.jpg"))
        meta = json.loads((pub / "metadata.json").read_text())
        out.append(f"Title ({len(meta['title'])} characters): {meta['title']}\n")
    elif g == "7":
        files = sorted(str(f.relative_to(proj)) for f in (proj / "publish/social").rglob("*") if f.is_file() and f.suffix in {".md", ".pdf", ".mp4"} and f.name != "README.md")
    out.append("Files:\n" + "\n".join(f"- {P(f)}" for f in files if (proj / f).exists()) + "\n")
    missing = [f for f in files if not (proj / f).exists()]
    if missing:
        out.append("Missing: " + ", ".join(missing) + "\n")
    if g in ("3", "5") and (proj / "audio/timings.json").exists():
        try:
            rows, removed = changed_lines(proj, default_ref(proj))
            if rows and len(rows) < 30:
                out.append("Changed lines, new timestamps:\n" + "\n".join(f"- {format_row(r)}" for r in rows) + "\n")
        except (subprocess.CalledProcessError, XVError):
            pass
    for s in stale(proj):
        out.append(f"STALE: {s}\n")
    fb = st.items("Open feedback")
    if fb:
        out.append(f"Open feedback still listed: {len(fb)}\n")
    out.append(f"Reply \"approved\" to pass gate {g}, or list changes.")
    return "\n".join(out)
