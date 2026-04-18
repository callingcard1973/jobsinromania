"""Create directories + claude.md for all IDEAS that don't have one."""
import csv, os, pathlib

BASE = pathlib.Path(r"D:\MEMORY\IDEAS")

# Map existing directories to their IDEA numbers (already have dirs)
EXISTING_MAP = {
    "GUMROAD": "GUMROAD",
    "ASOCIATII": "ASOCIATII",
    "CHINA": "CHINA",
    "COOPERATIVA BUSINESS": "COOPERATIVA BUSINESS",
    "DATING": "DATING",
    "EU_FUNDING": "EU_FUNDING",
    "FOOD": "FOOD",
    "FRESKON": "FRESKON",
    "LEO CASA BUZAU": "LEO CASA BUZAU",
    "LLM": "LLM",
    "MERCOSUR": "MERCOSUR",
    "NATO": "NATO",
    "PRODUS MONTAN": "PRODUS MONTAN",
    "TRASABILITATE PRODUS ALIMENTAR": "TRASABILITATE PRODUS ALIMENTAR",
    "UNIFIED DB USAGE": "UNIFIED DB USAGE",
    "LEGUME MASINI DE SORTAT LEGUME": "LEGUME MASINI DE SORTAT LEGUME",
    "CANADA_EU": "CANADA_EU",
}

# Project names that map to existing directories
PROJECT_TO_DIR = {
    "GUMROAD": "GUMROAD",
    "ASOCIATII": "ASOCIATII",
    "CHINA TRADE": "CHINA",
    "COOPERATIVA": "COOPERATIVA BUSINESS",
    "DATING SPEEDMATCH": "DATING",
    "EU PROIECTE": "EU_FUNDING",
    "FOOD HORECA": "FOOD",
    "FRESKON": "FRESKON",
    "LEO BUZAU": "LEO CASA BUZAU",
    "LLM CLASSIFIER": "LLM",
    "MERCOSUR": "MERCOSUR",
    "NATO": "NATO",
    "PRODUS MONTAN": "PRODUS MONTAN",
    "TRASABILITATE": "TRASABILITATE PRODUS ALIMENTAR",
    "UNIFIED DB": "UNIFIED DB USAGE",
    "LEGUME MASINI": "LEGUME MASINI DE SORTAT LEGUME",
    "CANADA CETA": "CANADA_EU",
    "FDATING": "DATING",
}

# Read MASTER.csv
ideas = []
with open(BASE / "INVENTAR" / "MASTER.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        ideas.append(row)

created = 0
skipped_existing = 0
skipped_dead = 0
claude_added = 0

for idea in ideas:
    idea_id = idea["ID"].strip()
    project = idea["Proiect"].strip()
    status = idea["Status"].strip()
    categorie = idea["Categorie"].strip()
    tip = idea["Tip"].strip()
    ce_face = idea["Ce_face"].strip().strip('"')
    venit = idea["Venit_EUR"].strip()
    efort = idea["Efort_ore"].strip()

    # Skip dead ideas
    if status == "UCIS":
        skipped_dead += 1
        continue

    # Check if maps to existing directory
    if project in PROJECT_TO_DIR:
        existing_dir = BASE / PROJECT_TO_DIR[project]
        if existing_dir.exists():
            # Check if claude.md exists
            cm = existing_dir / "claude.md"
            CM = existing_dir / "CLAUDE.md"
            if cm.exists() or CM.exists():
                skipped_existing += 1
                continue
            else:
                # Add claude.md to existing dir
                with open(cm, "w", encoding="utf-8") as f:
                    f.write(f"# {project} ({idea_id})\n\n")
                    f.write(f"**Status:** {status} | **Categorie:** {categorie} | **Tip:** {tip}\n\n")
                    f.write(f"## Ce face\n{ce_face}\n\n")
                    f.write(f"## Venit estimat\n{venit} EUR\n\n")
                    f.write(f"## Efort\n{efort} ore\n")
                claude_added += 1
                print(f"  CLAUDE.MD added: {existing_dir}")
                continue

    # Create new directory under INVENTAR
    dir_name = f"{idea_id}_{project.replace(' ', '_')}"
    dir_path = BASE / "INVENTAR" / dir_name

    if dir_path.exists():
        # Check for claude.md
        cm = dir_path / "claude.md"
        if cm.exists():
            skipped_existing += 1
            continue
    else:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Write claude.md
    cm = dir_path / "claude.md"
    with open(cm, "w", encoding="utf-8") as f:
        f.write(f"# {project} ({idea_id})\n\n")
        f.write(f"**Status:** {status} | **Categorie:** {categorie} | **Tip:** {tip}\n\n")
        f.write(f"## Ce face\n{ce_face}\n\n")
        f.write(f"## Venit estimat\n{venit} EUR\n\n")
        f.write(f"## Efort\n{efort} ore\n\n")
        f.write(f"## Next steps\n- [ ] TODO\n")

    created += 1
    print(f"  CREATED: {dir_path}")

print(f"\n--- DONE ---")
print(f"Created: {created}")
print(f"Claude.md added to existing: {claude_added}")
print(f"Skipped (already has claude.md): {skipped_existing}")
print(f"Skipped (UCIS/dead): {skipped_dead}")
