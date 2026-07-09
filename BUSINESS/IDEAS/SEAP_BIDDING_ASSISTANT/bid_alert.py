"""
SEAP Competitive Alert — monitor CPV codes, alert via Telegram when new contracts posted.
Usage:
  python bid_alert.py --add 45233140      # start monitoring CPV
  python bid_alert.py --check             # run check now (also called by cron)
  python bid_alert.py --list              # show monitored CPVs
  python bid_alert.py --remove 45233140  # stop monitoring

Cron (raspibig): 0 8 * * * python3 /opt/ACTIVE/SEAP/bid_alert.py --check
"""
import argparse, json, csv, sys, urllib.request, urllib.parse, os
from pathlib import Path
from datetime import date, timedelta

DATA      = Path(__file__).parent / "DATA"
STATE_FILE = Path(__file__).parent / "alert_state.json"

# Telegram — uses raspibig controller bot token
TG_TOKEN  = os.getenv("TG_TOKEN", "")
TG_CHAT   = os.getenv("TG_CHAT", "")  # your chat ID


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"cpvs": {}, "last_check": "", "alerts_sent": 0}


def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))


def send_telegram(msg):
    if not TG_TOKEN or not TG_CHAT:
        print(f"[TELEGRAM] {msg}")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


def fmt_ron(v):
    if v >= 1e6: return f"{v/1e6:.1f}M RON"
    if v >= 1e3: return f"{v/1e3:.0f}K RON"
    return f"{v:.0f} RON"


def scan_cpv(cpv_prefix):
    """Scan winner_contracts_detail.csv for contracts matching CPV, return stats."""
    contracts = []
    with open(DATA / "winner_contracts_detail.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["cpv"].replace("-","").startswith(cpv_prefix.replace("-","")):
                try: r["value_ron"] = float(r["value_ron"] or 0)
                except: r["value_ron"] = 0.0
                contracts.append(r)

    if not contracts:
        return None

    vals = [c["value_ron"] for c in contracts if c["value_ron"] > 0]
    from collections import Counter
    top_winners = Counter(c["winner"] for c in contracts).most_common(3)
    top_buyers  = Counter(c["buyer"] for c in contracts if c["buyer"]).most_common(3)

    return {
        "count":       len(contracts),
        "total":       sum(vals),
        "median":      sorted(vals)[len(vals)//2] if vals else 0,
        "avg":         sum(vals)/len(vals) if vals else 0,
        "top_winners": top_winners,
        "top_buyers":  top_buyers,
        "years":       sorted(set(c["year"] for c in contracts)),
    }


def check_all():
    state = load_state()
    if not state["cpvs"]:
        print("No CPVs monitored. Use --add <cpv>")
        return

    today = str(date.today())
    new_alerts = []

    for cpv, meta in state["cpvs"].items():
        stats = scan_cpv(cpv)
        if not stats:
            continue

        prev_count = meta.get("last_count", 0)
        curr_count = stats["count"]
        delta = curr_count - prev_count

        if delta > 0 and prev_count > 0:
            msg = (
                f"🔔 <b>SEAP Alert: CPV {cpv}</b>\n"
                f"📈 +{delta} new contracts found!\n\n"
                f"📊 Market stats:\n"
                f"  Total contracts: {curr_count:,}\n"
                f"  Median value: {fmt_ron(stats['median'])}\n"
                f"  Market total: {fmt_ron(stats['total'])}\n\n"
                f"🏆 Top winners:\n"
                + "\n".join(f"  • {w} ({c} contracts)" for w, c in stats["top_winners"])
                + f"\n\n🏛️ Top buyers:\n"
                + "\n".join(f"  • {b} ({c})" for b, c in stats["top_buyers"])
                + f"\n\n💡 Bid sweet spot: {fmt_ron(stats['median'] * 0.92)}–{fmt_ron(stats['median'] * 1.05)}"
            )
            send_telegram(msg)
            new_alerts.append(cpv)

        state["cpvs"][cpv]["last_count"] = curr_count
        state["cpvs"][cpv]["last_median"] = stats["median"]
        state["cpvs"][cpv]["last_check"] = today

    state["last_check"] = today
    state["alerts_sent"] = state.get("alerts_sent", 0) + len(new_alerts)
    save_state(state)

    print(f"✅ Checked {len(state['cpvs'])} CPVs. Alerts: {len(new_alerts)}")
    if new_alerts:
        print(f"   Alerted: {', '.join(new_alerts)}")


def add_cpv(cpv):
    state = load_state()
    stats = scan_cpv(cpv)
    if not stats:
        print(f"❌ No data for CPV {cpv}")
        return
    state["cpvs"][cpv] = {
        "added": str(date.today()),
        "last_count": stats["count"],
        "last_median": stats["median"],
        "last_check": str(date.today()),
    }
    save_state(state)
    print(f"✅ Monitoring CPV {cpv}: {stats['count']} contracts, median {fmt_ron(stats['median'])}")
    send_telegram(f"👁️ Now monitoring CPV <b>{cpv}</b>\n{stats['count']} contracts in DB | Median: {fmt_ron(stats['median'])}")


def list_cpvs():
    state = load_state()
    if not state["cpvs"]:
        print("No CPVs monitored.")
        return
    print(f"\n{'CPV':<20} {'Contracts':>10} {'Median':>12} {'Last check'}")
    print("-" * 60)
    for cpv, m in state["cpvs"].items():
        print(f"{cpv:<20} {m.get('last_count', 0):>10,} {fmt_ron(m.get('last_median', 0)):>12} {m.get('last_check', '-')}")
    print(f"\nTotal alerts sent: {state.get('alerts_sent', 0)}")


def remove_cpv(cpv):
    state = load_state()
    if cpv in state["cpvs"]:
        del state["cpvs"][cpv]
        save_state(state)
        print(f"✅ Removed CPV {cpv}")
    else:
        print(f"CPV {cpv} not monitored.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--add",    help="Start monitoring CPV")
    p.add_argument("--remove", help="Stop monitoring CPV")
    p.add_argument("--check",  action="store_true", help="Run check now")
    p.add_argument("--list",   action="store_true", help="List monitored CPVs")
    args = p.parse_args()

    if   args.add:    add_cpv(args.add)
    elif args.remove: remove_cpv(args.remove)
    elif args.check:  check_all()
    elif args.list:   list_cpvs()
    else:             p.print_help()
