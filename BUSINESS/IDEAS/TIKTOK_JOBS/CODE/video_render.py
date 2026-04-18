"""Render vertical 1080x1920 TikTok video: animated gradient + text overlay + voice. ffmpeg only."""
import subprocess
import sys
import io
import random
from pathlib import Path

if __name__ == "__main__" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

RASPI = "tudor@192.168.100.21"
REMOTE_BASE = "/opt/ACTIVE/TIKTOK_JOBS"
REMOTE_WORK = f"{REMOTE_BASE}/render"

GRADIENT_PALETTES = [
    ("#ff4b2b", "#ff416c"),
    ("#1a2980", "#26d0ce"),
    ("#141e30", "#243b55"),
    ("#000428", "#004e92"),
    ("#ee9ca7", "#ffdde1"),
    ("#f7971e", "#ffd200"),
    ("#4568dc", "#b06ab3"),
    ("#00c6ff", "#0072ff"),
]


def sanitize(text):
    return text.replace("'", "").replace('"', "").replace(":", " -").replace("\\", "")


def render(wav_path, hook_text, out_mp4, flag_country="Norvegia"):
    """wav_path: LOCAL windows path. out_mp4: LOCAL windows path."""
    remote_wav = f"{REMOTE_WORK}/voice.wav"
    remote_out = f"{REMOTE_WORK}/out.mp4"
    subprocess.run(["ssh", RASPI, f"mkdir -p {REMOTE_WORK}"], check=True)
    subprocess.run(["scp", "-q", str(wav_path), f"{RASPI}:{remote_wav}"], check=True)

    c1, c2 = random.choice(GRADIENT_PALETTES)
    safe_hook = sanitize(hook_text)
    safe_country = sanitize(flag_country).upper()

    wrapped = wrap_text(safe_hook, 28)

    filter_complex = (
        f"color=c={c1}:s=1080x1920:d=30[bg1];"
        f"color=c={c2}:s=1080x1920:d=30[bg2];"
        f"[bg1][bg2]blend=all_expr='A*(1-T/15)+B*(T/15)':shortest=1[bg];"
        f"[bg]drawtext=text='{safe_country}':fontsize=90:fontcolor=white:"
        f"x=(w-text_w)/2:y=150:borderw=4:bordercolor=black,"
        f"drawtext=text='{wrapped}':fontsize=54:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:borderw=5:bordercolor=black:line_spacing=20,"
        f"drawtext=text='LINK IN BIO':fontsize=70:fontcolor=yellow:"
        f"x=(w-text_w)/2:y=h-250:borderw=5:bordercolor=black:"
        f"enable='gt(mod(t\\,1)\\,0.5)'[v]"
    )

    cmd = (
        f"ffmpeg -y -f lavfi -i color=black:s=1080x1920:d=30 -i {remote_wav} "
        f"-filter_complex \"{filter_complex}\" -map '[v]' -map 1:a "
        f"-c:v libx264 -preset veryfast -pix_fmt yuv420p -c:a aac -b:a 128k "
        f"-shortest -movflags +faststart {remote_out}"
    )
    result = subprocess.run(
        ["ssh", RASPI, cmd], capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("FFMPEG ERROR:", result.stderr[-1500:])
        sys.exit(1)

    subprocess.run(["scp", "-q", f"{RASPI}:{remote_out}", str(out_mp4)], check=True)
    return out_mp4


def wrap_text(text, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines[:6])


if __name__ == "__main__":
    wav = Path(sys.argv[1]).resolve()
    hook = sys.argv[2]
    out = Path(sys.argv[3] if len(sys.argv) > 3 else "../OUTPUT/queue/test.mp4").resolve()
    country = sys.argv[4] if len(sys.argv) > 4 else "NORVEGIA"
    out.parent.mkdir(parents=True, exist_ok=True)
    render(wav, hook, out, country)
    print(f"OK: {out}")
