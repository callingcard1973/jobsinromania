/**
 * Classified Ads Bridge — Front-end JS
 * Handles: FB login, ad form submission, Stripe/sandbox checkout, my-ads listing.
 */
(function () {
    const API = cabConfig.apiUrl || '';
    const TOKEN_KEY = 'cab_api_token';

    function getApiHeaders() {
        const t = localStorage.getItem(TOKEN_KEY);
        const h = { 'Content-Type': 'application/json' };
        if (t) h['Authorization'] = 'Bearer ' + t;
        return h;
    }

    // --- Facebook Login ---
    function initFB() {
        if (!cabConfig.fbAppId || typeof FB === 'undefined') return;
        FB.init({ appId: cabConfig.fbAppId, cookie: true, xfbml: false, version: 'v19.0' });
    }

    function fbLogin() {
        if (typeof FB === 'undefined') { alert('Facebook SDK not loaded'); return; }
        FB.login(function (resp) {
            if (resp.authResponse) {
                sendToWP('cab_fb_login', { access_token: resp.authResponse.accessToken });
            } else {
                alert('Facebook login cancelled');
            }
        }, { scope: 'email,public_profile' });
    }

    // --- Native WP login/register ---
    async function nativeLogin() {
        await sendToWP('cab_native_login', {
            email: document.getElementById('cab-email').value,
            password: document.getElementById('cab-password').value,
        });
    }

    async function nativeRegister() {
        await sendToWP('cab_native_register', {
            name: document.getElementById('cab-reg-name').value,
            email: document.getElementById('cab-reg-email').value,
            password: document.getElementById('cab-reg-password').value,
        });
    }

    // Record login method so the PostHog mu-plugin can tag the identified user on reload.
    function markLoginMethod(method) {
        document.cookie = 'cab_login_method=' + method + ';path=/;max-age=120;SameSite=Lax';
    }

    async function sendToWP(action, fields) {
        const errDiv = document.getElementById('cab-auth-error');
        errDiv.style.display = 'none';
        const fd = new FormData();
        fd.append('action', action);
        for (const [k, v] of Object.entries(fields)) fd.append(k, v);
        try {
            const r = await fetch(cabConfig.ajaxUrl, { method: 'POST', body: fd });
            const data = await r.json();
            if (data.success && data.data.api_token) {
                localStorage.setItem(TOKEN_KEY, data.data.api_token);
                markLoginMethod(action === 'cab_fb_login' ? 'facebook'
                    : action === 'cab_native_register' ? 'native_register' : 'native');
                location.reload();
            } else {
                errDiv.textContent = data.data || 'Login failed';
                errDiv.style.display = 'block';
            }
        } catch (e) {
            errDiv.textContent = 'Error: ' + e.message;
            errDiv.style.display = 'block';
        }
    }

    // --- API helpers ---
    async function apiGet(endpoint) {
        const r = await fetch(API + endpoint, { headers: getApiHeaders() });
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'API error');
        return r.json();
    }

    async function apiPost(endpoint, body) {
        const r = await fetch(API + endpoint, { method: 'POST', headers: getApiHeaders(), body: JSON.stringify(body) });
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'API error');
        return r.json();
    }

    async function apiUpload(endpoint, formData) {
        const t = localStorage.getItem(TOKEN_KEY);
        const h = {};
        if (t) h['Authorization'] = 'Bearer ' + t;
        const r = await fetch(API + endpoint, { method: 'POST', headers: h, body: formData });
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Upload error');
        return r.json();
    }

    // --- Load categories into form ---
    async function loadCategories() {
        const sel = document.getElementById('cab-category');
        if (!sel) return;
        try {
            const cats = await apiGet('/api/categories/');
            sel.innerHTML = '<option value="">Select...</option>' +
                cats.map(c => '<option value="' + c.slug + '">' + esc(c.name) + '</option>').join('');
        } catch (e) { console.error('Categories load failed', e); }
    }

    // --- Ad form submission ---
    async function submitAd(e) {
        e.preventDefault();
        const errDiv = document.getElementById('cab-error');
        errDiv.style.display = 'none';
        const btn = e.target.querySelector('button[type=submit]');
        btn.disabled = true;
        btn.textContent = 'Processing...';

        try {
            // 1. Create ad
            const ad = await apiPost('/api/ads/', {
                title: document.getElementById('cab-title').value,
                description: document.getElementById('cab-description').value,
                category: document.getElementById('cab-category').value,
                location: document.getElementById('cab-location').value,
                price: document.getElementById('cab-price').value ? parseFloat(document.getElementById('cab-price').value) : null,
                contact_info: document.getElementById('cab-contact').value || null,
            });

            // 2. Upload images
            const files = document.getElementById('cab-images').files;
            for (const f of files) {
                const fd = new FormData();
                fd.append('file', f);
                try { await apiUpload('/api/ads/' + ad.id + '/media', fd); } catch (e) { console.error('Upload failed', e); }
            }

            // 3. Checkout (pay) — skip if no Stripe and sandbox available
            if (cabConfig.stripePk || cabConfig.priceCents === 0) {
                // Free mode or Stripe configured
                if (cabConfig.priceCents === 0) {
                    // Free: submit directly (skip payment)
                    try { await apiPost('/api/ads/' + ad.id + '/submit'); } catch (e) { console.error('Submit failed', e); }
                    alert('Your ad has been submitted for review!');
                    location.href = cabConfig.homeUrl + '/my-ads/';
                } else {
                    const checkout = await apiPost('/api/payments/ads/' + ad.id + '/checkout');
                    if (checkout.sandbox) {
                        await apiPost('/api/payments/sandbox/' + checkout.payment_id + '/confirm');
                        alert('Payment received! Your ad is now in review and will be published once approved.');
                        location.href = cabConfig.homeUrl + '/my-ads/?paid=1';
                    } else {
                        location.href = checkout.checkout_url;
                    }
                }
            } else {
                // No Stripe: try sandbox checkout
                try {
                    const checkout = await apiPost('/api/payments/ads/' + ad.id + '/checkout');
                    if (checkout.sandbox) {
                        await apiPost('/api/payments/sandbox/' + checkout.payment_id + '/confirm');
                        alert('Payment confirmed (sandbox). Your ad is in review.');
                        location.href = cabConfig.homeUrl + '/my-ads/?paid=1';
                    } else {
                        location.href = checkout.checkout_url;
                    }
                } catch (e) {
                    // If checkout fails, just submit for review
                    try { await apiPost('/api/ads/' + ad.id + '/submit'); } catch (e2) {}
                    alert('Ad created! Submitted for review.');
                    location.href = cabConfig.homeUrl + '/my-ads/';
                }
            }
        } catch (error) {
            errDiv.textContent = error.message;
            errDiv.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Pay & Post Ad';
        }
    }

    // --- My Ads ---
    async function loadMyAds() {
        const container = document.getElementById('cab-my-ads');
        if (!container) return;
        try {
            const ads = await apiGet('/api/users/me/ads');
            if (!ads.length) {
                container.innerHTML = '<p>You have no ads yet. <a href="' + cabConfig.homeUrl + '/post-ad/">Post one</a></p>';
                return;
            }
            container.innerHTML = ads.map(ad => {
                const badge = { draft: 'secondary', pending_review: 'warning', approved: 'info', rejected: 'danger', published: 'success', archived: 'dark' }[ad.status] || 'secondary';
                return '<div class="card mb-2" style="padding:12px;border:1px solid #ddd">' +
                    '<h4>' + esc(ad.title) + ' <span class="badge bg-' + badge + '">' + ad.status + '</span></h4>' +
                    '<small>' + esc(ad.category) + ' · ' + esc(ad.location) + '</small>' +
                    (ad.rejection_reason ? '<div class="alert alert-warning mt-1 py-1"><small>Rejected: ' + esc(ad.rejection_reason) + '</small></div>' : '') +
                    (ad.wp_post_url && ad.status === 'published' ? '<a href="' + esc(ad.wp_post_url) + '" target="_blank" class="btn btn-sm btn-outline-primary mt-1">View on site</a>' : '') +
                    '</div>';
            }).join('');
        } catch (e) {
            container.innerHTML = '<p class="text-danger">Error: ' + esc(e.message) + '</p>';
        }
    }

    function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

    // --- Init on DOMContentLoaded ---
    document.addEventListener('DOMContentLoaded', function () {
        // FB login button
        const fbBtn = document.getElementById('cab-fb-login-btn');
        if (fbBtn) fbBtn.addEventListener('click', fbLogin);

        // FB SDK init after loaded
        if (typeof FB !== 'undefined') initFB();
        else window.fbAsyncInit = initFB;

        // Native auth
        const loginBtn = document.getElementById('cab-login-btn');
        if (loginBtn) loginBtn.addEventListener('click', nativeLogin);
        const regBtn = document.getElementById('cab-register-btn');
        if (regBtn) regBtn.addEventListener('click', nativeRegister);

        // Toggle login/register forms
        const showReg = document.getElementById('cab-show-register');
        if (showReg) showReg.addEventListener('click', function (e) {
            e.preventDefault();
            document.getElementById('cab-login-form').style.display = 'none';
            document.getElementById('cab-register-form').style.display = 'block';
        });
        const showLogin = document.getElementById('cab-show-login');
        if (showLogin) showLogin.addEventListener('click', function (e) {
            e.preventDefault();
            document.getElementById('cab-register-form').style.display = 'none';
            document.getElementById('cab-login-form').style.display = 'block';
        });

        // Ad form
        const form = document.getElementById('cab-ad-form');
        if (form) {
            loadCategories();
            form.addEventListener('submit', submitAd);
        }

        // My ads
        if (document.getElementById('cab-my-ads')) loadMyAds();

        // Payment banner
        const params = new URLSearchParams(location.search);
        if (params.get('paid') === '1') {
            const el = document.getElementById('cab-my-ads');
            if (el) el.insertAdjacentHTML('afterbegin', '<div class="alert alert-success">Payment received! Your ad is in review.</div>');
        }
    });
})();
