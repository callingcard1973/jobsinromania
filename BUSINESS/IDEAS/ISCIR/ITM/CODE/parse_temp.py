"""
Parse mmuncii Reg_Nat_la_31012023.pdf → DATA/itm_temp.csv
The registry spans 389 pages; rows are split across pages.
Strategy: collect rows where col[0] is a number, col[1] has a name.
Columns: nr, denumire, sediu, cui, telefon, nr_autorizatie, data_prelungire, data_retragere
"""
import csv
import sys
import pdfplumber

PDF_PATH = "DATA/itm_temp_jan2023.pdf"
OUT_PATH = "DATA/itm_temp.csv"
HEADERS = ["nr", "denumire", "sediu", "cui", "telefon",
           "nr_autorizatie", "data_prelungire", "data_retragere"]


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
                    if not row or len(row) < 4:
                        continue
                    nr = clean(row[0])
                    if not nr.isdigit() or nr == "0":
                        continue
                    denumire = clean(row[1])
                    # Skip header-repeat rows (col 1 is '1', '2', etc.)
                    if denumire in ("1", "2", "Nr.", ""):
                        continue
                    sediu = clean(row[2])
                    # CUI is sometimes in col 3 or 4 (split across merged cells)
                    cui_a = clean(row[3]) if len(row) > 3 else ""
                    cui_b = clean(row[4]) if len(row) > 4 else ""
                    cui = cui_b if cui_b.isdigit() else (cui_a if cui_a.isdigit() else "")
                    telefon = clean(row[5]) if len(row) > 5 else ""
                    nr_auth = clean(row[6]) if len(row) > 6 else ""
                    data_prel = clean(row[7]) if len(row) > 7 else ""
                    data_retr = clean(row[8]) if len(row) > 8 else ""
                    if denumire:
                        rows.append({
                            "nr": nr,
                            "denumire": denumire,
                            "sediu": sediu,
                            "cui": cui,
                            "telefon": telefon,
                            "nr_autorizatie": nr_auth,
                            "data_prelungire": data_prel,
                            "data_retragere": data_retr,
                        })
    return rows


def main():
    rows = extract_rows(PDF_PATH)
    print(f"Extracted {len(rows)} temp agencies", file=sys.stderr)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved to {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
