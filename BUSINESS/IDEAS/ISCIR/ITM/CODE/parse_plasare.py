"""
Parse ITM lista_ag_SITE_ian_2025.pdf → DATA/itm_plasare.csv
Columns: itm, denumire, data_inregistrare, cui, adresa, judet
"""
import csv
import re
import sys
import pdfplumber

PDF_PATH = "DATA/itm_plasare_ian2025.pdf"
OUT_PATH = "DATA/itm_plasare.csv"
HEADERS = ["itm", "denumire", "data_inregistrare", "cui", "adresa", "judet"]


def clean(s):
    if not s:
        return ""
    return " ".join(str(s).split())


def extract_rows(pdf_path):
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or not row[0]:
                        continue
                    idx = clean(row[0])
                    if not idx.isdigit():
                        continue
                    # cols: idx, itm, denumire, data_reg, cui, adresa, judet, punct_lucru, judet_pl
                    itm = clean(row[1]) if len(row) > 1 else ""
                    denumire = clean(row[2]) if len(row) > 2 else ""
                    data_reg = clean(row[3]) if len(row) > 3 else ""
                    cui = clean(row[4]) if len(row) > 4 else ""
                    adresa = clean(row[5]) if len(row) > 5 else ""
                    judet = clean(row[6]) if len(row) > 6 else ""
                    if denumire:
                        rows.append({
                            "itm": itm,
                            "denumire": denumire,
                            "data_inregistrare": data_reg,
                            "cui": cui,
                            "adresa": adresa,
                            "judet": judet,
                        })
    return rows


def main():
    rows = extract_rows(PDF_PATH)
    print(f"Extracted {len(rows)} plasare agencies", file=sys.stderr)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved to {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
