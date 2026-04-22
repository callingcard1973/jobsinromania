<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Harta Terenuri Agricole Romania - AgroEvolution</title>
<meta name="description" content="Harta interactiva cu terenuri agricole de vanzare in Romania. Date oficiale MADR.">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#f5f5f5}
#header{background:linear-gradient(135deg,#2d5a3d,#4a7c59);color:#fff;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
#header h1{font-size:1.4rem}
#header .stats{display:flex;gap:16px;font-size:.85rem}
#header .stats span{background:rgba(255,255,255,.15);padding:4px 10px;border-radius:12px}
#controls{background:#fff;padding:10px 20px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;border-bottom:1px solid #ddd;font-size:.85rem}
#controls select,#controls input{padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85rem}
#controls button{padding:5px 14px;background:#2d5a3d;color:#fff;border:none;border-radius:4px;cursor:pointer}
#controls button:hover{background:#4a7c59}
#map{height:calc(100vh - 110px);width:100%}
.legend{background:#fff;padding:10px 14px;border-radius:6px;box-shadow:0 2px 6px rgba(0,0,0,.3);font-size:.8rem;line-height:1.8}
.legend i{width:14px;height:14px;display:inline-block;border-radius:50%;margin-right:6px;vertical-align:middle}
.popup-content{font-size:.85rem;line-height:1.6;min-width:200px}
.popup-content h3{color:#2d5a3d;margin-bottom:4px;font-size:1rem}
.popup-content .price{font-size:1.1rem;font-weight:bold;color:#c0392b}
.popup-content .detail{color:#555}
@media(max-width:600px){
  #header h1{font-size:1rem}
  #header .stats{font-size:.75rem}
  #controls{padding:6px 10px;gap:6px}
  #map{height:calc(100vh - 130px)}
}
</style>
</head>
<body>
<div id="header">
  <h1>Terenuri Agricole Romania</h1>
  <div class="stats">
    <span id="stat-total">Se incarca...</span>
    <span id="stat-ha">-</span>
    <span id="stat-visible">-</span>
  </div>
</div>
<div id="controls">
  <label>Judet: <select id="f-judet"><option value="">Toate</option></select></label>
  <label>Categorie: <select id="f-cat"><option value="">Toate</option></select></label>
  <label>Min ha: <input id="f-min-ha" type="number" step="0.1" min="0" style="width:70px"></label>
  <label>Max pret/ha: <input id="f-max-ph" type="number" step="1000" min="0" style="width:90px" placeholder="RON"></label>
  <button onclick="applyFilters()">Filtreaza</button>
  <button onclick="resetFilters()" style="background:#888">Reset</button>
</div>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
const CAT_COLORS={ARABIL:'#27ae60',FANEATA:'#2980b9',PASUNI:'#e67e22',VII:'#8e44ad',LIVEZI:'#c0392b','PEPINIERE POMICOLE':'#795548','PAJISTI PERMANENTE':'#00897b','ALTE CULTURI':'#78909c',NECUNOSCUT:'#999'};
const map=L.map('map').setView([45.9,25.0],7);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{attribution:'� CARTO | Date MADR',maxZoom:18,subdomains:'abcd'}).addTo(map);
const legend=L.control({position:'bottomright'});
legend.onAdd=function(){const d=L.DomUtil.create('div','legend');d.innerHTML='<b>Categorie</b><br>'+Object.entries(CAT_COLORS).filter(([k])=>!['NECUNOSCUT','PAJISTI PERMANENTE','ALTE CULTURI','PEPINIERE POMICOLE'].includes(k)).map(([k,v])=>`<i style="background:${v}"></i>${k}`).join('<br>');return d};
legend.addTo(map);

let allData=[],markers=L.markerClusterGroup({maxClusterRadius:50,spiderfyOnMaxZoom:true,showCoverageOnHover:false});

function fmt(n){return n?n.toLocaleString('ro-RO'):'—'}
function fmtP(n){return n?n.toLocaleString('ro-RO',{maximumFractionDigits:0})+' RON':'—'}

function makePopup(d){
  const ph=d.ha>0?d.p/d.ha:0;
  return `<div class="popup-content">
    <h3>${d.l}, ${d.j}</h3>
    <div class="price">${fmtP(d.p)}</div>
    <div class="detail">Suprafata: <b>${d.ha?d.ha.toFixed(2)+' ha':'—'}</b></div>
    <div class="detail">Pret/ha: <b>${ph>0?fmtP(ph):'—'}</b></div>
    <div class="detail">Categorie: ${d.c||'—'}</div>
    <div class="detail">Termen: ${d.t||'—'}</div>
  </div>`;
}

function makeMarker(d){
  const color=CAT_COLORS[d.c]||CAT_COLORS.NECUNOSCUT;
  const r=Math.min(8,Math.max(4,d.ha?Math.sqrt(d.ha)*2:4));
  return L.circleMarker([d.lat,d.lng],{radius:r,fillColor:color,color:'#fff',weight:1,opacity:.9,fillOpacity:.7}).bindPopup(makePopup(d));
}

function updateStats(data){
  const totalHa=data.reduce((s,d)=>s+(d.ha||0),0);
  document.getElementById('stat-total').textContent=data.length+' terenuri';
  document.getElementById('stat-ha').textContent=fmt(Math.round(totalHa))+' ha';
  document.getElementById('stat-visible').textContent='Afisate: '+data.length;
}

function populateFilters(){
  const judete=[...new Set(allData.map(d=>d.j))].sort();
  const cats=[...new Set(allData.map(d=>d.c).filter(Boolean))].sort();
  const fj=document.getElementById('f-judet');
  judete.forEach(j=>{const o=document.createElement('option');o.value=j;o.textContent=j;fj.appendChild(o)});
  const fc=document.getElementById('f-cat');
  cats.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;fc.appendChild(o)});
}

function applyFilters(){
  const judet=document.getElementById('f-judet').value;
  const cat=document.getElementById('f-cat').value;
  const minHa=parseFloat(document.getElementById('f-min-ha').value)||0;
  const maxPh=parseFloat(document.getElementById('f-max-ph').value)||Infinity;
  let filtered=allData.filter(d=>{
    if(judet&&d.j!==judet)return false;
    if(cat&&d.c!==cat)return false;
    if(d.ha<minHa)return false;
    if(d.ha>0&&d.p/d.ha>maxPh&&maxPh<Infinity)return false;
    return true;
  });
  renderMarkers(filtered);
}

function resetFilters(){
  document.getElementById('f-judet').value='';
  document.getElementById('f-cat').value='';
  document.getElementById('f-min-ha').value='';
  document.getElementById('f-max-ph').value='';
  renderMarkers(allData);
}

function renderMarkers(data){
  markers.clearLayers();
  data.forEach(d=>{if(d.lat&&d.lng)markers.addLayer(makeMarker(d))});
  updateStats(data);
}

fetch('/land_map_data.json').then(r=>r.json()).then(data=>{
  // Filter out extreme outliers (>100M RON/ha)
  allData=data.filter(d=>!(d.ha>0&&d.p/d.ha>100000000));
  populateFilters();
  renderMarkers(allData);
  map.addLayer(markers);
}).catch(e=>{
  document.getElementById('stat-total').textContent='Eroare la incarcare date';
  console.error(e);
});
</script>
<!-- Lead capture: floating button + modal for harta.php -->
<style>
#lead-btn {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 9999;
  background: #2d7a2d;
  color: #fff;
  border: none;
  border-radius: 28px;
  padding: 14px 22px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0,0,0,0.28);
  transition: background 0.2s;
}
#lead-btn:hover { background: #235e23; }
#lead-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.55);
  z-index: 10000;
  align-items: center;
  justify-content: center;
}
#lead-overlay.active { display: flex; }
#lead-card {
  background: #fff;
  border-radius: 12px;
  max-width: 420px;
  width: 94%;
  padding: 32px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.22);
  position: relative;
}
#lead-card h2 { margin: 0 0 20px; font-size: 20px; color: #1a4a1a; }
#lead-card label { display: block; font-size: 13px; font-weight: 600; margin: 12px 0 4px; color: #444; }
#lead-card input, #lead-card select {
  width: 100%; box-sizing: border-box;
  padding: 9px 11px; border: 1px solid #ccc;
  border-radius: 7px; font-size: 14px;
}
#lead-submit {
  margin-top: 20px; width: 100%;
  background: #2d7a2d; color: #fff;
  border: none; border-radius: 8px;
  padding: 13px; font-size: 15px;
  font-weight: 700; cursor: pointer;
  transition: background 0.2s;
}
#lead-submit:hover { background: #235e23; }
#lead-close {
  position: absolute; top: 14px; right: 18px;
  background: none; border: none;
  font-size: 22px; cursor: pointer; color: #888;
}
#lead-success {
  display: none; text-align: center;
  padding: 20px 0; color: #2d7a2d;
  font-size: 16px; font-weight: 600;
}
</style>

