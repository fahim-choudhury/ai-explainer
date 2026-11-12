"""xv (short for explainer video): the toolkit CLI. Run `xv --help` or `xv help <command>`.

Command-line conventions follow https://clig.dev: results on stdout, progress and hints on stderr,
--json for machine-readable output, -q to quiet, -d for debugging, stable exit codes.
"""
import argparse, datetime, difflib, json, re, shutil, subprocess, sys, traceback
from pathlib import Path

import paths
import ui
from paths import LIB, REPO, PY
from ui import XVError, USAGE

TOOLKIT = LIB
ISSUES = "https://github.com/fahim-choudhury/ai-explainer/issues"
DOCS = "https://github.com/fahim-choudhury/ai-explainer#readme"


def ws():
    return paths.workspace()


# ---------------------------------------------------------------- helpers
def run(cmd, **kw):
    """Run a tool. Its output goes to stderr (stdout stays for xv's results); --quiet hides it unless it fails."""
    cmd = [str(c) for c in cmd]
    ui.debug("+ " + " ".join(cmd))
    if ui.QUIET:
        r = subprocess.run(cmd, capture_output=True, text=True, **kw)
        if r.returncode:
            sys.stderr.write(r.stdout + r.stderr)
            raise XVError(f"{Path(cmd[0]).name} failed (exit {r.returncode})", "its output is above")
        return r
    r = subprocess.run(cmd, stdout=sys.stderr, **kw)
    if r.returncode:
        raise XVError(f"`{' '.join(Path(c).name if i == 0 else c for i, c in enumerate(cmd[:4]))} ...` failed (exit {r.returncode})",
                      "its output is above; rerun with --debug to see the full command")
    return r


def projects():
    w = ws()
    return sorted(p for p in w.glob("explainer-*") if (p / "script/script.json").exists()) if w.exists() else []


def proj_path(p):
    q = Path(p)
    q = q if q.is_absolute() or q.exists() else ws() / p
    q = q.resolve()
    if not (q / "script/script.json").exists():
        names = [x.name for x in projects()]
        close = difflib.get_close_matches(Path(p).name, names, n=1)
        hint = f"did you mean {close[0]}?" if close else (f"projects in {ws()}: {', '.join(names)}" if names else f"no projects in {ws()} yet; create one with `xv new`")
        raise XVError(f"{q} is not an explainer project (no script/script.json)", hint)
    return q


def slug_of(proj):
    return json.loads((proj / "script/script.json").read_text())["slug"]


def remotion(proj, *args):
    return run(["npx", "--no-install", "remotion", *args, "--public-dir", proj / "video/public"], cwd=REPO)


def timings(proj):
    f = proj / "audio/timings.json"
    if not f.exists():
        raise XVError("no audio/timings.json yet", f"run `xv synth {proj.name}` first")
    return json.loads(f.read_text())


def script_md_text(proj):
    s = json.loads((proj / "script/script.json").read_text())
    words = sum(len(l.split()) for sc in s["scenes"] for l in sc["lines"])
    out = [f"# {s.get('title', s['slug'])}: narration script\n",
           f"{words} words, about {words / 150:.1f} min at 150 wpm (actual length comes from `xv synth`). Voice `{s.get('voice')}`, speed {s.get('speed', 1.0)}.\n"]
    for i, sc in enumerate(s["scenes"], 1):
        out.append(f"## {i}. {sc.get('title', sc['id'])} (`{sc['id']}`)\n")
        out += [f"{l}\n" for l in sc["lines"]]
    return "\n".join(out)


def write_or_print(text, output):
    if output and output != "-":
        Path(output).write_text(text)
        ui.out(str(Path(output).resolve()))
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


# ---------------------------------------------------------------- project commands
def cmd_new(a):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.slug):
        raise XVError(f"invalid slug {a.slug!r}", "use lowercase letters, digits and dashes, e.g. zero-trust", code=USAGE)
    dest = ws() / f"explainer-{a.slug}"
    if dest.exists():
        raise XVError(f"{dest} already exists", f"pick another slug, or continue it with `xv status {dest.name}`")
    if a.dry_run:
        ui.out(f"would create {dest} from {REPO / 'template'}")
        return
    ws().mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO / "template", dest)
    title, today = a.title or a.slug, datetime.date.today().isoformat()
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix in {".md", ".json", ".tsx", ".ts", ""}:
            s = f.read_text()
            s2 = s.replace("{{SLUG}}", a.slug).replace("{{TITLE}}", title).replace("{{DATE}}", today)
            if s2 != s:
                f.write_text(s2)
    run(["git", "init", "-q"], cwd=dest)
    ui.out(str(dest))
    ui.info(f"seed material goes in {dest / 'inputs'}/")
    ui.hint(f"xv status {dest.name}")


