import requests

HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
TOKEN = "9QEJ4ANOPHXZ0YE34NEWDAKA1UXZPKNX"
H = {"Authorization": f"cpanel loaiidil:{TOKEN}"}

domains = ["factoryjobs.eu","interjob.ro","mivromania.online","careworkers.eu",
    "expatsinromania.org","horecaworkers2026.eu","cifn.info"]

for d in domains:
    results = []
    for func in ["ensure_dkim_keys_present", "install_dkim_private_keys", "enable_dkim"]:
        r = requests.get(f"{HOST}/execute/EmailAuth/{func}", headers=H, params={"domain": d}, timeout=15)
        ok = r.ok and r.json().get("status", 0)
        results.append((func, ok, r.status_code))

    fixed = any(ok for _, ok, _ in results)
    detail = " ".join(f"{f}={'OK' if ok else sc}" for f, ok, sc in results)
    status = "FIXED" if fixed else "MANUAL"
    print(f"  {d:25s} {status:8s} {detail}")
