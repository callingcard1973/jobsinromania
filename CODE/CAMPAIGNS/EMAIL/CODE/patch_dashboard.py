#!/usr/bin/env python3
"""Patch dashboard.py to add CSV upload support."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

# 1. Add campaign_csv + european_funds to databases list
old_db = '''    databases = [
        {'name': 'romania_emails', 'tables': 5, 'desc': 'ANOFM Romanian contacts'},
        {'name': 'interjob_master', 'tables': 12, 'desc': 'Master DB (EU companies, tenders)'},
        {'name': 'norway_emails', 'tables': 4, 'desc': 'Norway 16-sector campaign'},
        {'name': 'denmark_emails', 'tables': 3, 'desc': 'Denmark contacts'},
        {'name': 'email_sender', 'tables': 3, 'desc': 'Send tracking DB'},
    ]'''
new_db = '''    databases = [
        {'name': 'campaign_csv', 'tables': 0, 'desc': 'CSV uploads (auto-created tables)'},
        {'name': 'european_funds', 'tables': 4, 'desc': 'EU Funds beneficiari (15,969 projects)'},
        {'name': 'romania_emails', 'tables': 5, 'desc': 'ANOFM Romanian contacts'},
        {'name': 'interjob_master', 'tables': 12, 'desc': 'Master DB (EU companies, tenders)'},
        {'name': 'norway_emails', 'tables': 4, 'desc': 'Norway 16-sector campaign'},
        {'name': 'denmark_emails', 'tables': 3, 'desc': 'Denmark contacts'},
        {'name': 'email_sender', 'tables': 3, 'desc': 'Send tracking DB'},
    ]'''
content = content.replace(old_db, new_db)

# 2. Change form to multipart
content = content.replace(
    '<form method="POST" action="/api/new-campaign">',
    '<form method="POST" action="/api/new-campaign" enctype="multipart/form-data">'
)

# 3. Add CSV upload UI after database section
old_section = '''  <div class="row" style="margin-top: 15px;">
    <div class="form-group">
      <label>Contacts Table</label>
      <input type="text" name="contacts_table" value="contacts">
    </div>
    <div class="form-group">
      <label>Send Log Table</label>
      <input type="text" name="send_log_table" value="send_log">
    </div>
  </div>
</div>

<!-- Step 3'''

new_section = '''  <div class="row" style="margin-top: 15px;">
    <div class="form-group">
      <label>Contacts Table</label>
      <input type="text" name="contacts_table" value="contacts" id="contacts_table">
    </div>
    <div class="form-group">
      <label>Send Log Table</label>
      <input type="text" name="send_log_table" value="send_log">
    </div>
  </div>
  <div style="margin-top:15px; padding:15px; background:#0f172a; border-radius:8px; border:1px dashed #38bdf8;">
    <h4 style="color:#38bdf8; margin:0 0 10px;">Or Upload CSV</h4>
    <input type="file" name="csv_file" id="csv_file" accept=".csv,.tsv,.txt" style="margin-bottom:10px;">
    <div id="csv_preview" style="display:none; margin-top:10px;">
      <p style="color:#22c55e;"><span id="csv_rows">0</span> rows found. Map your columns:</p>
      <div id="csv_columns"></div>
      <input type="hidden" name="csv_filename" id="csv_filename">
      <input type="hidden" name="csv_delimiter" id="csv_delimiter">
      <input type="hidden" name="csv_col_map" id="csv_col_map">
    </div>
  </div>
</div>
<script>
document.getElementById("csv_file").addEventListener("change", function() {
  var fd = new FormData();
  fd.append("csv_file", this.files[0]);
  fetch("/api/csv-preview", {method: "POST", body: fd})
    .then(r => r.json())
    .then(d => {
      if (d.error) { alert(d.error); return; }
      document.getElementById("csv_rows").textContent = d.rows;
      document.getElementById("csv_filename").value = d.file;
      document.getElementById("csv_delimiter").value = d.delimiter;
      var radios = document.querySelectorAll("input[name=database]");
      for (var r of radios) { if (r.value === "campaign_csv") r.checked = true; }
      var html = "<table><tr><th>CSV Column</th><th>Use as (template variable)</th></tr>";
      d.columns.forEach(function(col) {
        var clean = col.toLowerCase().replace(/[^a-z0-9]/g, "_");
        html += "<tr><td><code>" + col + "</code></td><td>";
        html += "<input type='text' class='col-map' data-csv='" + col + "' value='" + clean + "' ";
        html += "style='width:200px;padding:6px;background:#1e293b;border:1px solid #334155;color:#e2e8f0;border-radius:4px;'>";
        html += " <small style='color:#94a3b8;'>use as {" + clean + "} in template</small></td></tr>";
      });
      html += "</table><p style='color:#94a3b8;margin-top:10px;font-size:12px;'>Column names become template variables: {column_name}</p>";
      document.getElementById("csv_columns").innerHTML = html;
      document.getElementById("csv_preview").style.display = "block";
      var tbl = document.getElementById("csv_file").files[0].name.replace(/\\.csv$/i,"").replace(/[^a-zA-Z0-9_]/g,"_").toLowerCase();
      document.getElementById("contacts_table").value = tbl;
    });
});
document.querySelector("form").addEventListener("submit", function() {
  var map = {};
  document.querySelectorAll(".col-map").forEach(function(s) {
    var csv_col = s.getAttribute("data-csv");
    map[csv_col] = s.value;
  });
  document.getElementById("csv_col_map").value = JSON.stringify(map);
});
</script>

<!-- Step 3'''
content = content.replace(old_section, new_section)

# 4. Update api_new_campaign to handle CSV import
old_handler = '''        if not campaign_name or not url_prefix:
            return redirect('/new?msg=Campaign+name+and+URL+prefix+required&msg_type=error')'''
new_handler = '''        if not campaign_name or not url_prefix:
            return redirect('/new?msg=Campaign+name+and+URL+prefix+required&msg_type=error')

        # Handle CSV upload if present
        csv_filename = request.form.get('csv_filename', '')
        csv_delimiter = request.form.get('csv_delimiter', ',')
        csv_col_map_str = request.form.get('csv_col_map', '{}')
        if csv_filename:
            import json as _json
            col_map = _json.loads(csv_col_map_str) if csv_col_map_str else {}
            import requests as _req
            resp = _req.post('http://localhost:8096/api/csv-import', json={
                'file': csv_filename,
                'table_name': contacts_table,
                'col_map': col_map,
                'delimiter': csv_delimiter,
            })
            if resp.status_code == 200 and resp.json().get('ok'):
                database = 'campaign_csv'
                # Find the email column from mapping
                for csv_col, db_col in col_map.items():
                    if db_col == 'email':
                        break'''
content = content.replace(old_handler, new_handler)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - CSV upload added to dashboard")
