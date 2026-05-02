"""Campaign CRUD blueprint - list, create, toggle, send, stop."""
import json, glob, os, subprocess, signal
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint("campaigns", __name__)
ACTIVE_PIDS = {}  # campaign -> pid

def load_configs():
    cfgs, seen = [], set()
    for d in current_app.config["CONFIGS_DIRS"]:
        for f in sorted(glob.glob(f"{d}/*.json")):
            real = os.path.realpath(f)
            if real in seen: continue
            seen.add(real)
            try:
                cfg = json.load(open(real))
                cfg["_file"] = real
                cfg["_name"] = os.path.basename(f).replace(".json", "")
                cfgs.append(cfg)
            except: pass
    return cfgs

def load_templates():
    tpls = {}
    base = current_app.config["TEMPLATES_BASE"]
    for d in sorted(glob.glob(f"{base}/*/")):
        name = os.path.basename(d.rstrip("/"))
        files = sorted([os.path.basename(f) for f in glob.glob(f"{d}*.txt")])
        if files: tpls[name] = files
    return tpls

@bp.route("/api/campaigns")
def list_campaigns():
    cfgs = load_configs()
    tpls = load_templates()
    campaigns = []
    for cfg in cfgs:
        sectors = []
        for s, c in cfg.get("sectors", {}).items():
            se = c.get("sender_email", "?")
            method = "gmail" if "@gmail" in se else "zoho" if "zoho" in se else "a2" if c.get("sender_type") == "a2" else "brevo"
            sectors.append({"name": s, "enabled": c.get("enabled", False), "sender": se,
                "sender_key": c.get("sender_key", ""), "limit": c.get("daily_limit", 0),
                "filter_type": c.get("filter_type", ""), "template_prefix": c.get("template_prefix", "template"),
                "method": method, "delay_min": c.get("delay_min", 0), "delay_max": c.get("delay_max", 0),
                "reply_to": c.get("reply_to", ""), "sender_name": c.get("sender_name", ""),
                "bh": c.get("business_hours", {}).get("enabled", False)})
        if sectors:
            campaigns.append({"name": cfg["_name"], "file": cfg["_file"],
                "campaign_name": cfg.get("campaign_name", cfg["_name"]),
                "db": cfg.get("db", {}).get("dbname", ""),
                "csv": cfg.get("csv_file", ""),
                "templates_dir": cfg.get("templates_dir", ""), "sectors": sectors})
    tpl_list = [{"dir": d, "files": f} for d, f in tpls.items()]
    return jsonify({"campaigns": campaigns, "templates": tpl_list})

@bp.route("/api/campaigns/<name>/toggle", methods=["POST"])
def toggle_sector(name):
    data = request.json
    sector, enable = data.get("sector"), data.get("enable")
    cfgs = load_configs()
    for cfg in cfgs:
        if cfg["_name"] == name and sector in cfg.get("sectors", {}):
            cfg["sectors"][sector]["enabled"] = enable
            clean = {k: v for k, v in cfg.items() if not k.startswith("_")}
            json.dump(clean, open(cfg["_file"], "w"), indent=2, ensure_ascii=False)
            return jsonify({"ok": True, "message": f"{sector} {'ON' if enable else 'OFF'}"})
    return jsonify({"ok": False, "message": "Not found"})

@bp.route("/api/campaigns/<name>/update", methods=["POST"])
def update_sector(name):
    data = request.json
    sector = data.get("sector")
    cfgs = load_configs()
    for cfg in cfgs:
        if cfg["_name"] != name or sector not in cfg.get("sectors", {}): continue
        s = cfg["sectors"][sector]
        for key in ["sender_email", "sender_key", "sender_name", "reply_to",
                     "daily_limit", "delay_min", "delay_max", "template_prefix", "filter_type"]:
            if key in data:
                s[key] = int(data[key]) if key in ("daily_limit", "delay_min", "delay_max") else data[key]
        if "method" in data:
            s["sender_type"] = "gmail_only" if data["method"] == "gmail" else data["method"] if data["method"] in ("zoho", "a2") else ""
        clean = {k: v for k, v in cfg.items() if not k.startswith("_")}
        json.dump(clean, open(cfg["_file"], "w"), indent=2, ensure_ascii=False)
        return jsonify({"ok": True, "message": f"{sector} updated"})
    return jsonify({"ok": False, "message": "Not found"})

