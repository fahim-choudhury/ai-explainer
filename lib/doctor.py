"""Dependency verification. ./setup installs; this module checks, and gates every other xv command.

  xv doctor [--quick] [--json]   check every dependency; a full pass writes .xv-verified
  xv selftest                    throwaway project through synth, ASR, lint, typecheck, stills, thumbnail and a full render
  python lib/doctor.py fetch-models   download and verify models (used by ./setup)
"""
import hashlib, json, os, platform, re, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import REPO, PY, MODELS, STAMP
import ui
from ui import XVError, NOT_SET_UP

# System tools ./setup checks but does not install. (command, version args, minimum version or None, install hint)
SYSTEM = [
    ("git", ["--version"], None, "dnf install git | apt install git"),
    ("curl", ["--version"], None, "dnf install curl | apt install curl"),
    ("tar", ["--version"], None, "dnf install tar | apt install tar"),
    ("ffmpeg", ["-version"], None, "dnf install ffmpeg (RPM Fusion) | apt install ffmpeg"),
    ("ffprobe", ["-version"], None, "ships with ffmpeg"),
    ("node", ["--version"], (20, 0), "Node.js 20 or newer: https://nodejs.org or your distro's nodejs package"),
    ("npm", ["--version"], None, "ships with Node.js"),
    ("npx", ["--version"], None, "ships with Node.js"),
]
LOCKS = ["uv.lock", "package-lock.json", "deps/models.json", "deps/tools.json", "pyproject.toml"]


def sha256(f):
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lock_digest():
    return {name: sha256(REPO / name) for name in LOCKS}


def models():
    return json.loads((REPO / "deps/models.json").read_text())["files"]


def fetch_models():
    for m in models():
        dest = MODELS / m["path"]
        if dest.exists() and sha256(dest) == m["sha256"]:
            print(f"  ok   {m['path']} (present)")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        print(f"  get  {m['url']}", flush=True)
        with urllib.request.urlopen(m["url"]) as r, open(tmp, "wb") as out:
            shutil.copyfileobj(r, out, 1 << 20)
        got = sha256(tmp)
        if got != m["sha256"]:
            tmp.unlink()
            sys.exit(f"  FAIL {m['path']}: SHA256 {got} does not match the pinned {m['sha256']}")
        tmp.rename(dest)
        print(f"  ok   {m['path']}")