def cmd_list(a):
    rows = []
    for p in projects():
        import state
        try:
            st = state.Status(p)
            rows.append({"project": p.name, "stage": st.stage(), "path": str(p)})
        except Exception:
            rows.append({"project": p.name, "stage": "?", "path": str(p)})
    if a.json:
        return ui.emit_json({"workspace": str(ws()), "projects": rows})
    ui.info(f"workspace {ws()}")
    for r in rows:
        ui.out(f"{r['project']:40s} {r['stage']}")
    if not rows:
        ui.info("no projects yet")
        ui.hint('xv new <slug> "<Working title>"')


def cmd_synth(a):
    import synth
    proj = proj_path(a.project)
    ui.info("synthesizing narration (changed lines only)")
    synth.main(proj)
    ui.hint(f"xv asr {proj.name}")


def cmd_asr(a):
    import asr_check
    proj = proj_path(a.project)
    timings(proj)
    ui.info(f"transcribing every line with Whisper {a.model}")
    flagged, total, _ = asr_check.check(proj, a.threshold, a.model, a.output)
    if flagged:
        ui.hint("fix the flags with `say` in script.json or lib/tts/lexicon.json (or `asr_accept`)", f"xv synth {proj.name}", f"xv asr {proj.name}")
    else:
        ui.hint(f'xv commit {proj.name} narration "<summary>"', f"xv review {proj.name}")


def cmd_script_md(a):
    proj = proj_path(a.project)
    (proj / "script/script.md").write_text(script_md_text(proj))
    ui.out(str(proj / "script/script.md"))
    ui.hint(f"xv lint {proj.name}")


def cmd_typecheck(a):
    proj = proj_path(a.project)
    cfg = REPO / ".cache" / f"tsconfig-{proj.name}.json"
    cfg.parent.mkdir(exist_ok=True)
    cfg.write_text(json.dumps({
        "extends": str(REPO / "remotion/tsconfig.base.json"),
        "compilerOptions": {"baseUrl": str(REPO), "paths": {"@xv/*": ["remotion/*"], "*": ["node_modules/@types/*", "node_modules/*"]},
                            "typeRoots": [str(REPO / "node_modules/@types")]},
        "include": [str(proj / "video/src"), str(REPO / "remotion")]}, indent=1))
    run(["npx", "--no-install", "tsc", "-p", cfg], cwd=REPO)
    ui.out(f"{proj.name}: no type errors")


def cmd_studio(a):
    proj = proj_path(a.project)
    ui.info("starting Remotion Studio; press Ctrl-C to stop")
    remotion(proj, "studio", proj / "video/src/index.ts")


def contact_sheets(files, outdir, prefix):
    sheets = []
    for k in range(0, len(files), 6):
        grp = files[k:k + 6]
        while len(grp) < 6:
            grp.append(grp[-1])
        out = outdir / f"{prefix}-sheet-{k // 6 + 1}.png"
        inputs = sum([["-i", f] for f in grp], [])
        run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex",
             "xstack=inputs=6:layout=0_0|w0_0|0_h0|w0_h0|0_h0+h0|w0_h0+h0,scale=1920:-1", out])
        sheets.append(out)
    return sheets


