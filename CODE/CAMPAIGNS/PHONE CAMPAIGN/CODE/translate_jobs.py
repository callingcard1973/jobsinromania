#!/usr/bin/env python3
"""
Translate all Romanian ANOFM job titles to English using Ollama qwen3-4b.
Runs on raspibig. Output: job_translations.py (importable dict)
"""
import csv, json, subprocess, sys, time, os

INPUT = "/opt/ACTIVE/PHONE_CAMPAIGN/anofm_phones_20260416.csv"
OUTPUT = "/opt/ACTIVE/PHONE_CAMPAIGN/job_translations.json"
BATCH = 30   # titles per LLM call
MODEL = "qwen3-4b"

# Known good translations (skip LLM for these)
KNOWN = {
    "LUCRATOR COMERCIAL": "Sales & Retail Worker",
    "AJUTOR BUCATAR": "Kitchen Assistant",
    "MANIPULANT MARFURI": "Goods Handler",
    "FEMEIE DE SERVICIU": "Cleaning Operative",
    "Conducător auto transport rutier de mărfuri": "Freight Truck Driver",
    "MUNCITOR NECALIFICAT LA ASAMBLAREA, MONTAREA PIESELOR": "Assembly Line Worker",
    "SOFER DE AUTOTURISME SI CAMIONETE": "Car & Van Driver",
    "LUCRATOR BUCATARIE": "Kitchen Worker",
    "VÂNZATOR": "Sales Assistant",
    "AGENT DE SECURITATE": "Security Guard",
    "SUDOR": "Welder",
    "BUCATAR": "Cook / Chef",
    "AGENT DE VÂNZARI": "Sales Agent",
    "CURIER": "Courier / Delivery Driver",
    "MECANIC AUTO": "Auto Mechanic",
    "OSPATAR": "Waiter / Waitress",
    "AMBALATOR MANUAL": "Manual Packer",
    "LACATUS MECANIC": "Mechanical Fitter",
    "MUNCITOR NECALIFICAT ÎN INDUSTRIA CONFECTIILOR": "Garment Industry Worker",
    "UCENIC": "Apprentice",
    "MASINIST LA MASINI PENTRU TERASAMENTE": "Earthmoving Machine Operator",
    "LUCRATOR GESTIONAR": "Stock Controller",
    "OPERATOR INTRODUCERE, VALIDARE SI PRELUCRARE DATE": "Data Entry Operator",
    "OPERATOR LA MASINI-UNELTE CU COMANDA NUMERICA": "CNC Machine Operator",
    "AJUTOR OSPATAR": "Waiter Assistant",
    "ÎNGRIJITOR CLADIRI": "Building Caretaker",
    "CAMERISTA HOTEL": "Hotel Chambermaid",
    "ELECTRICIAN ÎN CONSTRUCTII": "Construction Electrician",
    "MUNCITOR NECALIFICAT ÎN AGRICULTURA": "Agricultural Labourer",
    "ASISTENT MEDICAL GENERALIST": "General Nurse",
    "ASISTENT MANAGER": "Executive Assistant",
    "AGENT CURATENIE CLADIRI SI MIJLOACE DE TRANSPORT": "Cleaning Agent",
    "DULGHER": "Carpenter",
    "ZIDAR ROSAR-TENCUITOR": "Bricklayer & Plasterer",
    "FIERAR BETONIST": "Reinforced Concrete Worker",
    "ÎNGRIJITOR ANIMALE": "Animal Care Worker",
    "CONTABIL": "Accountant",
    "TÂMPLAR UNIVERSAL": "Joiner / Woodworker",
    "BRUTAR": "Baker",
    "BARMAN": "Bartender",
    "ELECTRICIAN DE ÎNTRETINERE SI REPARATII": "Maintenance Electrician",
    "ZUGRAV": "Painter & Decorator",
    "INSTALATOR INSTALATII TEHNICO-SANITARE SI DE GAZE": "Plumber & Gas Fitter",
    "GESTIONAR DEPOZIT": "Warehouse Keeper",
    "STIVUITORIST": "Forklift Operator",
    "MENAJERA": "Housekeeper",
    "CONFECTIONER-ASAMBLOR ARTICOLE DIN TEXTILE": "Textile Assembly Worker",
    "CASIER": "Cashier",
    "MECANIC UTILAJ": "Equipment Mechanic",
    "PATISER": "Pastry Chef",
    "SPALATOR VEHICULE": "Car Wash Operative",
    "INGINER CONSTRUCTII CIVILE, INDUSTRIALE SI AGRICOLE": "Civil Construction Engineer",
    "INGINER MECANIC": "Mechanical Engineer",
    "Conducator auto transport rutier de persoane": "Passenger Bus Driver",
    "MUNCITOR NECALIFICAT ÎN SILVICULTURA": "Forestry Labourer",
    "LACATUS CONSTRUCTII METALICE SI NAVALE": "Steel & Naval Fitter",
    "SUDOR CU ARC ELECTRIC ACOPERIT SUB STRAT DE FLUX": "Submerged Arc Welder",
    "TUBULATOR NAVAL": "Naval Pipefitter",
    "LACATUS-MONTATOR AGREGATE ENERGETICE SI DE TRANSPORT": "Power & Transport Fitter",
    "LACATUS MECANIC DE ÎNTRETINERE SI REPARATII UNIVERSALE": "Universal Maintenance Fitter",
    "MUNCITOR NECALIFICAT LA DEMOLAREA CLADIRILOR, CAPTUSELI ZIDARIE, PLACI MOZAIC, FAIANTA, GRESIE, PARCHET": "General Construction Labourer",
    "MUNCITOR NECALIFICAT LA SPARGEREA SI TAIEREA MATERIALELOR DE CONSTRUCTII": "Construction Labourer",
    "MUNCITOR NECALIFICAT LA ÎNTRETINEREA DE DRUMURI, SOSELE, PODURI, BARAJE": "Road Maintenance Worker",
    "MUNCITOR NECALIFICAT LA AMBALAREA PRODUSELOR SOLIDE SI SEMISOLIDE": "Packaging Worker",
    "VÂNZĂRI": "Sales",
    "INGINER CONSTRUCTII CIVILE": "Civil Engineer",
}