def version_tuple(text):
    m = re.search(r"(\d+)\.(\d+)", text)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def checks(quick=False):
    """Every dependency check as {"group", "name", "ok", "fix"}. Writes the verification stamp when all pass (not with quick)."""
    res = []

    def add(group, good, name, fix=""):
        res.append({"group": group, "name": name, "ok": bool(good), "fix": "" if good else fix})

    add("system", platform.system() == "Linux", f"operating system {platform.system()}", "this workflow supports Linux only (Windows: use WSL)")
    for cmd, vargs, minimum, fix in SYSTEM:
        if not shutil.which(cmd):
            add("system", False, f"{cmd} not found", fix)
            continue
        out = subprocess.run([cmd, *vargs], capture_output=True, text=True).stdout
        if minimum:
            have = version_tuple(out)
            add("system", have >= minimum, f"{cmd} {out.strip().splitlines()[0]} (need {'.'.join(map(str, minimum))}+)", fix)
        else:
            add("system", True, cmd)

    uv = REPO / ".tools/uv"
    add("python", uv.exists(), f"uv at {uv}", "run ./setup")
    add("python", PY.exists(), "virtual environment .venv", "run ./setup")
    if uv.exists() and PY.exists():
        want = json.loads((REPO / "deps/tools.json").read_text())["python"]
        have = subprocess.run([PY, "-c", "import platform; print(platform.python_version())"], capture_output=True, text=True).stdout.strip()
        add("python", have == want, f"python {have} (pinned {want})", "run ./setup")
        r = subprocess.run([uv, "sync", "--locked", "--check", "--python", want], cwd=REPO, capture_output=True, text=True,
                           env={**os.environ, "UV_PYTHON_INSTALL_DIR": str(REPO / ".tools/python"), "UV_PYTHON_PREFERENCE": "only-managed"})
        add("python", r.returncode == 0, ".venv matches uv.lock", "run ./setup  (" + (r.stderr.strip().splitlines() or [""])[-1] + ")")

    lock = json.loads((REPO / "package-lock.json").read_text())["packages"]
    inst_f = REPO / "node_modules/.package-lock.json"
    if not inst_f.exists():
        add("node", False, "node_modules", "run ./setup")
    else:
        inst = json.loads(inst_f.read_text())["packages"]
        bad = [k for k, v in lock.items() if k and not v.get("optional") and inst.get(k, {}).get("version") != v.get("version")]
        add("node", not bad, "node_modules matches package-lock.json" + (f": {', '.join(bad[:5])}" if bad else ""), "run ./setup")
        shell = list((REPO / "node_modules/.remotion").glob("chrome-headless-shell/*/*/chrome-headless-shell")) + \
            list((REPO / "node_modules/.remotion").glob("chrome-headless-shell/*/chrome-headless-shell*"))
        add("node", bool(shell), "Remotion headless browser", "run ./setup  (npx remotion browser ensure)")

    for m in models():
        f = MODELS / m["path"]
        if not f.exists():
            add("models", False, m["path"], "run ./setup")
        elif quick:
            add("models", f.stat().st_size > 0, f"{m['path']} (size only)")
        else:
            add("models", sha256(f) == m["sha256"], m["path"], "delete it and run ./setup")

    if all(c["ok"] for c in res) and not quick:
        STAMP.write_text(json.dumps(lock_digest(), indent=1) + "\n")
    return res


def require_verified():
    """Called before every command that uses a dependency. Cheap: compares lockfile hashes with the stamp."""
    if not STAMP.exists():
        raise XVError("dependencies are not verified yet", "run ./setup (or `xv doctor` if setup already ran)", code=NOT_SET_UP)
    if json.loads(STAMP.read_text()) != lock_digest():
        raise XVError("a lockfile changed since the last verification", "run ./setup, then `xv doctor`", code=NOT_SET_UP)
    missing = [m["path"] for m in models() if not (MODELS / m["path"]).exists()]
    if missing or not PY.exists() or not (REPO / "node_modules").exists():
        raise XVError("dependencies are missing: " + ", ".join(missing or ["venv or node_modules"]), "run ./setup", code=NOT_SET_UP)


def selftest():
    """Throwaway project through the main steps, including a full render (a still alone misses
    failures that only appear across many frames, such as an uncleared delayRender; the short --timeout (Remotion's minimum, 7 s) makes those fail
    within this 12-second video instead of after Remotion's default 30 s). Returns the failed step, or None."""
    xv = REPO / "bin/xv"
    with tempfile.TemporaryDirectory(prefix="xv-selftest-") as ws:
        p = "explainer-selftest"
        steps = [["new", "selftest", "Self test"], ["synth", p], ["asr", p], ["lint", p, "--only", "narration"], ["typecheck", p],
                 ["stills", p, "--frames", "30"], ["thumbnail", p], ["render", p, "--timeout", "7000"]]
        for s in steps:
            ui.info(f"== xv {' '.join(s)}")
            r = subprocess.run([xv, "--workspace", ws, *(["--quiet"] if ui.QUIET else []), *s], stdout=sys.stderr)
            if r.returncode != 0:
                return " ".join(s)
        ui.info((Path(ws) / p / "audio/asr-check.md").read_text().splitlines()[2])
        for f in ("stills/f30.png", "publish/youtube/thumbnail.jpg", "render/selftest.mp4", "render/manifest.json"):
            if not (Path(ws) / p / f).exists():
                return f"{f} was not produced"
    return None


if __name__ == "__main__":
    if sys.argv[1:] != ["fetch-models"]:
        sys.exit("usage: python lib/doctor.py fetch-models   (called by ./setup; use `xv doctor` to check)")
    fetch_models()