def cmd_stills(a):
    proj = proj_path(a.project)
    t = timings(proj)
    fps = t["fps"]
    frames = []
    if a.frames:
        try:
            frames = [(int(x), f"f{x}") for x in a.frames.split(",")]
        except ValueError:
            raise XVError(f"--frames takes frame numbers separated by commas, not {a.frames!r}", "e.g. --frames 120,900", code=USAGE)
    else:
        for sc in t["scenes"]:
            s0 = round(sc["start"] * fps)
            beats = [round(l["start"] * fps) for l in sc["lines"]]
            pts = [b + 45 for b in beats] if a.per_beat else [min(round(sc["end"] * fps) - 15, beats[-1] + 75)]
            frames += [(p, f"{sc['id']}-{p - s0}") for p in pts]
    outdir = proj / "stills"; outdir.mkdir(exist_ok=True)
    files = []
    for n, (fr, name) in enumerate(frames, 1):
        ui.info(f"still {n}/{len(frames)}: frame {fr}")
        f = outdir / f"{name}.png"
        remotion(proj, "still", proj / "video/src/index.ts", "Main", f, f"--frame={fr}", "--log=error")
        files.append(f)
    for s in contact_sheets(files, outdir, "per-beat" if a.per_beat else "scenes"):
        ui.out(str(s))
    ui.hint("look at every sheet", f'xv commit {proj.name} styleframes "<summary>"')


def loudnorm(src, dst, target=-14.0):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]*\}", r.stderr)[-1])
    af = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-c:v", "copy", "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", dst])
    return float(m["input_i"])


def cmd_render(a):
    proj = proj_path(a.project)
    slug = slug_of(proj)
    t = timings(proj)
    (proj / "render").mkdir(exist_ok=True)
    raw = proj / "render/.raw.mp4"
    out = proj / f"render/{slug}.mp4"
    ui.info(f"rendering {t['total']:.0f} s of video; this takes a while")
    remotion(proj, "render", proj / "video/src/index.ts", "Main", raw, "--codec=h264", "--crf=18", "--concurrency=8", "--log=error")
    ui.info("normalizing loudness to -14 LUFS")
    before = loudnorm(raw, out)
    raw.unlink()
    shutil.copy2(proj / f"audio/{slug}.srt", proj / f"render/{slug}.srt")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate",
                            "-of", "json", out], capture_output=True, text=True)
    p = json.loads(probe.stdout)
    d = float(p["format"]["duration"]); size = int(p["format"]["size"]) / 1e6
    ui.out(f"{out}  {int(d // 60)}:{int(d % 60):02d} ({d:.1f} s), {size:.0f} MB, loudness {before:.1f} -> -14 LUFS")
    for s in p["streams"]:
        ui.info(f"  {s['codec_type']} {s['codec_name']} {s.get('width', '')} {s.get('height', '')} {s.get('r_frame_rate', '')}".rstrip())
    if abs(d - (t["total"] + 1)) > 2:
        ui.warn(f"duration differs from the narration ({t['total']:.1f} s)")
    from state import visuals_hash
    (proj / "render/manifest.json").write_text(json.dumps(
        {"duration": round(d, 3), "size_mb": round(size, 1), "loudness_in": before, "visuals_hash": visuals_hash(proj)}, indent=1) + "\n")
    ui.hint(f"xv stills {proj.name}", f'xv commit {proj.name} render "<summary>"', f"xv review {proj.name}")


def thumbnail_ids(proj):
    """Every <Still id="Thumbnail..."> in Root.tsx: Thumbnail -> thumbnail.jpg, ThumbnailB -> thumbnail-b.jpg."""
    ids = re.findall(r'<Still\s+id="(Thumbnail\w*)"', (proj / "video/src/Root.tsx").read_text())
    return [(i, "thumbnail.jpg" if i == "Thumbnail" else f"thumbnail-{i[9:].lower()}.jpg") for i in ids]


def cmd_thumbnail(a):
    proj = proj_path(a.project)
    ids = thumbnail_ids(proj)
    if not ids:
        raise XVError("Root.tsx registers no <Still id=\"Thumbnail...\">", "add one, e.g. <Still id=\"Thumbnail\" component={Thumbnail} .../>")
    outdir = proj / "publish/youtube"
    outdir.mkdir(parents=True, exist_ok=True)
    for comp, name in ids:
        out = outdir / name
        tmp = out.with_suffix(".full.png")
        ui.info(f"rendering {comp}")
        remotion(proj, "still", proj / "video/src/index.ts", comp, tmp, "--log=error")
        run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-vf", "scale=1280:720:flags=lanczos", "-q:v", "2", out])
        tmp.unlink()
        kb = out.stat().st_size / 1024
        ui.out(f"{out}  {kb:.0f} KB")
        if kb > 2048:
            ui.warn(f"{name} is over YouTube's 2 MB thumbnail limit")
    ui.hint(f"xv youtube {proj.name}")


