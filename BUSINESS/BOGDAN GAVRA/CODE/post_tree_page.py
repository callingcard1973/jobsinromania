import requests
from requests.auth import HTTPBasicAuth

url = "https://www.agroevolution.com/wp-json/wp/v2/pages"
auth = HTTPBasicAuth("apaminerala", "unzQWjnSo2EEGA0cajdXoW2P")

content = """
<style>
.agro-tree-page { font-family: 'Segoe UI', Arial, sans-serif; color: #2d3a2e; max-width: 900px; margin: 0 auto; }
.agro-hero { background: linear-gradient(135deg, #1a4a1a 0%, #2d7a2d 60%, #4CAF50 100%); color: #fff; padding: 48px 36px; border-radius: 12px; margin-bottom: 36px; text-align: center; }
.agro-hero h2 { font-size: 2em; margin: 0 0 12px; }
.agro-hero p { font-size: 1.15em; opacity: 0.93; margin: 0; }
.agro-legal-box { background: #fff8e1; border-left: 6px solid #f9a825; padding: 24px 28px; border-radius: 8px; margin-bottom: 36px; }
.agro-legal-box h3 { color: #e65100; margin-top: 0; font-size: 1.2em; }
.agro-legal-box p { margin: 6px 0; font-size: 1em; }
.agro-legal-box strong { color: #bf360c; }
.agro-section-title { color: #1b5e20; font-size: 1.4em; font-weight: 700; margin: 36px 0 18px; border-bottom: 3px solid #4CAF50; padding-bottom: 6px; }
.agro-packages { display: flex; flex-wrap: wrap; gap: 24px; margin-bottom: 36px; }
.agro-package { flex: 1 1 240px; border: 2px solid #a5d6a7; border-radius: 12px; padding: 24px 20px; background: #f1f8e9; }
.agro-package.highlight { border-color: #2e7d32; background: #e8f5e9; box-shadow: 0 4px 16px rgba(46,125,50,0.12); }
.agro-package h4 { color: #1b5e20; font-size: 1.1em; margin: 0 0 10px; }
.agro-package .price { font-size: 1.25em; font-weight: 700; color: #2e7d32; margin: 10px 0; }
.agro-package ul { margin: 10px 0 0; padding-left: 18px; }
.agro-package ul li { margin-bottom: 6px; font-size: 0.97em; }
.agro-cadru-legal { background: #e8f5e9; border: 1px solid #a5d6a7; border-radius: 10px; padding: 22px 26px; margin-bottom: 36px; }
.agro-cadru-legal h3 { color: #1b5e20; margin-top: 0; }
.agro-cadru-legal ul { margin: 0; padding-left: 20px; }
.agro-cadru-legal ul li { margin-bottom: 8px; }
.agro-deliverables { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 36px; }
.agro-deliv-item { flex: 1 1 180px; background: #fff; border: 1px solid #c8e6c9; border-radius: 10px; padding: 16px 14px; text-align: center; }
.agro-deliv-item .icon { font-size: 2em; display: block; margin-bottom: 8px; }
.agro-deliv-item p { margin: 0; font-size: 0.93em; color: #2d3a2e; }
.agro-cta-box { background: linear-gradient(135deg, #2e7d32, #4CAF50); color: #fff; border-radius: 12px; padding: 36px 28px; text-align: center; margin-top: 36px; }
.agro-cta-box h3 { font-size: 1.4em; margin: 0 0 14px; }
.agro-cta-box p { font-size: 1.05em; margin: 6px 0; }
.agro-cta-box a { color: #fff; font-weight: 700; text-decoration: underline; }
.agro-badge { display: inline-block; background: #388e3c; color: #fff; font-size: 0.8em; padding: 3px 10px; border-radius: 20px; vertical-align: middle; margin-left: 8px; }
</style>

<div class="agro-tree-page">

<div class="agro-hero">
  <h2>&#127795; Plantare Arbori &amp; Compensare CO&#8322; pentru Companii</h2>
  <p>AgroEvolution executa obligatiile legale de reimpadurire si programele CSR de mediu pentru companii din toata Romania.<br>Documentatie completa, arbori garantati, rapoarte pentru APM si raportare ESG.</p>
</div>

<div class="agro-legal-box">
  <h3>&#9878; Obligatie Legala: Legea 24/2007 &mdash; 6 Arbori pentru Fiecare Copac Taiat</h3>
  <p>Daca compania dvs. a obtinut un <strong>aviz de defrisare</strong>, aveti obligatia legala de a planta <strong>6 arbori</strong> pentru fiecare copac taiat, in locatii aprobate de APM.</p>
  <p>Nerespectarea acestei obligatii poate atrage <strong>amenzi contraventionale, blocarea autorizatiilor</strong> si notificari din partea Garzii de Mediu.</p>
  <p><strong>AgroEvolution identifica terenul, planteaza arborii si livreaza intreaga documentatie necesara APM &mdash; cheie in mana.</strong></p>
</div>

<div class="agro-section-title">Pachete de Servicii</div>

<div class="agro-packages">

  <div class="agro-package">
    <h4>&#127807; Compensare Legala <span class="agro-badge">Obligatoriu</span></h4>
    <div class="price">200&ndash;400 RON / arbore</div>
    <ul>
      <li>Executie obligatie 6:1 conform Legii 24/2007</li>
      <li>Identificare teren eligibil APM</li>
      <li>Plantare specii autohtone certificate</li>
      <li>Dosar complet pentru Agentia de Mediu</li>
      <li>Coordonate GPS pentru fiecare arbore</li>
      <li>Raport foto documentatie</li>
    </ul>
  </div>

  <div class="agro-package highlight">
    <h4>&#127807; CSR Verde 100 <span class="agro-badge">Popular</span></h4>
    <div class="price">6.000&ndash;10.000 RON</div>
    <ul>
      <li>100 arbori plantati in zone aprobate</li>
      <li>Certificat oficial de plantare emis de AgroEvolution</li>
      <li>Raport foto + coordonate GPS</li>
      <li>Continut pentru comunicare CSR / raport sustenabilitate</li>
      <li>Logo companie pe placutele de identificare (optional)</li>
    </ul>
  </div>

  <div class="agro-package">
    <h4>&#127794; CSR Verde 500</h4>
    <div class="price">25.000&ndash;40.000 RON</div>
    <ul>
      <li>500 arbori plantati &mdash; impact ESG semnificativ</li>
      <li>Certificat recunoscut + raport complet de mediu</li>
      <li>Calculul CO&#8322; absorbit (tone/an)</li>
      <li>Dosar ESG / sustenabilitate ready-to-use</li>
      <li>Eveniment de plantare cu echipa companiei (optional)</li>
      <li>Monitorizare supravietuire arbori 12 luni</li>
    </ul>
  </div>

</div>

<div class="agro-cadru-legal">
  <h3>&#128203; Cadru Legal &amp; Oportunitati de Finantare</h3>
  <ul>
    <li><strong>Legea 24/2007</strong> &mdash; privind reglementarea si administrarea spatiilor verzi din intravilanul localitatilor; impune raportul 6:1 pentru defrisari autorizate</li>
    <li><strong>HG 525/1996</strong> &mdash; regulamentul general de urbanism; conditioneaza autorizatiile de constructie de obligatii de plantare</li>
    <li><strong>PNRR &mdash; Componenta C2, Paduri</strong> &mdash; 325 milioane EUR alocati pentru impaduriri si perdele forestiere in Romania 2021&ndash;2026</li>
    <li><strong>Raportare ESG</strong> &mdash; Directiva CSRD (Corporate Sustainability Reporting Directive) impune din 2025 raportare de mediu pentru companiile mari din UE</li>
  </ul>
</div>

<div class="agro-section-title">Ce Primesti</div>

<div class="agro-deliverables">
  <div class="agro-deliv-item">
    <span class="icon">&#128220;</span>
    <p><strong>Certificat de Plantare</strong><br>Document oficial emis de AgroEvolution</p>
  </div>
  <div class="agro-deliv-item">
    <span class="icon">&#128205;</span>
    <p><strong>Coordonate GPS</strong><br>Localizare exacta pentru fiecare arbore plantat</p>
  </div>
  <div class="agro-deliv-item">
    <span class="icon">&#128247;</span>
    <p><strong>Foto Documentatie</strong><br>Inainte, in timpul si dupa plantare</p>
  </div>
  <div class="agro-deliv-item">
    <span class="icon">&#128202;</span>
    <p><strong>Raport ESG/CSR</strong><br>Ready-to-use pentru raportare interna si APM</p>
  </div>
  <div class="agro-deliv-item">
    <span class="icon">&#127807;</span>
    <p><strong>Specii Autohtone</strong><br>Stejar, frasin, tei, salcam &mdash; adaptate climei locale</p>
  </div>
  <div class="agro-deliv-item">
    <span class="icon">&#9989;</span>
    <p><strong>Conformitate APM</strong><br>Dosar complet pentru Agentia de Mediu</p>
  </div>
</div>

<div class="agro-cta-box">
  <h3>Solicitati o Oferta Personalizata</h3>
  <p>Spuneti-ne cati arbori aveti nevoie sa plantati si de ce tip de documentatie aveti nevoie.</p>
  <p>&#128231; <a href="mailto:tudor@agroevolution.com">tudor@agroevolution.com</a></p>
  <p>&#128222; <a href="tel:+40750609594">+40 750 609 594</a></p>
  <p style="font-size:0.9em; margin-top:16px; opacity:0.85;">Raspuns in 24 ore &middot; Oferta fara angajament &middot; Executie in toata Romania</p>
</div>

</div>
"""

payload = {
    "title": "Plantare Arbori \u0219i Compensare CO\u2082 pentru Companii",
    "slug": "plantare-arbori",
    "content": content,
    "status": "publish",
}

response = requests.post(url, auth=auth, json=payload)
print("Status:", response.status_code)
if response.status_code in (200, 201):
    data = response.json()
    print("Page ID:", data.get("id"))
    print("URL:", data.get("link"))
else:
    print("Error:", response.text[:2000])
