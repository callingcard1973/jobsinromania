#!/usr/bin/env python3
"""Genereaza drafturi gated (cerere-de-oferta) ASCII catre furnizori. NU trimite."""

from pathlib import Path

DATA = Path(__file__).parent.parent / "DATA"
DRAFTS = DATA / "drafts"
SENDER = "office@cumparlegume.com"
SIG = f"\n\nCu stima,\nGospodarii de Altadata\n{SENDER}"


def build_draft(to_email, name, produse_text):
    return f"""TO: {to_email}
FROM: {SENDER}
SUBJECT: Cerere oferta materie prima legume-fructe (industrial)

Buna ziua, {name},

Cautam materie prima pentru procesare industriala (conserve) si avem cumparatori
fermi pentru:

{produse_text}

Va rugam sa ne transmiteti:
- pret RON/kg
- calitate / calibru disponibil
- tonaj disponibil si perioada de livrare
- termeni livrare si plata

Multumim.{SIG}
"""


def write_draft(slug, to_email, name, produse_text):
    DRAFTS.mkdir(parents=True, exist_ok=True)
    body = build_draft(to_email, name, produse_text)
    path = DRAFTS / f"DRAFT_cerere_{slug}.txt"
    path.write_text(body.encode("ascii", "ignore").decode("ascii"), encoding="ascii")
    return path


# cerere clara -> furnizor candidat (editeaza aici pe masura ce apar cereri noi)
DRAFTURI = [
    ("VISINE_partenope", "office@partenopefrutta.ro", "Partenope Frutta",
     "- VISINE 100 tone, industrial, fructe sanatoase calibru 18-20mm, fara fermentatie"),
    ("ARDEI_VINETE_bioprod", "office@bioprodcolibasi.ro", "Coop Bioprod Colibasi",
     "- ARDEI KAPIA 100 tone, industrial\n- VINETE 60 tone, industrial"),
    ("ARDEI_VINETE_hortifruct", "office@hortifruct.ro", "Hortifruct",
     "- ARDEI KAPIA 100 tone, industrial\n- VINETE 60 tone, industrial"),
    ("ARDEI_VINETE_roua", "office@rouacoop.ro", "Coop Roua",
     "- ARDEI KAPIA 100 tone, industrial\n- VINETE 60 tone, industrial"),
]


def main():
    for d in DRAFTURI:
        print("OK", write_draft(*d))


if __name__ == "__main__":
    main()