@bp.route("/api/campaigns/create", methods=["POST"])
def create_campaign():
    data = request.json
    name = data.get("name", "").strip().replace(" ", "_").lower()
    if not name: return jsonify({"ok": False, "message": "Name required"})
    configs_dir = current_app.config["CONFIGS_DIRS"][0]
    fpath = os.path.join(configs_dir, f"{name}.json")
    if os.path.exists(fpath): return jsonify({"ok": False, "message": "Already exists"})
    cfg = {
        "db": {"host": "localhost", "dbname": data.get("db", "anofm"), "user": "tudor", "password": "tudor"},
        "campaign_name": data.get("campaign_name", name.upper()),
        "templates_dir": os.path.join(current_app.config["TEMPLATES_BASE"], data.get("template_dir", "anofm")) + "/",
        "null_status_is_pending": True, "gov_domains": [], "exclude_nace": [], "exclude_sources": [],
        "tables": {"contacts": data.get("table", "jobs"), "send_log": "send_log", "dnc": "dnc",
            "col_email": "email", "col_name": "company_name", "col_company": "company_name",
            "col_city": "city", "col_campaign_status": "campaign_status", "col_last_contacted": "last_contacted",
            "col_employees": "id", "col_sector": "sector", "col_sector_name": "sector",
            "col_org_number": "email", "col_tier": "sector", "col_caen": "sector",
            "sl_sender": "sender", "sl_company": "sector", "sl_tpl_num": "method", "sl_msg_id": "status"},
        "sectors": {
            "MAIN": {
                "filter": data.get("filter", "1=1"),
                "sender_key": data.get("sender_key", ""),
                "sender_email": data.get("sender_email", ""),
                "sender_name": data.get("sender_name", ""),
                "reply_to": data.get("reply_to", ""),
                "daily_limit": int(data.get("daily_limit", 50)),
                "delay_min": 360, "delay_max": 600, "enabled": False,
                "template_prefix": data.get("template_prefix", "template"),
                "business_hours": {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18},
            }
        }
    }
    if data.get("csv_file"):
        cfg["csv_file"] = data["csv_file"]
    json.dump(cfg, open(fpath, "w"), indent=2, ensure_ascii=False)
    return jsonify({"ok": True, "message": f"Created {name}", "file": fpath})

