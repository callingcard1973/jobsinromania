#!/usr/bin/env python3
"""Campaign Manager - Assign senders + templates to campaigns via web UI.
Port 8097. Dark theme. Read/write campaign configs.
Usage: python3 campaign_manager.py [--port 8097]
"""
import json, glob, os, sys
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
CONFIGS = ["/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs",
           "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs"]
TEMPLATES_BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/templates"

BREVO_SENDERS = [
    ("buildjobs.eu","BREVO_BUILDJOBS_API_KEY",290),
    ("factoryjobs.eu","BREVO_FACTORYJOBS_API_KEY",290),
    ("warehouseworkers.eu","BREVO_WAREHOUSEWORKERS_API_KEY",290),
    ("interjob.ro","BREVO_INTERJOB_API_KEY",290),
    ("mivromania.info","BREVO_MIVROMANIA_API_KEY",290),
    ("mivromania.online","BREVO_MIVROMANIA_ONLINE_API_KEY",290),
    ("careworkers.eu","BREVO_CAREWORKERS_API_KEY",290),
    ("nepalezi.com","BREVO_NEPALEZI_API_KEY",290),
    ("expatsinromania.org","BREVO_EXPATSINROMANIA_API_KEY",290),
    ("horecaworkers2026.eu","BREVO_HORECAWORKERS2026_EU_API_KEY",290),
    ("horecaworkers2026.com","BREVO_HORECAWORKERS2026_COM_API_KEY",290),
    ("electricjobs.eu","BREVO_ELECTRICJOBS_API_KEY",290),
    ("meatworkers.eu","BREVO_MEATWORKERS_API_KEY",290),
    ("cumparlegume.com","BREVO_CUMPARLEGUME_API_KEY",290),
    ("agroevolution.com","BREVO_AGROEVOLUTION_API_KEY",290),
    ("seicarescu.com","BREVO_SEICARESCU_API_KEY",280),
    ("bppltd.co.uk","BREVO_BPPLTD_API_KEY",289),
    ("farmworkers.eu","BREVO_FARMWORKERS_API_KEY",290),
    ("mechanicjobs.eu","BREVO_MECHANICJOBS_API_KEY",290),
    ("horecaworkers.eu","BREVO_HORECAWORKERS_API_KEY",290),
]
A2_SENDERS = [d for d,_,_ in BREVO_SENDERS] + ["aluminumrecyclehub.com","internaltransfers.eu","cifn.eu"]
GMAIL_SENDERS = [
    "manpowersearchromania@gmail.com","pamintstrabun@gmail.com","casafaurbucuresti@gmail.com",
    "elena.manpower.dristor@gmail.com","cumparlegume@gmail.com","fructexportromania@gmail.com",
    "carteledeapel@gmail.com","vegetablesbucharest@gmail.com","expatsinromania@gmail.com",
    "icralbucuresti@gmail.com",
]
ZOHO_SENDERS = ["transport.work@zohomail.com","workers.europe@zohomail.eu"]

def load_configs():
    cfgs = []
    seen = set()
    for d in CONFIGS:
        for f in sorted(glob.glob(f"{d}/*.json")):
            real = os.path.realpath(f)
            if real in seen: continue
            seen.add(real)
            try:
                cfg = json.load(open(real))
                cfg["_file"] = real
                cfg["_name"] = os.path.basename(f).replace(".json","")
                cfgs.append(cfg)
            except: pass
    return cfgs

