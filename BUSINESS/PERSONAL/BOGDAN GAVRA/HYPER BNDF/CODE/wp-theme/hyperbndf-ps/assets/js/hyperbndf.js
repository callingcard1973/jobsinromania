(function() {
'use strict';

/* ── STATE ─────────────────────────────────────────── */
let products = [];
let filtered = [];
let wishlist = JSON.parse(localStorage.getItem('hb_wish') || '[]');
let activeCategory = '';
let searchQuery = '';

/* ── CATALOG URL ───────────────────────────────────── */
function getCatalogUrl() {
  const m = document.querySelector('nav a[href*="loc-de-joac"], nav a[href*="catalog"], .category-sub-menu a');
  return m ? m.href : '/2-loc-de-joaca';
}

/* ── HEADER INJECT ─────────────────────────────────── */
function injectHeader() {
  const header = document.getElementById('header');
  if (!header) return;
  const catalogUrl = getCatalogUrl() || '/2-loc-de-joaca';
  const isHome = window.location.pathname === '/';
  header.innerHTML = `
  <div class="hb-header">
    <a href="/" class="hb-logo">
      <div class="hb-logo-mark">HB</div>
      <div class="hb-logo-text">
        <span class="hb-logo-name">HYPER BNDF</span>
        <span class="hb-logo-sub">Echipamente Loc de Joacă</span>
      </div>
    </a>
    <nav class="hb-nav" id="hb-nav">
      <a href="/" ${isHome?'class="active"':''}>Acasă</a>
      <a href="${catalogUrl}" ${!isHome?'class="active"':''}>Catalog</a>
      <a href="/catalog.html">Pachete &amp; Prețuri</a>
      <a href="mailto:office@hyperbndf.com" class="nav-contact-email">office@hyperbndf.com</a>
      <a href="tel:+40722380349" class="nav-cta">+40 722 380 349</a>
    </nav>
    <button class="hb-burger" id="hb-burger" aria-label="Meniu" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
  </div>`;
  document.getElementById('hb-burger').addEventListener('click', () => {
    const nav = document.getElementById('hb-nav');
    const burger = document.getElementById('hb-burger');
    const open = nav.classList.toggle('open');
    burger.classList.toggle('open', open);
    burger.setAttribute('aria-expanded', open);
  });
}

/* ── PRODUCT DATA ──────────────────────────────────── */
function extractProducts() {
  // Try to get PS product data from page
  const psProducts = window.__products || [];
  if (psProducts.length) return psProducts;

  // Extract from PS DOM
  const items = document.querySelectorAll('.product-miniature, article.product-miniature');
  return Array.from(items).map((el, i) => {
    const img = el.querySelector('img');
    const nameEl = el.querySelector('.product-title a, h3 a, h2 a');
    const priceEl = el.querySelector('.price, .product-price');
    const linkEl = el.querySelector('a');
    return {
      id: el.dataset.idProduct || i,
      name: nameEl ? nameEl.textContent.trim() : '',
      price: priceEl ? priceEl.textContent.trim() : '',
      image: img ? (img.dataset.src || img.src) : '',
      url: linkEl ? linkEl.href : '#',
      category: el.dataset.category || '',
      specs: {}
    };
  });
}

/* ── RENDER CATALOG ────────────────────────────────── */
function renderCatalog() {
  if (!document.querySelector('.hb-catalog-wrap')) return;

  filtered = products.filter(p => {
    const matchCat = !activeCategory || p.category === activeCategory;
    const matchSearch = !searchQuery ||
      p.name.toLowerCase().includes(searchQuery) ||
      (p.description||'').toLowerCase().includes(searchQuery);
    return matchCat && matchSearch;
  });

  const grid = document.getElementById('hb-grid');
  if (!grid) return;

  document.getElementById('hb-results-count').textContent = `${filtered.length} produse`;

  if (!filtered.length) {
    grid.innerHTML = `<div class="hb-no-products"><h3>Niciun produs găsit</h3><p>Încearcă alte filtre</p></div>`;
    return;
  }

  grid.innerHTML = filtered.map(p => cardHTML(p)).join('');
  grid.querySelectorAll('.hb-card').forEach(card => {
    const id = card.dataset.id;
    card.addEventListener('click', e => {
      if (e.target.closest('.hb-card-wish') || e.target.closest('.hb-card-offer-btn')) return;
      openModal(products.find(p => p.id == id));
    });
    card.querySelector('.hb-card-wish').addEventListener('click', e => {
      e.stopPropagation();
      toggleWish(products.find(p => p.id == id), card.querySelector('.hb-card-wish'));
    });
  });
  updateWishButtons();
}

function cardHTML(p) {
  const specs = buildSpecTags(p);
  const wished = wishlist.some(w => w.id == p.id);
  return `
  <div class="hb-card" data-id="${p.id}">
    <div class="hb-card-img">
      <img src="${p.image}" alt="${esc(p.name)}" loading="lazy"
           onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%23e8e6e2%22 width=%22200%22 height=%22200%22/%3E%3Ctext x=%22100%22 y=%22105%22 font-size=%2214%22 text-anchor=%22middle%22 fill=%22%239a9590%22%3EAVP Park%3C/text%3E%3C/svg%3E'">
      <button class="hb-card-wish${wished?' wishlisted':''}" aria-label="Adaugă la ofertă">
        <svg viewBox="0 0 24 24" fill="${wished?'#e53e3e':'none'}" stroke="${wished?'#e53e3e':'currentColor'}" stroke-width="2">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
        </svg>
      </button>
    </div>
    <div class="hb-card-body">
      <span class="hb-card-cat">${esc(p.category)}</span>
      <div class="hb-card-name">${esc(p.name)}</div>
      ${specs ? `<div class="hb-card-specs">${specs}</div>` : ''}
      <div class="hb-card-price">${p.price} <span class="currency">EUR</span></div>
      <a class="hb-card-offer-btn" href="mailto:office@hyperbndf.com?subject=${encodeURIComponent('Cerere ofertă: '+p.name)}&body=${encodeURIComponent('Bună ziua,\n\nDoresc o ofertă pentru:\n'+p.name+'\n\nNumele meu:\nTelefon:\nLocalitate:')}">Solicită ofertă</a>
    </div>
  </div>`;
}

function buildSpecTags(p) {
  const tags = [];
  if (p.age) tags.push(`<span class="hb-spec-tag">Vârsta ${p.age}</span>`);
  if (p.children) tags.push(`<span class="hb-spec-tag">${p.children} copii</span>`);
  if (p.material) tags.push(`<span class="hb-spec-tag">${p.material}</span>`);
  return tags.join('');
}

/* ── MODAL ─────────────────────────────────────────── */
function openModal(p) {
  if (!p) return;
  const overlay = document.getElementById('hb-modal-overlay');
  const wished = wishlist.some(w => w.id == p.id);
  overlay.querySelector('.hb-modal-img img').src = p.image;
  overlay.querySelector('.hb-modal-cat').textContent = p.category;
  overlay.querySelector('.hb-modal-name').textContent = p.name;
  overlay.querySelector('.hb-modal-price').textContent = p.price + ' EUR';
  overlay.querySelector('.hb-modal-desc').textContent = p.description || '';
  const specs = overlay.querySelector('.hb-modal-specs');
  specs.innerHTML = buildModalSpecs(p);
  const wishBtn = overlay.querySelector('.hb-btn-wish-modal');
  wishBtn.className = 'hb-btn-wish-modal' + (wished ? ' wishlisted' : '');
  wishBtn.dataset.id = p.id;
  overlay.querySelector('.hb-btn-offer').dataset.id = p.id;
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function buildModalSpecs(p) {
  const sp = [];
  if (p.age) sp.push(`<div class="hb-modal-spec">👶 Vârsta: ${p.age}</div>`);
  if (p.children) sp.push(`<div class="hb-modal-spec">👥 Capacitate: ${p.children} copii</div>`);
  if (p.material) sp.push(`<div class="hb-modal-spec">🔩 Material: ${p.material}</div>`);
  if (p.dimensions) sp.push(`<div class="hb-modal-spec">📐 Dimensiuni: ${p.dimensions}</div>`);
  return sp.join('');
}

function closeModal() {
  document.getElementById('hb-modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}

/* ── WISHLIST ──────────────────────────────────────── */
function toggleWish(p, btn) {
  if (!p) return;
  const idx = wishlist.findIndex(w => w.id == p.id);
  if (idx >= 0) {
    wishlist.splice(idx, 1);
    if (btn) { btn.classList.remove('wishlisted'); btn.querySelector('svg').setAttribute('fill','none'); btn.querySelector('svg').setAttribute('stroke','currentColor'); }
  } else {
    wishlist.push(p);
    if (btn) { btn.classList.add('wishlisted'); btn.querySelector('svg').setAttribute('fill','#e53e3e'); btn.querySelector('svg').setAttribute('stroke','#e53e3e'); }
  }
  localStorage.setItem('hb_wish', JSON.stringify(wishlist));
  updateWishBadge();
  if (document.querySelector('.hb-wish-panel.open')) renderWishList();
  showToast(idx >= 0 ? 'Eliminat din ofertă' : 'Adăugat la ofertă ✓');
}

function updateWishButtons() {
  document.querySelectorAll('.hb-card-wish').forEach(btn => {
    const card = btn.closest('.hb-card');
    if (!card) return;
    const id = card.dataset.id;
    const w = wishlist.some(x => x.id == id);
    btn.classList.toggle('wishlisted', w);
    btn.querySelector('svg').setAttribute('fill', w ? '#e53e3e' : 'none');
    btn.querySelector('svg').setAttribute('stroke', w ? '#e53e3e' : 'currentColor');
  });
}

function updateWishBadge() {
  const count = wishlist.length;
  document.querySelectorAll('.hb-wish-count, #hb-wish-count-nav').forEach(el => {
    el.textContent = count > 0 ? count : '';
  });
}

function openWishlist() {
  document.querySelector('.hb-wish-panel').classList.add('open');
  document.getElementById('hb-wish-backdrop').classList.add('open');
  renderWishList();
}

function renderWishList() {
  const list = document.querySelector('.hb-wish-list');
  if (!list) return;
  if (!wishlist.length) {
    list.innerHTML = '<div class="hb-wish-empty">Lista dvs. de ofertă este goală.<br>Adăugați produse din catalog.</div>';
    return;
  }
  list.innerHTML = wishlist.map(p => `
  <div class="hb-wish-item">
    <img src="${p.image}" alt="${esc(p.name)}">
    <div class="hb-wish-item-info">
      <div class="hb-wish-item-name">${esc(p.name)}</div>
      <div class="hb-wish-item-price">${p.price} EUR</div>
    </div>
    <button class="hb-wish-item-remove" data-id="${p.id}">×</button>
  </div>`).join('');
  list.querySelectorAll('.hb-wish-item-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = wishlist.find(x => x.id == btn.dataset.id);
      if (p) toggleWish(p, null);
      renderWishList();
    });
  });
}

function sendOffer() {
  if (!wishlist.length) { showToast('Adăugați produse mai întâi'); return; }
  const names = wishlist.map(p => p.name).join('\n');
  const subject = encodeURIComponent('Cerere ofertă echipamente loc de joacă');
  const body = encodeURIComponent(`Bună ziua,\n\nDoresc o ofertă pentru:\n${names}\n\nNumele meu:\nTelefon:\nLocalitate:`);
  window.location.href = `mailto:office@hyperbndf.com?subject=${subject}&body=${body}`;
}

/* ── SIDEBAR FILTER ────────────────────────────────── */
function buildSidebar() {
  const sb = document.querySelector('.hb-cat-list');
  if (!sb || !products.length) return;
  const cats = [...new Set(products.map(p => p.category).filter(Boolean))];
  const total = products.length;
  sb.innerHTML = `<li><a class="active" data-cat="">Toate <span class="hb-cat-count">${total}</span></a></li>` +
    cats.map(c => {
      const cnt = products.filter(p => p.category === c).length;
      return `<li><a data-cat="${esc(c)}">${esc(c)} <span class="hb-cat-count">${cnt}</span></a></li>`;
    }).join('');
  sb.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      sb.querySelectorAll('a').forEach(x => x.classList.remove('active'));
      a.classList.add('active');
      activeCategory = a.dataset.cat;
      renderCatalog();
      updateFilterBar();
    });
  });
}

