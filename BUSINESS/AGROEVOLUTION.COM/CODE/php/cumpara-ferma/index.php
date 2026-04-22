<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cumpără o Fermă – AgroEvolution</title>
<meta name="description" content="Colaborăm cu lichidatori judiciari și executori din toată România. Te anunțăm când apare o fermă potrivită pentru tine.">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;color:#222;background:#f7f5f0;line-height:1.6}
a{color:#2d7a2d;text-decoration:none}
a:hover{text-decoration:underline}

/* HERO */
.hero{background:linear-gradient(135deg,#1a4a1a 0%,#2d7a2d 100%);color:#fff;padding:clamp(40px,8vw,90px) 20px clamp(50px,10vw,100px);text-align:center}
.badge{display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:20px;padding:6px 18px;font-size:clamp(13px,2.5vw,15px);margin-bottom:22px;letter-spacing:.5px}
.hero h1{font-size:clamp(26px,5vw,52px);font-weight:800;max-width:760px;margin:0 auto 20px;line-height:1.15}
.hero p{font-size:clamp(15px,2.5vw,20px);max-width:600px;margin:0 auto 40px;opacity:.9}
.stats{display:flex;flex-wrap:wrap;justify-content:center;gap:16px 40px;margin-top:10px}
.stat{text-align:center}
.stat-num{display:block;font-size:clamp(26px,4vw,40px);font-weight:800;line-height:1}
.stat-lbl{font-size:clamp(11px,2vw,14px);opacity:.8;margin-top:4px}

/* FORM SECTION */
.form-section{padding:clamp(30px,6vw,70px) 20px;display:flex;justify-content:center}
.form-card{background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,.12);padding:clamp(28px,5vw,50px);width:100%;max-width:520px}
.form-card h2{font-size:clamp(20px,3.5vw,28px);color:#1a4a1a;margin-bottom:6px;text-align:center}
.form-card .sub{color:#666;text-align:center;margin-bottom:28px;font-size:15px}
label{display:block;font-size:13px;font-weight:600;color:#444;margin-bottom:4px;margin-top:16px}
label:first-of-type{margin-top:0}
input,select,textarea{width:100%;padding:12px 14px;border:1.5px solid #ddd;border-radius:8px;font-size:15px;color:#222;background:#fafafa;transition:border-color .2s}
input:focus,select:focus,textarea:focus{outline:none;border-color:#2d7a2d;background:#fff}
textarea{resize:vertical;min-height:80px}
.req{color:#c0392b}
.btn{display:block;width:100%;margin-top:24px;padding:16px;background:#2d7a2d;color:#fff;border:none;border-radius:10px;font-size:17px;font-weight:700;cursor:pointer;transition:background .2s;letter-spacing:.3px}
.btn:hover{background:#1a5e1a}
.success{display:none;text-align:center;padding:28px 10px;font-size:17px;color:#1a4a1a;font-weight:600}
.success .check{font-size:48px;display:block;margin-bottom:12px}
.note{font-size:12px;color:#999;text-align:center;margin-top:12px}

/* HOW IT WORKS */
.how{background:#fff;padding:clamp(40px,7vw,80px) 20px;text-align:center}
.how h2{font-size:clamp(20px,3.5vw,32px);color:#1a4a1a;margin-bottom:10px}
.how .sub{color:#666;font-size:16px;margin-bottom:44px}
.steps{display:flex;flex-wrap:wrap;justify-content:center;gap:24px;max-width:900px;margin:0 auto}
.step{background:#f7f5f0;border-radius:12px;padding:28px 24px;flex:1;min-width:220px;max-width:260px;position:relative}
.step-num{display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;background:#2d7a2d;color:#fff;border-radius:50%;font-size:20px;font-weight:800;margin-bottom:14px}
.step h3{font-size:16px;color:#1a4a1a;margin-bottom:8px}
.step p{font-size:14px;color:#555}

/* FOOTER */
footer{background:#1a4a1a;color:#ccc;text-align:center;padding:24px 20px;font-size:14px}
footer a{color:#8dc88d}
footer a:hover{color:#fff}
footer .sep{margin:0 10px;opacity:.4}

@media(max-width:600px){
  .steps{flex-direction:column;align-items:center}
  .step{max-width:100%;width:100%}
}
</style>
</head>
<body>

<!-- HERO -->
<section class="hero">
  <div class="badge">🌾 Ferme falimentare · Prețuri sub piață</div>
  <h1>Cumpără o Fermă Înainte Să Ajungă la Licitație</h1>
  <p>Colaborăm cu lichidatori judiciari și executori din toată România. Te anunțăm când apare o fermă potrivită pentru tine.</p>
  <div class="stats">
    <div class="stat"><span class="stat-num">836</span><span class="stat-lbl">Executori parteneri</span></div>
    <div class="stat"><span class="stat-num">3.554</span><span class="stat-lbl">Lichidatori în rețea</span></div>
    <div class="stat"><span class="stat-num">9.658</span><span class="stat-lbl">Terenuri monitorizate</span></div>
  </div>
</section>

<!-- FORM -->
<section class="form-section">
  <div class="form-card">
    <h2>Înscrie-te gratuit</h2>
    <p class="sub">Primești oferte exclusive înainte de licitație publică</p>

    <div id="form-wrap">
      <form id="lead-form">
        <label for="email">Email <span class="req">*</span></label>
        <input type="email" id="email" name="email" placeholder="adresa@email.ro" required>

        <label for="telefon">Telefon</label>
        <input type="tel" id="telefon" name="telefon" placeholder="07xx xxx xxx">

        <label for="judet">Județ preferat</label>
        <select id="judet" name="judet">
          <option value="">— Oriunde în România —</option>
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

        <label for="suprafata">Suprafață minimă (ha)</label>
        <input type="number" id="suprafata" name="suprafata" placeholder="ex: 50" min="1">

        <label for="budget">Budget maxim (RON)</label>
        <input type="number" id="budget" name="budget" placeholder="ex: 500000" min="0">

        <label for="tip">Tip fermă / alte detalii</label>
        <textarea id="tip" name="tip" placeholder="ex: fermă de cereale, livadă, complex zootehnic..."></textarea>

        <button type="submit" class="btn">Vreau să fiu contactat</button>
        <p class="note">Fără spam. Datele tale sunt confidențiale.</p>
      </form>
    </div>

    <div class="success" id="success-msg">
      <span class="check">✓</span>
      Cerere primită! Te contactăm în 24–48h cu opțiuni disponibile.
    </div>
  </div>
</section>

<!-- HOW IT WORKS -->
<section class="how">
  <h2>Cum funcționează</h2>
  <p class="sub">Simplu, rapid, fără intermediari inutili</p>
  <div class="steps">
    <div class="step">
      <div class="step-num">1</div>
      <h3>Înscrie-te și specifică ce cauți</h3>
      <p>Completează formularul cu preferințele tale: județ, suprafață, tip de fermă și buget disponibil.</p>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <h3>Monitorizăm rețeaua de lichidatori</h3>
      <p>Scanăm zilnic dosarele de insolvență și executare silită din toată țara pentru ferme care corespund criteriilor tale.</p>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <h3>Primești oferte înainte de licitație publică</h3>
      <p>Te contactăm direct cu detalii și prețul de valorificare — adesea cu 20–40% sub valoarea de piață.</p>
    </div>
  </div>
</section>

<!-- FOOTER -->
<footer>
  <a href="https://agroevolution.com">AgroEvolution.com</a>
  <span class="sep">|</span>
  <a href="https://agroevolution.com/harta.php">Harta Terenuri Agricole</a>
  <span class="sep">|</span>
  <span>© <?php echo date('Y'); ?> AgroEvolution</span>
</footer>

<script>
document.getElementById('lead-form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = this.querySelector('.btn');
  btn.textContent = 'Se trimite...';
  btn.disabled = true;

  const budget = document.getElementById('budget').value;
  const tip = document.getElementById('tip').value;
  const mesaj = [budget ? 'Budget: ' + budget + ' RON' : '', tip ? 'Tip: ' + tip : ''].filter(Boolean).join('. ');

  const payload = {
    email: document.getElementById('email').value,
    telefon: document.getElementById('telefon').value,
    judet: document.getElementById('judet').value,
    suprafata_min: parseFloat(document.getElementById('suprafata').value) || null,
    pret_max_ha: null,
    mesaj: mesaj,
    sursa: 'cumparferme'
  };

  try {
    const resp = await fetch('/save_lead.php', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    if (resp.ok) {
      document.getElementById('form-wrap').style.display = 'none';
      document.getElementById('success-msg').style.display = 'block';
    } else {
      throw new Error('server error');
    }
  } catch (err) {
    btn.textContent = 'Eroare – încearcă din nou';
    btn.disabled = false;
    btn.style.background = '#c0392b';
  }
});
</script>
</body>
</html>
