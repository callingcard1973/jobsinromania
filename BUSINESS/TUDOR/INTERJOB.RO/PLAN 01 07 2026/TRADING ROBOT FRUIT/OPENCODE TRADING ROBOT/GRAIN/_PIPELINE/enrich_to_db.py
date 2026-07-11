#!/usr/bin/env python3
"""Pipeline enrich: citeste enriched_final.csv + toate sursele _ENRICH/, 
merge dupa CUI, scrie in grain.db (CAEN 4621/0111) si VegFru.db (CAEN 4631/0113).

Coloane tinta: 50 (model trading_partners_50columns.csv).

Usage:
  python GRAIN/_PIPELINE/enrich_to_db.py
  python GRAIN/_PIPELINE/enrich_to_db.py --quick   # doar GMP+ si DSVSA
"""
import csv, json, os, re, sqlite3, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(BASE, "DATA")
ENRICH = os.path.join(DATA, "_ENRICH")
BASE_CSV = os.path.join(DATA, "enriched_final.csv")
GRAIN_DB = os.path.join(DATA, "grain.db")
VEGFRU_DB = os.path.join(DATA, "VegFru.db")

DEBUG = "--debug" in sys.argv
QUICK = "--quick" in sys.argv


def log(msg):
    print("  %s" % msg)


# --- Incarcare surse enrich ---

