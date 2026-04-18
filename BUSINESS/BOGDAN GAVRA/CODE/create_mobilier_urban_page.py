import urllib.request, base64, json

url = 'https://agroevolution.com/wp-json/wp/v2/pages'
token = base64.b64encode(b'apaminerala:unzQWjnSo2EEGA0cajdXoW2P').decode()

content = '''<!-- wp:paragraph -->
<p>Oferim <strong>mobilier urban complet</strong> pentru primării, parcuri, spații publice și instituții — bănci, coșuri de gunoi, pergole, stâlpi de iluminat solar, suporturi biciclete și jardiniere. Livrare din stoc sau la comandă, cu documentație pentru achiziție publică SEAP.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Produse Disponibile</h2>
<!-- /wp:heading -->

<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#4CAF50"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#4CAF50;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🪑 Bănci de Parc</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>800 – 2.500 RON + TVA / buc</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul>
<li>✅ Oțel vopsit electrostatic sau inox</li>
<li>✅ Șipci lemn tratat sau plastic reciclat</li>
<li>✅ Cu/fără spătar, cu/fără brațe</li>
<li>✅ Ancorare în beton inclusă</li>
<li>✅ Garanție 5 ani structură</li>
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#2196F3"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#2196F3;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🗑️ Coșuri de Gunoi</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>400 – 1.200 RON + TVA / buc</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul>
<li>✅ Capacitate 30–120 litri</li>
<li>✅ Oțel zincat sau inox</li>
<li>✅ Cu capac antivânt / antivandalism</li>
<li>✅ Montare pe stâlp sau fixare sol</li>
<li>✅ Colectare selectivă (opțional 2 camere)</li>
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#FF9800"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#FF9800;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3} --><h3>⛺ Pergole și Foișoare</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>5.000 – 18.000 RON + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul>
<li>✅ Oțel vopsit sau aluminiu</li>
<li>✅ Acoperiș policarbonat / șindrilă / tablă</li>
<li>✅ Dimensiuni la comandă</li>
<li>✅ Opțional: iluminat integrat LED</li>
<li>✅ Fundație + montaj inclus</li>
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->

<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#ddd"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#ddd;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>💡 Stâlpi Iluminat Solar</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>2.000 – 6.000 RON + TVA / buc</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul>
<li>✅ Panou solar + baterie LiFePO4</li>
<li>✅ LED 20–80W, autonomie 3+ nopți</li>
<li>✅ Senzor crepuscular + telecomandă</li>
<li>✅ Zero cablu electric — montaj rapid</li>
<li>✅ Garanție 3 ani</li>
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#ddd"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#ddd;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🚲 Suporturi Biciclete</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>300 – 900 RON + TVA / buc</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul>
<li>✅ Oțel zincat sau inox</li>
<li>✅ 2–10 locuri per modul</li>
<li>✅ Ancorare beton sau șuruburi</li>
<li>✅ Design modern sau clasic</li>
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#ddd"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#ddd;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🌸 Jardiniere și Ghivece Urbane</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>500 – 3.000 RON + TVA / buc</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul>
<li>✅ Beton fibrat, oțel sau lemn</li>
<li>✅ Dimensiuni variate (50cm – 2m)</li>
<li>✅ Cu/fără sistem irigare</li>
<li>✅ Rezistente îngheț</li>
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->

<!-- wp:heading -->
<h2>Pachete Complete pentru Primării</h2>
<!-- /wp:heading -->

<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#4CAF50"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#4CAF50;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🏘️ Pachet Sat / Comună</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p>10 bănci + 10 coșuri + 1 pergolă + 5 stâlpi solar</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>35.000 – 55.000 RON + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p>Procedură simplificată SEAP. Sub pragul de licitație deschisă.</p><!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#2196F3"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#2196F3;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3,"style":{"color":{"text":"#2196F3"}}} --><h3 style="color:#2196F3">🏙️ Pachet Oraș Mic</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p>30 bănci + 30 coșuri + 3 pergole + 15 stâlpi solar + suporturi biciclete</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>120.000 – 180.000 RON + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p>Documentație completă pentru licitație SEAP inclusă.</p><!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#ddd"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#ddd;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🏛️ Pachet Personalizat</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p>Orice combinație de produse, orice cantitate.</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>Ofertă la cerere în 24h</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p>Proiect de amplasament inclus gratuit pentru comenzi peste 20.000 RON.</p><!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->

<!-- wp:heading -->
<h2>De Ce Mobilier Urban de Calitate</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>
<li>✅ <strong>Durabilitate</strong> — materiale tratate anticoroziv, rezistente 10+ ani în exterior</li>
<li>✅ <strong>Conformitate</strong> — produse CE, fișe tehnice pentru dosarul SEAP</li>
<li>✅ <strong>Livrare rapidă</strong> — produse standard din stoc, livrare 5–10 zile</li>
<li>✅ <strong>Montaj inclus</strong> — echipă proprie, fără subcontractori</li>
<li>✅ <strong>Garanție</strong> — 2–5 ani funcție de produs</li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2>Eligibil Fonduri Europene</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Mobilierul urban poate fi achiziționat prin <strong>buget local</strong>, <strong>Programul Regional FEDR 2021–2027</strong> (reabilitare spații publice) sau <strong>PNRR Componenta 10</strong> (infrastructură locală). Vă ajutăm cu specificațiile tehnice pentru caietul de sarcini.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Solicitați Ofertă</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Spuneți-ne ce produse și cantități doriți. Răspundem cu ofertă detaliată în 24 de ore, inclusiv fotografii, fișe tehnice și prețuri finale cu transport.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>📧 <a href="mailto:tudor@agroevolution.com">tudor@agroevolution.com</a><br>📞 <a href="tel:+40750609594">+40 750 609 594</a></p>
<!-- /wp:paragraph -->'''

data = json.dumps({
    'title': 'Mobilier Urban pentru Primării — Bănci, Coșuri, Pergole, Iluminat Solar',
    'content': content,
    'status': 'publish',
    'slug': 'mobilier-urban',
    'excerpt': 'Mobilier urban complet pentru primării și spații publice: bănci, coșuri gunoi, pergole, stâlpi iluminat solar. Livrare rapidă, documentație SEAP, montaj inclus.'
}).encode('utf-8')

req = urllib.request.Request(url, data=data, headers={
    'Authorization': f'Basic {token}',
    'Content-Type': 'application/json; charset=utf-8'
})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print('OK — Page ID:', result['id'])
    print('URL:', result['link'])
    print('Edit:', f"https://agroevolution.com/wp-admin/post.php?post={result['id']}&action=edit")
except Exception as e:
    print('ERROR:', e)
