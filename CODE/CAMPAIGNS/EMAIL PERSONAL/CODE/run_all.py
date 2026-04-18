import subprocess
import sys

STAGES = ['00_merge.py', '01_clean.py', '02_dedupe.py', '03_score.py', '04_segment.py', '05_export.py']

for stage in STAGES:
    print(f"\n{'='*40}\nRunning {stage}\n{'='*40}")
    result = subprocess.run([sys.executable, stage], capture_output=False)
    if result.returncode != 0:
        print(f"FAILED at {stage}")
        sys.exit(1)

print("\nDone. Pipeline complete. Open export/index.html in browser.")
