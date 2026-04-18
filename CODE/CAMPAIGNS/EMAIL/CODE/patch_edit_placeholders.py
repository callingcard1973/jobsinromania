#!/usr/bin/env python3
"""Patch template editor page to show ALL database columns as available placeholders."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

# 1. Replace the static placeholder list in the template editor HTML
old_placeholder_box = """<div style="margin-top: 30px; padding: 20px; background: #1e293b; border-radius: 8px;">
  <h3 style="margin-top: 0; color: #94a3b8; font-size: 14px;">Available Placeholders</h3>
  <code style="color: #22c55e;">{company}</code> - Company name<br>
  <code style="color: #22c55e;">{name}</code> - Contact name<br>
  <code style="color: #22c55e;">{city}</code> - City<br>
  <code style="color: #22c55e;">{email}</code> - Email address<br>
</div>"""

new_placeholder_box = """<div style="margin-top: 30px; padding: 20px; background: #1e293b; border-radius: 8px;">
  <h3 style="margin-top: 0; color: #94a3b8; font-size: 14px;">Available Placeholders (click to insert)</h3>
  <p style="color: #94a3b8; font-size: 12px; margin-bottom: 10px;">Built-in:</p>
  <code class="ph" style="cursor:pointer;color:#22c55e;margin:2px;padding:2px 6px;background:#0f172a;border-radius:4px;display:inline-block;" onclick="insertPh('{company_name}')">{company_name}</code>
  <code class="ph" style="cursor:pointer;color:#22c55e;margin:2px;padding:2px 6px;background:#0f172a;border-radius:4px;display:inline-block;" onclick="insertPh('{email}')">{email}</code>
  <code class="ph" style="cursor:pointer;color:#22c55e;margin:2px;padding:2px 6px;background:#0f172a;border-radius:4px;display:inline-block;" onclick="insertPh('{city}')">{city}</code>
  <code class="ph" style="cursor:pointer;color:#22c55e;margin:2px;padding:2px 6px;background:#0f172a;border-radius:4px;display:inline-block;" onclick="insertPh('{county}')">{county}</code>
  <code class="ph" style="cursor:pointer;color:#22c55e;margin:2px;padding:2px 6px;background:#0f172a;border-radius:4px;display:inline-block;" onclick="insertPh('{contact_greeting}')">{contact_greeting}</code>
  <code class="ph" style="cursor:pointer;color:#22c55e;margin:2px;padding:2px 6px;background:#0f172a;border-radius:4px;display:inline-block;" onclick="insertPh('{contact_person}')">{contact_person}</code>
  <code class="ph" style="cursor:pointer;color:#22c55e;margin:2px;padding:2px 6px;background:#0f172a;border-radius:4px;display:inline-block;" onclick="insertPh('{unsubscribe_url}')">{unsubscribe_url}</code>
  <br><br>
  <p style="color: #94a3b8; font-size: 12px; margin-bottom: 10px;">Database columns (any column = a placeholder):</p>
  <div id="db_placeholders" style="line-height: 2;">
    {% for col in db_columns %}
    <code class="ph" style="cursor:pointer;color:#38bdf8;margin:2px;padding:2px 6px;background:#0f172a;border:1px solid #334155;border-radius:4px;display:inline-block;" onclick="insertPh('{{'+'{{ col }}'+'}}')">{{'{'}}{{ col }}{{'}'}}</code>
    {% endfor %}
  </div>
  {% if not db_columns %}
  <p style="color:#ef4444;font-size:12px;">Could not read database columns. Any {column_name} matching your table columns will work.</p>
  {% endif %}
</div>
<script>
function insertPh(ph) {
  var ta = document.querySelector("textarea[name=content]");
  var pos = ta.selectionStart;
  var text = ta.value;
  ta.value = text.substring(0, pos) + ph + text.substring(pos);
  ta.selectionStart = ta.selectionEnd = pos + ph.length;
  ta.focus();
}
</script>"""

content = content.replace(old_placeholder_box, new_placeholder_box)

# 2. Update campaign_template() to fetch db columns and pass them to the template
old_render = """    return render_template_string(TEMPLATE_HTML,
        cfg=cfg, prefix=prefix, template_path=template_path, content=content,
        msg=msg, msg_type=msg_type,
        nav=nav_html(prefix, 'template'))"""

new_render = """    # Fetch actual column names from the database table
    db_columns = []
    try:
        db_cfg = cfg.get('db', {})
        tbl_cfg = cfg.get('tables', {})
        contacts_tbl = tbl_cfg.get('contacts', 'contacts')
        conn = psycopg2.connect(
            host=db_cfg.get('host', 'localhost'),
            dbname=db_cfg.get('dbname', 'interjob_master'),
            user=db_cfg.get('user', 'tudor'),
            password=db_cfg.get('password', 'tudor')
        )
        cur = conn.cursor()
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", (contacts_tbl,))
        db_columns = [row[0] for row in cur.fetchall() if row[0] not in ('id', 'campaign_status', 'last_contacted')]
        cur.close()
        conn.close()
    except Exception:
        pass

    return render_template_string(TEMPLATE_HTML,
        cfg=cfg, prefix=prefix, template_path=template_path, content=content,
        msg=msg, msg_type=msg_type, db_columns=db_columns,
        nav=nav_html(prefix, 'template'))"""

content = content.replace(old_render, new_render)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - Template editor now shows all DB columns as clickable placeholders")