@bp.route("/api/campaigns/<name>/send", methods=["POST"])
def send_campaign(name):
    data = request.json
    sector = data.get("sector", "MAIN")
    limit = data.get("limit", 50)
    cfgs = load_configs()
    for cfg in cfgs:
        if cfg["_name"] != name: continue
        py = current_app.config["PYTHON"]
        if cfg.get("csv_file"):
            script = current_app.config["QUICK_SCRIPT"]
            se = cfg["sectors"].get(sector, {}).get("sender_email", "")
            tpl_dir = cfg.get("templates_dir", "")
            tpl_prefix = cfg["sectors"].get(sector, {}).get("template_prefix", "template")
            tpl = os.path.join(tpl_dir, f"{tpl_prefix}1.txt")
            sender_domain = se.split("@")[1] if "@" in se and "gmail" not in se else se
            cmd = [py, "-u", script, "--csv", cfg["csv_file"], "--sender", sender_domain,
                   "--template", tpl, "--limit", str(limit), "--delay", "360"]
        else:
            script = current_app.config["SENDER_SCRIPT"]
            cmd = [py, script, "--config", cfg["_file"], "--sector", sector,
                   "--limit", str(limit), "--template", "1"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        key = f"{name}_{sector}"
        ACTIVE_PIDS[key] = proc.pid
        return jsonify({"ok": True, "message": f"Started {key} PID {proc.pid}", "pid": proc.pid})
    return jsonify({"ok": False, "message": "Campaign not found"})

@bp.route("/api/campaigns/<name>/stop", methods=["POST"])
def stop_campaign(name):
    sector = request.json.get("sector", "MAIN")
    key = f"{name}_{sector}"
    pid = ACTIVE_PIDS.pop(key, None)
    if pid:
        try: os.kill(pid, signal.SIGTERM)
        except: pass
        return jsonify({"ok": True, "message": f"Stopped {key} PID {pid}"})
    return jsonify({"ok": False, "message": f"No active PID for {key}"})

@bp.route("/api/template", methods=["GET", "POST"])
def template_editor():
    tpl_dir = request.args.get("dir", "") or (request.json or {}).get("dir", "")
    tpl_file = request.args.get("file", "") or (request.json or {}).get("file", "")
    base = current_app.config["TEMPLATES_BASE"]
    path = os.path.join(base, tpl_dir, tpl_file)
    if not path.startswith(base): return jsonify({"ok": False, "message": "Invalid path"})
    if request.method == "GET":
        if os.path.exists(path):
            return jsonify({"ok": True, "content": open(path, encoding="utf-8").read(), "path": path})
        return jsonify({"ok": False, "message": f"Not found: {path}"})
    else:
        content = (request.json or {}).get("content", "")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(content)
        return jsonify({"ok": True, "message": f"Saved {tpl_dir}/{tpl_file}"})

@bp.route("/api/campaigns/active")
def active_sends():
    alive = {}
    for key, pid in list(ACTIVE_PIDS.items()):
        try:
            os.kill(pid, 0)
            alive[key] = pid
        except:
            del ACTIVE_PIDS[key]
    return jsonify({"active": alive})

# Register frontend JS
from dashboard_shared import register_js
register_js("campaigns.js", """
async function load_campaigns(){
  const d=await api('/api/campaigns');const act=await api('/api/campaigns/active');
  let h='<h2>Campaigns ('+d.campaigns.length+')</h2>';
  h+='<button onclick="showCreate()" class="btn-green" style="margin-bottom:10px">+ New Campaign</button>';
  h+='<div id="createForm" style="display:none;margin:10px 0;padding:15px;background:var(--sf);border-radius:8px"></div>';
  h+='<table><thead><tr><th>Campaign</th><th>Sector</th><th>ON</th><th>Sender</th><th>Type</th><th>/day</th><th>Template</th><th>Filter</th><th>BH</th><th>Actions</th></tr></thead><tbody>';
  d.campaigns.forEach(c=>{c.sectors.forEach(s=>{
    const key=c.name+'_'+s.name;const running=act.active[key];
    const badge='<span class="badge badge-'+s.method+'">'+s.method+'</span>';
    h+='<tr><td>'+c.campaign_name+'</td><td>'+s.name+'</td>';
    h+='<td class="'+(s.enabled?'on':'off')+'">'+(s.enabled?'ON':'OFF')+'</td>';
    h+='<td>'+badge+' '+s.sender+'</td><td>'+s.method+'</td><td>'+s.limit+'</td>';
    const tdir=c.templates_dir.split('/templates/')[1]||'';const tfile=s.template_prefix+'1.txt';
    h+='<td><a href="#" onclick="viewTpl(\\''+tdir.replace(/\\/$/,'')+'\\',\\''+tfile+'\\')">'+s.template_prefix+'</a></td><td>'+s.filter_type+'</td><td>'+(s.bh?'8-18':'24h')+'</td>';
    h+='<td><button onclick="toggle(\\''+c.name+'\\',\\''+s.name+'\\','+(!s.enabled)+')" class="'+(s.enabled?'btn-red':'btn-green')+'">'+(s.enabled?'OFF':'ON')+'</button> ';
    if(running) h+='<button onclick="stopC(\\''+c.name+'\\',\\''+s.name+'\\')">Stop</button>';
    h+='</td></tr>';
  });});
  h+='</tbody></table>';
  document.getElementById('campaigns').innerHTML=h;
}
async function toggle(name,sector,enable){const r=await post('/api/campaigns/'+name+'/toggle',{sector,enable});msg(r.message,!r.ok);load_campaigns();}
async function stopC(name,sector){const r=await post('/api/campaigns/'+name+'/stop',{sector});msg(r.message,!r.ok);load_campaigns();}
function showCreate(){document.getElementById('createForm').style.display='block';
  document.getElementById('createForm').innerHTML=`<h2>New Campaign</h2>
<div style="display:grid;grid-template-columns:120px 1fr;gap:8px;max-width:700px">
<label>1. Name:</label><input id="nc_name" placeholder="campaign_name" style="width:200px">
<label>2. CSV:</label><input type="file" id="nc_csv" accept=".csv">
<label>3. Sender:</label><input id="nc_sender" placeholder="office@domain.eu" style="width:250px">
<label>4. Limit/day:</label><input id="nc_limit" type="number" value="50" style="width:80px">
<label>5. Template:</label><div><select id="nc_tpl_existing"><option value="">-- write new below --</option></select>
<textarea id="nc_tpl_new" rows="8" style="margin-top:5px" placeholder="Subject: Muncitori disponibili&#10;&#10;Buna ziua,&#10;..."></textarea></div>
</div><br><button onclick="createC()" class="btn-green">Create Campaign</button> <button onclick="document.getElementById('createForm').style.display='none'">Cancel</button>`;
  api('/api/campaigns').then(d=>{const sel=document.getElementById('nc_tpl_existing');d.templates.forEach(t=>{t.files.forEach(f=>{const o=document.createElement('option');o.value=t.dir+'/'+f;o.text=t.dir+'/'+f;sel.appendChild(o);});});});}
async function createC(){
  const name=document.getElementById('nc_name').value;if(!name){msg('Name required',true);return;}
  const se=document.getElementById('nc_sender').value;const limit=document.getElementById('nc_limit').value;
  const csvFile=document.getElementById('nc_csv').files[0];
  const existing=document.getElementById('nc_tpl_existing').value;
  const newTpl=document.getElementById('nc_tpl_new').value;
  let csvPath='';
  if(csvFile){const fd=new FormData();fd.append('file',csvFile);
    const u=await fetch(BASE+'/api/upload',{method:'POST',body:fd});const ud=await u.json();
    if(!ud.ok){msg(ud.message,true);return;} csvPath=ud.path;msg(ud.message);}
  let tpl_dir='anofm',tpl_prefix='template';
  if(existing){tpl_dir=existing.split('/')[0];tpl_prefix=existing.split('/')[1].replace(/\d+\.txt$/,'');}
  else if(newTpl){tpl_dir=name;tpl_prefix='template';
    await post('/api/template',{dir:name,file:'template1.txt',content:newTpl});}
  const r=await post('/api/campaigns/create',{name,sender_email:se,daily_limit:limit,template_dir:tpl_dir,template_prefix:tpl_prefix,csv_file:csvPath});
  msg(r.message,!r.ok);load_campaigns();}
async function viewTpl(dir,file){const r=await api('/api/template?dir='+dir+'&file='+file);
  if(!r.ok){msg(r.message,true);return;}
  const el=document.getElementById('createForm');el.style.display='block';
  el.innerHTML='<h2>Template: '+dir+'/'+file+'</h2><textarea id="tplContent" rows="20">'+r.content.replace(/</g,'&lt;')+'</textarea><br><button onclick="saveTpl(\\''+dir+'\\',\\''+file+'\\')">Save</button> <button onclick="document.getElementById(\\'createForm\\').style.display=\\'none\\'">Close</button>';}
async function saveTpl(dir,file){const c=document.getElementById('tplContent').value;const r=await post('/api/template',{dir,file,content:c});msg(r.message,!r.ok);}
""")
