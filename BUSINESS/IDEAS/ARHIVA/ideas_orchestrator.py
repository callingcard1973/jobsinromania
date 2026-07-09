"""Ideas Orchestrator — Inspect, create dirs, generate claude.md, research."""
import csv
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = Path(r"D:\MEMORY\IDEAS")
INVENTAR = BASE / "INVENTAR"
STATE_FILE = INVENTAR / "orchestrator_state.json"
MASTER_CSV = INVENTAR / "MASTER.csv"

# Existing top-level directories mapped to project names
PROJECT_TO_DIR = {
    "GUMROAD": "GUMROAD", "ASOCIATII": "ASOCIATII", "CHINA TRADE": "CHINA",
    "COOPERATIVA": "COOPERATIVA BUSINESS", "DATING SPEEDMATCH": "DATING",
    "EU PROIECTE": "EU_FUNDING", "FOOD HORECA": "FOOD", "FRESKON": "FRESKON",
    "LEO BUZAU": "LEO CASA BUZAU", "LLM CLASSIFIER": "LLM",
    "MERCOSUR": "MERCOSUR", "NATO": "NATO", "PRODUS MONTAN": "PRODUS MONTAN",
    "TRASABILITATE": "TRASABILITATE PRODUS ALIMENTAR",
    "UNIFIED DB": "UNIFIED DB USAGE",
    "LEGUME MASINI": "LEGUME MASINI DE SORTAT LEGUME",
    "CANADA CETA": "CANADA_EU", "FDATING": "DATING",
}


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"phase": "inspect", "processed": [], "last_run": None}


