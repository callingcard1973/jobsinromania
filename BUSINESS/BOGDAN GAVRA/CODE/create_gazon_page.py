import urllib.request, urllib.parse, base64, json

url = 'https://agroevolution.com/wp-json/wp/v2/pages'
user = 'apaminerala'
passwd = 'unzQWjnSo2EEGA0cajdXoW2P'
token = base64.b64encode(f'{user}:{passwd}'.encode()).decode()

content = '''<!-- wp:paragraph -->
<p>Oferim soluții complete de <strong>gazon sintetic</strong> pentru terenuri sportive, școli, primării și spații publice — de la consultanță și proiectare până la instalare și garanție extinsă.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Lucrăm cu producători certificați FIFA, cu experiență în livrări în toată Europa. Transport rapid din Turcia (3–5 zile), materiale cu garanție 8–10 ani.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Pachete Terenuri Sportive</h2>
<!-- /wp:heading -->

<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#4CAF50"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#4CAF50;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3,"style":{"color":{"text":"#4CAF50"}}} -->
<h3 style="color:#4CAF50">🏃 Multisport Mic</h3>
<!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>~400 m²</strong> | 20×20m</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>€12.000 – €18.000 + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul><li>✅ Gazon sintetic 40mm multisport</li>
<li>✅ Marcare teren fotbal/baschet/handbal</li>
<li>✅ Strat drenaj + geotextil</li>
<li>✅ Garanție 8 ani material</li>
<li>✅ Documentație tehnică inclusă</li></ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#2196F3"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#2196F3;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3,"style":{"color":{"text":"#2196F3"}}} -->
<h3 style="color:#2196F3">⚽ Teren Fotbal Standard</h3>
<!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>~800 m²</strong> | 40×20m</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>€22.000 – €30.000 + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul><li>✅ Gazon sintetic 50mm FIFA Quality</li>
<li>✅ Infill nisip cuarț + granule SBR</li>
<li>✅ Marcare oficială fotbal</li>
<li>✅ Porți + plase incluse</li>
<li>✅ Iluminat perimetral opțional</li>
<li>✅ Garanție 10 ani material</li></ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"2px","style":"solid","color":"#FF9800"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#FF9800;border-style:solid;border-width:2px;padding:20px">
<!-- wp:heading {"level":3,"style":{"color":{"text":"#FF9800"}}} -->
<h3 style="color:#FF9800">🏆 Complex Sportiv Premium</h3>
<!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>1.200–2.000 m²</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>€45.000 – €80.000 + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul><li>✅ Gazon FIFA Quality Pro</li>
<li>✅ Fotbal + tenis + multisport</li>
<li>✅ Tribună/bănci spectatori</li>
<li>✅ Iluminat LED sportiv</li>
<li>✅ Împrejmuire completă</li>
<li>✅ Proiect tehnic + autorizație</li>
<li>✅ Management complet proiect</li></ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->

<!-- wp:heading -->
<h2>Gazon Decorativ pentru Primării și Spații Publice</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Soluție ideală pentru parcuri, curți instituționale, zone pietonale și spații verzi care necesită aspect impecabil tot anul fără costuri de întreținere.</p>
<!-- /wp:paragraph -->

<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#ddd"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#ddd;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🌿 Gazon Peisagistic</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>20–35mm pile height</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>55–90 RON/m² + TVA instalat</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul><li>✅ Aspect natural, verde intens</li>
<li>✅ Rezistent UV, fără decolorare</li>
<li>✅ Zero întreținere sezonieră</li>
<li>✅ Drenaj rapid</li></ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:group {"style":{"border":{"width":"1px","style":"solid","color":"#ddd"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="border-color:#ddd;border-style:solid;border-width:1px;padding:20px">
<!-- wp:heading {"level":3} --><h3>🏫 Curți Școli și Grădinițe</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>Suprafețe 200–1.500 m²</strong></p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><strong>€8.000 – €35.000 + TVA</strong></p><!-- /wp:paragraph -->
<!-- wp:list -->
<ul><li>✅ Compatibil cu echipamente joacă</li>
<li>✅ Amortizare căderi (HIC certificat)</li>
<li>✅ Fără alergeni, fără noroi</li>
<li>✅ Curățare ușoară</li></ul>
<!-- /wp:list -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->

<!-- wp:heading -->
<h2>Cum Funcționează</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p><strong>1. Consultanță gratuită</strong> → <strong>2. Ofertă personalizată</strong> → <strong>3. Contract + Avans</strong> → <strong>4. Livrare materiale</strong> → <strong>5. Instalare</strong> → <strong>6. Recepție + Garanție</strong></p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Certificări și Standarde</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Lucrăm exclusiv cu producători care dețin: <strong>FIFA Quality</strong> | <strong>FIFA Quality Pro</strong> | <strong>ISO 9001</strong> | <strong>CE Mark</strong> | <strong>World Rugby Compliant</strong></p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Eligibil Fonduri Europene și PNRR</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Proiectele de terenuri sportive pot fi finanțate prin <strong>PNRR Componenta 10</strong>, <strong>fonduri AFIR</strong> sau <strong>buget local</strong>. Vă ajutăm cu documentația pentru achiziție publică (SEAP/SICAP).</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Solicită Ofertă Gratuită</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Trimiteți-ne suprafața și tipul de teren dorit. Răspundem în 24 de ore cu o ofertă detaliată.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>📧 <a href="mailto:tudor@agroevolution.com">tudor@agroevolution.com</a><br>📞 <a href="tel:+40750609594">+40 750 609 594</a></p>
<!-- /wp:paragraph -->'''

data = json.dumps({
    'title': 'Gazon Sintetic — Terenuri Sportive și Spații Verzi',
    'content': content,
    'status': 'draft',
    'slug': 'gazon-sintetic',
    'excerpt': 'Soluții complete de gazon sintetic pentru terenuri sportive, școli și primării. FIFA certified, garanție 8-10 ani, prețuri competitive.',
    'parent': 0
}).encode('utf-8')

req = urllib.request.Request(url, data=data, headers={
    'Authorization': f'Basic {token}',
    'Content-Type': 'application/json; charset=utf-8'
})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print('OK — Page ID:', result['id'])
    print('Slug:', result['slug'])
    print('Edit:', f"https://agroevolution.com/wp-admin/post.php?post={result['id']}&action=edit")
    print('Preview:', result.get('link', ''))
except Exception as e:
    print('ERROR:', e)