def cmd_short(a):
    proj = proj_path(a.project); slug = slug_of(proj)
    if a.end <= a.start:
        raise XVError("--end must be after --start", code=USAGE)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.name):
        raise XVError(f"invalid --name {a.name!r}", "lowercase letters, digits and dashes; it becomes the file name", code=USAGE)
    src = proj / f"render/{slug}.mp4"
    if not src.exists():
        raise XVError(f"no render yet at {src}", f"run `xv render {proj.name}` first")
    outdir = proj / "publish/social/shorts"; outdir.mkdir(parents=True, exist_ok=True)
    t = timings(proj); cues = []
    for sc in t["scenes"]:
        for ln in sc["lines"]:
            if ln["end"] > a.start and ln["start"] < a.end:
                cues.append((max(0, ln["start"] - a.start), min(a.end, ln["end"]) - a.start, ln["text"]))

    def ts(x):
        cs = int(round(x * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
        return f"{h}:{m:02}:{s:02}.{cs:02}"
    ass = outdir / f"{a.name}.ass"
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Alignment, MarginL, MarginR, MarginV, BorderStyle, Outline, Shadow\n"
            "Style: Cap,Inter,58,&H00FFFFFF,&H00000000,&H99000000,0,2,70,70,330,1,4,0\n"
            "Style: Title,Inter,74,&H003083F6,&H00000000,&H00000000,0,8,70,70,230,1,0,0\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    ev = [f"Dialogue: 0,{ts(0)},{ts(a.end - a.start)},Title,{a.title}"] if a.title else []
    ev += [f"Dialogue: 0,{ts(s)},{ts(e)},Cap,{txt}" for s, e, txt in cues]
    ass.write_text(head + "\n".join(ev) + "\n")
    out = outdir / f"{a.name}.mp4"
    vf = ("[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.15[bg];"
          f"[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2,ass='{ass}':fontsdir='{REPO / "remotion/fonts"}'")
    ui.info(f"cutting {a.end - a.start:.0f} s from {src.name}")
    run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a.start), "-to", str(a.end), "-i", src, "-filter_complex", vf,
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])
    ui.out(f"{out}  {a.end - a.start:.0f} s, 1080x1920")


def cmd_carousel(a):
    from PIL import Image
    proj = proj_path(a.project)
    t = timings(proj)
    files = []
    for sc in t["scenes"]:
        hits = sorted((proj / "stills").glob(f"{sc['id']}-*.png"), key=lambda f: int(f.stem.rsplit("-", 1)[1]))
        if hits:
            files.append(hits[-1])
    if not files:
        raise XVError("no scene stills", f"run `xv stills {proj.name}` first")
    pages = [Image.open(f).convert("RGB") for f in files]
    out = proj / "publish/social/linkedin-carousel.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=144)
    ui.out(f"{out}  {len(pages)} pages")


def cmd_youtube(a):
    import package
    proj = proj_path(a.project)
    warn = package.main(proj)
    if warn:
        ui.hint("fix the warnings above, then run `xv youtube` again")
    else:
        ui.hint(f"xv lint {proj.name}", f'xv commit {proj.name} youtube "<summary>"', f"xv review {proj.name}")


def cmd_lint(a):
    import lint
    proj = proj_path(a.project)
    r = lint.run(proj, a.only)
    if a.json:
        ui.emit_json({"project": proj.name, "errors": r.errors, "warnings": r.warnings, "findings": r.findings})
    else:
        for f in r.findings:
            level = ui.paint(f["level"], "red" if f["level"] == "E" else "yellow")
            ui.out(f"{f['file']}:{f['line']}: {level} {f['rule']}: {f['message']}")
        ui.info(f"{r.errors} errors, {r.warnings} warnings" if r.findings else "clean")
    if r.errors:
        raise SystemExit(ui.FAILED)


