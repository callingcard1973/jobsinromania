"""Fix get_body in response_tracker to handle HTML-only emails."""
import re as regex

f = "/opt/ACTIVE/INFRA/SKILLS/response_tracker.py"
content = open(f).read()

old = '''def get_body(msg):
    for part in (msg.walk() if msg.is_multipart() else [msg]):
        if part.get_content_type() == "text/plain":
            try:
                return part.get_payload(decode=True).decode(errors="replace")[:1000]
            except Exception:
                pass
    return ""'''

new = '''def get_body(msg):
    plain, html = "", ""
    for part in (msg.walk() if msg.is_multipart() else [msg]):
        ct = part.get_content_type()
        try:
            text = part.get_payload(decode=True).decode(errors="replace")
        except Exception:
            continue
        if ct == "text/plain" and not plain:
            plain = text[:1000]
        elif ct == "text/html" and not html:
            html = re.sub(r"<[^>]+>", " ", text)
            html = re.sub(r"\\s+", " ", html).strip()[:1000]
    return plain or html or ""'''

if old in content:
    content = content.replace(old, new)
    open(f, "w").write(content)
    print("response_tracker: fixed get_body for HTML")
else:
    print("response_tracker: pattern not found")
