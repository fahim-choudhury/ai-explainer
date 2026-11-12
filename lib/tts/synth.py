"""Narration for an explainer project: Kokoro TTS per line -> narration.wav, timings.json, .srt

Usage:  xv synth <project>

Reads   <project>/script/script.json
Writes  <project>/audio/narration.wav      (also copied to video/public/)
        <project>/audio/timings.json
        <project>/audio/<slug>.srt
Lines are cached in <project>/audio/.cache by (text, voice, speed), so edits only
re-synthesize the lines that changed.
"""
import hashlib, json, re, shutil, sys
from pathlib import Path
import numpy as np
import soundfile as sf

TOOLKIT = Path(__file__).resolve().parent.parent
SR = 24000


def load_lexicon(script):
    lex = json.loads((TOOLKIT / "tts/lexicon.json").read_text())
    lex.pop("_comment", None)
    lex.update(script.get("say", {}))
    return lex


def spoken(text, lex):
    for pat, rep in lex.items():
        text = re.sub(pat, rep, text)
    return text


def ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main(proj):
    proj = Path(proj).resolve()
    script = json.loads((proj / "script/script.json").read_text())
    slug = script["slug"]
    voice, speed, lang = script.get("voice", "af_heart"), float(script.get("speed", 1.0)), script.get("lang", "en-us")
    gaps = {"line": 0.35, "head": 0.5, "tail": 0.9, **script.get("gaps", {})}
    lex = load_lexicon(script)

    audio_dir = proj / "audio"; cache = audio_dir / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    kokoro = None

    def line_audio(text):
        nonlocal kokoro
        said = spoken(text, lex)
        key = hashlib.sha1(json.dumps([said, voice, speed, lang]).encode()).hexdigest()[:16]
        f = cache / f"{key}.wav"
        if f.exists():
            return sf.read(f, dtype="float32")[0], False
        if kokoro is None:
            from kokoro_onnx import Kokoro
            sys.path.insert(0, str(TOOLKIT))
            from paths import model
            kokoro = Kokoro(str(model("kokoro/kokoro-v1.0.onnx")), str(model("kokoro/voices-v1.0.bin")))
        a, sr = kokoro.create(said, voice=voice, speed=speed, lang=lang)
        assert sr == SR
        a = a.astype(np.float32)
        sf.write(f, a, SR)
        return a, True

    silence = lambda s: np.zeros(int(s * SR), dtype=np.float32)
    chunks, t, made, used = [], 0.0, 0, set()
    timings = {"fps": script.get("fps", 30), "scenes": []}
    for sc in script["scenes"]:
        start = t
        chunks.append(silence(gaps["head"])); t += gaps["head"]
        lines = []
        for i, text in enumerate(sc["lines"]):
            a, new = line_audio(text); made += new
            lines.append({"text": text, "start": round(t, 3), "end": round(t + len(a) / SR, 3)})
            chunks.append(a); t += len(a) / SR
            g = gaps["line"] if i < len(sc["lines"]) - 1 else gaps["tail"]
            chunks.append(silence(g)); t += g
        timings["scenes"].append({"id": sc["id"], "start": round(start, 3), "end": round(t, 3), "lines": lines})
        print(f"{sc['id']:14s} {start:7.1f}s -> {t:7.1f}s", flush=True)
    timings["total"] = round(t, 3)
    sys.path.insert(0, str(TOOLKIT))
    from state import script_hash
    timings["script_hash"] = script_hash(proj)

    sf.write(audio_dir / "narration.wav", np.concatenate(chunks), SR)
    (audio_dir / "timings.json").write_text(json.dumps(timings, indent=1))
    srt, n = [], 1
    for sc in timings["scenes"]:
        for ln in sc["lines"]:
            srt.append(f"{n}\n{ts(ln['start'])} --> {ts(ln['end'])}\n{ln['text']}\n"); n += 1
    (audio_dir / f"{slug}.srt").write_text("\n".join(srt))
    pub = proj / "video/public"; pub.mkdir(parents=True, exist_ok=True)
    shutil.copy2(audio_dir / "narration.wav", pub / "narration.wav")
    words = sum(len(l.split()) for s in script["scenes"] for l in s["lines"])
    print(f"total {t:.1f}s ({int(t // 60)}:{int(t % 60):02d}) | {words} words | {made} lines synthesized, rest cached")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
