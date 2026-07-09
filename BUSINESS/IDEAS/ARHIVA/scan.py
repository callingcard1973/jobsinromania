#!/usr/bin/env python3
"""Scaneaza IDEAS/ si compara cu MASTER.csv. Raporteaza lipsuri."""
import csv, os, subprocess, sys

IDEAS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MASTER.csv")
SKIP = {".claude", "INVENTAR", "__pycache__", ".venv", "node_modules", "openspec", ".easy-search", ".git"}
RASPIBIG = "tudor@192.168.100.21"
RASPIBIG_DIR = "/opt/ACTIVE/IDEAS"

def load_master():
    """Incarca MASTER.csv si returneaza set de proiecte + fisiere."""
    proiecte = set()
    fisiere = set()
    with open(MASTER, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            proiecte.add(row["Proiect"].strip())
            fisiere.add(row["Fisier"].strip())
    return proiecte, fisiere

def scan_local():
    """Scaneaza directoarele locale si returneaza statistici."""
    dirs = {}
    for entry in sorted(os.listdir(IDEAS_DIR)):
        path = os.path.join(IDEAS_DIR, entry)
        if not os.path.isdir(path) or entry in SKIP:
            continue
        stats = {"py": 0, "csv": 0, "json": 0, "md": 0, "db": 0, "total": 0}
        for root, subdirs, files in os.walk(path):
            subdirs[:] = [d for d in subdirs if d not in SKIP]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext == ".py": stats["py"] += 1
                elif ext == ".csv": stats["csv"] += 1
                elif ext == ".json": stats["json"] += 1
                elif ext == ".md": stats["md"] += 1
                elif ext == ".db": stats["db"] += 1
                stats["total"] += 1
        dirs[entry] = stats
    return dirs

def scan_raspibig():
    """Scaneaza directoarele pe raspibig via SSH."""
    try:
        result = subprocess.run(
            ["ssh", RASPIBIG, f"ls -1 {RASPIBIG_DIR}/"],
            capture_output=True, text=True, timeout=10
        )
        return set(result.stdout.strip().split("\n")) - SKIP
    except Exception as e:
        return set()

def main():
    proiecte_master, _ = load_master()
    dirs_local = scan_local()
    dirs_raspibig = scan_raspibig()

    print("=" * 70)
    print("INVENTAR SCAN — Raport")
    print("=" * 70)

    # Directoare locale
    print(f"\n{'Director':<35} {'PY':>4} {'CSV':>4} {'JSON':>5} {'MD':>4} {'DB':>3} {'Total':>6}")
    print("-" * 70)
    total_py = total_csv = total_json = total_md = total_db = total_all = 0
    for name, s in sorted(dirs_local.items()):
        print(f"{name:<35} {s['py']:>4} {s['csv']:>4} {s['json']:>5} {s['md']:>4} {s['db']:>3} {s['total']:>6}")
        total_py += s["py"]; total_csv += s["csv"]; total_json += s["json"]
        total_md += s["md"]; total_db += s["db"]; total_all += s["total"]
    print("-" * 70)
    print(f"{'TOTAL':<35} {total_py:>4} {total_csv:>4} {total_json:>5} {total_md:>4} {total_db:>3} {total_all:>6}")

    # Directoare locale care nu sunt in MASTER
    local_names = set(dirs_local.keys())
    # Mapare manuala directoare -> proiecte din MASTER
    ALIAS = {
        "CANADA_EU": "CANADA CETA", "EU_FUNDING": "EU PROIECTE",
        "LEGUME MASINI DE SORTAT LEGUME": "LEGUME MASINI",
        "LEO CASA BUZAU": "LEO BUZAU", "PRODUS MONTAN": "PRODUS MONTAN",
        "UNIFIED DB USAGE": "UNIFIED DB", "COOPERATIVA BUSINESS": "COOPERATIVA",
        "TRASABILITATE PRODUS ALIMENTAR": "TRASABILITATE",
    }
    master_upper = {p.upper() for p in proiecte_master}
    missing = []
    for d in local_names:
        alias = ALIAS.get(d, d).upper()
        d_upper = d.upper().replace(" ", "_").replace("-", "_")
        if not any(alias in m or d_upper in m or m in d_upper or m in alias for m in master_upper):
            missing.append(d)
    if missing:
        print(f"\n!! DIRECTOARE LOCALE FARA INTRARE IN MASTER.csv:")
        for m in sorted(missing):
            print(f"   - {m}/")

    # Sincronizare cu raspibig (compara doar directoare, ignora fisiere .md/.csv/.txt)
    if dirs_raspibig:
        raspibig_dirs = {d for d in dirs_raspibig if "." not in d}
        only_local = local_names - raspibig_dirs - {"INVENTAR"}
        only_raspibig = raspibig_dirs - local_names - {"INVENTAR"}
        if only_local:
            print(f"\n!! DOAR LOCAL (lipsesc pe raspibig):")
            for d in sorted(only_local): print(f"   - {d}/")
        if only_raspibig:
            print(f"\n!! DOAR RASPIBIG (lipsesc local):")
            for d in sorted(only_raspibig): print(f"   - {d}/")
        if not only_local and not only_raspibig:
            print(f"\n>> Sincronizare OK — {len(local_names)} directoare identice")
    else:
        print("\n!! Nu am putut contacta raspibig (SSH)")

    # Sumar MASTER.csv
    total_idei = len(proiecte_master)
    print(f"\n>> MASTER.csv: {total_idei} proiecte unice")
    print(f">> Local: {len(dirs_local)} directoare, {total_all} fisiere")
    print(f">> Din care: {total_py} .py, {total_csv} .csv, {total_json} .json, {total_md} .md")

if __name__ == "__main__":
    main()