def cmd_doctor(a):
    import doctor
    ui.info("checking dependencies" + (" (model sizes only)" if a.quick else ", hashing models takes a few seconds"))
    res = doctor.checks(a.quick)
    ok = all(c["ok"] for c in res)
    if a.json:
        ui.emit_json({"ok": ok, "quick": a.quick, "checks": res})
    else:
        group = None
        for c in res:
            if c["group"] != group:
                group = c["group"]
                ui.out(ui.paint(group, "bold"))
            mark = ui.paint("ok  ", "green") if c["ok"] else ui.paint("FAIL", "red")
            ui.out(f"  {mark} {c['name']}" + (f"\n       fix: {c['fix']}" if c["fix"] else ""))
        if ok:
            ui.info("all checks passed" + ("" if a.quick else f"; wrote {paths.STAMP.name}"))
        else:
            ui.info(f"{sum(not c['ok'] for c in res)} check(s) failed; fix them, then run `xv doctor` again")
    if not ok:
        raise SystemExit(ui.FAILED)


def cmd_selftest(a):
    import doctor
    failed = doctor.selftest()
    if failed:
        raise XVError(f"selftest failed at `xv {failed}`", "its output is above; `xv doctor` checks the dependencies")
    ui.out("selftest passed")


def cmd_transcribe(a):
    import transcribe
    if not Path(a.file).exists():
        raise XVError(f"no such file: {a.file}", code=USAGE)
    ui.info(f"transcribing {a.file} with Whisper {a.model}")
    write_or_print(transcribe.transcribe(a.file, a.model), a.output)


def cmd_pdftext(a):
    from pypdf import PdfReader
    if not Path(a.file).exists():
        raise XVError(f"no such file: {a.file}", code=USAGE)
    text = "\n\n".join(f"--- page {i} ---\n{p.extract_text() or ''}" for i, p in enumerate(PdfReader(a.file).pages, 1))
    write_or_print(text, a.output)


# ---------------------------------------------------------------- state commands
def cmd_status(a):
    import state
    d = state.status(proj_path(a.project))
    if a.json:
        return ui.emit_json(d)
    ui.out(f"{d['project']}\nStage: {d['stage']}\n")
    for k, v in d["gates"].items():
        colour = {"approved": "green", "skipped": "dim", "open": "yellow"}.get(v)
        ui.out(f"  gate {k:4s} {ui.paint(v, colour) if colour else v}")
    ui.out(f"\nOpen feedback: {len(d['open_feedback']) or 'none'}")
    for n, t in enumerate(d["open_feedback"], 1):
        ui.out(f"  {n}. {t}")
    for s in d["stale"]:
        ui.out(f"{ui.paint('STALE', 'yellow')}: {s}")
    ui.out(f"\nNext: {d['next']}")


def cmd_commit(a):
    import state
    proj = proj_path(a.project)
    msg, changes = state.commit(proj, a.kind, " ".join(a.summary), dry_run=a.dry_run)
    if a.dry_run:
        ui.out(f"would commit: {msg}")
        for c in changes:
            ui.out(f"  {c}")
        return
    ui.out(msg)
    if state.KINDS[a.kind]:
        ui.hint(f"xv review {proj.name}")


def cmd_gate(a):
    import state
    proj = proj_path(a.project)
    msg, stage = state.gate(proj, a.gate, skip=a.skip, force=a.force, dry_run=a.dry_run)
    ui.out(("would commit: " if a.dry_run else "") + msg)
    ui.info(f"stage: {stage}")
    if not a.dry_run:
        ui.hint(f"xv status {proj.name}")


def cmd_feedback(a):
    import state
    proj = proj_path(a.project)
    if a.action == "add":
        if not a.items:
            raise XVError("nothing to add", f'xv feedback {proj.name} add "<item>" ["<item>" ...]', code=USAGE)
        items = state.feedback_add(proj, a.items)
    elif a.action == "done":
        try:
            nums = [int(x) for x in a.items]
        except ValueError:
            raise XVError("`done` takes item numbers", f"xv feedback {proj.name} done 1 2", code=USAGE)
        if not nums:
            raise XVError("which items?", f"xv feedback {proj.name} done 1 2", code=USAGE)
        items = state.feedback_done(proj, nums)
    else:
        items = state.feedback_list(proj)
    if a.json:
        return ui.emit_json({"open_feedback": items})
    for n, t in enumerate(items, 1):
        ui.out(f"{n}. {t}")
    if not items:
        ui.info("no open feedback")


def cmd_decision(a):
    import state
    state.decision(proj_path(a.project), " ".join(a.text))
    ui.out("added to Decisions in STATUS.md")


