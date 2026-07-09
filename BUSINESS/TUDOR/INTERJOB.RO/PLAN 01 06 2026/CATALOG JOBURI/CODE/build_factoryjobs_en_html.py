import json, re
from pathlib import Path
from datetime import datetime

SECTOR_EN={"productie":"Manufacturing","constructii":"Construction","agricultura":"Agriculture","vanzari":"Sales","it":"IT","horeca":"Hospitality","sanatate":"Healthcare","transport":"Transport & Logistics","altul":"Other"}
KEEP_UPPER={"SRL","S.R.L.","SA","S.A.","LTD","LLC","PFA","II","SNC","SCS","GMBH","BV","AG"}
TITLE_FIX={
 "manipulant marfuri":"Goods Handler",
 "muncitor necalificat la asamblarea, montarea pieselor":"Unskilled Worker - Parts Assembly",
 "muncitor necalificat în industria confectiilor":"Unskilled Worker - Garment Industry",
 "muncitor necalificat la ambalarea produselor solide si semisolide":"Unskilled Worker - Packaging",
 "electrician de întretinere si reparatii":"Maintenance & Repair Electrician",
 "consilier/expert/inspector/referent/economist în gestiunea economica":"Economic Management Specialist",
 "masinist la instalatiile de turbine hidraulice":"Hydraulic Turbine Operator",
 "electrician exploatare centrale si statii electrice":"Power Plant & Substation Electrician",
 "conducător auto transport rutier de mărfuri":"Freight Truck Driver",
 "sef birou/serviciu financiar-contabilitate":"Head of Finance & Accounting",
 "femeie de serviciu":"Cleaner","îngrijitor cladiri":"Building Caretaker","programator ajutor":"Junior Programmer",
 "confectioner tâmplarie din aluminiu si mase plastice":"Aluminium & PVC Joinery Fabricator",
 "sofer de autoturisme si camionete":"Car & Van Driver","masinist la masini de ambalat":"Packaging Machine Operator",
 "electrician echipamente electrice si energetice":"Electrical & Power Equipment Electrician",
 "masinist la masini pentru terasamente (ifronist)":"Earthmoving Machine Operator (Backhoe)",
 "confectioner produse textile":"Textile Products Maker","încarcator-descarcator":"Loader-Unloader",
 "instalator apa, canal":"Water & Sewage Plumber","legator manual (în poligrafie si ateliere speciale)":"Manual Bookbinder (Printing)",
 "sef formatie în industria de masini si echipamente":"Team Leader - Machinery & Equipment",
 "lucrator comercial":"Retail Worker","auditor intern în sectorul public":"Internal Auditor (Public Sector)",
 "sef serviciu":"Department Head","sef serviciu resurse umane":"HR Department Head",
 "consilier/expert/inspector/referent/economist în economie generala":"General Economy Specialist",
 "specialist în domeniul securitatii si sanatatii în munca":"Occupational Health & Safety Specialist",
 "strungar la masini de alezat":"Boring Machine Turner","primitor-distribuitor materiale si scule":"Materials & Tools Storekeeper",
 "agent servicii client":"Customer Service Agent","muncitor necalificat în metalurgie":"Unskilled Worker - Metallurgy",
 "inginer confectii piele si înlocuitori":"Leather Goods Engineer","croitor-stantator piese încaltaminte":"Footwear Cutter",
 "cusator piese din piele si înlocuitori":"Leather Goods Stitcher","pregatitor piese încaltaminte":"Footwear Parts Preparer",
 "coordonator în materie de securitate si sanatate în munca (studii superioare)":"Health & Safety Coordinator",
 "vulcanizator de produse industriale din cauciuc":"Industrial Rubber Vulcanizer",
 "preparator la confectionarea produselor industriale din cauciuc":"Industrial Rubber Products Preparer",
 "masinist la masini mobile pentru transporturi interioare":"Mobile Internal Transport Operator",
 "croitor pentru încaltaminte si articole tehnice din cauciuc":"Footwear & Rubber Goods Cutter",
 "specialist în domeniul calitatii":"Quality Specialist","broder la gherghef":"Embroiderer",
 "confectioner articole din piele si înlocuitori":"Leather Goods Maker","sofer automacaragiu":"Crane Truck Driver",
 "masinist la masini speciale fara aschiere":"Non-cutting Machine Operator",
 "sef schimb":"Shift Supervisor","sef sectie":"Section Manager","strungar universal":"Universal Lathe Operator",
}
def en_title(j):
    raw=(j.get("title_en") or j.get("title_ro") or "Position").strip()
    return TITLE_FIX.get(raw.lower(),raw)