def load_templates():
    tpls = {}
    for d in glob.glob(f"{TEMPLATES_BASE}/*/"):
        name = os.path.basename(d.rstrip("/"))
        files = [os.path.basename(f) for f in glob.glob(f"{d}*.txt")]
        tpls[name] = files
    return tpls

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Campaign Manager</title><style>
*{box-sizing:border-box}body{font-family:sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:20px}
h1{color:#38bdf8;text-align:center}h2{color:#38bdf8;border-bottom:1px solid #334155;padding-bottom:8px}
table{width:100%;border-collapse:collapse;margin:15px 0}th,td{padding:8px 12px;border:1px solid #334155;text-align:left;font-size:13px}
th{background:#1e293b;color:#94a3b8}tr:hover{background:#1e293b}
select,input{background:#1e293b;color:#e2e8f0;border:1px solid #334155;padding:5px;border-radius:4px;font-size:12px}
button{background:#38bdf8;color:#0f172a;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:bold}
button:hover{background:#0ea5e9}.on{color:#22c55e;font-weight:bold}.off{color:#ef4444}
.badge{display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:bold}
.badge-brevo{background:#3b82f633;color:#60a5fa}.badge-gmail{background:#ef444433;color:#f87171}
.badge-a2{background:#22c55e33;color:#4ade80}.badge-zoho{background:#a855f733;color:#c084fc}
.msg{padding:10px;margin:10px 0;border-radius:6px;background:#22c55e33;color:#22c55e;display:none}
</style></head><body>
<h1>Campaign Manager</h1>
<div id="msg" class="msg"></div>
<h2>Campaigns & Sender Assignment</h2>
<table><thead><tr><th>Campaign</th><th>Sector</th><th>Status</th><th>Sender</th><th>Method</th><th>Limit/day</th><th>Template</th><th>Filter</th><th>Action</th></tr></thead>
<tbody id="rows"></tbody></table>
<h2>Available Senders</h2>
<table><thead><tr><th>Type</th><th>Sender</th><th>Max/day</th></tr></thead><tbody id="senders"></tbody></table>
<h2>Templates</h2>
<table><thead><tr><th>Directory</th><th>Files</th></tr></thead><tbody id="templates"></tbody></table>
<script>
async function load(){
  const r=await fetch('/api/campaigns');const d=await r.json();
  let html='';
  d.campaigns.forEach(c=>{
    c.sectors.forEach(s=>{
      const method=s.sender.includes('@gmail')?'gmail':s.sender.includes('zoho')?'zoho':'brevo';
      const badge=`<span class="badge badge-${method}">${method}</span>`;
      html+=`<tr>
        <td>${c.name}</td><td>${s.name}</td>
        <td class="${s.enabled?'on':'off'}">${s.enabled?'ON':'OFF'}</td>
        <td>${badge} ${s.sender}</td>
        <td><select id="method_${c.name}_${s.name}">
          <option ${method=='brevo'?'selected':''}>brevo</option>
          <option ${method=='gmail'?'selected':''}>gmail</option>
          <option ${method=='a2'?'selected':''}>a2</option>
          <option ${method=='zoho'?'selected':''}>zoho</option></select></td>
        <td><input type="number" value="${s.limit}" style="width:60px" id="limit_${c.name}_${s.name}"></td>
        <td><select id="tpl_${c.name}_${s.name}">${d.template_options}</select></td>
        <td>${s.filter_type||'-'}</td>
        <td><button onclick="save('${c.file}','${s.name}')">Save</button>
        <button onclick="toggle('${c.file}','${s.name}',${!s.enabled})" style="background:${s.enabled?'#ef4444':'#22c55e'}">${s.enabled?'OFF':'ON'}</button></td></tr>`;
    });
  });
  document.getElementById('rows').innerHTML=html;
  let sh='';d.senders.forEach(s=>{sh+=`<tr><td><span class="badge badge-${s.type}">${s.type}</span></td><td>${s.name}</td><td>${s.max}</td></tr>`;});
  document.getElementById('senders').innerHTML=sh;
  let th='';Object.entries(d.templates).forEach(([dir,files])=>{th+=`<tr><td>${dir}</td><td>${files.join(', ')}</td></tr>`;});
  document.getElementById('templates').innerHTML=th;
}
async function save(file,sector){
  const m=document.getElementById('method_'+file.split('/').pop().replace('.json','')+'_'+sector);
  // simplified - just reload for now
  show('Use CLI to change sender. Dashboard shows current state.');
}
async function toggle(file,sector,enable){
  const r=await fetch('/api/toggle',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({file,sector,enable})});
  const d=await r.json();show(d.message);load();
}
function show(msg){const e=document.getElementById('msg');e.textContent=msg;e.style.display='block';setTimeout(()=>e.style.display='none',3000);}
load();
</script></body></html>"""

@app.route("/")
def index():
    return Response(HTML, content_type="text/html")

@app.route("/api/campaigns")
def api_campaigns():
    cfgs = load_configs()
    tpls = load_templates()
    campaigns = []
    for cfg in cfgs:
        sectors = []
        for s, c in cfg.get("sectors", {}).items():
            sectors.append({
                "name": s, "enabled": c.get("enabled", False),
                "sender": c.get("sender_email", "?"),
                "limit": c.get("daily_limit", 0),
                "filter_type": c.get("filter_type", ""),
                "template_prefix": c.get("template_prefix", "template"),
            })
        if sectors:
            campaigns.append({"name": cfg["_name"], "file": cfg["_file"], "sectors": sectors})
    tpl_opts = "".join(f'<option value="{d}/{f}">{d}/{f}</option>' for d, files in tpls.items() for f in files)
    senders = [{"type":"brevo","name":f"office@{d}","max":m} for d,_,m in BREVO_SENDERS]
    senders += [{"type":"gmail","name":g,"max":40} for g in GMAIL_SENDERS]
    senders += [{"type":"zoho","name":z,"max":250} for z in ZOHO_SENDERS]
    senders += [{"type":"a2","name":f"office@{d}","max":500} for d in A2_SENDERS[:5]]
    return jsonify({"campaigns": campaigns, "templates": tpls, "template_options": tpl_opts, "senders": senders})

@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    data = request.json
    f, sector, enable = data["file"], data["sector"], data["enable"]
    cfg = json.load(open(f))
    if sector in cfg.get("sectors", {}):
        cfg["sectors"][sector]["enabled"] = enable
        json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)
        return jsonify({"ok": True, "message": f"{sector} {'enabled' if enable else 'disabled'}"})
    return jsonify({"ok": False, "message": "Sector not found"})

if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port")+1]) if "--port" in sys.argv else 8097
    app.run(host="0.0.0.0", port=port)
