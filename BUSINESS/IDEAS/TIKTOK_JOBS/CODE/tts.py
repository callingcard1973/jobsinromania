"""Unified TTS: Piper for EU langs (RO/EN/FR/ES/IT/DE), edge-tts for non-EU."""
import subprocess
import sys
import io
from pathlib import Path

if __name__ == "__main__" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

RASPI = "tudor@192.168.100.21"
REMOTE_BASE = "/opt/ACTIVE/TIKTOK_JOBS"
REMOTE_VOICES = f"{REMOTE_BASE}/voices"
REMOTE_VENV_PIPER = f"{REMOTE_BASE}/venv/bin/piper"
REMOTE_VENV_EDGE = f"{REMOTE_BASE}/venv/bin/edge-tts"

PIPER_VOICES = {
    "ro": "ro.onnx",
    "en": "en_US-ryan-medium.onnx",
    "fr": "fr_FR-siwis-medium.onnx",
    "es": "es_ES-davefx-medium.onnx",
    "it": "it_IT-paola-medium.onnx",
    "de": "de_DE-thorsten-medium.onnx",
}

EDGE_VOICES = {
    "ur": "ur-PK-AsadNeural",
    "hi": "hi-IN-MadhurNeural",
    "ar": "ar-SA-HamedNeural",
    "tl": "fil-PH-AngeloNeural",
    "vi": "vi-VN-NamMinhNeural",
    "uk": "uk-UA-OstapNeural",
    "bn": "bn-IN-BashkarNeural",
    "ne": "ne-NP-SagarNeural",
}


def synth(text, lang, out_path):
    """Synthesize to local Windows path. Runs on raspibig via SSH, copies back."""
    remote_wav = f"/tmp/tts_{lang}_{abs(hash(text)) % 100000}.wav"
    if lang in PIPER_VOICES:
        voice = f"{REMOTE_VOICES}/{PIPER_VOICES[lang]}"
        cmd = f"echo {shell_escape(text)} | {REMOTE_VENV_PIPER} -m {voice} -f {remote_wav}"
    elif lang in EDGE_VOICES:
        cmd = f"{REMOTE_VENV_EDGE} --voice {EDGE_VOICES[lang]} --text {shell_escape(text)} --write-media {remote_wav}"
    else:
        raise ValueError(f"Unsupported lang: {lang}")

    subprocess.run(["ssh", RASPI, cmd], check=True, capture_output=True)
    subprocess.run(["scp", f"{RASPI}:{remote_wav}", str(out_path)], check=True, capture_output=True)
    subprocess.run(["ssh", RASPI, f"rm -f {remote_wav}"], check=False, capture_output=True)
    return out_path


def shell_escape(s):
    return "'" + s.replace("'", "'\\''") + "'"


def supported_langs():
    return list(PIPER_VOICES.keys()) + list(EDGE_VOICES.keys())


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "ro"
    text = sys.argv[2] if len(sys.argv) > 2 else "Salutare, test TTS."
    out = Path(sys.argv[3] if len(sys.argv) > 3 else f"../OUTPUT/queue/test_{lang}.wav").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    synth(text, lang, out)
    print(f"OK: {out}")
