"""Run full pipeline: wb_fetch → ti_fetch → merge_profiles → print import instructions."""
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).parent


def run(script: str) -> None:
    print(f"\n=== Running {script} ===")
    result = subprocess.run([sys.executable, CODE / script], check=False)
    if result.returncode != 0:
        print(f"FAILED: {script}")
        sys.exit(1)


def main() -> None:
    run("wb_fetch.py")
    run("ti_fetch.py")
    run("merge_profiles.py")
    run("db_insert.py")
    print("\n=== Pipeline + DB insert complete ===")
    print("Next steps:")
    print("  1. Upload DATA/countries.json to A2: scp DATA/countries.json loaiidil@nl1-cl8-ats1.a2hosting.com:~/ajwang.org/DATA/")
    print("  2. Run importer: wp eval-file CODE/wp_import.php --path=~/ajwang.org")


if __name__ == "__main__":
    main()
