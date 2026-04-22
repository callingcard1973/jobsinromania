"""Generate HTML article files for 6 launch countries from countries.json."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "DATA"
ARTICLES_DIR = DATA_DIR / "articles"
COUNTRIES_JSON = DATA_DIR / "countries.json"

LAUNCH = {"NG", "KE", "ET", "MA", "ZA", "GH"}


def fmt_usd(val) -> str:
    if val is None:
        return "N/A"
    b = val / 1_000_000_000
    if b >= 1:
        return f"${b:.1f}B"
    m = val / 1_000_000
    return f"${m:.0f}M"


def fmt_pop(val) -> str:
    if val is None:
        return "N/A"
    m = val / 1_000_000
    return f"{m:.1f} million"


def cpi_label(score) -> str:
    if score is None:
        return "N/A"
    if score >= 60:
        return f"{score}/100 (Low corruption)"
    if score >= 40:
        return f"{score}/100 (Moderate)"
    if score >= 25:
        return f"{score}/100 (High corruption)"
    return f"{score}/100 (Very high corruption)"


def visa_summary(c: dict) -> str:
    vf = c.get("visa_free_count")
    voa = c.get("voa_count")
    ev = c.get("evisa_count")
    schengen = c.get("schengen_access", "visa_required")
    schengen_label = {
        "visa_free": "Visa-free to Schengen/EU",
        "visa_on_arrival": "Visa on arrival for Schengen/EU",
        "evisa": "E-Visa available for Schengen/EU",
        "visa_required": "Visa required for Schengen/EU",
    }.get(schengen, "Visa required for Schengen/EU")
    parts = []
    if vf is not None:
        parts.append(f"{vf} visa-free destinations")
    if voa is not None:
        parts.append(f"{voa} visa-on-arrival")
    if ev is not None:
        parts.append(f"{ev} e-visa")
    return (", ".join(parts) + f". {schengen_label}.") if parts else schengen_label


def article_html(c: dict) -> str:
    name = c["name"]
    region = c["region"]
    capital = c["capital"]
    currency = c["currency"]
    language = c["language"]
    gdp = fmt_usd(c.get("gdp_usd"))
    gdp_pc = fmt_usd(c.get("gdp_per_capita"))
    growth = f"{c['gdp_growth_pct']:.1f}%" if c.get("gdp_growth_pct") else "N/A"
    pop = fmt_pop(c.get("population"))
    inflation = f"{c['inflation_pct']:.1f}%" if c.get("inflation_pct") else "N/A"
    unemployment = f"{c['unemployment_pct']:.1f}%" if c.get("unemployment_pct") else "N/A"
    cpi = cpi_label(c.get("cpi_score"))
    exports = fmt_usd(c.get("exports_usd"))
    imports = fmt_usd(c.get("imports_usd"))
    visa = visa_summary(c)
    treaty_count = c.get("treaty_count", 0)

    return f"""<article class="country-profile">
<h1>Doing Business in {name}: Complete Guide for International Investors</h1>

<p class="lead">{name}, located in {region} with its capital in {capital}, is one of Africa's key markets for international trade and investment. This guide covers everything you need to know about entering the {name} market — from economic fundamentals to legal requirements, banking, and mobility.</p>

<h2>Country at a Glance</h2>
<table class="data-table">
  <tr><th>Capital</th><td>{capital}</td></tr>
  <tr><th>Region</th><td>{region}</td></tr>
  <tr><th>Currency</th><td>{currency}</td></tr>
  <tr><th>Business Language</th><td>{language}</td></tr>
  <tr><th>Population</th><td>{pop}</td></tr>
</table>

<h2>Economic Overview</h2>
<p>{name}'s economy has a GDP of <strong>{gdp}</strong> with a GDP per capita of <strong>{gdp_pc}</strong>. The economy grew at <strong>{growth}</strong> in the most recent reported year, with an inflation rate of {inflation} and unemployment at {unemployment}.</p>

