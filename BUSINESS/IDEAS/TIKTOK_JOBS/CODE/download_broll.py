"""Download CC0 b-roll from Coverr (no signup, direct URLs). Run once."""
import subprocess
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

RASPI = "tudor@192.168.100.21"
REMOTE_BROLL = "/opt/ACTIVE/TIKTOK_JOBS/broll"

CLIPS = {
    "construction_site.mp4": "https://assets.mixkit.co/videos/preview/mixkit-construction-worker-cutting-an-iron-bar-1530-large.mp4",
    "welder.mp4": "https://assets.mixkit.co/videos/preview/mixkit-welder-working-on-metal-beams-1546-large.mp4",
    "factory_line.mp4": "https://assets.mixkit.co/videos/preview/mixkit-factory-conveyor-belt-transporting-products-2694-large.mp4",
    "warehouse.mp4": "https://assets.mixkit.co/videos/preview/mixkit-industrial-shelf-in-a-warehouse-4785-large.mp4",
    "cargo_truck.mp4": "https://assets.mixkit.co/videos/preview/mixkit-truck-driving-on-the-highway-1155-large.mp4",
    "norway_fjord.mp4": "https://assets.mixkit.co/videos/preview/mixkit-aerial-shot-of-the-norwegian-fjord-32715-large.mp4",
    "city_aerial.mp4": "https://assets.mixkit.co/videos/preview/mixkit-aerial-view-of-a-city-at-dawn-34445-large.mp4",
    "money_counting.mp4": "https://assets.mixkit.co/videos/preview/mixkit-hands-counting-dollars-4894-large.mp4",
    "worker_hands.mp4": "https://assets.mixkit.co/videos/preview/mixkit-worker-tightening-a-bolt-using-a-wrench-1550-large.mp4",
    "cooking_kitchen.mp4": "https://assets.mixkit.co/videos/preview/mixkit-chef-cooking-in-a-professional-kitchen-4882-large.mp4",
    "farm_tractor.mp4": "https://assets.mixkit.co/videos/preview/mixkit-tractor-ploughing-a-field-1447-large.mp4",
    "nurse_patient.mp4": "https://assets.mixkit.co/videos/preview/mixkit-nurse-caring-for-an-elderly-patient-4882-large.mp4",
}


def download():
    cmd = f"mkdir -p {REMOTE_BROLL}"
    subprocess.run(["ssh", RASPI, cmd], check=True)
    for name, url in CLIPS.items():
        path = f"{REMOTE_BROLL}/{name}"
        check = subprocess.run(
            ["ssh", RASPI, f"test -s {path} && echo EXISTS || echo MISSING"],
            capture_output=True, text=True,
        )
        if "EXISTS" in check.stdout:
            print(f"SKIP {name}")
            continue
        dl = subprocess.run(
            ["ssh", RASPI, f"curl -sSL -o {path} '{url}' && ls -l {path}"],
            capture_output=True, text=True,
        )
        ok = "OK" if dl.returncode == 0 else "FAIL"
        print(f"{ok} {name}")


if __name__ == "__main__":
    download()