def cmd_changed(a):
    import state
    d = state.changed(proj_path(a.project), a.since)
    if a.json:
        return ui.emit_json(d)
    ui.info(f"narration changes since {d['since']}")
    for r in d["changed"]:
        ui.out(state.format_row(r))
    for r in d["removed"]:
        ui.out(f"removed: {r}")
    if not d["changed"] and not d["removed"]:
        ui.info("no changed lines")


def cmd_review(a):
    import state
    ui.out(state.review(proj_path(a.project), a.gate))


# ---------------------------------------------------------------- parser
EXAMPLES = {
    "new": ['xv new zero-trust "Zero trust in five minutes"', "xv new zero-trust --dry-run"],
    "list": ["xv list", "xv list --json"],
    "status": ["xv status explainer-zero-trust", "xv status explainer-zero-trust --json"],
    "lint": ["xv lint explainer-zero-trust", "xv lint explainer-zero-trust --only narration --json"],
    "commit": ['xv commit explainer-zero-trust script "tighten intro, add relay line"', 'xv commit explainer-zero-trust maintenance "fix typo" -n'],
    "gate": ["xv gate explainer-zero-trust 3", 'xv gate explainer-zero-trust 7 --skip "YouTube only per brief"'],
    "feedback": ['xv feedback explainer-zero-trust add "shorter intro" "fix the relay colour"', "xv feedback explainer-zero-trust done 1 2",
                 "xv feedback explainer-zero-trust list"],
    "decision": ['xv decision explainer-zero-trust "Voice speed 1.05 to match the series"'],
    "changed": ["xv changed explainer-zero-trust", "xv changed explainer-zero-trust --since HEAD~3 --json"],
    "review": ["xv review explainer-zero-trust", "xv review explainer-zero-trust 6"],
    "synth": ["xv synth explainer-zero-trust"],
    "asr": ["xv asr explainer-zero-trust", "xv asr explainer-zero-trust --threshold 0.1 -o /tmp/asr.md"],
    "stills": ["xv stills explainer-zero-trust", "xv stills explainer-zero-trust --per-beat", "xv stills explainer-zero-trust --frames 120,900"],
    "short": ['xv short explainer-zero-trust --start 182 --end 222 --name mobile --title "Zero trust on mobile"'],
    "transcribe": ["xv transcribe inputs/media/memo.m4a -o inputs/notes/memo.md"],
    "pdftext": ["xv pdftext inputs/docs/spec.pdf -o inputs/notes/spec.md", "xv pdftext inputs/docs/spec.pdf | less"],
    "doctor": ["xv doctor", "xv doctor --quick --json"],
}

GROUPS = [
    ("Start and check", ["doctor", "selftest", "new", "list"]),
    ("Project state", ["status", "lint", "commit", "gate", "feedback", "decision", "review", "changed"]),
    ("Research inputs", ["pdftext", "transcribe"]),
    ("Narration", ["script-md", "synth", "asr"]),
    ("Visuals and render", ["typecheck", "stills", "studio", "render", "thumbnail"]),
    ("Publishing packages", ["youtube", "short", "carousel"]),
]

EPILOG = f"""Exit codes: 0 success; 1 failure or failed check; 2 usage error; 3 dependencies not set up (run ./setup); 130 interrupted.
Environment: XV_WORKSPACE (project folder), NO_COLOR or XV_NO_COLOR (no colour), FORCE_COLOR.
Docs: {DOCS}   Issues: {ISSUES}"""

# commands that run without a verified install (they touch only text files and git)
NO_DEPS = {"doctor", "selftest", "lint", "status", "feedback", "decision", "review", "changed", "commit", "gate", "script-md", "list", "help", "new"}


class Formatter(argparse.RawDescriptionHelpFormatter):
    pass


