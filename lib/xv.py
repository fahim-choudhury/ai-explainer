"""xv (Xplainer Video): the explainer video toolkit CLI.

  xv new <slug> "<Working title>"      create a project from the template (+ git init)
  xv synth <project>                   narration, timings and subtitles from script/script.json
  xv asr <project>                     Whisper pronunciation check -> audio/asr-check.md
  xv script-md <project>               readable script/script.md (for review) from script.json
  xv typecheck <project>               TypeScript check of the project's scenes
  xv studio <project>                  Remotion Studio (live preview in the browser)
  xv stills <project> [--per-beat | --frames 120,900]   review frames + contact sheets in stills/
  xv render <project>                  full render -> render/<slug>.mp4 (loudness-normalized, QA printed)
  xv thumbnail <project>               render the Thumbnail still -> publish/youtube/thumbnail.jpg
  xv short <project> --start S --end E --name N [--title "..."]   9:16 cutdown -> publish/social/shorts/
  xv carousel <project>                scene stills -> publish/social/linkedin-carousel.pdf
  xv youtube <project>                 description.txt + upload-sheet.md for a manual Studio upload
  xv lint <project> [--only narration|prose]   narration rules and writing checks; exit 1 on errors
  xv doctor [--quick]                  verify every dependency against the lockfiles; writes .xv-verified
  xv selftest                          throwaway project: synth, ASR, lint, typecheck, one still
  xv transcribe <file> [--out F]       Whisper transcript of an audio or video input
  xv pdftext <file> [--out F]          text of a PDF input

State (STATUS.md and git; see state.py):
  xv status <project>                  stage, gates, open feedback, stale outputs, next step
  xv commit <project> <kind> "<summary>"   kind: brief script narration styleframes render youtube social maintenance
  xv gate <project> <gate> [--skip "<why>"]   approve or skip a gate and commit
  xv feedback <project> add "<item>" | done <n> | list
  xv decision <project> "<text>"
  xv changed <project> [--since <ref>]  changed narration lines with their new timestamps
  xv review <project> [<gate>]         review package for the current stage

<project> is a folder name under the workspace (see lib/paths.py) or a path.
Every command except doctor and selftest refuses to run until `xv doctor` has passed.
"""
import json, re, shutil, subprocess, sys, datetime
from pathlib import Path

from paths import LIB, REPO, PY, STAMP, workspace

TOOLKIT = LIB
WS = workspace()


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def proj_path(p):
    q = Path(p)
    q = q if q.is_absolute() or q.exists() else WS / p
    q = q.resolve()
    if not (q / "script/script.json").exists():
        sys.exit(f"{q} is not an explainer project (no script/script.json)")
    return q


def slug_of(proj):
    return json.loads((proj / "script/script.json").read_text())["slug"]


def remotion(proj, *args):
    return run(["npx", "--no-install", "remotion", *args, "--public-dir", proj / "video/public"], cwd=REPO)


def timings(proj):
    f = proj / "audio/timings.json"
    if not f.exists():
        sys.exit("No audio/timings.json yet: run `xv synth` first")
    return json.loads(f.read_text())


# ---------------------------------------------------------------- commands
def cmd_new(args):
    if len(args) < 1:
        sys.exit("usage: xv new <slug> \"<Working title>\"")
    slug, title = args[0], (args[1] if len(args) > 1 else args[0])
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        sys.exit("slug: lowercase letters, digits and dashes only")
    dest = WS / f"explainer-{slug}"
    if dest.exists():
        sys.exit(f"{dest} already exists")
    WS.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO / "template", dest)
    today = datetime.date.today().isoformat()
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix in {".md", ".json", ".tsx", ".ts", ""}:
            s = f.read_text()
            s2 = s.replace("{{SLUG}}", slug).replace("{{TITLE}}", title).replace("{{DATE}}", today)
            if s2 != s:
                f.write_text(s2)
    run(["git", "init", "-q"], cwd=dest)
    print(f"\nCreated {dest}\nPut seed material in {dest}/inputs/")


def cmd_synth(args):
    run([PY, TOOLKIT / "tts/synth.py", proj_path(args[0])])


def cmd_asr(args):
    run([PY, TOOLKIT / "tts/asr_check.py", proj_path(args[0]), *args[1:]])


