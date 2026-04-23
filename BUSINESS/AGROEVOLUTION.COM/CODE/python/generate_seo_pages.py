"""
SEO county pages generator + deployer for agroevolution.com
Generates 41 static HTML pages (one per Romanian county) with MADR stats.
"""

from __future__ import annotations
import sys
# Force UTF-8 on Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SUPABASE_URL = "https://jaurgtjadyiannbalhhb.supabase.co"
SUPABASE_KEY = "sb_secret_6M9Pf8i46lvXMjSN3wvBYA_Zr2qiO7R"

CPANEL_HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = os.environ.get("CPANEL_TOKEN", "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U")
REMOTE_BASE = "/home/loaiidil/agroevolution.com/teren-vanzare"

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "teren-vanzare"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# County mapping  (display name → slug, Supabase key)
# Supabase stores uppercase diacritics-free names like ALBA, BACAU, etc.
# We map each display name to its Supabase key.
# ---------------------------------------------------------------------------

JUDETE: dict[str, dict[str, str]] = {
    "Alba": {"slug": "alba", "sb": "ALBA"},
    "Arad": {"slug": "arad", "sb": "ARAD"},
    "Argeș": {"slug": "arges", "sb": "ARGES"},
    "Bacău": {"slug": "bacau", "sb": "BACAU"},
    "Bihor": {"slug": "bihor", "sb": "BIHOR"},
    "Bistrița-Năsăud": {"slug": "bistrita-nasaud", "sb": "BISTRITA-NASAUD"},
    "Botoșani": {"slug": "botosani", "sb": "BOTOSANI"},
    "Brăila": {"slug": "braila", "sb": "BRAILA"},
    "Brașov": {"slug": "brasov", "sb": "BRASOV"},
    "Buzău": {"slug": "buzau", "sb": "BUZAU"},
    "Călărași": {"slug": "calarasi", "sb": "CALARASI"},
    "Caraș-Severin": {"slug": "caras-severin", "sb": "CARAS-SEVERIN"},
    "Cluj": {"slug": "cluj", "sb": "CLUJ"},
    "Constanța": {"slug": "constanta", "sb": "CONSTANTA"},
    "Covasna": {"slug": "covasna", "sb": "COVASNA"},
    "Dâmbovița": {"slug": "dambovita", "sb": "DAMBOVITA"},
    "Dolj": {"slug": "dolj", "sb": "DOLJ"},
    "Galați": {"slug": "galati", "sb": "GALATI"},
    "Giurgiu": {"slug": "giurgiu", "sb": "GIURGIU"},
    "Gorj": {"slug": "gorj", "sb": "GORJ"},
    "Harghita": {"slug": "harghita", "sb": "HARGHITA"},
    "Hunedoara": {"slug": "hunedoara", "sb": "HUNEDOARA"},
    "Ialomița": {"slug": "ialomita", "sb": "IALOMITA"},
    "Iași": {"slug": "iasi", "sb": "IASI"},
    "Ilfov": {"slug": "ilfov", "sb": "ILFOV"},
    "Maramureș": {"slug": "maramures", "sb": "MARAMURES"},
    "Mehedinți": {"slug": "mehedinti", "sb": "MEHEDINTI"},
    "Mureș": {"slug": "mures", "sb": "MURES"},
    "Neamț": {"slug": "neamt", "sb": "NEAMT"},
    "Olt": {"slug": "olt", "sb": "OLT"},
    "Prahova": {"slug": "prahova", "sb": "PRAHOVA"},
    "Sălaj": {"slug": "salaj", "sb": "SALAJ"},
    "Satu Mare": {"slug": "satu-mare", "sb": "SATU MARE"},
    "Sibiu": {"slug": "sibiu", "sb": "SIBIU"},
    "Suceava": {"slug": "suceava", "sb": "SUCEAVA"},
    "Teleorman": {"slug": "teleorman", "sb": "TELEORMAN"},
    "Timiș": {"slug": "timis", "sb": "TIMIS"},
    "Tulcea": {"slug": "tulcea", "sb": "TULCEA"},
    "Vâlcea": {"slug": "valcea", "sb": "VALCEA"},
    "Vaslui": {"slug": "vaslui", "sb": "VASLUI"},
    "Vrancea": {"slug": "vrancea", "sb": "VRANCEA"},
}


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def fetch_judet_data(sb_key: str) -> list[dict]:
    """Fetch all listings for a county from Supabase."""
    encoded = urllib.parse.quote(sb_key)
    url = (
        f"{SUPABASE_URL}/rest/v1/land_listings"
        f"?judet=eq.{encoded}"
        f"&select=localitate,suprafata_ha,pret_ron,categorie"
        f"&limit=10000"
    )
    req = urllib.request.Request(
        url,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"  [Supabase error] {sb_key}: {exc}")
        return []