def global_options(p, suppress):
    d = argparse.SUPPRESS if suppress else None
    g = p.add_argument_group("global options")
    g.add_argument("-q", "--quiet", action="store_true", default=d if suppress else False, help="only print results and errors")
    g.add_argument("-d", "--debug", action="store_true", default=d if suppress else False, help="show commands xv runs and full tracebacks")
    g.add_argument("--no-color", action="store_true", default=d if suppress else False, help="never use colour (also NO_COLOR=1)")
    g.add_argument("--workspace", metavar="DIR", default=d, help="project folder (overrides XV_WORKSPACE and xv.toml)")


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    global_options(common, suppress=True)
    overview = "\n".join(f"{title}:\n" + "\n".join(f"  {name:12s} {HELP[name]}" for name in names) for title, names in GROUPS)
    top = argparse.ArgumentParser(
        prog="xv", formatter_class=Formatter, allow_abbrev=False, suggest_on_error=True,
        description="xv (short for explainer video) runs every step of the explainer video workflow.\n"
                    "An AI agent drives it by following AGENTS.md; you can run any step yourself.\n\n"
                    "Examples:\n  xv doctor\n  xv new zero-trust \"Zero trust in five minutes\"\n  xv status explainer-zero-trust",
        epilog=f"Commands:\n{overview}\n  help         show help for xv or a command\n\n"
               f"Run `xv help <command>` for a command's options and examples.\n\n{EPILOG}")
    top.add_argument("--version", action="version", version=f"xv {paths.version()}")
    global_options(top, suppress=False)
    sub = top.add_subparsers(dest="command", metavar="<command>", help="one of the commands listed below")

    def cmd(name, func, project=True, **kw):
        ex = EXAMPLES.get(name)
        p = sub.add_parser(name, parents=[common], description=HELP[name][0].upper() + HELP[name][1:] + ".",
                           formatter_class=Formatter, allow_abbrev=False, suggest_on_error=True,
                           epilog=("Examples:\n" + "\n".join(f"  {e}" for e in ex) if ex else None), **kw)
        if project:
            p.add_argument("project", help="project folder name in the workspace, or a path")
        p.set_defaults(func=func)
        return p

    p = cmd("doctor", cmd_doctor, project=False)
    p.add_argument("--quick", action="store_true", help="check model sizes instead of hashing them; does not write the stamp")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    cmd("selftest", cmd_selftest, project=False)
    p = cmd("new", cmd_new, project=False)
    p.add_argument("slug", help="lowercase name, becomes explainer-<slug>")
    p.add_argument("title", nargs="?", help="working title (default: the slug)")
    p.add_argument("-n", "--dry-run", action="store_true", help="show what would be created")
    p = cmd("list", cmd_list, project=False)
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = cmd("status", cmd_status)
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p = cmd("lint", cmd_lint)
    p.add_argument("--only", choices=["narration", "prose"], help="run one rule set")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p = cmd("commit", cmd_commit)
    p.add_argument("kind", choices=["brief", "script", "narration", "styleframes", "render", "youtube", "social", "maintenance"])
    p.add_argument("summary", nargs="+", help="what changed in this version")
    p.add_argument("-n", "--dry-run", action="store_true", help="show the message and files without committing")
    p = cmd("gate", cmd_gate)
    p.add_argument("gate", help="0, 1-2, 3, 4, 5, 6 or 7")
    p.add_argument("--skip", metavar="REASON", help="skip the gate instead of approving it")
    p.add_argument("-f", "--force", action="store_true", help="approve even with open feedback")
    p.add_argument("-n", "--dry-run", action="store_true", help="show the commit message without changing anything")
    p = cmd("feedback", cmd_feedback)
    p.add_argument("action", choices=["add", "done", "list"], nargs="?", default="list")
    p.add_argument("items", nargs="*", help="feedback text (add) or item numbers (done)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p = cmd("decision", cmd_decision)
    p.add_argument("text", nargs="+", help="the decision and its reason")
    p = cmd("review", cmd_review)
    p.add_argument("gate", nargs="?", help="gate to review (default: the current one)")
    p = cmd("changed", cmd_changed)
    p.add_argument("--since", metavar="REF", help="git ref to compare with (default: before the last script commit)")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    for name, func in (("pdftext", cmd_pdftext), ("transcribe", cmd_transcribe)):
        p = cmd(name, func, project=False)
        p.add_argument("file", help="input file")
        p.add_argument("-o", "--output", "--out", metavar="FILE", help="write to FILE instead of stdout (- for stdout)")
        if name == "transcribe":
            p.add_argument("--model", default="small.en", help="Whisper model (default: small.en, the pinned one)")

    cmd("script-md", cmd_script_md)
    cmd("synth", cmd_synth)
    p = cmd("asr", cmd_asr)
    p.add_argument("--threshold", type=float, default=0.06, help="character error rate that flags a line (default: 0.06)")
    p.add_argument("--model", default="small.en", help="Whisper model (default: small.en, the pinned one)")
    p.add_argument("-o", "--output", "--out", metavar="FILE", help="report path (default: audio/asr-check.md)")

    cmd("typecheck", cmd_typecheck)
    p = cmd("stills", cmd_stills)
    m = p.add_mutually_exclusive_group()
    m.add_argument("--per-beat", action="store_true", help="one frame per narration line instead of per scene")
    m.add_argument("--frames", metavar="N,N", help="specific frame numbers, comma-separated")
    cmd("studio", cmd_studio)
    cmd("render", cmd_render)
    cmd("thumbnail", cmd_thumbnail)

    cmd("youtube", cmd_youtube)
    p = cmd("short", cmd_short)
    p.add_argument("--start", type=float, required=True, metavar="SEC", help="start time in seconds")
    p.add_argument("--end", type=float, required=True, metavar="SEC", help="end time in seconds")
    p.add_argument("--name", required=True, help="file name, e.g. mobile")
    p.add_argument("--title", default="", help="title burned in at the top")
    cmd("carousel", cmd_carousel)

    p = sub.add_parser("help", parents=[common], allow_abbrev=False, description="Show help for xv or a command.")
    p.add_argument("topic", nargs="?", metavar="command")
    p.set_defaults(func=None)
    return top


HELP = {
    "doctor": "check every dependency against the lockfiles",
    "selftest": "run a throwaway project through the main steps",
    "new": "create a project from the template",
    "list": "list projects in the workspace with their stage",
    "status": "stage, gates, open feedback, stale outputs and the next step",
    "lint": "check narration rules and writing style",
    "commit": 'commit the project as "<kind> vN: <summary>"',
    "gate": "approve or skip a review gate, and commit",
    "feedback": "add, close or list open review feedback",
    "decision": "record a decision in STATUS.md",
    "review": "print the review package for the current gate",
    "changed": "narration lines changed since a commit, with new timestamps",
    "pdftext": "extract the text of a PDF input",
    "transcribe": "transcribe an audio or video input with Whisper",
    "script-md": "write script/script.md for review",
    "synth": "synthesize narration, timings and subtitles",
    "asr": "check pronunciation of every line with Whisper",
    "typecheck": "type-check the project's scenes",
    "stills": "render review frames and contact sheets",
    "studio": "open Remotion Studio for live preview",
    "render": "render the final video, loudness-normalized",
    "thumbnail": "render every Thumbnail* still",
    "youtube": "write description.txt and upload-sheet.md",
    "short": "cut a 9:16 clip with burned-in captions",
    "carousel": "turn scene stills into a LinkedIn PDF",
}


def main(argv):
    parser = build_parser()
    if not argv:
        parser.print_help()
        return ui.OK
    a = parser.parse_args(argv)
    ui.QUIET, ui.DEBUG, ui.NO_COLOR_FLAG = bool(getattr(a, "quiet", False)), bool(getattr(a, "debug", False)), bool(getattr(a, "no_color", False))
    if getattr(a, "workspace", None):
        paths.OVERRIDE = a.workspace
    if a.command == "help":
        if a.topic:
            parser.parse_args([a.topic, "--help"])
        parser.print_help()
        return ui.OK
    if a.command not in NO_DEPS:
        import doctor
        doctor.require_verified()
    a.func(a)
    return ui.OK


def entry():
    sys.path.insert(0, str(LIB / "tts"))
    sys.path.insert(0, str(LIB / "youtube"))
    try:
        code = main(sys.argv[1:])
    except XVError as e:
        ui.error(str(e), e.hint)
        code = e.code
    except KeyboardInterrupt:
        print("\nxv: interrupted", file=sys.stderr)
        code = ui.INTERRUPTED
    except BrokenPipeError:  # e.g. `xv status p | head`: stop quietly
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        code = ui.OK
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (ui.FAILED if e.code else ui.OK)
    except Exception as e:
        if ui.DEBUG:
            traceback.print_exc()
        ui.error(f"unexpected {type(e).__name__}: {e}",
                 ("" if ui.DEBUG else "rerun with --debug for the traceback; ") + f"please report it at {ISSUES}")
        code = ui.FAILED
    sys.exit(code)


if __name__ == "__main__":
    entry()