def en_sector(s): return SECTOR_EN.get((s or "").strip().lower(),(s or "Other").title())
def en_location(loc):
    parts=[p.strip() for p in (loc or "").split(">") if p.strip()]
    if not parts: return "Romania"
    county=parts[0].title()
    city=re.sub(r"^MUNICIPIUL\s+|^ORAS(UL)?\s+|^COMUNA\s+|^SAT(UL)?\s+","",parts[-1],flags=re.I).strip().title()
    return f"{city}, {county}, Romania" if city and city.lower()!=county.lower() else f"{county}, Romania"
def en_company(c): return " ".join(t if t.upper() in KEEP_UPPER else t.title() for t in (c or "").split())
def en_salary(s):
    s=(s or "").strip(); return "On request" if (not s or "N/A" in s.upper()) else s
def transform(jobs):
    return [{"ref":j.get("ref",""),"title":en_title(j),"company":en_company(j.get("company","")),
             "location":en_location(j.get("location","")),"sector":en_sector(j.get("sector","")),
             "positions":j.get("positions",1),"salary":en_salary(j.get("salary","")),
             "posted":j.get("posted",""),"apply_url":j.get("apply_url","https://interjob.ro/apply.html"),
             "urgent":bool(j.get("urgent"))} for j in jobs]

CSS="* { margin:0; padding:0; box-sizing:border-box; } body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif; background:#f0f2f5; color:#222; min-height:100vh; font-size:15px; line-height:1.6; } .header { background:#fff; border-bottom:1px solid #e0e4ea; padding:28px 20px; text-align:center; } .header-title { font-size:32px; font-weight:800; color:#0f2942; } .header-sub { font-size:16px; color:#666; margin-top:8px; } .header-stats { margin-top:12px; font-size:13px; color:#888; } .controls { background:#fff; padding:16px 20px; border-bottom:1px solid #e0e4ea; display:flex; gap:12px; align-items:center; justify-content:center; flex-wrap:wrap; } .controls input { padding:10px 16px; border:1px solid #d0d6dd; border-radius:6px; font-size:14px; width:320px; max-width:100%; } .controls input:focus,.controls select:focus { outline:none; border-color:#f5a000; } .controls select { padding:10px 12px; border:1px solid #d0d6dd; border-radius:6px; font-size:14px; background:#fff; cursor:pointer; } .count-info { font-size:13px; color:#888; font-weight:600; } .count-info span { color:#0f2942; font-size:16px; } .content { max-width:1160px; margin:0 auto; padding:24px 16px; width:100%; } .jobs-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; } .job-card { background:#fff; border:1px solid #e0e4ea; border-radius:8px; padding:16px; display:flex; flex-direction:column; gap:8px; } .job-card:hover { box-shadow:0 4px 12px rgba(0,0,0,.12); border-color:#f5a000; } .job-ref { font-family:Consolas,Monaco,monospace; font-size:11px; color:#c77000; font-weight:700; text-transform:uppercase; } .job-title { font-size:16px; font-weight:700; color:#0f2942; } .job-company { font-size:13px; font-weight:600; color:#0f2942; } .job-location { font-size:12px; color:#666; } .job-meta { font-size:12px; color:#666; padding-top:8px; border-top:1px solid #e0e4ea; } .job-sector { display:inline-block; background:#fff3e0; color:#c77000; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; } .badge-urgent { display:inline-block; background:#ffe3e3; color:#c0392b; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:700; margin-left:6px; } .job-salary { font-size:14px; font-weight:700; color:#f5a000; margin-top:8px; } .job-posted { font-size:11px; color:#aaa; margin-top:8px; } .apply-btn { background:#f5a000; color:#fff; border-radius:4px; padding:10px 16px; font-weight:600; text-decoration:none; display:inline-block; margin-top:12px; text-align:center; } .apply-btn:hover { background:#e69500; } .footer { background:#0f2942; color:rgba(255,255,255,.7); text-align:center; padding:24px 20px; margin-top:40px; } .footer a { color:#f5a000; text-decoration:none; font-weight:600; } @media (max-width:768px){ .controls{flex-direction:column;align-items:stretch;} .controls input,.controls select{width:100%;} .jobs-grid{grid-template-columns:1fr;} }"

