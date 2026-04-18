#!/usr/bin/env python3
"""Save research findings to country HANDOFF files."""
import os, glob

base = "D:/MEMORY/BERD EBRD"
tasks_dir = r"C:\Users\apami\AppData\Local\Temp\claude\D--MEMORY-EMAIL\b355909d-c61e-45a8-8665-bcc47451a4b7\tasks"

# Map agent IDs to countries
agents = {
    "a3d3807149b18133a": "Ukraine",
    "af64a0ae73b1816dd": "Poland",
    "a1d339427a5a6c874": "Serbia",
    "a8c90b9c07775d4ac": "Greece",
    "ab56af6231d4c719c": ["Georgia", "Croatia", "Montenegro"],
    "a546c6710c427b952": ["Kazakhstan", "Egypt", "Morocco"],
    "a895ae7bd925f291b": ["Uzbekistan", "Kyrgyz_Republic", "Tajikistan"],
    "a0c2560244de983b7": ["Albania", "Kosovo", "North_Macedonia", "Bosnia_and_Herzegovina", "Hungary", "Lithuania", "Latvia", "Estonia", "Slovenia", "Slovak_Republic"],
}

for agent_id, countries in agents.items():
    output_file = os.path.join(tasks_dir, f"{agent_id}.output")
    if not os.path.exists(output_file):
        print(f"SKIP {agent_id}: no output file")
        continue

    content = open(output_file, encoding="utf-8", errors="replace").read()

    if isinstance(countries, str):
        countries = [countries]

    for country in countries:
        safe = country.replace(" ", "_")
        country_dir = os.path.join(base, safe)
        os.makedirs(country_dir, exist_ok=True)

        research_file = os.path.join(country_dir, "RESEARCH.md")
        with open(research_file, "w", encoding="utf-8") as f:
            f.write(f"# EBRD {country} — Research Notes\n")
            f.write(f"Source: Agent research, 9 April 2026\n\n")
            f.write(content)

        print(f"  Saved: {country}/RESEARCH.md ({len(content)} chars)")

print("\nDone")
