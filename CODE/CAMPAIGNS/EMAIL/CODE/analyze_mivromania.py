import requests, os
from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

key = os.environ.get("BREVO_MIVROMANIA_API_KEY", "")
h = {"api-key": key}

r = requests.get("https://api.brevo.com/v3/smtp/statistics/events",
    headers=h, params={"event": "hardBounces", "limit": 50, "days": 7})
events = r.json().get("events", [])
print(f"Hard bounces last 7 days: {len(events)}")

domains = {}
for e in events:
    email = e.get("email", "")
    d = email.split("@")[1] if "@" in email else "?"
    domains[d] = domains.get(d, 0) + 1

print("\nTop bounced domains:")
for d, c in sorted(domains.items(), key=lambda x: -x[1])[:15]:
    print(f"  {c:>3} {d}")

reasons = {}
for e in events:
    r_txt = e.get("reason", "")[:50]
    reasons[r_txt] = reasons.get(r_txt, 0) + 1
print("\nReasons:")
for r_txt, c in sorted(reasons.items(), key=lambda x: -x[1])[:10]:
    print(f"  {c:>3} {r_txt}")

print("\nSample:")
for e in events[:10]:
    em = e.get("email", "?")
    dt = e.get("date", "")[:10]
    rs = e.get("reason", "")[:50]
    print(f"  {em:40s} {dt} {rs}")
