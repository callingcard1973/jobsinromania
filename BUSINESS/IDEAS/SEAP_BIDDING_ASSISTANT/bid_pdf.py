"""
SEAP Bid Intelligence PDF Report — sellable €200-500/report
Usage: python bid_pdf.py --cpv 45233 --out report.pdf
Requires: pip install reportlab
"""
import argparse, sys
from pathlib import Path
from datetime import date

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
except ImportError:
    print("Install: pip install reportlab")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from bid_report import report as get_data, load_contracts, fmt_ron

BLUE   = HexColor("#0073aa")
DARK   = HexColor("#1a1a2e")
LIGHT  = HexColor("#f0f4f8")
ACCENT = HexColor("#e74c3c")
GREEN  = HexColor("#27ae60")


def build_pdf(args):
    import argparse as _a
    data_args = _a.Namespace(cpv=args.cpv, company=args.company or "", buyer=args.buyer or "", year=args.year or "", top=20)

    # Suppress stdout from report()
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        data = get_data(data_args)

    if not data:
        print("No data found.")
        return

    out_path = args.out or f"seap_report_{args.cpv or args.company}.pdf"
    doc = SimpleDocTemplate(out_path, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    title_style  = ParagraphStyle("Title",  fontSize=22, textColor=white,    spaceAfter=4,  alignment=TA_CENTER, fontName="Helvetica-Bold")
    h1_style     = ParagraphStyle("H1",     fontSize=14, textColor=BLUE,     spaceAfter=6,  spaceBefore=16, fontName="Helvetica-Bold")
    h2_style     = ParagraphStyle("H2",     fontSize=11, textColor=DARK,     spaceAfter=4,  spaceBefore=10, fontName="Helvetica-Bold")
    body_style   = ParagraphStyle("Body",   fontSize=9,  textColor=DARK,     spaceAfter=3,  leading=14)
    caption_style= ParagraphStyle("Caption",fontSize=8,  textColor=HexColor("#888888"), spaceAfter=8, alignment=TA_CENTER)
    insight_style= ParagraphStyle("Insight",fontSize=10, textColor=DARK,     spaceAfter=4,  leading=15, leftIndent=10, borderPad=8, backColor=LIGHT)

    story = []

    # Cover header
    header_data = [[Paragraph(f"SEAP BID INTELLIGENCE REPORT", title_style)]]
    header_table = Table(header_data, colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("ROWPADDING", (0,0), (-1,-1), 16),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*cm))

    filters = []
    if args.cpv:     filters.append(f"CPV: {args.cpv}")
    if args.company: filters.append(f"Company: {args.company}")
    if args.buyer:   filters.append(f"Buyer: {args.buyer}")
    if args.year:    filters.append(f"Year: {args.year}")
    story.append(Paragraph(" | ".join(filters), caption_style))
    story.append(Paragraph(f"Generated: {date.today().strftime('%d %B %Y')} · Source: SEAP Romania 2023-2025 · InterJob Intelligence", caption_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.4*cm))

    # Market overview
    story.append(Paragraph("1. MARKET OVERVIEW", h1_style))
    contracts = data["contracts"]
    all_vals = [c["value_ron"] for c in contracts if c["value_ron"] > 0]
    overview = [
        ["Metric", "Value"],
        ["Total contracts analysed", f"{len(contracts):,}"],
        ["Total market value", fmt_ron(data["market_total"])],
        ["Unique winners", f"{len(data['winners']):,}+"],
        ["Average contract", fmt_ron(data["avg"])],
        ["Median contract", fmt_ron(data["median"])],
        ["Min contract", fmt_ron(min(all_vals)) if all_vals else "N/A"],
        ["Max contract", fmt_ron(max(all_vals)) if all_vals else "N/A"],
    ]
    t = Table(overview, colWidths=[8*cm, 9*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), BLUE),
        ("TEXTCOLOR",   (0,0), (-1,0), white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT, white]),
        ("GRID",        (0,0), (-1,-1), 0.5, HexColor("#cccccc")),
        ("PADDING",     (0,0), (-1,-1), 6),
    ]))
    story.append(t)

    # Top winners table
    story.append(Paragraph("2. TOP WINNERS RANKING", h1_style))
    winner_data = [["#", "Company", "Contracts", "Total Value", "Avg Contract", "Market %"]]
    total_mkt = data["market_total"]
    for i, (name, d) in enumerate(data["winners"][:15], 1):
        pct = d["total"] / total_mkt * 100 if total_mkt else 0
        avg = d["total"] / d["contracts"] if d["contracts"] else 0
        winner_data.append([
            str(i), name[:40], f"{d['contracts']:,}",
            fmt_ron(d["total"]), fmt_ron(avg), f"{pct:.1f}%"
        ])
    t = Table(winner_data, colWidths=[0.7*cm, 6.5*cm, 1.8*cm, 2.8*cm, 2.5*cm, 1.7*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), DARK),
        ("TEXTCOLOR",   (0,0), (-1,0), white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("BACKGROUND",  (0,1), (-1,1), HexColor("#fff3cd")),  # gold for #1
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,2), (-1,-1), [LIGHT, white]),
        ("GRID",        (0,0), (-1,-1), 0.4, HexColor("#cccccc")),
        ("PADDING",     (0,0), (-1,-1), 5),
        ("ALIGN",       (2,0), (-1,-1), "RIGHT"),
    ]))
    story.append(t)

    # Top buyers
    story.append(Paragraph("3. TOP BUYERS (PUBLIC AUTHORITIES)", h1_style))
    buyer_data = [["Rank", "Buyer", "Contracts"]]
    for i, (b, cnt) in enumerate(data["top_buyers"][:10], 1):
        buyer_data.append([str(i), b[:55], str(cnt)])
    t = Table(buyer_data, colWidths=[1*cm, 13.5*cm, 2.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), BLUE),
        ("TEXTCOLOR",   (0,0), (-1,0), white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT, white]),
        ("GRID",        (0,0), (-1,-1), 0.4, HexColor("#cccccc")),
        ("PADDING",     (0,0), (-1,-1), 5),
        ("ALIGN",       (2,0), (-1,-1), "RIGHT"),
    ]))
    story.append(t)

    # Strategy insight
    story.append(Paragraph("4. BID STRATEGY RECOMMENDATIONS", h1_style))
    top_name, top_d = data["winners"][0] if data["winners"] else ("N/A", {"total": 0, "contracts": 0})
    top_pct = top_d["total"] / total_mkt * 100 if total_mkt else 0
    concentration = sum(d["total"] for _, d in data["winners"][:3]) / total_mkt * 100 if total_mkt else 0

    if top_pct > 30:
        competition = f"⚠️ Market is dominated by {top_name} ({top_pct:.0f}% of total value). Entry is difficult. Consider niche CPV sub-codes or smaller geographic areas."
    elif top_pct > 15:
        competition = f"⚡ {top_name} leads with {top_pct:.0f}%. Competitive but winnable. Focus on buyers they haven't served."
    else:
        competition = f"✅ Fragmented market — no single dominant player (top competitor: {top_pct:.0f}%). Strong entry opportunity."

    insights = [
        ("Market concentration", f"Top 3 winners hold {concentration:.0f}% of market value."),
        ("Competition level", competition),
        ("Optimal bid size", f"Target contracts near median: {fmt_ron(data['median'])}. Avoid extremes."),
        ("Entry strategy", f"Focus on buyers with 5-20 contracts/year — active but not locked into one supplier."),
        ("Pricing guidance", f"Price between {fmt_ron(data['median']*0.85)} and {fmt_ron(data['median']*1.1)} to be competitive."),
    ]
    for title, text in insights:
        story.append(Paragraph(f"<b>{title}:</b> {text}", insight_style))
        story.append(Spacer(1, 0.15*cm))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#cccccc")))
    story.append(Paragraph("© InterJob Intelligence · SEAP Romania Data 2023-2025 · interjob.ro", caption_style))

    doc.build(story)
    print(f"✅ Report saved: {out_path}")
    return out_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cpv",     default="", help="CPV code or prefix")
    p.add_argument("--company", default="", help="Company name fragment")
    p.add_argument("--buyer",   default="", help="Buyer name fragment")
    p.add_argument("--year",    default="", help="Year filter")
    p.add_argument("--out",     default="", help="Output PDF path")
    args = p.parse_args()
    if not any([args.cpv, args.company, args.buyer]):
        print("Usage: python bid_pdf.py --cpv 45233 [--out report.pdf]")
        sys.exit(1)
    build_pdf(args)
