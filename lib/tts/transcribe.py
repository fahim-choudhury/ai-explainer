"""Transcribe an audio or video input with the pinned Whisper model (temperature 0, so reruns match).

Called by `xv transcribe <file> [-o FILE] [--model small.en]`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import model as model_path


def transcribe(file, model_name="small.en"):
    from faster_whisper import WhisperModel
    local = model_path(f"whisper/{model_name}")
    m = WhisperModel(str(local) if local.exists() else model_name, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(file), beam_size=5, temperature=0.0)
    lines = [f"[{int(s.start) // 60}:{int(s.start) % 60:02d}] {s.text.strip()}" for s in segs]
    return f"# Transcript: {Path(file).name}\n\nModel `{model_name}`.\n\n" + "\n".join(lines) + "\n"
