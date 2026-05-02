"""CSV upload blueprint - upload contacts, preview, create campaign from CSV."""
import csv, os, json, io
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint("upload", __name__)

@bp.route("/api/uploads")
def list_uploads():
    d = current_app.config["UPLOADS_DIR"]
    os.makedirs(d, exist_ok=True)
    files = []
    for f in sorted(os.listdir(d), reverse=True):
        if not f.endswith(".csv"): continue
        path = os.path.join(d, f)
        try:
            with open(path, encoding="utf-8-sig") as fh:
                rows = sum(1 for _ in fh) - 1
            size = os.path.getsize(path)
            files.append({"name": f, "rows": rows, "size": size, "path": path,
                "date": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")})
        except: pass
    return jsonify({"uploads": files})

@bp.route("/api/upload", methods=["POST"])
def upload_csv():
    if "file" not in request.files:
        return jsonify({"ok": False, "message": "No file"})
    f = request.files["file"]
    if not f.filename.endswith(".csv"):
        return jsonify({"ok": False, "message": "Must be .csv"})
    d = current_app.config["UPLOADS_DIR"]
    os.makedirs(d, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{ts}_{f.filename}"
    path = os.path.join(d, name)
    content = f.read().decode("utf-8-sig", errors="replace")
    # Validate email column
    reader = csv.DictReader(io.StringIO(content))
    cols = reader.fieldnames or []
    if "email" not in [c.lower().strip() for c in cols]:
        return jsonify({"ok": False, "message": f"No 'email' column. Found: {cols}"})
    # Count and dedup
    emails = set()
    for row in reader:
        e = (row.get("email") or row.get("Email") or "").strip().lower()
        if e and "@" in e: emails.add(e)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(content)
    return jsonify({"ok": True, "message": f"Uploaded {name}: {len(emails)} unique emails", "name": name, "path": path, "emails": len(emails)})

@bp.route("/api/upload/<name>/preview")
def preview_csv(name):
    d = current_app.config["UPLOADS_DIR"]
    path = os.path.join(d, name)
    if not os.path.exists(path):
        return jsonify({"ok": False, "message": "File not found"})
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= 20: break
            rows.append(row)
    return jsonify({"ok": True, "columns": cols, "rows": rows, "preview": 20})

@bp.route("/api/upload/<name>/campaign", methods=["POST"])
def create_from_csv(name):
    data = request.json or {}
    d = current_app.config["UPLOADS_DIR"]
    csv_path = os.path.join(d, name)
    if not os.path.exists(csv_path):
        return jsonify({"ok": False, "message": "CSV not found"})
    campaign_name = data.get("campaign_name", name.replace(".csv", "").replace(" ", "_"))
    sender_email = data.get("sender_email", "")
    sender_key = data.get("sender_key", "")
    template_dir = data.get("template_dir", "anofm")
    template_prefix = data.get("template_prefix", "elena_template")
    daily_limit = int(data.get("daily_limit", 50))
    configs_dir = current_app.config["CONFIGS_DIRS"][0]
    cfg_path = os.path.join(configs_dir, f"{campaign_name}.json")
    cfg = {
        "csv_file": csv_path,
        "campaign_name": campaign_name.upper(),
        "templates_dir": os.path.join(current_app.config["TEMPLATES_BASE"], template_dir) + "/",
        "sectors": {
            "MAIN": {
                "sender_key": sender_key,
                "sender_email": sender_email,
                "sender_name": data.get("sender_name", "InterJob Solutions"),
                "reply_to": data.get("reply_to", sender_email),
                "daily_limit": daily_limit,
                "delay_min": 360, "delay_max": 600,
                "enabled": False,
                "template_prefix": template_prefix,
                "filter_type": data.get("filter_type", ""),
                "business_hours": {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18},
            }
        }
    }
    json.dump(cfg, open(cfg_path, "w"), indent=2, ensure_ascii=False)
    return jsonify({"ok": True, "message": f"Campaign {campaign_name} created from {name}", "config": cfg_path})

@bp.route("/api/upload/<name>/delete", methods=["POST"])
def delete_csv(name):
    path = os.path.join(current_app.config["UPLOADS_DIR"], name)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"ok": True, "message": f"Deleted {name}"})
    return jsonify({"ok": False, "message": "Not found"})

from dashboard_shared import register_js
register_js("upload.js", """
async function load_upload(){
  const d=await api('/api/uploads');
  let h='<h2>Upload CSV</h2>';
  h+='<form id="uploadForm" enctype="multipart/form-data" style="margin:10px 0"><input type="file" id="csvFile" accept=".csv"> <button type="button" onclick="doUpload()">Upload</button></form>';
  h+='<h2>Uploaded Files ('+d.uploads.length+')</h2><table><thead><tr><th>File</th><th>Rows</th><th>Size</th><th>Date</th><th>Actions</th></tr></thead><tbody>';
  d.uploads.forEach(u=>{
    h+='<tr><td>'+u.name+'</td><td>'+u.rows+'</td><td>'+(u.size/1024).toFixed(1)+'KB</td><td>'+u.date+'</td>';
    h+='<td><button onclick="previewCSV(\\''+u.name+'\\')">Preview</button> <button onclick="createFromCSV(\\''+u.name+'\\')">Create Campaign</button> <button class="btn-red" onclick="delCSV(\\''+u.name+'\\')">Delete</button></td></tr>';
  });
  h+='</tbody></table><div id="csvPreview"></div>';
  document.getElementById('upload').innerHTML=h;
}
async function doUpload(){const f=document.getElementById('csvFile').files[0];if(!f){msg('Select file',true);return;}
  const fd=new FormData();fd.append('file',f);const r=await fetch(BASE+'/api/upload',{method:'POST',body:fd});const d=await r.json();msg(d.message,!d.ok);load_upload();}
async function previewCSV(name){const d=await api('/api/upload/'+name+'/preview');
  let h='<h2>Preview: '+name+'</h2><table><thead><tr>';d.columns.forEach(c=>h+='<th>'+c+'</th>');
  h+='</tr></thead><tbody>';d.rows.forEach(r=>{h+='<tr>';d.columns.forEach(c=>h+='<td>'+(r[c]||'')+'</td>');h+='</tr>';});
  h+='</tbody></table>';document.getElementById('csvPreview').innerHTML=h;}
async function createFromCSV(name){const se=prompt('Sender email (e.g. office@buildjobs.eu):');if(!se)return;
  const r=await post('/api/upload/'+name+'/campaign',{sender_email:se});msg(r.message,!r.ok);show('campaigns');}
async function delCSV(name){if(!confirm('Delete '+name+'?'))return;const r=await post('/api/upload/'+name+'/delete',{});msg(r.message,!r.ok);load_upload();}
""")
