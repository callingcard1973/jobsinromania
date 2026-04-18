import csv
import os
import json
from collections import defaultdict

INPUT = '../DATA/segmented.csv'
EXPORT_DIR = '../DATA/export'

SEGMENTS_ORDER = [
    'business_intl', 'business_ro', 'business_austria',
    'anonymous',
    'recruitment', 'personal_close', 'school',
    'airbnb', 'phone_only', 'junk'
]

def truncate(s, n=60):
    s = (s or '').replace('\n', ' ').replace('\r', '')
    return s[:n] + '…' if len(s) > n else s

def build_html(segments_data):
    tabs_html = ''
    all_js_data = {}

    for seg in SEGMENTS_ORDER:
        rows = segments_data.get(seg, [])
        if not rows:
            continue
        label = seg.replace('_', ' ').title()
        tabs_html += f'<button class="tab" onclick="showTab(\'{seg}\')">{label} <span class="badge">{len(rows)}</span></button>\n'
        all_js_data[seg] = [
            {
                'name': (r.get('First Name','') + ' ' + r.get('Last Name','')).strip(),
                'email': r.get('E-mail 1 - Value',''),
                'phone': r.get('Phone 1 - Value',''),
                'org': r.get('Organization Name',''),
                'title': r.get('Organization Title',''),
                'score': int(r.get('score', 0)),
                'notes': truncate(r.get('Notes',''))
            }
            for r in rows
        ]

    js_data = json.dumps(all_js_data)

    panels_html = ''.join(
        f'<div class="panel" id="panel-{seg}"><input type="text" placeholder="Search name, email, org..." oninput="filterTable(\'{seg}\', this.value)"><table><thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Organization</th><th>Title</th><th>Score</th><th>Notes</th></tr></thead><tbody id="tbody-{seg}"></tbody></table></div>'
        for seg in SEGMENTS_ORDER if seg in all_js_data
    )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Personal Contacts</title>
<style>
body {{ font-family: sans-serif; background: #111; color: #eee; margin: 0; padding: 16px; }}
h1 {{ color: #fff; margin-bottom: 8px; }}
.tabs {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }}
.tab {{ background: #222; border: 1px solid #444; color: #ccc; padding: 6px 12px; cursor: pointer; border-radius: 4px; }}
.tab.active {{ background: #0ea5e9; color: #fff; border-color: #0ea5e9; }}
.badge {{ background: #333; border-radius: 10px; padding: 2px 7px; font-size: 11px; margin-left: 4px; }}
input[type=text] {{ background: #222; border: 1px solid #444; color: #eee; padding: 8px 12px; width: 300px; border-radius: 4px; margin-bottom: 12px; font-size: 14px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ background: #1e293b; color: #94a3b8; text-align: left; padding: 8px 10px; border-bottom: 1px solid #334155; }}
td {{ padding: 7px 10px; border-bottom: 1px solid #1e293b; vertical-align: top; }}
tr:hover td {{ background: #1a2332; }}
.score-badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }}
.panel {{ display: none; }}
.panel.active {{ display: block; }}
</style>
</head>
<body>
<h1>Personal Contacts — {sum(len(v) for v in all_js_data.values()):,} contacts</h1>
<div class="tabs">{tabs_html}</div>
<div id="panels">{panels_html}</div>
<script>
const DATA = {js_data};
function renderTable(seg, rows) {{
    const tbody = document.getElementById('tbody-' + seg);
    if (!tbody) return;
    tbody.innerHTML = rows.map(r => `<tr>
        <td>${{r.name || '-'}}</td>
        <td>${{r.email ? '<a href="mailto:'+r.email+'" style="color:#38bdf8">'+r.email+'</a>' : '-'}}</td>
        <td>${{r.phone || '-'}}</td>
        <td>${{r.org || '-'}}</td>
        <td>${{r.title || '-'}}</td>
        <td><span class="score-badge" style="background:${{scoreColor(r.score)}};color:#111">${{r.score}}</span></td>
        <td style="color:#888;font-size:12px">${{r.notes || ''}}</td>
    </tr>`).join('');
}}
function scoreColor(s) {{
    if (s >= 70) return '#4ade80';
    if (s >= 40) return '#facc15';
    return '#f87171';
}}
function filterTable(seg, q) {{
    q = q.toLowerCase();
    const rows = (DATA[seg] || []).filter(r =>
        (r.name+r.email+r.org+r.notes).toLowerCase().includes(q)
    );
    renderTable(seg, rows);
}}
function showTab(seg) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const btn = [...document.querySelectorAll('.tab')].find(t => t.onclick.toString().includes("'"+seg+"'"));
    if (btn) btn.classList.add('active');
    const panel = document.getElementById('panel-' + seg);
    if (panel) panel.classList.add('active');
    renderTable(seg, DATA[seg] || []);
}}
const firstSeg = Object.keys(DATA)[0];
if (firstSeg) showTab(firstSeg);
</script>
</body>
</html>'''

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    os.makedirs(EXPORT_DIR, exist_ok=True)

    by_seg = defaultdict(list)
    for row in rows:
        by_seg[row.get('segment', 'junk')].append(row)

    for seg in by_seg:
        by_seg[seg].sort(key=lambda r: int(r.get('score', 0)), reverse=True)

    for seg, seg_rows in by_seg.items():
        path = os.path.join(EXPORT_DIR, f'{seg}.csv')
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(seg_rows)

    html = build_html(by_seg)
    html_path = os.path.join(EXPORT_DIR, 'index.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Exported {len(rows)} contacts to {EXPORT_DIR}/")
    for seg in SEGMENTS_ORDER:
        if seg in by_seg:
            print(f"  {seg}: {len(by_seg[seg])}")

if __name__ == '__main__':
    main()
