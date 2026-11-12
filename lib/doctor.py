"""Dependency verification. ./setup installs; this module checks, and gates every other xv command.

  xv doctor            full check (hashes every model file); writes .xv-verified on success
  xv doctor --quick    skip model hashing (sizes only)
  xv selftest          throwaway project through synth, ASR, lint, typecheck and two stills
  python lib/doctor.py fetch-models   download and verify models (used by ./setup)
"""
import hashlib, json, os, platform, re, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import REPO, PY, MODELS, STAMP

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


def main(args):
    quick = "--quick" in args
    ok = True

    def say(good, msg, hint=""):
        nonlocal ok
        ok &= bool(good)
        print(("  ok   " if good else "  FAIL ") + msg + ("" if good or not hint else f"\n         fix: {hint}"))

    print("system tools")
    say(platform.system() == "Linux", f"operating system {platform.system()}", "this workflow supports Linux only (Windows: use WSL)")
    for cmd, vargs, minimum, hint in SYSTEM:
        path = shutil.which(cmd)
        if not path:
            say(False, f"{cmd} not found", hint)
            continue
        out = subprocess.run([cmd, *vargs], capture_output=True, text=True).stdout
        if minimum:
            have = version_tuple(out)
            say(have >= minimum, f"{cmd} {out.strip().splitlines()[0]} (need {'.'.join(map(str, minimum))}+)", hint)
        else:
            say(True, cmd)

    print("python")
    uv = REPO / ".tools/uv"
    say(uv.exists(), f"uv at {uv}", "run ./setup")
    say(PY.exists(), "virtual environment .venv", "run ./setup")
    if uv.exists() and PY.exists():
        want = json.loads((REPO / "deps/tools.json").read_text())["python"]
        have = subprocess.run([PY, "-c", "import platform; print(platform.python_version())"], capture_output=True, text=True).stdout.strip()
        say(have == want, f"python {have} (pinned {want})", "run ./setup")
        r = subprocess.run([uv, "sync", "--locked", "--check", "--python", want], cwd=REPO, capture_output=True, text=True,
                           env={**os.environ, "UV_PYTHON_INSTALL_DIR": str(REPO / ".tools/python"), "UV_PYTHON_PREFERENCE": "only-managed"})
        say(r.returncode == 0, ".venv matches uv.lock", "run ./setup  (" + (r.stderr.strip().splitlines() or [""])[-1] + ")")

    print("node")
    lock = json.loads((REPO / "package-lock.json").read_text())["packages"]
    inst_f = REPO / "node_modules/.package-lock.json"
    if not inst_f.exists():
        say(False, "node_modules", "run ./setup")
    else:
        inst = json.loads(inst_f.read_text())["packages"]
        bad = [k for k, v in lock.items() if k and not v.get("optional") and inst.get(k, {}).get("version") != v.get("version")]
        say(not bad, "node_modules matches package-lock.json" + (f": {', '.join(bad[:5])}" if bad else ""), "run ./setup")
        shell = list((REPO / "node_modules/.remotion").glob("chrome-headless-shell/*/*/chrome-headless-shell")) + \
            list((REPO / "node_modules/.remotion").glob("chrome-headless-shell/*/chrome-headless-shell*"))
        say(bool(shell), "Remotion headless browser", "run ./setup  (npx remotion browser ensure)")

    print("models" + (" (sizes only, --quick)" if quick else ""))
    for m in models():
        f = MODELS / m["path"]
        if not f.exists():
            say(False, m["path"], "run ./setup")
        elif quick:
            say(f.stat().st_size > 0, m["path"])
        else:
            say(sha256(f) == m["sha256"], m["path"], "delete it and run ./setup")

    if ok and not quick:
        STAMP.write_text(json.dumps(lock_digest(), indent=1) + "\n")
        print(f"\nAll checks passed. Wrote {STAMP.name}.")
    elif ok:
        print("\nAll quick checks passed (run without --quick to write the verification stamp).")
    else:
        print("\nSome checks failed. Fix them, then run `xv doctor` again.")
    return 0 if ok else 1


def require_verified():
    """Called before every command that uses a dependency. Cheap: compares lockfile hashes with the stamp."""
    if not STAMP.exists():
        sys.exit("xv: dependencies not verified yet. Run ./setup (or `xv doctor` if setup already ran).")
    if json.loads(STAMP.read_text()) != lock_digest():
        sys.exit("xv: a lockfile changed since the last verification. Run ./setup, then `xv doctor`.")
    missing = [m["path"] for m in models() if not (MODELS / m["path"]).exists()]
    if missing or not PY.exists() or not (REPO / "node_modules").exists():
        sys.exit("xv: dependencies are missing (" + ", ".join(missing or ["venv or node_modules"]) + "). Run ./setup.")


def selftest():
    xv = REPO / "bin/xv"
    with tempfile.TemporaryDirectory(prefix="xv-selftest-") as ws:
        env = {**os.environ, "XV_WORKSPACE": ws}
        p = "explainer-selftest"
        steps = [["new", "selftest", "Self test"], ["synth", p], ["asr", p], ["lint", p, "--only", "narration"], ["typecheck", p],
                 ["stills", p, "--frames", "30"], ["thumbnail", p]]
        for s in steps:
            print(f"\n== xv {' '.join(s)}", flush=True)
            r = subprocess.run([xv, *s], env=env)
            if r.returncode != 0:
                print(f"\nselftest FAILED at `xv {' '.join(s)}`")
                return 1
        asr = (Path(ws) / p / "audio/asr-check.md").read_text()
        print("\n" + asr.splitlines()[2])
        for f in ("stills/f30.png", "publish/youtube/thumbnail.jpg"):
            if not (Path(ws) / p / f).exists():
                print(f"selftest FAILED: {f} was not produced")
                return 1
    print("\nselftest passed")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["fetch-models"]:
        fetch_models()
    else:
        sys.exit(main(sys.argv[1:]))
