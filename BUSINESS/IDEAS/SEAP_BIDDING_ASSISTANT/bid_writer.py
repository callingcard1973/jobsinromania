"""
bid_writer.py — CLI tool: generates a Romanian bid proposal using TED market data + LM Studio.
Usage: python bid_writer.py --title "..." --cpv 45000000 --buyer "Primaria X" --value 500000
"""
import argparse
import json
import os
import sys
from datetime import date

import requests

# Import analyzer from same directory
sys.path.insert(0, os.path.dirname(__file__))
from bid_analyzer import analyze_cpv, format_summary

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "local-model"
PROPOSALS_DIR = os.path.join(os.path.dirname(__file__), "proposals")

SYSTEM_PROMPT = """Esti un expert in achizitii publice din Romania cu 15 ani experienta.
Scrii oferte tehnice si financiare castigatoare pentru licitatii SEAP/eTender.
Stilul este profesional, concis, cu date concrete. Evita platitudini.
Scrie EXCLUSIV in limba romana."""

PROPOSAL_TEMPLATE = """Pe baza urmatoarelor informatii, scrie o oferta completa pentru licitatia descrisa.

## Date licitatie
- Titlu: {title}
- Cod CPV: {cpv_code}
- Autoritate contractanta: {buyer}
- Valoare estimata: {value_ron:,.0f} RON ({value_eur:,.0f} EUR)

## Analiza de piata (date reale din baza TED EU)
{market_summary}

## Cerinte oferta
Scrie o oferta structurata cu aceste sectiuni EXACTE (foloseste headere markdown ##):

## 1. Prezentare Firma
(Descriere fictiva dar credibila: firma romaneasca cu 10+ ani experienta, certificari ISO, personal calificat, referinte similare)

## 2. Experienta Relevanta
(Minim 3 contracte similare executate, cu valori in intervalul pietei: {value_min:,.0f} - {value_max:,.0f} EUR. Foloseste nume de autoritati contractante reale din Romania)

## 3. Propunere Tehnica
(Metodologie detaliata, personal propus cu CV-uri schematice, echipamente, grafic Gantt simplificat, masuri calitate si mediu)

## 4. Propunere Financiara
(Defalcare costuri: manopera, materiale, subcontractori, profit. Valoare totala: {value_ron:,.0f} RON + TVA. Justifica de ce esti cu {discount}% sub media pietei de {avg_eur:,.0f} EUR)

## 5. Termeni si Conditii
(Garantie de buna executie 10%, garantie lucrari 36 luni, asigurari, penalitati acceptate conform legislatie RO)

## 6. Documente Anexate
(Lista documente: CUI, statut, bilant, ISO, CV-uri, referinte)

Oferta trebuie sa fie CASTIGATOARE: pret competitiv, tehnic solid, experienta relevanta."""


def call_lm_studio(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
    }
    try:
        resp = requests.post(LM_STUDIO_URL, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "EROARE: LM Studio nu este pornit. Porneste LM Studio pe portul 1234."
    except Exception as e:
        return f"EROARE LLM: {e}"


def write_proposal(title: str, cpv_code: str, buyer: str, value_ron: float,
                   keyword: str = None) -> str:
    print(f"[1/3] Analizez piata pentru CPV {cpv_code}...")
    market = analyze_cpv(cpv_code=cpv_code, keyword=keyword)

    if "error" in market:
        print(f"  Avertisment: {market['error']} — continui fara date de piata")
        market_summary = "Date de piata indisponibile pentru acest CPV."
        avg_eur = value_ron / 5.0
        value_min = avg_eur * 0.5
        value_max = avg_eur * 2.0
    else:
        market_summary = format_summary(market)
        avg_eur = market["stats"].get("avg_value") or (value_ron / 5.0)
        value_min = market["stats"].get("min_value") or avg_eur * 0.3
        value_max = market["stats"].get("max_value") or avg_eur * 3.0

    value_eur = value_ron / 5.0
    discount = max(3, min(15, round((avg_eur - value_eur) / avg_eur * 100, 1))) if avg_eur > 0 else 8

    print("[2/3] Generez oferta cu LM Studio...")
    prompt = PROPOSAL_TEMPLATE.format(
        title=title,
        cpv_code=cpv_code,
        buyer=buyer,
        value_ron=value_ron,
        value_eur=value_eur,
        market_summary=market_summary,
        value_min=value_min,
        value_max=value_max,
        avg_eur=avg_eur,
        discount=discount,
    )

    proposal_text = call_lm_studio(prompt)

    # Save to file
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    safe_cpv = (cpv_code or "general").replace("/", "-")
    filename = f"{safe_cpv}_{date.today().isoformat()}.txt"
    filepath = os.path.join(PROPOSALS_DIR, filename)

    header = f"""OFERTA TEHNICA SI FINANCIARA
{'='*60}
Titlu licitatie: {title}
CPV: {cpv_code}
Autoritate contractanta: {buyer}
Valoare ofertata: {value_ron:,.0f} RON + TVA
Data generare: {date.today().isoformat()}
{'='*60}

"""
    full_text = header + proposal_text

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"[3/3] Oferta salvata: {filepath}")
    return full_text


def main():
    parser = argparse.ArgumentParser(description="Generator oferte licitatie SEAP")
    parser.add_argument("--title", required=True, help="Titlul contractului")
    parser.add_argument("--cpv", required=True, help="Cod CPV (ex: 45000000)")
    parser.add_argument("--buyer", required=True, help="Autoritatea contractanta")
    parser.add_argument("--value", required=True, type=float, help="Valoare estimata in RON")
    parser.add_argument("--keyword", help="Cuvant cheie alternativ pentru match CPV")
    parser.add_argument("--print", action="store_true", dest="print_output",
                        help="Afiseaza oferta in terminal")
    args = parser.parse_args()

    result = write_proposal(
        title=args.title,
        cpv_code=args.cpv,
        buyer=args.buyer,
        value_ron=args.value,
        keyword=args.keyword,
    )

    if args.print_output:
        print("\n" + "="*60)
        print(result)


if __name__ == "__main__":
    main()
