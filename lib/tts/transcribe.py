"""Transcribe an audio or video input with the pinned Whisper model (temperature 0, so reruns match).

Usage:  xv transcribe <file> [--out transcript.md] [--model small.en]
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import model as model_path


def main():
    ap = argparse.ArgumentParser(prog="xv transcribe")
    ap.add_argument("file")
    ap.add_argument("--out")
    ap.add_argument("--model", default="small.en")
    a = ap.parse_args()
    from faster_whisper import WhisperModel
    local = model_path(f"whisper/{a.model}")
    m = WhisperModel(str(local) if local.exists() else a.model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(a.file, beam_size=5, temperature=0.0)
    lines = [f"[{int(s.start) // 60}:{int(s.start) % 60:02d}] {s.text.strip()}" for s in segs]
    text = f"# Transcript: {Path(a.file).name}\n\nModel `{a.model}`.\n\n" + "\n".join(lines) + "\n"
    if a.out:
        Path(a.out).write_text(text)
        print(f"wrote {a.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