<button id="lead-btn">🌾 Vreau să cumpăr teren</button>

<div id="lead-overlay" role="dialog" aria-modal="true">
  <div id="lead-card">
    <button id="lead-close" aria-label="Închide">&times;</button>
    <h2>🌾 Caută teren agricol</h2>
    <div id="lead-form-wrap">
      <form id="lead-form" novalidate>
        <label for="lf-email">Email *</label>
        <input type="email" id="lf-email" name="email" required placeholder="adresa@email.com">

        <label for="lf-tel">Telefon</label>
        <input type="tel" id="lf-tel" name="telefon" placeholder="07xxxxxxxx">

        <label for="lf-judet">Județ</label>
        <select id="lf-judet" name="judet">
          <option value="">— Oricare —</option>
          <option>Alba</option><option>Arad</option><option>Argeș</option>
          <option>Bacău</option><option>Bihor</option><option>Bistrița-Năsăud</option>
          <option>Botoșani</option><option>Brăila</option><option>Brașov</option>
          <option>Buzău</option><option>Călărași</option><option>Caraș-Severin</option>
          <option>Cluj</option><option>Constanța</option><option>Covasna</option>
          <option>Dâmbovița</option><option>Dolj</option><option>Galați</option>
          <option>Giurgiu</option><option>Gorj</option><option>Harghita</option>
          <option>Hunedoara</option><option>Ialomița</option><option>Iași</option>
          <option>Ilfov</option><option>Maramureș</option><option>Mehedinți</option>
          <option>Mureș</option><option>Neamț</option><option>Olt</option>
          <option>Prahova</option><option>Sălaj</option><option>Satu Mare</option>
          <option>Sibiu</option><option>Suceava</option><option>Teleorman</option>
          <option>Timiș</option><option>Tulcea</option><option>Vâlcea</option>
          <option>Vaslui</option><option>Vrancea</option>
        </select>

        <label for="lf-tip">Tip teren</label>
        <select id="lf-tip" name="tip_teren">
          <option value="">— Oricare —</option>
          <option>ARABIL</option><option>PĂȘUNI</option><option>VII</option>
          <option>LIVEZI</option><option>PĂDURI</option>
        </select>

        <label for="lf-sup">Suprafață minimă (ha)</label>
        <input type="number" id="lf-sup" name="suprafata_min" min="0.1" step="0.1" placeholder="ex. 5">

        <label for="lf-pret">Preț maxim (RON/ha)</label>
        <input type="number" id="lf-pret" name="pret_max" min="0" step="100" placeholder="ex. 15000">

        <button type="submit" id="lead-submit">Trimite cererea</button>
      </form>
    </div>
    <div id="lead-success">✓ Am primit cererea ta. Te contactăm în curând.</div>
  </div>
