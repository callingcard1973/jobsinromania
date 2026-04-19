"""
SEAP Full Bid Package — Analysis + LM Studio proposal draft
Usage: python bid_package.py --cpv 45233140 --title "Lucrari asfaltare" --buyer "CJ Ilfov" --value 2000000
Output: bid_package_{cpv}.md + bid_package_{cpv}.pdf
"""
import argparse, sys, json, urllib.request, re
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from bid_report import report as get_data, fmt_ron

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"


def call_lm(prompt, max_tokens=1500):
    payload = json.dumps({
        "model": "local-model",
        "messages": [
            {"role": "system", "content": "You are an expert Romanian public procurement consultant. Write professional, winning bid proposals in Romanian."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode()
    try:
        req = urllib.request.Request(LM_STUDIO_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        r = urllib.request.urlopen(req, timeout=120)
        resp = json.loads(r.read())
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LM Studio error: {e}]"


def build_package(args):
    import argparse as _a
    data_args = _a.Namespace(cpv=args.cpv, company="", buyer="", year="", top=10)

    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        data = get_data(data_args)

    if not data:
        print("❌ No SEAP data for this CPV.")
        return

    contracts = data["contracts"]
    winners = data["winners"]
    top_buyers = data["top_buyers"]

    # Build context for LM Studio
    winner_summary = "\n".join([
        f"  {i+1}. {name} — {d['contracts']} contracte, {fmt_ron(d['total'])}"
        for i, (name, d) in enumerate(winners[:5])
    ])
    buyer_summary = "\n".join([f"  - {b} ({cnt} contracte)" for b, cnt in top_buyers[:5]])

    prompt = f"""Ești un consultant expert în achiziții publice România.

Context piață (date reale SEAP 2023-2025):
- CPV: {args.cpv}
- Titlu licitație: {args.title}
- Autoritate contractantă: {args.buyer}
- Valoare estimată: {fmt_ron(float(args.value))}
- Total contracte similare în piață: {len(contracts)}
- Valoare mediană contract: {fmt_ron(data['median'])}

Top câștigători actuali pe acest CPV:
{winner_summary}

Top cumpărători activi:
{buyer_summary}

Generează o propunere tehnică și financiară profesională pentru această licitație, incluzând:
1. Scrisoare de intenție (150 cuvinte)
2. Metodologie de execuție (300 cuvinte)
3. Justificare preț (cu referință la mediana pieței {fmt_ron(data['median'])})
4. Avantaje competitive față de concurență
5. Plan de implementare (3 faze)
6. Garanții și riscuri asumate

Scrie profesional, în română, ca pentru o firmă serioasă cu experiență."""

    print("\n🤖 Generating bid proposal with LM Studio...")
    proposal = call_lm(prompt)

    # Build markdown package
    md = f"""# SEAP BID PACKAGE — {args.title}
**Generated:** {date.today().strftime('%d %B %Y')}
**CPV:** {args.cpv} | **Buyer:** {args.buyer} | **Value:** {fmt_ron(float(args.value))}

---

## 1. MARKET INTELLIGENCE

| Metric | Value |
|--------|-------|
| Total contracts (CPV) | {len(contracts):,} |
| Market total value | {fmt_ron(data['market_total'])} |
| Median contract | {fmt_ron(data['median'])} |
| Average contract | {fmt_ron(data['avg'])} |
| Unique winners | {len(set(c['winner'] for c in contracts)):,} |

### Top 5 Competitors
{chr(10).join(f"{i+1}. **{name}** — {d['contracts']} contracts, {fmt_ron(d['total'])}" for i, (name, d) in enumerate(winners[:5]))}

### Top Buyers
{chr(10).join(f"- {b} ({cnt} contracts)" for b, cnt in top_buyers[:5])}

---

## 2. STRATEGY

"""
    # Add concentration insight
    concentration = sum(d["total"] for _, d in winners[:3]) / data["market_total"] * 100 if data["market_total"] else 0
    top_name, top_d = winners[0] if winners else ("N/A", {"total": 0})
    top_pct = top_d["total"] / data["market_total"] * 100 if data["market_total"] else 0
    md += f"- Top 3 winners control **{concentration:.0f}%** of market\n"
    md += f"- Market leader: **{top_name}** ({top_pct:.0f}%)\n"
    md += f"- **Recommended bid price:** {fmt_ron(data['median'] * 0.92)} — {fmt_ron(data['median'] * 1.05)}\n"

    md += f"""
---

## 3. PROPOSED BID DOCUMENT

{proposal}

---

## 4. PRICING RECOMMENDATION

| Scenario | Price | Probability |
|----------|-------|-------------|
| Aggressive (win-focused) | {fmt_ron(data['median'] * 0.88)} | High |
| Balanced | {fmt_ron(data['median'] * 0.95)} | Medium-High |
| Profitable | {fmt_ron(data['median'] * 1.02)} | Medium |
| Maximum | {fmt_ron(data['median'] * 1.10)} | Low |

---
*Source: SEAP Romania 2023-2025 · InterJob Intelligence · interjob.ro*
"""

    slug = args.cpv.replace("-", "") or "report"
    out_md = Path(__file__).parent / f"bid_package_{slug}.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"✅ Markdown: {out_md}")

    # Try PDF too
    try:
        sys.argv = ["bid_pdf.py", "--cpv", args.cpv, "--out", str(out_md.with_suffix(".pdf"))]
        from bid_pdf import build_pdf
        build_pdf(argparse.Namespace(cpv=args.cpv, company="", buyer="", year="", out=str(out_md.with_suffix(".pdf"))))
    except Exception as e:
        print(f"PDF skipped: {e}")

    return out_md


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cpv",   required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--buyer", required=True)
    p.add_argument("--value", required=True, type=float)
    args = p.parse_args()
    build_package(args)
