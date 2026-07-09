// BuildJobs.eu — Content Renderer
// Loads content.json and renders page dynamically

async function renderContent() {
  try {
    const res = await fetch('content.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}: content.json not found`);

    const data = await res.json();

    // HERO SECTION
    renderHero(data.hero);

    // STATS
    renderStats(data.stats);

    // LANGUAGES
    renderLanguages(data.languages);

    // FEATURES
    renderFeatures(data.features);

    // COUNTRIES
    renderCountries(data.countries);

    // TELEGRAM
    renderTelegram(data.telegram);

    // PDF SECTION
    renderPdfSection(data.pdf_section);

    // FOOTER
    renderFooter(data.footer);

    console.log('Content rendered successfully');
  } catch (err) {
    console.error('Error rendering content:', err);
    document.body.innerHTML = `<p style="color:red;padding:2rem">Error: Could not load content. Check console.</p>${document.body.innerHTML}`;
  }
}

function renderHero(hero) {
  document.getElementById('hero-h1').innerHTML = hero.h1;
  document.getElementById('hero-p').textContent = hero.p;
  document.getElementById('pdf-desc').textContent = hero.pdf_desc;

  const gallery = document.getElementById('hero-gallery');
  hero.images.forEach(img => {
    const el = document.createElement('img');
    el.src = img.src;
    el.alt = img.alt;
    el.loading = 'lazy';
    gallery.appendChild(el);
  });

  document.getElementById('cta-apply').textContent = hero.cta_apply;
  document.getElementById('cta-apply').href = CONFIG.urls.apply;
  document.getElementById('cta-pdf').textContent = hero.cta_pdf;
  document.getElementById('cta-pdf').href = CONFIG.urls.pdfArchive;
}

function renderStats(stats) {
  const container = document.getElementById('stats');
  stats.forEach(s => {
    const el = document.createElement('div');
    el.className = 'stat';
    el.innerHTML = `<div class="stat-num" ${s.id ? `id="${s.id}"` : ''}>${s.num}</div><div class="stat-label">${s.label}</div>`;
    container.appendChild(el);
  });
}

function renderLanguages(languages) {
  // Header selector
  const langSel = document.getElementById('lang-selector');
  languages.forEach(l => {
    const btn = document.createElement('a');
    btn.href = l.code === 'en' ? '/' : `/${l.code}/`;
    btn.className = 'lang-btn';
    btn.textContent = l.name;
    langSel.appendChild(btn);
  });

  // Full language grid
  const langFull = document.getElementById('lang-full');
  languages.forEach(l => {
    const a = document.createElement('a');
    a.href = l.code === 'en' ? '/' : `/${l.code}/`;
    a.textContent = l.name;
    langFull.appendChild(a);
  });
}

function renderFeatures(features) {
  const container = document.getElementById('features');
  features.forEach(f => {
    const el = document.createElement('div');
    el.className = 'feature';
    el.innerHTML = `<div class="feature-icon">${f.icon}</div><h3>${f.title}</h3><p>${f.desc}</p>`;
    container.appendChild(el);
  });
}

function renderCountries(countries) {
  const container = document.getElementById('countries');
  countries.forEach(c => {
    const tag = document.createElement('span');
    tag.className = 'country-tag';
    tag.textContent = c;
    container.appendChild(tag);
  });
}

function renderTelegram(telegram) {
  const box = document.getElementById('telegram-box');
  box.innerHTML = `
    <div style="font-size:3rem;margin-bottom:1rem">🤖</div>
    <h3 class="telegram-box h3">${telegram.title}</h3>
    <p>${telegram.desc}</p>
    <a href="${telegram.btn_link}" target="_blank" class="telegram-btn">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.461-1.901-.903-1.056-.692-1.653-1.123-2.678-1.799-1.185-.781-.417-1.21.258-1.911.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.479.329-.913.489-1.302.481-.428-.009-1.252-.242-1.865-.442-.751-.244-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.015 3.333-1.386 4.025-1.627 4.477-1.635.099-.002.321.023.465.141.12.098.153.229.169.339.015.11.035.322.019.496z"/></svg>
      ${telegram.btn_text}
    </a>
    <p style="color:var(--text-dim);font-size:0.78rem;margin-top:1rem">${telegram.note}</p>
  `;
}

function renderPdfSection(pdf) {
  document.getElementById('pdf-h2').textContent = pdf.h2;
  document.getElementById('pdf-p').textContent = pdf.p;
  document.getElementById('pdf-note').textContent = pdf.note;

  const btns = document.getElementById('pdf-buttons');
  btns.innerHTML = `
    <a href="${CONFIG.urls.pdfArchive}" target="_blank" class="pdf-btn">View on Archive.org</a>
    <a href="${CONFIG.urls.pdfDirect}" class="pdf-btn" style="margin-left:10px">Direct Download</a>
  `;
}

function renderFooter(footer) {
  document.getElementById('footer-tagline').textContent = footer.tagline;

  const links = footer.links.map(l => `<a href="${l.href}">${l.text}</a>`).join(' &nbsp;|&nbsp; ');
  document.getElementById('footer-links').innerHTML = links;

  document.getElementById('footer-copyright').textContent = footer.copyright;
}

// Init on page load
document.addEventListener('DOMContentLoaded', renderContent);
