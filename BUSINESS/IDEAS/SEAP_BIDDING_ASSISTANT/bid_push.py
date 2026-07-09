"""
SEAP Push — sends top winners data to seicarescu.com WP options every 6h.
Fixes interjob-seap-widget and interjob-job-board plugins (A2 can't reach raspibig).
Usage: python bid_push.py [--cpv 45] [--limit 20]
Cron (raspibig): 0 */6 * * * python3 /opt/ACTIVE/SEAP/bid_push.py
"""
import csv, json, urllib.request, urllib.parse, sys, os
from pathlib import Path
from collections import defaultdict

DATA     = Path(__file__).parent / "DATA"
WP_SITES = [
    {"url": "https://seicarescu.com",    "user": "raspibig",   "pass": "Raspibig2026!"},
]


def fmt_ron(v):
    if v >= 1e6: return f"{v/1e6:.1f}M"
    if v >= 1e3: return f"{v/1e3:.0f}K"
    return str(int(v))


def get_top_winners(cpv_prefix="", limit=20):
    winners = defaultdict(lambda: {"name": "", "cui": "", "city": "", "contracts": 0, "total": 0.0})
    with open(DATA / "winner_contracts_detail.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if cpv_prefix and not r["cpv"].replace("-","").startswith(cpv_prefix.replace("-","")):
                continue
            try: val = float(r["value_ron"] or 0)
            except: val = 0.0
            k = r["winner_cui"] or r["winner"].upper()
            winners[k]["name"] = r["winner"]
            winners[k]["cui"]  = r["winner_cui"]
            winners[k]["contracts"] += 1
            winners[k]["total"] += val

    sorted_w = sorted(winners.values(), key=lambda x: x["total"], reverse=True)[:limit]
    return [{"name": w["name"], "cui": w["cui"], "contracts": w["contracts"],
             "total_ron_M": round(w["total"]/1e6, 2), "city": w.get("city", "")}
            for w in sorted_w]


def push_to_wp(site, data_key, data_value):
    import base64
    token = base64.b64encode(f"{site['user']}:{site['pass']}".encode()).decode()
    payload = json.dumps({"meta": {data_key: json.dumps(data_value)}}).encode()
    # Try REST API options endpoint
    req = urllib.request.Request(
        f"{site['url']}/wp-json/wp/v2/settings",
        data=json.dumps({data_key: json.dumps(data_value)}).encode(),
        method="POST",
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status == 200
    except Exception as e:
        print(f"  REST failed: {e}")
        return False


def push_via_php(site, key, value):
    """Fallback: push via cPanel PHP runner if on A2."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "CODE/INFRA/CLAUDE"))
    try:
        from cpanel_runner import upload_file
        import ssl, time, urllib.request as ur

        CTX = ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
        json_val = json.dumps(value).replace("'", "\\'")
        php = f"""<?php
define('ABSPATH', '/home/loaiidil/seicarescu.com/');
chdir(ABSPATH);
$_SERVER['HTTP_HOST'] = 'seicarescu.com';
$_SERVER['REQUEST_URI'] = '/';
require_once(ABSPATH . 'wp-config.php');
update_option('{key}', '{json_val}');
echo 'ok:' . strlen('{json_val}');
@unlink(__FILE__);
""".encode()
        upload_file(php, '_push_seap.php', '/home/loaiidil/seicarescu.com', domain='seicarescu.com')
        time.sleep(1)
        r = ur.urlopen('https://seicarescu.com/_push_seap.php', timeout=15, context=CTX)
        result = r.read().decode()
        return result.startswith("ok:")
    except Exception as e:
        print(f"  PHP push failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--cpv",   default="", help="CPV prefix filter")
    p.add_argument("--limit", default=20, type=int)
    args = p.parse_args()

    print("📤 Building SEAP winners data...")
    winners = get_top_winners(args.cpv, args.limit)
    print(f"   Got {len(winners)} winners")

    for site in WP_SITES:
        print(f"\n→ {site['url']}")
        ok = push_via_php(site, "isw_cached_winners", winners)
        print(f"  Push: {'✅ OK' if ok else '❌ FAILED'}")

    print("\nDone.")