def script_md_text(proj):
    s = json.loads((proj / "script/script.json").read_text())
    words = sum(len(l.split()) for sc in s["scenes"] for l in sc["lines"])
    out = [f"# {s.get('title', s['slug'])}: narration script\n",
           f"{words} words, about {words / 150:.1f} min at 150 wpm (actual length comes from `xv synth`). Voice `{s.get('voice')}`, speed {s.get('speed', 1.0)}.\n"]
    for i, sc in enumerate(s["scenes"], 1):
        out.append(f"## {i}. {sc.get('title', sc['id'])} (`{sc['id']}`)\n")
        out += [f"{l}\n" for l in sc["lines"]]
    return "\n".join(out)


def cmd_script_md(args):
    proj = proj_path(args[0])
    (proj / "script/script.md").write_text(script_md_text(proj))
    print(f"wrote {proj / 'script/script.md'}")


def cmd_typecheck(args):
    proj = proj_path(args[0])
    cfg = REPO / ".cache" / f"tsconfig-{proj.name}.json"
    cfg.parent.mkdir(exist_ok=True)
    cfg.write_text(json.dumps({
        "extends": str(REPO / "remotion/tsconfig.base.json"),
        "compilerOptions": {"baseUrl": str(REPO), "paths": {"@xv/*": ["remotion/*"], "*": ["node_modules/@types/*", "node_modules/*"]},
                            "typeRoots": [str(REPO / "node_modules/@types")]},
        "include": [str(proj / "video/src"), str(REPO / "remotion")]}, indent=1))
    run(["npx", "--no-install", "tsc", "-p", cfg], cwd=REPO)


def cmd_studio(args):
    proj = proj_path(args[0])
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


def cmd_stills(args):
    proj = proj_path(args[0])
    t = timings(proj)
    fps = t["fps"]
    frames = []
    if "--frames" in args:
        frames = [(int(x), f"f{x}") for x in args[args.index("--frames") + 1].split(",")]
    else:
        for sc in t["scenes"]:
            s0 = round(sc["start"] * fps)
            beats = [round(l["start"] * fps) for l in sc["lines"]]
            if "--per-beat" in args:
                pts = [b + 45 for b in beats]
            else:  # one frame per scene, after the last line has started and its animation settled
                pts = [min(round(sc["end"] * fps) - 15, beats[-1] + 75)]
            frames += [(p, f"{sc['id']}-{p - s0}") for p in pts]
    outdir = proj / "stills"; outdir.mkdir(exist_ok=True)
    files = []
    for fr, name in frames:
        f = outdir / f"{name}.png"
        remotion(proj, "still", proj / "video/src/index.ts", "Main", f, f"--frame={fr}", "--log=error")
        files.append(f)
    for s in contact_sheets(files, outdir, "per-beat" if "--per-beat" in args else "scenes"):
        print("sheet:", s)


def loudnorm(src, dst, target=-14.0):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]*\}", r.stderr)[-1])
    af = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-c:v", "copy", "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", dst])
    return float(m["input_i"])


def cmd_render(args):
    proj = proj_path(args[0])
    slug = slug_of(proj)
    (proj / "render").mkdir(exist_ok=True)
    raw = proj / "render/.raw.mp4"
    out = proj / f"render/{slug}.mp4"
    remotion(proj, "render", proj / "video/src/index.ts", "Main", raw, "--codec=h264", "--crf=18", "--concurrency=8", "--log=error")
    before = loudnorm(raw, out)
    raw.unlink()
    shutil.copy2(proj / f"audio/{slug}.srt", proj / f"render/{slug}.srt")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate",
                            "-of", "json", out], capture_output=True, text=True)
    p = json.loads(probe.stdout)
    d = float(p["format"]["duration"]); size = int(p["format"]["size"]) / 1e6
    print(f"\n{out}\n  duration {int(d // 60)}:{int(d % 60):02d} ({d:.1f}s), {size:.0f} MB, loudness {before:.1f} -> -14 LUFS")
    for s in p["streams"]:
        print("  ", s["codec_type"], s["codec_name"], s.get("width", ""), s.get("height", ""), s.get("r_frame_rate", ""))
    t = timings(proj)
    if abs(d - (t["total"] + 1)) > 2:
        print(f"  WARNING: duration differs from narration ({t['total']:.1f}s)")
    from state import visuals_hash
    (proj / "render/manifest.json").write_text(json.dumps(
        {"duration": round(d, 3), "size_mb": round(size, 1), "loudness_in": before, "visuals_hash": visuals_hash(proj)}, indent=1) + "\n")