</div>

<script>
(function(){
  var btn=document.getElementById('lead-btn');
  var overlay=document.getElementById('lead-overlay');
  var closeBtn=document.getElementById('lead-close');
  var form=document.getElementById('lead-form');
  var formWrap=document.getElementById('lead-form-wrap');
  var success=document.getElementById('lead-success');

  btn.addEventListener('click',function(){ overlay.classList.add('active'); });
  closeBtn.addEventListener('click',function(){ overlay.classList.remove('active'); });
  overlay.addEventListener('click',function(e){ if(e.target===overlay) overlay.classList.remove('active'); });

  form.addEventListener('submit',function(e){
    e.preventDefault();
    var email=document.getElementById('lf-email').value.trim();
    if(!email){ document.getElementById('lf-email').focus(); return; }
    var payload={
      sursa:'harta',
      email:email,
      telefon:document.getElementById('lf-tel').value.trim(),
      judet:document.getElementById('lf-judet').value,
      tip_teren:document.getElementById('lf-tip').value,
      suprafata_min:document.getElementById('lf-sup').value,
      pret_max:document.getElementById('lf-pret').value
    };
    fetch('/save_lead.php',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){
        formWrap.style.display='none';
        success.style.display='block';
        setTimeout(function(){ overlay.classList.remove('active'); formWrap.style.display=''; success.style.display='none'; form.reset(); },2000);
      }
    }).catch(function(){ alert('Eroare la trimitere. Încearcă din nou.'); });
  });
})();
</script>