def load_csv(path, key_col="cui", alt_key=None):
    """Load CSV by key_col, return dict key->row. alt_key = fallback column."""
    if not os.path.exists(path):
        log("  (nu exista: %s)" % os.path.basename(path))
        return {}
    out = {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            k = (r.get(key_col) or "").strip()
            if not k and alt_key:
                k = (r.get(alt_key) or "").strip()
            if k:
                out[k] = r
    return out


def load_master_csv(path):
    """Load CUMPARATORI_MASTER.csv (keyed on cui)."""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            k = (r.get("cui") or "").strip()
            if k:
                out[k] = r
    return out


def norm_name(n):
    n = (n or "").upper().strip()
    n = re.sub(r"\b(S\.?R\.?L\.?|S\.?A\.?|SRL|SA|S\.C\.|SC)\b\.?", "", n)
    return re.sub(r"[^A-Z0-9 ]", "", n).strip()


def match_by_name(rows, name_key, target, target_name_key="firma"):
    """Fallback match by normalized name for rows without CUI."""
    name_map = {}
    for k, v in target.items():
        nm = norm_name(v.get(target_name_key, ""))
        if nm:
            name_map[nm] = k
    matched = 0
    for r in rows:
        if r.get("cui") and r["cui"] in target:
            continue
        nm = norm_name(r.get(name_key, ""))
        if nm in name_map:
            r["cui"] = name_map[nm]
            matched += 1
    return matched


# --- Constructie rand 50 coloane ---

def build_partner_row(base_row, master_row, enrich_sources):
    """Merge base + master + enrichment into one 50-col dict."""
    row = {}

    # Identitate
    row["firma_cui"] = (base_row.get("cui") or master_row.get("cui") or "").strip()
    row["firma_nume"] = base_row.get("name") or master_row.get("firma") or ""

    # Locatie
    row["judet"] = base_row.get("county") or master_row.get("judet") or ""
    row["oras"] = base_row.get("city") or master_row.get("oras") or ""
    row["localitate"] = master_row.get("localitate") or ""
    row["adresa"] = base_row.get("address") or master_row.get("adresa") or ""
    row["cod_postal"] = master_row.get("cod_postal") or ""
    row["tara"] = "RO"

    # Contact
    row["telefon_fix"] = master_row.get("telefon") or base_row.get("phone") or ""
    row["telefon_mobil"] = ""
    row["whatsapp"] = ""
    row["email_principal"] = base_row.get("email") or master_row.get("email") or ""
    row["email_alternativ"] = ""

    # Business
    row["caen_principal"] = base_row.get("caen") or master_row.get("caen") or ""
    row["caen_secundare"] = master_row.get("caen_secundar") or ""
    row["tip_firma"] = master_row.get("tip_firma") or ""
    row["inregistrare_firma"] = master_row.get("inregistrare") or ""
    row["capital_social"] = master_row.get("capital_social") or ""
    row["cifra_afaceri"] = master_row.get("cifra_afaceri") or ""
    row["numar_angajati"] = master_row.get("numar_angajati") or ""

    # Trading type
    cui = row["firma_cui"]
    caen = row["caen_principal"]
    if caen in ("4621", "4631"):
        row["tip_trader"] = "Buyer"
    elif caen in ("0111", "0113"):
        row["tip_trader"] = "Seller"
    else:
        row["tip_trader"] = "Unknown"
    row["tip_produs"] = "Cereal" if caen == "4621" else "LegumeFructe" if caen in ("4631", "0113") else "Mix"
    row["segment"] = master_row.get("marime") or ""
    if caen == "4621":
        row["produse_principale"] = "grau/porumb/orz/fl-soarelui/rapita"
    elif caen in ("4631", "0113"):
        row["produse_principale"] = "legume/fructe"

    # Enrichment: GMP+
    gmp = enrich_sources.get("gmp", {}).get(cui)
    if gmp:
        row["certificari_gmp"] = gmp.get("scop_certificare", "")
        row["certificari_iasc"] = ""
    else:
        row["certificari_gmp"] = ""
        row["certificari_iasc"] = ""

    # Enrichment: DSVSA
    dsvsa = enrich_sources.get("dsvsa", {}).get(cui)
    if dsvsa:
        row["depozit_licentiat"] = dsvsa.get("tip_autorizatie") or "DA"
        row["tip_depozit"] = dsvsa.get("adresa_unitate") or ""
    else:
        row["depozit_licentiat"] = ""
        row["tip_depozit"] = ""

    # Enrichment: BRM
    brm = enrich_sources.get("brm", {}).get(cui)
    row["calitate_certificata"] = "BRM" if brm else ""

    # Enrichment: insolventa
    ins = enrich_sources.get("insolventa", {}).get(cui)
    row["insolventa"] = "DA" if ins else ""

    # Enrichment: licitatii SEAP
    lic = enrich_sources.get("licitatii", {}).get(cui)
    row["valoare_contracte"] = (lic.get("valoare") if lic else master_row.get("valoare") or "")

    # Enrichment: MFinante
    mf = enrich_sources.get("mfinante", {}).get(cui)
    if mf:
        row["rating_financiar"] = mf.get("stare") or ""
        row["platitor_tva"] = mf.get("platitor_tva") or ""
    else:
        row["rating_financiar"] = ""
        row["platitor_tva"] = ""

    # Capacitati (MADR)
    madr = enrich_sources.get("madr_spatii", {}).get(cui)
    if madr:
        row["capacitate_stocare"] = madr.get("capacitate", "")
    else:
        row["capacitate_stocare"] = ""

    # APIA
    apia = enrich_sources.get("apia", {}).get(cui)
    if apia:
        row["suprafata_agricola"] = apia.get("suprafata", "")
        row["valoare_contracte"] = apia.get("valoare", row.get("valoare_contracte", ""))

    # Defaults
    row["suprafata_irie"] = ""
    row["suprafata_ecologica"] = ""
    row["capacitate_productie"] = ""
    row["produse_secundare"] = ""
    row["capacitate_consum"] = ""
    row["umiditate_max"] = ""
    row["proteina_min"] = ""
    row["test_weight_min"] = ""
    row["admixture_max"] = ""
    row["data_prima_interactiune"] = ""
    row["numar_dealuri_inchise"] = ""
    row["valoare_dealuri"] = ""
    row["rating_reliability"] = ""
    row["piata_principala"] = "national"
    row["geo_target"] = "national"
    row["sursa"] = base_row.get("source", "")
    row["ultima_actualizare"] = time.strftime("%Y-%m-%d")

    return row


FIELDS_50 = [
    "firma_cui", "firma_nume", "judet", "oras", "localitate", "adresa", "cod_postal", "tara",
    "telefon_fix", "telefon_mobil", "whatsapp", "email_principal", "email_alternativ",
    "caen_principal", "caen_secundare", "tip_firma", "inregistrare_firma",
    "capital_social", "cifra_afaceri", "numar_angajati",
    "tip_trader", "tip_produs", "segment",
    "suprafata_agricola", "suprafata_irie", "suprafata_ecologica", "capacitate_productie",
    "produse_principale", "produse_secundare",
    "capacitate_consum", "capacitate_stocare",
    "depozit_licentiat", "tip_depozit",
    "certificari_gmp", "certificari_iasc",
    "umiditate_max", "proteina_min", "test_weight_min", "admixture_max",
    "calitate_certificata",
    "platitor_tva", "rating_financiar",
    "valoare_contracte", "insolventa",
    "data_prima_interactiune", "numar_dealuri_inchise", "valoare_dealuri", "rating_reliability",
    "piata_principala", "geo_target",
    "sursa", "ultima_actualizare",
]


def insert_rows(con, rows):
    cur = con.cursor()
    placeholders = ",".join(["?" for _ in FIELDS_50])
    cols = ",".join(FIELDS_50)
    sql = f"INSERT OR REPLACE INTO trading_partners ({cols}) VALUES ({placeholders})"
    vals = [[r.get(c, "") for c in FIELDS_50] for r in rows]
    cur.executemany(sql, vals)
    con.commit()
    return len(rows)


def main():
    t0 = time.time()
    print("=== Pipeline Enrich -> 50 coloane ===")

    # 1. Incarca enriched_final.csv
    base = []
    with open(BASE_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            base.append(r)
    print("  Base enriched_final.csv: %d randuri" % len(base))

    # 2. Incarca master
    master_path = os.path.join(ENRICH, "CUMPARATORI_MASTER.csv")
    master = load_master_csv(master_path)
    print("  Master CUMPARATORI_MASTER: %d CUI" % len(master))

    # 3. Incarca sursele de enrich (CUI-keyed)
    sources = {}
    source_files = {
        "gmp": "enrich_certificari.csv",
        "dsvsa": "enrich_dsvsa.csv",
        "brm": "enrich_brm_membri.csv",
        "insolventa": "enrich_insolventa.csv",
        "licitatii": "enrich_licitatii.csv",
        "mfinante": "enrich_mfinante.csv",
        "madr_spatii": "enrich_madr_spatii.csv",
        "madr_depozite": "enrich_madr_depozite.csv",
        "apia": "enrich_apia.csv",
        "afir": "enrich_afir.csv",
        "firme_noi": "enrich_firme_noi.csv",
        "gmaps": "enrich_gmaps.csv",
        "email_web": "enrich_email_web.csv",
    }
    for key, fname in source_files.items():
        fpath = os.path.join(ENRICH, fname)
        alt = "cui_master" if key == "gmp" else ("cui" if key == "brm" else None)
        sources[key] = load_csv(fpath, alt_key=alt)
        cnt = len(sources[key])
        if cnt:
            log("  %s: %d CUI" % (fname, cnt))

    # 4. Fallback match by name for GMP+ rows without CUI
    gmp_matched = match_by_name(base, "name", sources["gmp"], "firma")
    if gmp_matched:
        log("  Name-matched GMP+ -> CUI: %d" % gmp_matched)

    # 5. Construieste randuri 50 coloane pentru fiecare firma de baza
    rows_50 = []
    caen_grain = {"4621", "0111"}
    caen_veg = {"4631", "0113"}

    grain_rows = []
    veg_rows = []

    for br in base:
        cui = (br.get("cui") or "").strip()
        mr = master.get(cui, {})
        row = build_partner_row(br, mr, sources)
        rows_50.append(row)

        caen = row["caen_principal"]
        if caen in caen_grain:
            grain_rows.append(row)
        elif caen in caen_veg:
            veg_rows.append(row)
        # else: skip (other CAEN)

    print("\n  Randuri 50 coloane construite: %d" % len(rows_50))
    print("    Grain (CAEN 4621/0111): %d" % len(grain_rows))
    print("    VegFru (CAEN 4631/0113): %d" % len(veg_rows))

    # 6. Scrie in SQLite
    con_g = sqlite3.connect(GRAIN_DB)
    con_v = sqlite3.connect(VEGFRU_DB)
    n_g = insert_rows(con_g, grain_rows)
    n_v = insert_rows(con_v, veg_rows)
    con_g.close()
    con_v.close()
    print("\n  Scris in grain.db: %d parteneri" % n_g)
    print("  Scris in VegFru.db: %d parteneri" % n_v)

    # 7. Optional: export CSV complet
    out_csv = os.path.join(DATA, "trading_partners_50cols.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS_50)
        w.writeheader()
        w.writerows(rows_50)
    print("  Export CSV: %s (%d randuri)" % (out_csv, len(rows_50)))

    elapsed = time.time() - t0
    print("\n  Durata: %.1fs" % elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