<table class="data-table">
  <tr><th>GDP (Total)</th><td>{gdp}</td></tr>
  <tr><th>GDP per Capita</th><td>{gdp_pc}</td></tr>
  <tr><th>GDP Growth</th><td>{growth}</td></tr>
  <tr><th>Inflation</th><td>{inflation}</td></tr>
  <tr><th>Unemployment</th><td>{unemployment}</td></tr>
  <tr><th>Total Exports</th><td>{exports}</td></tr>
  <tr><th>Total Imports</th><td>{imports}</td></tr>
</table>

<h2>Trade &amp; Investment Climate</h2>
<p>{name} is a signatory to <strong>{treaty_count} international investment agreements</strong>, including bilateral investment treaties (BITs) and free trade agreements. These treaties provide legal protections for foreign investors, covering fair treatment, expropriation compensation, and dispute resolution mechanisms.</p>

<p>The country's <strong>Corruption Perceptions Index (CPI) score is {cpi}</strong> (Transparency International, 2025). Investors should account for governance considerations when structuring transactions and contracts.</p>

<h2>Doing Business: Practical Steps</h2>
<ol>
  <li><strong>Choose your entry structure:</strong> Foreign investors can enter {name} through a wholly-owned subsidiary, joint venture with a local partner, branch office, or representative office. Each structure has different regulatory, tax, and liability implications.</li>
  <li><strong>Register your company:</strong> Business registration is handled by the national companies registry. Typical requirements include memorandum and articles of association, director/shareholder details, registered office address, and initial capital deposit. Costs and timelines vary — budget 2–8 weeks and legal fees.</li>
  <li><strong>Open a business bank account:</strong> Major international banks operating in {name} include local branches of Standard Chartered, Ecobank, Stanbic, and regional development banks. Foreign companies will need notarised incorporation documents and proof of business activity.</li>
  <li><strong>Understand taxation:</strong> Research current corporate income tax rates, VAT registration thresholds, withholding tax on dividends and royalties, and any sector-specific levies. Tax treaties with your home country may reduce withholding rates.</li>
  <li><strong>Hire and comply:</strong> Local labour laws govern minimum wages, contracts, social security contributions, and termination procedures. Foreign workers typically require work permits sponsored by the registered entity.</li>
</ol>

<h2>Travel &amp; Mobility</h2>
<p>{visa}. Business travellers should verify current entry requirements directly with the relevant embassy, as visa policies change frequently.</p>

<p>For companies seeking to relocate skilled African professionals to Europe, work permit and visa pathways exist through standard EU labour migration channels. Processing times and requirements vary by destination country.</p>

<h2>Key Sectors for Investment</h2>
<p>International investors in {name} find opportunities across multiple sectors. Agriculture and agro-processing, construction and infrastructure, hospitality and tourism, manufacturing, financial services, and technology represent consistently active areas. Sector-specific licensing and local ownership requirements may apply — legal due diligence is essential before committing capital.</p>

<h2>Resources</h2>
<ul>
  <li>Investment promotion agency: Contact the national investment authority for incentive packages and facilitation</li>
  <li>Chamber of commerce: Local chambers provide business matching, legal referrals, and market intelligence</li>
  <li>World Bank Doing Business indicators: <a href="https://data.worldbank.org" rel="nofollow">data.worldbank.org</a></li>
  <li>UNCTAD Investment Policy Hub: <a href="https://investmentpolicy.unctad.org" rel="nofollow">investmentpolicy.unctad.org</a></li>
</ul>

<div class="cta-box">
  <h3>Looking for skilled workers from {name}?</h3>
  <p>We connect businesses with verified African professionals across construction, agriculture, hospitality, and manufacturing. <a href="https://interjob.ro/apply.html">Browse available candidates &rarr;</a></p>
</div>

</article>"""


def main() -> None:
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(COUNTRIES_JSON.read_text(encoding="utf-8"))

    count = 0
    for c in data:
        if c["iso2"] not in LAUNCH:
            continue
        html = article_html(c)
        out = ARTICLES_DIR / f"{c['iso2'].lower()}_{c['name'].lower().replace(' ', '_')}.html"
        out.write_text(html, encoding="utf-8")
        print(f"Written: {out.name}")
        count += 1

    print(f"\nDone. {count} articles written to {ARTICLES_DIR}")


if __name__ == "__main__":
    main()