def save_state(state):
    state["last_run"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_ideas():
    ideas = []
    with open(MASTER_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ideas.append({k.strip(): v.strip().strip('"') for k, v in row.items()})
    return ideas


def get_idea_dir(idea):
    project = idea["Proiect"]
    idea_id = idea["ID"]
    # Check if maps to existing top-level dir
    if project in PROJECT_TO_DIR:
        d = BASE / PROJECT_TO_DIR[project]
        if d.exists():
            return d
    # Otherwise INVENTAR/IDEA-NNN_NAME
    dir_name = f"{idea_id}_{project.replace(' ', '_')}"
    return INVENTAR / dir_name


def has_detailed_claude(idea_dir):
    """Check if claude.md exists and has more than basic template."""
    for name in ["claude.md", "CLAUDE.md"]:
        p = idea_dir / name
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="ignore")
            # Basic template has ~10 lines, detailed has more
            if len(content) > 500:
                return True
    return False


# === PHASE 1: INSPECT ===
def phase_inspect(ideas):
    print("=" * 60)
    print("PHASE 1: INSPECT")
    print("=" * 60)
    report = {"total": len(ideas), "has_dir": 0, "has_claude": 0,
              "has_detailed": 0, "dead": 0, "missing_dir": [], "missing_claude": []}

    for idea in ideas:
        if idea["Status"] == "UCIS":
            report["dead"] += 1
            continue
        d = get_idea_dir(idea)
        if d.exists():
            report["has_dir"] += 1
            has_cm = any((d / n).exists() for n in ["claude.md", "CLAUDE.md"])
            if has_cm:
                report["has_claude"] += 1
            if has_detailed_claude(d):
                report["has_detailed"] += 1
            if not has_cm:
                report["missing_claude"].append(idea["ID"])
        else:
            report["missing_dir"].append(idea["ID"])

    print(f"  Total ideas: {report['total']}")
    print(f"  Dead (UCIS): {report['dead']}")
    print(f"  Has directory: {report['has_dir']}")
    print(f"  Has claude.md: {report['has_claude']}")
    print(f"  Has DETAILED claude.md: {report['has_detailed']}")
    print(f"  Missing directory: {len(report['missing_dir'])}")
    print(f"  Missing claude.md: {len(report['missing_claude'])}")
    if report["missing_dir"]:
        print(f"  Missing dirs: {report['missing_dir'][:10]}...")
    return report


# === PHASE 2: CREATE DIRECTORIES ===
def phase_directories(ideas):
    print("\n" + "=" * 60)
    print("PHASE 2: CREATE DIRECTORIES")
    print("=" * 60)
    created = 0
    for idea in ideas:
        if idea["Status"] == "UCIS":
            continue
        d = get_idea_dir(idea)
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {d.name}")
            created += 1
    print(f"  Total created: {created}")
    return created


# === PHASE 3: GENERATE CLAUDE.MD ===
def phase_claude_md(ideas):
    print("\n" + "=" * 60)
    print("PHASE 3: GENERATE CLAUDE.MD")
    print("=" * 60)
    generated = 0
    for idea in ideas:
        if idea["Status"] == "UCIS":
            continue
        d = get_idea_dir(idea)
        if not d.exists():
            continue
        if has_detailed_claude(d):
            continue

        # Generate claude.md from MASTER.csv data
        content = generate_claude_content(idea)
        cm = d / "claude.md"
        cm.write_text(content, encoding="utf-8")
        print(f"  Generated: {idea['ID']} {idea['Proiect']}")
        generated += 1

    print(f"  Total generated: {generated}")
    return generated


def generate_claude_content(idea):
    """Generate detailed claude.md from idea data."""
    lines = [
        f"# {idea['Proiect']} ({idea['ID']})",
        "",
        f"**Status:** {idea['Status']} | **Categorie:** {idea['Categorie']} | **Tip:** {idea['Tip']}",
        "",
        "## Ce face",
        idea["Ce_face"],
        "",
        "## Venit estimat",
        f"{idea['Venit_EUR']} EUR",
        "",
        "## Efort",
        f"{idea['Efort_ore']} ore",
        "",
        "## Fisiere",
        f"Referinta: {idea['Fisier'] if idea['Fisier'] != '-' else 'Niciun fisier inca'}",
        "",
        "## Data assets disponibile",
    ]

    # Check what data files exist nearby
    d = get_idea_dir(idea)
    data_files = []
    for ext in ["*.csv", "*.json", "*.xlsx", "*.sql"]:
        data_files.extend(d.glob(ext))
    if data_files:
        for f in data_files[:5]:
            lines.append(f"- {f.name} ({f.stat().st_size // 1024} KB)")
    else:
        lines.append("- Niciun fisier de date local (posibil in PostgreSQL)")

    lines.extend([
        "",
        "## Competitori",
        "- [ ] De cercetat (Phase 4)",
        "",
        "## Next steps",
        "- [ ] Cercetare piata + competitori",
        "- [ ] Validare cerere (exista clienti?)",
        "- [ ] MVP sau campanie test",
        "",
        f"## Ultima actualizare",
        idea["Actualizare"],
    ])
    return "\n".join(lines)


# === PHASE 4: RESEARCH ===
def phase_research(ideas, state):
    """Research each idea — runs slowly, saves progress."""
    print("\n" + "=" * 60)
    print("PHASE 4: RESEARCH (slow, resumable)")
    print("=" * 60)

    already_done = set(state.get("researched", []))
    to_research = [i for i in ideas
                   if i["Status"] not in ("UCIS",)
                   and i["ID"] not in already_done]

    print(f"  To research: {len(to_research)} ideas")
    print(f"  Already done: {len(already_done)}")

    for i, idea in enumerate(to_research):
        d = get_idea_dir(idea)
        research_file = d / "research.md"

        if research_file.exists() and research_file.stat().st_size > 200:
            # Already has research
            state.setdefault("researched", []).append(idea["ID"])
            save_state(state)
            continue

        print(f"\n  [{i+1}/{len(to_research)}] {idea['ID']}: {idea['Proiect']}")

        # Build search queries from idea data
        queries = build_research_queries(idea)
        results = []

        for q in queries:
            print(f"    Searching: {q[:60]}...")
            try:
                # Use local search — write query to file for external tool
                result = do_search(q)
                if result:
                    results.append({"query": q, "result": result})
            except Exception as e:
                print(f"    Error: {e}")
            time.sleep(2)  # Rate limit

        # Save research
        research_content = format_research(idea, results)
        research_file.write_text(research_content, encoding="utf-8")
        print(f"    Saved: {research_file}")

        # Update state
        state.setdefault("researched", []).append(idea["ID"])
        save_state(state)

    print(f"\n  Research complete: {len(to_research)} ideas processed")


def build_research_queries(idea):
    """Build search queries for an idea."""
    name = idea["Proiect"]
    desc = idea["Ce_face"]
    cat = idea["Categorie"]

    queries = []
    # Competitor search
    if cat in ("PRODUS", "SERVICIU"):
        queries.append(f"{desc[:80]} competitor alternative 2026")
        queries.append(f"{name} SaaS market size pricing")
    elif cat == "CAMPANIE":
        queries.append(f"{name} email campaign best practices recruitment")
    elif cat == "DATE":
        queries.append(f"buy {name} data Europe CSV download")
    elif cat == "CERCETARE":
        queries.append(f"{name} feasibility analysis 2026")

    # General market query
    queries.append(f"{desc[:60]} market opportunity Europe")

    return queries[:3]  # Max 3 queries per idea


def do_search(query):
    """Placeholder — in overnight mode, use web search API or save for Claude."""
    # Write query to a file that Claude/external tool can process
    search_log = INVENTAR / "research_queries.txt"
    with open(search_log, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {query}\n")
    return f"[PENDING] Query logged: {query}"


def format_research(idea, results):
    """Format research results into markdown."""
    lines = [
        f"# Research: {idea['Proiect']} ({idea['ID']})",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"## Description",
        idea["Ce_face"],
        "",
        "## Search Results",
    ]
    for r in results:
        lines.extend([
            f"### Query: {r['query']}",
            r["result"],
            "",
        ])
    if not results:
        lines.append("No results yet — run with web search enabled.")

    lines.extend([
        "",
        "## Competitors Found",
        "- [ ] To be filled after web search",
        "",
        "## Market Validation",
        "- [ ] Demand confirmed?",
        "- [ ] Price point validated?",
        "- [ ] Existing customers findable?",
    ])
    return "\n".join(lines)


# === MAIN ===
def main():
    import argparse
    p = argparse.ArgumentParser(description="Ideas Orchestrator")
    p.add_argument("--mode", default="full",
                   choices=["inspect", "dirs", "claude", "research", "full"])
    p.add_argument("--resume", action="store_true",
                   help="Resume from last state")
    args = p.parse_args()

    state = load_state() if args.resume else {"phase": "inspect", "processed": []}
    ideas = load_ideas()

    print(f"Ideas Orchestrator — {len(ideas)} ideas loaded")
    print(f"Mode: {args.mode} | Resume: {args.resume}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if args.mode in ("inspect", "full"):
        phase_inspect(ideas)

    if args.mode in ("dirs", "full"):
        phase_directories(ideas)

    if args.mode in ("claude", "full"):
        phase_claude_md(ideas)

    if args.mode in ("research", "full"):
        phase_research(ideas, state)

    save_state(state)
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
