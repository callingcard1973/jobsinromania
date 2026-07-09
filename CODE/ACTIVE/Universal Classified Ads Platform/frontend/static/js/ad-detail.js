const STATUS_COLORS = {
    draft: 'secondary',
    pending_review: 'warning',
    approved: 'info',
    rejected: 'danger',
    published: 'success',
    archived: 'dark',
};

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : text;
    return div.innerHTML;
}

function statusBadge(status) {
    const color = STATUS_COLORS[status] || 'secondary';
    return `<span class="badge bg-${color}">${escapeHtml(status)}</span>`;
}

function formatPrice(cents, currency) {
    const amount = (cents / 100).toFixed(2);
    return `${(currency || 'usd').toUpperCase()} ${amount}`;
}

function getAdId() {
    const params = new URLSearchParams(window.location.search);
    const queryId = params.get('id');
    if (queryId) return queryId;
    const parts = window.location.pathname.split('/').filter(Boolean);
    return parts[parts.length - 1];
}

async function loadMediaHtml(adId, title) {
    try {
        const media = await API.getAdMedia(adId);
        if (!media || media.length === 0) return '';
        const items = media.map(m => `
            <div class="col-md-4 mb-3">
                <img src="${escapeHtml(m.url)}" class="img-fluid rounded ad-image" alt="${escapeHtml(title)}">
            </div>
        `).join('');
        return `<div class="row mb-3">${items}</div>`;
    } catch (error) {
        return '';
    }
}

async function payAndPublish(adId, button) {
    const errorDiv = document.getElementById('ad-error');
    errorDiv.classList.add('d-none');
    button.disabled = true;
    try {
        const result = await API.createCheckout(adId);
        window.location.href = result.checkout_url;
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
        button.disabled = false;
    }
}

async function loadAdDetail() {
    const container = document.getElementById('ad-detail');
    const errorDiv = document.getElementById('ad-error');
    if (!container) return;

    const adId = getAdId();
    if (!adId) {
        errorDiv.textContent = 'No ad specified';
        errorDiv.classList.remove('d-none');
        container.innerHTML = '';
        return;
    }

    try {
        const ad = await API.getAd(adId);

        let currentUser = null;
        if (localStorage.getItem('token')) {
            try {
                currentUser = await API.getCurrentUser();
            } catch (error) {
                currentUser = null;
            }
        }

        const mediaHtml = await loadMediaHtml(adId, ad.title);

        const canPay = currentUser
            && currentUser.id === ad.user_id
            && ['draft', 'rejected'].includes(ad.status);

        container.innerHTML = `
            <div class="card">
                ${ad.is_featured ? '<span class="position-absolute top-0 end-0 badge badge-featured m-2">Featured</span>' : ''}
                <div class="card-body">
                    <h2 class="card-title">${escapeHtml(ad.title)}</h2>
                    <p class="mb-2">${statusBadge(ad.status)}</p>
                    ${mediaHtml}
                    ${ad.price != null ? `<p class="price-tag">$${parseFloat(ad.price).toFixed(2)}</p>` : ''}
                    <p class="card-text">${escapeHtml(ad.description)}</p>
                    <ul class="list-group list-group-flush mb-3">
                        <li class="list-group-item"><strong>Category:</strong> ${escapeHtml(ad.category)}</li>
                        <li class="list-group-item"><strong>Location:</strong> ${escapeHtml(ad.location)}</li>
                        ${ad.contact_info ? `<li class="list-group-item"><strong>Contact:</strong> ${escapeHtml(ad.contact_info)}</li>` : ''}
                        ${ad.tags ? `<li class="list-group-item"><strong>Tags:</strong> ${escapeHtml(ad.tags)}</li>` : ''}
                        <li class="list-group-item"><strong>Posted:</strong> ${new Date(ad.created_at).toLocaleString()}</li>
                        ${ad.expires_at ? `<li class="list-group-item"><strong>Expires:</strong> ${new Date(ad.expires_at).toLocaleString()}</li>` : ''}
                    </ul>
                    ${ad.status === 'rejected' && ad.rejection_reason ? `<div class="alert alert-warning"><strong>Rejection reason:</strong> ${escapeHtml(ad.rejection_reason)}</div>` : ''}
                    ${canPay ? '<button id="pay-publish-btn" class="btn btn-success">Pay &amp; Publish</button>' : ''}
                </div>
            </div>
        `;

        if (canPay) {
            const btn = document.getElementById('pay-publish-btn');
            try {
                const config = await API.getPaymentConfig();
                btn.textContent = `Pay & Publish (${formatPrice(config.amount_cents, config.currency)})`;
            } catch (error) {
                // keep default label if config unavailable
            }
            btn.addEventListener('click', () => payAndPublish(ad.id, btn));
        }
    } catch (error) {
        container.innerHTML = '';
        errorDiv.textContent = `Error loading ad: ${error.message}`;
        errorDiv.classList.remove('d-none');
    }
}

document.addEventListener('DOMContentLoaded', loadAdDetail);