def collect_titles():
    titles = set()
    with open(INPUT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for j in row["jobs"].split(" | "):
                t = j.split("(")[0].strip()
                if t:
                    titles.add(t)
    return sorted(titles)


def translate_batch(batch: list) -> dict:
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(batch))
    prompt = f"""Translate these Romanian job titles to English.
Return ONLY a JSON object mapping each number to the English translation.
Be concise and professional. Use standard English job title conventions.

{numbered}

Return JSON only, no explanation:"""

    result = subprocess.run(
        ["ollama", "run", MODEL, "--nowordwrap"],
        input=prompt, capture_output=True, text=True, timeout=120
    )
    raw = result.stdout.strip()

    # Extract JSON from response
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {}

    try:
        data = json.loads(raw[start:end])
        return {batch[int(k)-1]: v for k, v in data.items() if k.isdigit() and int(k)-1 < len(batch)}
    except Exception:
        return {}


def main():
    # Load existing translations if resuming
    existing = dict(KNOWN)
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            existing.update(json.load(f))

    all_titles = collect_titles()
    todo = [t for t in all_titles if t not in existing]
    print(f"Total titles: {len(all_titles)} | Already done: {len(existing)} | To translate: {len(todo)}")

    translated = dict(existing)
    errors = 0

    for i in range(0, len(todo), BATCH):
        batch = todo[i:i+BATCH]
        print(f"Batch {i//BATCH + 1}/{(len(todo)+BATCH-1)//BATCH} ({len(batch)} titles)...", end=" ", flush=True)

        result = translate_batch(batch)
        if result:
            translated.update(result)
            print(f"✓ {len(result)}")
        else:
            errors += 1
            print(f"✗ failed (will use fallback)")
            # fallback: title-case the Romanian
            for t in batch:
                translated[t] = t.title()

        # Save after each batch (resume-safe)
        with open(OUTPUT, "w") as f:
            json.dump(translated, f, ensure_ascii=False, indent=2)

        time.sleep(1)  # brief pause between calls

    print(f"\nDone. {len(translated)} titles. Errors: {errors}")
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