<style>
#alert-btn {
  position: fixed; bottom: 24px; right: 220px; z-index: 1000;
  background: #f5a623; color: #fff; border: none; border-radius: 8px;
  padding: 14px 22px; font-size: 15px; font-weight: 700;
  cursor: pointer; box-shadow: 0 4px 16px rgba(0,0,0,0.22);
  white-space: nowrap;
}
#alert-btn:hover { background: #d48b10; }
#alert-overlay {
  display: none; position: fixed; inset: 0; z-index: 2000;
  background: rgba(0,0,0,0.55); align-items: center; justify-content: center;
}
#alert-overlay.active { display: flex; }
#alert-card {
  background: #fff; border-radius: 14px; padding: 36px 32px 28px;
  width: 100%; max-width: 420px; position: relative;
  box-shadow: 0 8px 40px rgba(0,0,0,0.18);
}
#alert-card h2 { margin: 0 0 6px; font-size: 20px; color: #1a1a1a; }
#alert-card p { margin: 0 0 20px; font-size: 14px; color: #666; }
#alert-close {
  position: absolute; top: 14px; right: 18px;
  background: none; border: none; font-size: 22px; cursor: pointer; color: #888;
}
#alert-form label { display: block; font-size: 13px; color: #444; margin-bottom: 4px; margin-top: 14px; }
#alert-form input, #alert-form select {
  width: 100%; padding: 10px 12px; border: 1px solid #ddd;
  border-radius: 6px; font-size: 14px; box-sizing: border-box;
}
#alert-submit {
  margin-top: 22px; width: 100%; padding: 13px;
  background: #f5a623; color: #fff; border: none; border-radius: 7px;
  font-size: 15px; font-weight: 700; cursor: pointer;
}
#alert-submit:hover { background: #d48b10; }
#alert-msg {
  display: none; text-align: center;
  padding: 20px 0; color: #2d7a2d;
  font-size: 16px; font-weight: 600;
}
</style>

<button id="alert-btn">🔔 Alertă preț</button>

<div id="alert-overlay" role="dialog" aria-modal="true">
  <div id="alert-card">
    <button id="alert-close" aria-label="Închide">&times;</button>
    <h2>🔔 Alertă preț teren</h2>
    <p>Te anunțăm când apare teren la prețul tău.</p>
    <form id="alert-form" novalidate>
      <label for="af-email">Email *</label>
      <input type="email" id="af-email" name="email" required placeholder="adresa@email.com">

      <label for="af-judet">Județ</label>
      <select id="af-judet" name="judet">
        <option value="">— Oricare —</option>
        <option>Alba</option><option>Arad</option><option>Argeș</option>
        <option>Bacău</option><option>Bihor</option><option>Bistrița-Năsăud</option>
        <option>Botoșani</option><option>Brăila</option><option>Brașov</option>
        <option>Buzău</option><option>Călărași</option><option>Caraș-Severin</option>
        <option>Cluj</option><option>Constanța</option><option>Covasna</option>
        <option>Dâmbovița</option><option>Dolj</option><option>Galați</option>
        <option>Giurgiu</option><option>Gorj</option><option>Harghita</option>
        <option>Hunedoara</option><option>Ialomița</option><option>Iași</option>
        <option>Ilfov</option><option>Maramureș</option><option>Mehedinți</option>
        <option>Mureș</option><option>Neamț</option><option>Olt</option>
        <option>Prahova</option><option>Sălaj</option><option>Satu Mare</option>
        <option>Sibiu</option><option>Suceava</option><option>Teleorman</option>
        <option>Timiș</option><option>Tulcea</option><option>Vâlcea</option>
        <option>Vaslui</option><option>Vrancea</option>
      </select>

      <label for="af-cat">Tip teren</label>
      <select id="af-cat" name="categorie">
        <option value="">— Oricare —</option>
        <option>ARABIL</option><option>PĂȘUNI</option><option>LIVEZI</option>
      </select>

      <label for="af-pret">Preț maxim RON/ha *</label>
      <input type="number" id="af-pret" name="pret_max_ha" required min="1" step="100" placeholder="ex. 5000">

      <button type="submit" id="alert-submit">Activează alerta</button>
    </form>
    <div id="alert-msg">✓ Verifică emailul pentru confirmare!</div>
  </div>
</div>

<script>
(function(){
  var btn=document.getElementById('alert-btn');
  var overlay=document.getElementById('alert-overlay');
  var closeBtn=document.getElementById('alert-close');
  var form=document.getElementById('alert-form');
  var msg=document.getElementById('alert-msg');

  btn.addEventListener('click',function(){ overlay.classList.add('active'); });
  closeBtn.addEventListener('click',function(){ overlay.classList.remove('active'); });
  overlay.addEventListener('click',function(e){ if(e.target===overlay) overlay.classList.remove('active'); });

  form.addEventListener('submit',function(e){
    e.preventDefault();
    var email=document.getElementById('af-email').value.trim();
    var pret=document.getElementById('af-pret').value;
    if(!email){ document.getElementById('af-email').focus(); return; }
    if(!pret){ document.getElementById('af-pret').focus(); return; }
    var payload={
      email:email,
      judet:document.getElementById('af-judet').value,
      categorie:document.getElementById('af-cat').value,
      pret_max_ha:parseFloat(pret)
    };
    fetch('/subscribe_alert.php',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.ok||d.status==='ok'||d.success){
        form.style.display='none';
        msg.style.display='block';
      } else {
        alert(d.message||'Eroare. Încearcă din nou.');
      }
    }).catch(function(){ alert('Eroare la trimitere. Încearcă din nou.'); });
  });
})();
</script>

</body>
</html>