def compute_stats(rows: list[dict]) -> dict:
    """Aggregate stats from raw listing rows."""
    total = len(rows)
    total_ha = 0.0
    price_per_ha_vals: list[float] = []
    cats: Counter = Counter()
    locs: Counter = Counter()

    for r in rows:
        sup = r.get("suprafata_ha")
        pret = r.get("pret_ron")
        cat = r.get("categorie") or "NECUNOSCUT"
        loc = r.get("localitate") or "—"

        if sup and sup > 0:
            total_ha += float(sup)
            if pret and pret > 0:
                price_per_ha_vals.append(float(pret) / float(sup))

        cats[cat.upper()] += 1
        if loc != "—":
            locs[loc.title()] += 1

    avg_price = sum(price_per_ha_vals) / len(price_per_ha_vals) if price_per_ha_vals else 0.0
    top_cat = cats.most_common(1)[0][0] if cats else "ARABIL"
    top_locs = locs.most_common(5)

    return {
        "total": total,
        "total_ha": round(total_ha, 1),
        "avg_price": round(avg_price, 0),
        "top_cat": top_cat,
        "cats": dict(cats.most_common()),
        "top_locs": top_locs,
    }


# ---------------------------------------------------------------------------
# AI content
# ---------------------------------------------------------------------------