def thumbnail_ids(proj):
    """Every <Still id="Thumbnail..."> in Root.tsx: Thumbnail -> thumbnail.jpg, ThumbnailB -> thumbnail-b.jpg."""
    ids = re.findall(r'<Still\s+id="(Thumbnail\w*)"', (proj / "video/src/Root.tsx").read_text())
    return [(i, "thumbnail.jpg" if i == "Thumbnail" else f"thumbnail-{i[9:].lower()}.jpg") for i in ids]


def cmd_thumbnail(args):
    proj = proj_path(args[0])
    outdir = proj / "publish/youtube"
    outdir.mkdir(parents=True, exist_ok=True)
    for comp, name in thumbnail_ids(proj):
        out = outdir / name
        tmp = out.with_suffix(".full.png")
        remotion(proj, "still", proj / "video/src/index.ts", comp, tmp, "--log=error")
        run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-vf", "scale=1280:720:flags=lanczos", "-q:v", "2", out])
        tmp.unlink()
        kb = out.stat().st_size / 1024
        print(f"{out} ({kb:.0f} KB){'  WARNING: over 2 MB YouTube limit' if kb > 2048 else ''}")


def cmd_short(args):
    import argparse
    ap = argparse.ArgumentParser(prog="xv short")
    ap.add_argument("project"); ap.add_argument("--start", type=float, required=True); ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--name", required=True); ap.add_argument("--title", default="")
    a = ap.parse_args(args)
    proj = proj_path(a.project); slug = slug_of(proj)
    src = proj / f"render/{slug}.mp4"
    outdir = proj / "publish/social/shorts"; outdir.mkdir(parents=True, exist_ok=True)
    # captions for the window, shifted to start at 0
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
    run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a.start), "-to", str(a.end), "-i", src, "-filter_complex", vf,
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])
    print(f"{out}  ({a.end - a.start:.0f}s, 1080x1920)")


def cmd_carousel(args):
    """LinkedIn document post: the per-scene stills as one PDF."""
    from PIL import Image
    proj = proj_path(args[0])
    t = timings(proj)
    files = []
    for sc in t["scenes"]:
        hits = sorted((proj / "stills").glob(f"{sc['id']}-*.png"), key=lambda f: int(f.stem.rsplit("-", 1)[1]))
        if hits:
            files.append(hits[-1])
    if not files:
        sys.exit("No scene stills: run `xv stills <project>` first")
    pages = [Image.open(f).convert("RGB") for f in files]
    out = proj / "publish/social/linkedin-carousel.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=144)
    print(f"{out} ({len(pages)} pages)")


def cmd_youtube(args):
    run([PY, TOOLKIT / "youtube/package.py", proj_path(args[0])])


def cmd_lint(args):
    import lint
    sys.exit(lint.main(args))


def cmd_doctor(args):
    import doctor
    sys.exit(doctor.main(args))


def cmd_selftest(args):
    import doctor
    sys.exit(doctor.selftest())


def cmd_transcribe(args):
    run([PY, TOOLKIT / "tts/transcribe.py", *args])


def cmd_pdftext(args):
    from pypdf import PdfReader
    src = Path(args[0])
    text = "\n\n".join(f"--- page {i} ---\n{p.extract_text() or ''}" for i, p in enumerate(PdfReader(src).pages, 1))
    if "--out" in args:
        Path(args[args.index("--out") + 1]).write_text(text)
        print(f"wrote {args[args.index('--out') + 1]}")
    else:
        print(text)


def state_cmd(name):
    def f(args):
        import state
        state.CMDS[name](proj_path(args[0]), args[1:])
    return f


CMDS = {"new": cmd_new, "synth": cmd_synth, "asr": cmd_asr, "script-md": cmd_script_md, "typecheck": cmd_typecheck, "studio": cmd_studio,
        "stills": cmd_stills, "render": cmd_render, "thumbnail": cmd_thumbnail, "short": cmd_short, "carousel": cmd_carousel, "youtube": cmd_youtube,
        "lint": cmd_lint, "doctor": cmd_doctor, "selftest": cmd_selftest, "transcribe": cmd_transcribe, "pdftext": cmd_pdftext, **{k: state_cmd(k) for k in ("status", "commit", "gate", "feedback", "decision", "changed", "review")}}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS or (len(sys.argv) < 3 and sys.argv[1] not in ("new", "doctor", "selftest")):
        sys.exit(__doc__)
    if sys.argv[1] not in ("doctor", "selftest", "lint", "status", "feedback", "decision", "review", "changed", "commit", "gate", "script-md"):
        import doctor
        doctor.require_verified()
    try:
        CMDS[sys.argv[1]](sys.argv[2:])
    except subprocess.CalledProcessError as e:
        sys.exit(f"command failed ({e.returncode})")