JS_TMPL=r"""
const allJobs = __JOBS__;
let filteredJobs = [...allJobs];
document.getElementById('total').textContent = allJobs.length;
document.getElementById('count').textContent = allJobs.length;
document.getElementById('stats').textContent = allJobs.length + ' production sector jobs available';
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML;}
function renderJobs(){
  var grid=document.getElementById('jobs-grid'); grid.innerHTML='';
  filteredJobs.forEach(function(job){
    var card=document.createElement('div'); card.className='job-card';
    var posted=''; if(job.posted){var d=new Date(job.posted); if(!isNaN(d)) posted=d.toLocaleDateString('en-GB',{year:'numeric',month:'short',day:'numeric'});}
    var urgent=job.urgent?'<span class="badge-urgent">URGENT</span>':'';
    card.innerHTML='<div class="job-ref">'+esc(job.ref)+'</div>'+
      '<div class="job-title">'+esc(job.title)+'</div>'+
      '<div class="job-company">'+esc(job.company)+'</div>'+
      '<div class="job-location">📍 '+esc(job.location)+'</div>'+
      '<div class="job-meta"><span class="job-sector">'+esc(job.sector)+'</span>'+urgent+'<span style="margin-left:8px;">'+esc(job.positions)+' position(s)</span></div>'+
      '<div class="job-salary">Salary: '+esc(job.salary)+'</div>'+
      '<div class="job-posted">Posted: '+posted+'</div>'+
      '<a href="'+esc(job.apply_url)+'" class="apply-btn" target="_blank">APPLY NOW</a>';
    grid.appendChild(card);
  });
  document.getElementById('count').textContent=filteredJobs.length;
}
function filterJobs(){
  var t=document.getElementById('search').value.toLowerCase();
  filteredJobs=allJobs.filter(function(j){return (j.title+' '+j.company+' '+j.location+' '+j.sector).toLowerCase().indexOf(t)>=0;});
  sortJobs(); renderJobs();
}
function sortJobs(){
  var parts=document.getElementById('sort').value.split('-'),field=parts[0],dir=parts[1];
  filteredJobs.sort(function(a,b){
    var av,bv;
    if(field==='posted'){av=new Date(a.posted).getTime();bv=new Date(b.posted).getTime();}
    else{av=(a[field]||'').toString().toLowerCase();bv=(b[field]||'').toString().toLowerCase();}
    if(av<bv)return dir==='asc'?-1:1; if(av>bv)return dir==='asc'?1:-1; return 0;
  });
}
document.getElementById('search').addEventListener('input',filterJobs);
document.getElementById('sort').addEventListener('change',function(){sortJobs();renderJobs();});
renderJobs();
"""

def generate(jobs_path, out_path, title):
    raw=json.loads(Path(jobs_path).read_text(encoding="utf-8"))
    jobs=transform(raw if isinstance(raw,list) else raw.get("data") or raw.get("jobs") or [])
    js=JS_TMPL.replace("__JOBS__", json.dumps(jobs, ensure_ascii=True))
    html=('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
      '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
      '<title>'+title+' - Job Catalog (English)</title>\n<style>'+CSS+'</style>\n</head>\n<body>\n'
      '<div class="header"><div class="header-title">'+title+'</div>'
      '<div class="header-sub">Industrial &amp; Production Jobs in Romania</div>'
      '<div class="header-stats" id="stats">Loading...</div></div>\n'
      '<div class="controls"><input type="text" id="search" placeholder="Search by title, company, location, sector...">'
      '<select id="sort"><option value="posted-desc">Newest First</option><option value="posted-asc">Oldest First</option>'
      '<option value="title-asc">Title A-Z</option><option value="company-asc">Company A-Z</option>'
      '<option value="location-asc">Location A-Z</option></select>'
      '<div class="count-info"><span id="count">0</span> / <span id="total">0</span> jobs</div></div>\n'
      '<div class="content"><div class="jobs-grid" id="jobs-grid"></div></div>\n'
      '<div class="footer"><p>'+title+' - Job Catalog</p><p>Updated: '+datetime.now().strftime("%d %b %Y")+'</p>'
      '<p>Apply: <a href="https://interjob.ro/apply.html">interjob.ro</a></p></div>\n'
      '<script>'+js+'</script>\n</body>\n</html>')
    Path(out_path).write_text(html, encoding="utf-8")
    return jobs, out_path

JOBS="/sessions/zealous-jolly-pasteur/mnt/PLAN 01 06 2026/CATALOG JOBURI/DATA/factoryjobs_jobs.json"
OUT="/sessions/zealous-jolly-pasteur/mnt/PLAN 01 06 2026/CATALOG JOBURI/FOR CLIENTS/factoryjobs_catalog_EN.html"
jobs,out=generate(JOBS,OUT,"FactoryJobs.eu")
import os
print("Generated:",out,"|",os.path.getsize(out)//1024,"KB |",len(jobs),"jobs")
ro=set("de si și la cu pentru fara muncitor femeie sofer vanzator lucrator ajutor serviciu ingrijitor manipulant confectioner croitor instalator masinist necalificat sef cladiri strungar cusator broder vulcanizator".split())
def looks_ro(t):
    tl=t.lower(); return bool(re.search(r"[ăâîșțş]",tl)) or any(w in ro for w in re.findall(r"[a-zăâîșțţ]+",tl))
left=sorted({j["title"] for j in jobs if looks_ro(j["title"])})
print("still Romanian titles:",len(left))
for t in left: print("  -",t)
