import urllib.request, base64, json

url = 'https://agroevolution.com/wp-json/wp/v2/pages'
user = 'apaminerala'
passwd = 'unzQWjnSo2EEGA0cajdXoW2P'
token = base64.b64encode(f'{user}:{passwd}'.encode()).decode()

content = '''<!-- wp:paragraph -->
<p>Terenurile sportive degradate din comune și orașe mici pot fi <strong>reabilitate complet</strong> — de la demolarea suprafeței vechi până la instalarea gazonului sintetic nou — printr-un singur contract, cu un singur contractor.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Oferim servicii integrate de reabilitare pentru primării, școli și instituții publice: evaluare tehnică gratuită, proiect tehnic, execuție și recepție cu documentație completă pentru SEAP/SICAP.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Ce Includem într-un Contract de Reabilitare</h2>
<!-- /wp:heading -->

<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#4CAF50"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#4CAF50;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🔨 Demolare și Pregătire</h3><!-- /wp:heading -->
<!-- wp:list -->
<ul>
<li>✅ Demolare suprafață veche (asfalt, beton, pietriș)</li>
<li>✅ Evacuare materiale demolate</li>
<li>✅ Nivelare teren + compactare</li>
<li>✅ Sistem drenaj perimetral și subteran</li>
<li>✅ Strat de bază permeabilă (200mm+)</li>
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
<!-- wp:heading {"level":3} --><h3>🌿 Instalare Suprafață Nouă</h3><!-- /wp:heading -->
<!-- wp:list -->
<ul>
<li>✅ Gazon sintetic 40–50mm FIFA certified</li>
<li>✅ Infill nisip cuarț + granule SBR</li>
<li>✅ Marcare oficială (fotbal, baschet, handbal)</li>
<li>✅ Porți + plase + echipamente sport</li>
<li>✅ Garanție material 8–10 ani</li>
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
<!-- wp:heading {"level":3} --><h3>📄 Documentație și Recepție</h3><!-- /wp:heading -->
<!-- wp:list -->
<ul>
<li>✅ Proiect tehnic complet</li>
<li>✅ Autorizație de construire (asistență)</li>
<li>✅ Dosar SEAP/SICAP pentru achiziție publică</li>
<li>✅ Proces verbal recepție</li>
<li>✅ Certificare materiale (FIFA, ISO, CE)</li>
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->

<!-- wp:heading -->
<h2>Pachete de Reabilitare</h2>
<!-- /wp:heading -->

<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#ddd"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#ddd;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🏫 Teren Școală / Grădiniță</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>200–500 m²</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>150.000 – 400.000 lei + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p>Procedură simplificată SEAP. Ideal pentru comune și orașe mici. Fără licitație deschisă până la €130.000.</p><!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#4CAF50"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#4CAF50;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3,"style":{"color":{"text":"#4CAF50"}}} --><h3 style="color:#4CAF50">⚽ Teren Multisport Comunal</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>500–800 m²</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>400.000 – 900.000 lei + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p>Cel mai solicitat pachet. Înlocuire completă teren degradat + gazon sintetic nou + echipamente.</p><!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#ddd"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#ddd;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🏟️ Complex Sportiv Municipal</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>1.000–2.000 m²</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>800.000 – 2.000.000 lei + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p>Reabilitare integrală: fotbal + multisport + tenis. Proiect tehnic inclus, eligibil fonduri structurale UE.</p><!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->

<!-- wp:heading -->
<h2>De Ce să Alegeți un Contractor Integrat</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Un singur contract înseamnă <strong>un singur responsabil</strong> — de la demolare până la garanție. Fără coordonare între firme diferite, fără întârzieri, fără dispute de responsabilitate.</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul>
<li>✅ <strong>Un singur contract</strong> — procedură simplificată pentru primărie</li>
<li>✅ <strong>Termen fix de execuție</strong> — 30–60 zile în funcție de suprafață</li>
<li>✅ <strong>Garanție unitară</strong> — un singur interlocutor pentru orice problemă</li>
<li>✅ <strong>Documentație completă</strong> pentru SEAP și control financiar</li>
<li>✅ <strong>Experiență cu achiziții publice</strong> — înțelegem cerințele UAT-urilor</li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2>Cum Se Finanțează</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>
<li>💰 <strong>Buget local</strong> — cel mai rapid, procedură simplificată sub 130.000 €</li>
<li>💰 <strong>Fonduri structurale UE (FEDR/FSE+)</strong> — Programul Regional 2021–2027</li>
<li>💰 <strong>AFIR</strong> — pentru comune rurale cu infrastructură sportivă</li>
<li>💰 <strong>Parteneriat public-privat</strong> — sponsorizare locală + cofinanțare primărie</li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2>Cum Funcționează</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p><strong>1. Evaluare gratuită</strong> (fotografii + suprafață) → <strong>2. Ofertă detaliată</strong> în 48h → <strong>3. Proiect tehnic</strong> → <strong>4. Achiziție publică SEAP</strong> → <strong>5. Execuție 30–60 zile</strong> → <strong>6. Recepție + Garanție</strong></p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Cereți Evaluare Gratuită</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Trimiteți-ne câteva fotografii ale terenului și suprafața aproximativă. Facem o evaluare gratuită și vă trimitem o estimare de cost în 48 de ore.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>📧 <a href="mailto:tudor@agroevolution.com">tudor@agroevolution.com</a><br>📞 <a href="tel:+40750609594">+40 750 609 594</a></p>
<!-- /wp:paragraph -->'''

data = json.dumps({
    'title': 'Reabilitare Terenuri Sportive — Soluție Completă pentru Primării',
    'content': content,
    'status': 'publish',
    'slug': 'reabilitare-terenuri-sportive',
    'excerpt': 'Reabilitare completă terenuri sportive degradate pentru primării și școli — demolare, drenaj, gazon sintetic FIFA, documentație SEAP. Un singur contract, garanție 8-10 ani.'
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