function buildFilterBar() {
  const bar = document.getElementById('hb-filter-bar');
  if (!bar || !products.length) return;
  const cats = [...new Set(products.map(p => p.category).filter(Boolean))];
  bar.innerHTML = `<button class="hb-filter-btn active" data-cat="">Toate</button>` +
    cats.map(c => `<button class="hb-filter-btn" data-cat="${esc(c)}">${esc(c)}</button>`).join('') +
    `<span class="hb-results-count" id="hb-results-count">${products.length} produse</span>`;
  bar.querySelectorAll('.hb-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      bar.querySelectorAll('.hb-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.cat;
      document.querySelectorAll('.hb-cat-list a').forEach(a => {
        a.classList.toggle('active', a.dataset.cat === activeCategory);
      });
      renderCatalog();
    });
  });
}

function updateFilterBar() {
  document.querySelectorAll('#hb-filter-bar .hb-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.cat === activeCategory);
  });
}

/* ── TOAST ─────────────────────────────────────────── */
function showToast(msg) {
  const t = document.getElementById('hb-toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

/* ── INJECT CATALOG UI ─────────────────────────────── */
function injectCatalogUI() {
  const content = document.getElementById('content') || document.querySelector('.container');
  if (!content) return;
  if (document.querySelector('.hb-catalog-wrap')) return;

  const hero = document.querySelector('.hb-hero');
  if (!hero) {
    // inject hero before content
    const heroEl = document.createElement('div');
    heroEl.className = 'hb-hero';
    heroEl.innerHTML = `
    <div class="hb-hero-content">
      <h1>Catalog <span>Echipamente</span><br>Loc de Joacă</h1>
      <p>226 produse AVP Park — structuri de joacă, leagăne, echipamente fitness exterior</p>
      <div class="hb-hero-search">
        <input type="text" id="hb-search" placeholder="Caută produs...">
        <button onclick="document.getElementById('hb-search').dispatchEvent(new Event('input'))">Caută</button>
      </div>
    </div>`;
    content.parentNode.insertBefore(heroEl, content);
  }

  const wrap = document.createElement('div');
  wrap.className = 'hb-catalog-wrap';
  wrap.innerHTML = `
  <aside class="hb-sidebar">
    <div class="hb-sidebar-section">
      <div class="hb-sidebar-title">Categorii</div>
      <ul class="hb-cat-list"></ul>
    </div>
  </aside>
  <main>
    <div class="hb-filter-bar" id="hb-filter-bar"></div>
    <div class="hb-grid" id="hb-grid"></div>
  </main>`;

  // hide existing PS content
  content.style.display = 'none';
  content.parentNode.insertBefore(wrap, content.nextSibling);
}

function injectModals() {
  if (document.getElementById('hb-modal-overlay')) return;

  document.body.insertAdjacentHTML('beforeend', `
  <!-- Modal -->
  <div class="hb-modal-overlay" id="hb-modal-overlay">
    <div class="hb-modal">
      <div class="hb-modal-img" style="position:relative">
        <button class="hb-modal-close" id="hb-modal-close">×</button>
        <img src="" alt="">
      </div>
      <div class="hb-modal-body">
        <div class="hb-modal-cat"></div>
        <div class="hb-modal-name"></div>
        <div class="hb-modal-price"></div>
        <div class="hb-modal-specs"></div>
        <div class="hb-modal-desc"></div>
        <div class="hb-modal-actions">
          <button class="hb-btn-offer">Cerere ofertă</button>
          <button class="hb-btn-wish-modal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Wishlist panel -->
  <div class="hb-wish-panel">
    <div class="hb-wish-panel-head">
      <h3>Listă Ofertă</h3>
      <button class="hb-wish-close">×</button>
    </div>
    <div class="hb-wish-list"></div>
    <div class="hb-wish-footer">
      <p>Trimiteți lista pentru o ofertă personalizată</p>
      <button class="hb-btn-send-offer">Trimite cerere ofertă</button>
    </div>
  </div>

  <!-- Wishlist FAB -->
  <button class="hb-wish-badge" id="hb-wish-fab">
    <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
    </svg>
    <span class="hb-wish-count"></span>
  </button>

  <!-- Toast -->
  <div class="hb-toast" id="hb-toast"></div>
  <!-- Wishlist backdrop -->
  <div class="hb-wish-backdrop" id="hb-wish-backdrop"></div>
  `);

  document.getElementById('hb-modal-overlay').addEventListener('click', e => {
    if (e.target.id === 'hb-modal-overlay') closeModal();
  });
  document.getElementById('hb-modal-close').addEventListener('click', closeModal);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  document.querySelector('.hb-modal-overlay').addEventListener('click', e => {
    const wishBtn = e.target.closest('.hb-btn-wish-modal');
    if (wishBtn) {
      const p = products.find(x => x.id == wishBtn.dataset.id);
      toggleWish(p, wishBtn);
      wishBtn.classList.toggle('wishlisted');
    }
    const offerBtn = e.target.closest('.hb-btn-offer');
    if (offerBtn) {
      const p = products.find(x => x.id == offerBtn.dataset.id);
      if (p) { toggleWish(p, null); closeModal(); openWishlist(); }
    }
  });

  document.getElementById('hb-wish-fab').addEventListener('click', e => { e.stopPropagation(); openWishlist(); });
  document.querySelector('.hb-wish-close').addEventListener('click', e => {
    e.stopPropagation();
    document.querySelector('.hb-wish-panel').classList.remove('open');
    document.getElementById('hb-wish-backdrop').classList.remove('open');
  });
  document.querySelector('.hb-btn-send-offer').addEventListener('click', sendOffer);
  document.getElementById('hb-wish-backdrop').addEventListener('click', () => {
    document.querySelector('.hb-wish-panel').classList.remove('open');
    document.getElementById('hb-wish-backdrop').classList.remove('open');
  });
}

/* ── SEARCH ────────────────────────────────────────── */
function initSearch() {
  const input = document.getElementById('hb-search');
  if (!input) return;
  input.addEventListener('input', () => {
    searchQuery = input.value.toLowerCase().trim();
    renderCatalog();
  });
}

/* ── LOAD PRODUCTS FROM PS ─────────────────────────── */
function loadPSProducts() {
  // Products injected by PS into window.__hb_products by template
  if (window.__hb_products && window.__hb_products.length) {
    products = window.__hb_products;
    return true;
  }
  return false;
}

/* ── HOME CTA ──────────────────────────────────────── */
function injectHomeCTA() {
  const catalogUrl = getCatalogUrl() || '/2-loc-de-joaca';
  const content = document.getElementById('content') || document.querySelector('.container');
  if (!content) return;
  const cta = document.createElement('div');
  cta.className = 'hb-home-wrap';
  cta.innerHTML = `
  <div class="hb-home-hero">
    <div class="hb-home-hero-content">
      <div class="hb-home-eyebrow">Echipamente certificate CE · Partener AVP Park Turcia</div>
      <h1>Locuri de joacă<br><span>pentru comunitatea ta</span></h1>
      <p>226 produse — structuri de joacă, leagăne, fitness exterior, mobilier urban. Oferte personalizate pentru primării și instituții publice.</p>
      <div class="hb-home-actions">
        <a href="${catalogUrl}" class="hb-btn-primary">Vezi catalogul</a>
        <a href="mailto:office@hyperbndf.com?subject=Cerere%20ofert%C4%83" class="hb-btn-secondary">Solicită ofertă</a>
      </div>
    </div>
  </div>
  <div class="hb-cta-banner">
    <div class="hb-cta-banner-inner">
      <div class="hb-cta-banner-text">
        <div class="hb-cta-banner-title">AUDIT TEREN GRATUIT</div>
        <div class="hb-cta-banner-sub">Venim la tine, măsurăm terenul și îți lăsăm un proiect orientativ fără niciun cost.</div>
      </div>
      <a href="mailto:office@hyperbndf.com?subject=Audit%20teren%20gratuit" class="hb-cta-banner-btn">Programează acum →</a>
    </div>
  </div>
  <div class="hb-home-packages-cta">
    <div class="hb-home-packages-inner">
      <div>
        <div class="hb-home-pkg-label">Pachete complete cu prețuri fixe</div>
        <div class="hb-home-pkg-text">3 pachete gata configurate — de la 18.000 RON · montaj ISCIR inclus · documentație SEAP completă</div>
      </div>
      <a href="/catalog.html" class="hb-home-pkg-btn">Vezi pachete și prețuri →</a>
    </div>
  </div>
  <div class="hb-home-cats">
    <a href="/index.php?id_category=18&controller=category" class="hb-home-cat-card">
      <div class="hb-home-cat-icon">🛝</div>
      <div class="hb-home-cat-name">Loc de joacă</div>
      <div class="hb-home-cat-count">119 produse</div>
    </a>
    <a href="/index.php?id_category=19&controller=category" class="hb-home-cat-card">
      <div class="hb-home-cat-icon">🪑</div>
      <div class="hb-home-cat-name">Mobilier urban</div>
      <div class="hb-home-cat-count">88 produse</div>
    </a>
    <a href="/index.php?id_category=20&controller=category" class="hb-home-cat-card">
      <div class="hb-home-cat-icon">🏋️</div>
      <div class="hb-home-cat-name">Fitness exterior</div>
      <div class="hb-home-cat-count">7 produse</div>
    </a>
    <a href="/index.php?id_category=21&controller=category" class="hb-home-cat-card">
      <div class="hb-home-cat-icon">🔩</div>
      <div class="hb-home-cat-name">Elemente individuale</div>
      <div class="hb-home-cat-count">7 produse</div>
    </a>
    <a href="/index.php?id_category=22&controller=category" class="hb-home-cat-card">
      <div class="hb-home-cat-icon">⚽</div>
      <div class="hb-home-cat-name">Sport</div>
      <div class="hb-home-cat-count">5 produse</div>
    </a>
  </div>`;
  content.style.display = 'none';
  content.parentNode.insertBefore(cta, content.nextSibling);
}

/* ── SEO META ──────────────────────────────────────── */
function injectSeoMeta() {
  const head = document.head;
  if (!head.querySelector('meta[name="theme-color"]')) {
    const tc = document.createElement('meta');
    tc.name = 'theme-color'; tc.content = '#1a5c2a';
    head.appendChild(tc);
  }
  if (!head.querySelector('meta[name="twitter:card"]')) {
    [['twitter:card','summary'],['twitter:description','Echipamente certificate EN 1176 TUV pentru locuri de joacă. Primării România.']].forEach(([n,c]) => {
      const m = document.createElement('meta'); m.name = n; m.content = c; head.appendChild(m);
    });
  }
}

/* ── SCHEMA ────────────────────────────────────────── */
function injectSchema() {
  if (document.querySelector('script[type="application/ld+json"]')) return;
  const s = document.createElement('script');
  s.type = 'application/ld+json';
  s.textContent = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "HYPER BNDF SRL",
    "description": "Importator si distribuitor echipamente loc de joaca certificate EN 1176 TUV",
    "url": "https://hyperbndf.com",
    "telephone": "+40722380349",
    "email": "office@hyperbndf.com",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "Calea Serban Voda 234, Bl.2 Parter",
      "addressLocality": "Bucuresti",
      "postalCode": "040215",
      "addressCountry": "RO"
    },
    "areaServed": "RO",
    "priceRange": "18000-75000 RON"
  });
  document.head.appendChild(s);
}

/* ── INIT ──────────────────────────────────────────── */
function init() {
  injectSeoMeta();
  injectSchema();
  injectHeader();
  injectModals();

  const isHome = window.location.pathname === '/' || document.body.id === 'index';
  const isCatalog = document.body.id === 'category' || document.body.classList.contains('category-page') || window.__hb_products;

  if (isCatalog || window.__hb_products) {
    loadPSProducts();
    injectCatalogUI();
    buildSidebar();
    buildFilterBar();
    initSearch();
    renderCatalog();
  } else if (isHome) {
    injectHomeCTA();
  }

  updateWishBadge();
}

/* ── UTILS ─────────────────────────────────────────── */
function esc(s) {
  return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

})();