def generate_ai_content(judet: str, stats: dict) -> str:
    """Try LM Studio; fall back to template."""
    prompt = (
        f"Scrie un paragraf SEO de 120-150 cuvinte despre piața terenurilor agricole "
        f"din județul {judet}, România. "
        f"Include: {stats['total']} anunțuri active, preț mediu {stats['avg_price']:.0f} RON/ha, "
        f"categoria principală {stats['top_cat']}. "
        f"Ton: informativ, profesional. Fără liste, doar text continuu. "
        f"Termină cu un call-to-action subtil."
    )
    try:
        body = json.dumps(
            {
                "model": "local-model",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300,
            }
        ).encode()
        req = urllib.request.Request(
            LM_STUDIO_URL,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return text
    except Exception:
        pass
    return fallback_content(judet, stats)


def fallback_content(judet: str, stats: dict) -> str:
    top_cat = stats["top_cat"].lower()
    return (
        f"Județul {judet} oferă oportunități atractive pentru investiții în terenuri agricole. "
        f"Cu {stats['total']} anunțuri active și un preț mediu de {stats['avg_price']:.0f} RON/ha, "
        f"piața terenurilor din {judet} se remarcă printr-o ofertă diversificată de terenuri {top_cat}. "
        f"Suprafața totală disponibilă depășește {stats['total_ha']:.0f} hectare, oferind opțiuni "
        f"atât pentru fermierii locali cât și pentru investitorii care doresc să acceseze subvențiile "
        f"agricole europene. Consultați anunțurile disponibile și înregistrați-vă pentru a fi "
        f"notificat când apar terenuri noi la prețul dorit."
    )


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

CAT_LABELS = {
    "ARABIL": "Arabil",
    "PASUNI": "Pășuni",
    "PĂȘUNI": "Pășuni",
    "LIVEZI": "Livezi",
    "FANETE": "Fânețe",
    "FÂNEȚE": "Fânețe",
    "VII": "Vii",
    "PADURI": "Păduri",
    "PĂDURI": "Păduri",
    "NECUNOSCUT": "Alte categorii",
}


def cat_label(raw: str) -> str:
    return CAT_LABELS.get(raw.upper(), raw.title())


def build_cats_html(cats: dict) -> str:
    parts = []
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        parts.append(
            f'<div class="cat"><div class="cn">{cnt}</div>'
            f'<div class="cl">{cat_label(cat)}</div></div>'
        )
    return "\n".join(parts)


def build_locs_html(top_locs: list) -> str:
    rows = []
    for loc, cnt in top_locs:
        rows.append(
            f'<div class="loc-row"><span>{loc}</span>'
            f'<span><strong>{cnt}</strong> anunțuri</span></div>'
        )
    return "\n".join(rows) if rows else "<p>Date indisponibile</p>"


def build_page(judet: str, slug: str, stats: dict, ai_text: str) -> str:
    first_sentence = ai_text.split(".")[0].strip() + "."
    meta_desc = (
        f"Terenuri agricole de vânzare în județul {judet}. "
        f"{stats['total']} anunțuri, preț mediu {stats['avg_price']:.0f} RON/ha. "
        f"Suprafață totală {stats['total_ha']:.0f} ha."
    )
    meta_desc = meta_desc[:155]

    avg_price_fmt = f"{int(stats['avg_price']):,}".replace(",", ".")
    total_ha_fmt = f"{stats['total_ha']:,.1f}".replace(",", ".")

    cats_html = build_cats_html(stats["cats"])
    locs_html = build_locs_html(stats["top_locs"])

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Teren agricol vânzare {judet} | AgroEvolution</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="https://agroevolution.com/teren-vanzare/{slug}/">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"ItemList","name":"Terenuri agricole {judet}","numberOfItems":{stats['total']},"url":"https://agroevolution.com/teren-vanzare/{slug}/"}}
</script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Georgia, serif; background: #f7f4ef; color: #2a2a2a; }}
.nav {{ background: #1a4a1a; padding: 14px 24px; }}
.nav a {{ color: #fff; text-decoration: none; font-size: 18px; font-weight: bold; }}
.hero {{ background: linear-gradient(135deg, #1a4a1a, #2d7a2d); color: #fff; padding: 60px 24px; text-align: center; }}
.hero h1 {{ font-size: clamp(24px, 4vw, 42px); margin-bottom: 12px; }}
.hero p {{ font-size: 17px; opacity: 0.9; max-width: 650px; margin: 0 auto; }}
.stats-bar {{ display: flex; justify-content: center; gap: 40px; background: #fff; padding: 24px; flex-wrap: wrap; border-bottom: 1px solid #eee; }}
.stat {{ text-align: center; }}
.stat .num {{ font-size: 28px; font-weight: bold; color: #2d7a2d; }}
.stat .lab {{ font-size: 12px; color: #666; margin-top: 2px; }}
.content {{ max-width: 800px; margin: 40px auto; padding: 0 24px; }}
.ai-text {{ font-size: 16px; line-height: 1.8; color: #333; margin-bottom: 32px; }}
.cats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 32px; }}
.cat {{ background: #fff; border-radius: 8px; padding: 16px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.cat .cn {{ font-size: 22px; font-weight: bold; color: #2d7a2d; }}
.cat .cl {{ font-size: 12px; color: #888; margin-top: 4px; }}
.localitati {{ background: #fff; border-radius: 8px; padding: 24px; margin-bottom: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.localitati h3 {{ margin-bottom: 16px; font-size: 18px; }}
.loc-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
.form-section {{ background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); margin-bottom: 40px; }}
.form-section h2 {{ font-size: 22px; margin-bottom: 8px; }}
.form-section p {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
input, select {{ width: 100%; padding: 11px; border: 1px solid #ddd; border-radius: 6px; font-size: 15px; margin-bottom: 12px; font-family: inherit; }}
.btn {{ width: 100%; padding: 13px; background: #2d7a2d; color: #fff; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; }}
.success {{ color: #2d7a2d; text-align: center; margin-top: 12px; display: none; font-size: 15px; }}
footer {{ background: #1a4a1a; color: rgba(255,255,255,0.7); text-align: center; padding: 24px; font-size: 13px; }}
footer a {{ color: #fff; text-decoration: none; margin: 0 8px; }}
</style>
</head>
<body>
<nav class="nav"><a href="https://agroevolution.com">&#127806; AgroEvolution</a></nav>
<div class="hero">
  <h1>Teren agricol de vânzare în județul {judet}</h1>
  <p>{first_sentence}</p>
</div>
<div class="stats-bar">
  <div class="stat"><div class="num">{stats['total']}</div><div class="lab">Anunțuri active</div></div>
  <div class="stat"><div class="num">{avg_price_fmt} RON</div><div class="lab">Preț mediu/ha</div></div>
  <div class="stat"><div class="num">{total_ha_fmt} ha</div><div class="lab">Suprafață totală</div></div>
</div>
<div class="content">
  <div class="ai-text">{ai_text}</div>
  <div class="cats">
{cats_html}
  </div>
  <div class="localitati">
    <h3>Top localități cu terenuri disponibile</h3>
{locs_html}
  </div>
  <div class="form-section">
    <h2>Caută teren în {judet}</h2>
    <p>Lasă datele și te contactăm cu oferte potrivite.</p>
    <form id="seo-form">
      <input type="email" name="email" placeholder="Email *" required>
      <input type="tel" name="telefon" placeholder="Telefon">
      <input type="number" name="suprafata_min" placeholder="Suprafață minimă (ha)">
      <input type="number" name="pret_max_ha" placeholder="Preț maxim (RON/ha)">
      <button type="submit" class="btn">Vreau oferte pentru {judet}</button>
      <p class="success" id="seo-ok">&#10003; Cerere primită! Te contactăm în curând.</p>
    </form>
  </div>
</div>
<footer>
  <a href="https://agroevolution.com/harta.php">Hartă MADR</a>
  <a href="https://agroevolution.com/cumpara-ferma/">Cumpără Fermă</a>
  <a href="https://agroevolution.com">AgroEvolution</a>
</footer>
<script>
document.getElementById('seo-form').addEventListener('submit', async function(e) {{
  e.preventDefault();
  const fd = new FormData(e.target);
  const data = {{ sursa: 'seo-{slug}', judet: '{judet}' }};
  fd.forEach((v,k) => {{ if(v) data[k] = v; }});
  const r = await fetch('/save_lead.php', {{
    method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(data)
  }});
  if(r.ok) {{ document.getElementById('seo-ok').style.display='block'; e.target.reset(); }}
}});
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Overview index page
# ---------------------------------------------------------------------------

def build_index_page(county_stats: list[dict]) -> str:
    rows = []
    for cs in sorted(county_stats, key=lambda x: x["judet"]):
        rows.append(
            f'<tr>'
            f'<td><a href="/teren-vanzare/{cs["slug"]}/">{cs["judet"]}</a></td>'
            f'<td>{cs["total"]}</td>'
            f'<td>{int(cs["avg_price"]):,} RON'.replace(",", ".")
            + f'</td>'
            f'<td>{cs["total_ha"]:,.1f}'.replace(",", ".")
            + f' ha</td>'
            f'</tr>'
        )
    rows_html = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Terenuri agricole de vânzare în România | AgroEvolution</title>
<meta name="description" content="Browse terenuri agricole de vânzare în toate județele României. Date MADR actualizate, prețuri medii, suprafețe disponibile.">
<link rel="canonical" href="https://agroevolution.com/teren-vanzare/">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Georgia, serif; background: #f7f4ef; color: #2a2a2a; }}
.nav {{ background: #1a4a1a; padding: 14px 24px; }}
.nav a {{ color: #fff; text-decoration: none; font-size: 18px; font-weight: bold; }}
.hero {{ background: linear-gradient(135deg, #1a4a1a, #2d7a2d); color: #fff; padding: 60px 24px; text-align: center; }}
.hero h1 {{ font-size: clamp(22px, 4vw, 40px); margin-bottom: 12px; }}
.hero p {{ font-size: 17px; opacity: 0.9; }}
.content {{ max-width: 900px; margin: 40px auto; padding: 0 24px; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.07); }}
th {{ background: #2d7a2d; color: #fff; padding: 12px 16px; text-align: left; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ padding: 11px 16px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
tr:last-child td {{ border-bottom: none; }}
tr:hover td {{ background: #f9f9f9; }}
td a {{ color: #2d7a2d; text-decoration: none; font-weight: bold; }}
td a:hover {{ text-decoration: underline; }}
footer {{ background: #1a4a1a; color: rgba(255,255,255,0.7); text-align: center; padding: 24px; font-size: 13px; margin-top: 60px; }}
footer a {{ color: #fff; text-decoration: none; margin: 0 8px; }}
</style>
</head>
<body>
<nav class="nav"><a href="https://agroevolution.com">&#127806; AgroEvolution</a></nav>
<div class="hero">
  <h1>Terenuri agricole de vânzare în România</h1>
  <p>Explorați ofertele din toate județele, cu date MADR actualizate</p>
</div>
<div class="content">
  <table>
    <thead>
      <tr><th>Județ</th><th>Anunțuri</th><th>Preț mediu/ha</th><th>Suprafață totală</th></tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
</div>
<footer>
  <a href="https://agroevolution.com/harta.php">Hartă MADR</a>
  <a href="https://agroevolution.com/cumpara-ferma/">Cumpără Fermă</a>
  <a href="https://agroevolution.com">AgroEvolution</a>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# cPanel deploy
# ---------------------------------------------------------------------------

def cpanel_mkdir(remote_path: str) -> None:
    parts = remote_path.rstrip("/").rsplit("/", 1)
    if len(parts) < 2:
        return
    parent, name = parts[0], parts[1]
    data = (
        f"path={urllib.parse.quote(parent, safe='/')}"
        f"&name={urllib.parse.quote(name)}"
    ).encode()
    req = urllib.request.Request(
        f"{CPANEL_HOST}/execute/Fileman/mkdir",
        data=data,
        method="POST",
        headers={"Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"},
    )
    try:
        urllib.request.urlopen(req, timeout=15, context=CTX)
    except Exception:
        pass  # dir may already exist


def cpanel_upload(content: bytes, remote_dir: str, filename: str) -> bool:
    boundary = "----FormBound7x9z"
    body = b"".join(
        [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"dir\"\r\n\r\n{remote_dir}\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\n1\r\n".encode(),
            (
                f"--{boundary}\r\nContent-Disposition: form-data; "
                f'name="file-1"; filename="{filename}"\r\nContent-Type: text/html\r\n\r\n'
            ).encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        f"{CPANEL_HOST}/execute/Fileman/upload_files",
        data=body,
        method="POST",
        headers={
            "Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=30, context=CTX).read())
        return bool(resp.get("data", {}).get("succeeded", 0))
    except Exception as exc:
        print(f"    [upload error] {exc}")
        return False


def deploy_page(slug: str, html: str) -> bool:
    remote_dir = f"{REMOTE_BASE}/{slug}"
    cpanel_mkdir(remote_dir)
    return cpanel_upload(html.encode("utf-8"), remote_dir, "index.html")


def deploy_index(html: str) -> bool:
    cpanel_mkdir(REMOTE_BASE)
    return cpanel_upload(html.encode("utf-8"), REMOTE_BASE, "index.html")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    county_stats_list: list[dict] = []
    generated = 0
    deployed = 0
    skipped = 0

    for judet, meta in JUDETE.items():
        slug = meta["slug"]
        sb_key = meta["sb"]

        print(f"[{judet}] Fetching data...", end=" ", flush=True)
        rows = fetch_judet_data(sb_key)

        if not rows:
            print(f"0 listings — SKIPPED")
            skipped += 1
            continue

        stats = compute_stats(rows)
        print(
            f"{stats['total']} listings, "
            f"{stats['avg_price']:.0f} RON/ha avg, "
            f"{stats['total_ha']:.0f} ha total"
        )

        ai_text = generate_ai_content(judet, stats)
        time.sleep(0.5)

        html = build_page(judet, slug, stats, ai_text)

        # Save locally
        local_dir = OUTPUT_DIR / slug
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "index.html").write_text(html, encoding="utf-8")
        generated += 1

        # Deploy
        ok = deploy_page(slug, html)
        if ok:
            deployed += 1
            print(f"  ✓ {judet} ({stats['total']} listings, {stats['avg_price']:.0f} RON/ha avg) → deployed")
        else:
            print(f"  ! {judet} → deploy failed (check cPanel)")

        county_stats_list.append(
            {
                "judet": judet,
                "slug": slug,
                "total": stats["total"],
                "avg_price": stats["avg_price"],
                "total_ha": stats["total_ha"],
            }
        )

        time.sleep(0.3)

    # Overview index
    if county_stats_list:
        idx_html = build_index_page(county_stats_list)
        (OUTPUT_DIR / "index.html").write_text(idx_html, encoding="utf-8")
        ok = deploy_index(idx_html)
        if ok:
            print("\n✓ Overview index deployed → https://agroevolution.com/teren-vanzare/")
        else:
            print("\n! Overview index deploy failed")
        time.sleep(0.3)

    print(
        f"\nDone: {generated} pages generated, {deployed} deployed, {skipped} skipped (0 listings)."
    )


if __name__ == "__main__":
    main()
