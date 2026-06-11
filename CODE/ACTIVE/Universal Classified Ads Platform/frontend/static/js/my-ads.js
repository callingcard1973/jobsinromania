const STATUS_COLORS = {
    draft: 'secondary',
    pending_review: 'warning',
    approved: 'info',
    rejected: 'danger',
    published: 'success',
    archived: 'dark',
};

function escapeHtmlMa(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : text;
    return div.innerHTML;
}

function statusBadge(status) {
    const color = STATUS_COLORS[status] || 'secondary';
    return `<span class="badge bg-${color}">${escapeHtmlMa(status)}</span>`;
}

async function payAndPublish(adId, button) {
    const errorDiv = document.getElementById('my-ads-error');
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

async function archiveAd(adId) {
    if (!confirm('Archive this ad?')) return;
    try {
        await API.archiveAd(adId);
        loadMyAds();
    } catch (error) {
        const errorDiv = document.getElementById('my-ads-error');
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    }
}

async function deleteAd(adId) {
    if (!confirm('Delete this ad permanently?')) return;
    try {
        await API.deleteAd(adId);
        loadMyAds();
    } catch (error) {
        const errorDiv = document.getElementById('my-ads-error');
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    }
}

function showPaymentBanner() {
    const banner = document.getElementById('payment-banner');
    const params = new URLSearchParams(window.location.search);
    if (params.get('paid') === '1') {
        banner.innerHTML = '<div class="alert alert-success">Payment received. Your ad is now in review and will be published once approved.</div>';
    } else if (params.get('canceled') === '1') {
        banner.innerHTML = '<div class="alert alert-warning">Payment was canceled. Your ad remains a draft.</div>';
    }
}

async function loadMyAds() {
    const container = document.getElementById('my-ads-container');
    const errorDiv = document.getElementById('my-ads-error');
    if (!container) return;

    try {
        const ads = await API.getMyAds();
        if (ads.length === 0) {
            container.innerHTML = '<div class="alert alert-info">You have no ads yet. <a href="/create-ad">Create one</a></div>';
            return;
        }

        container.innerHTML = ads.map(ad => `
            <div class="card mb-3">
                <div class="card-body d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title">
                            <a href="/ads/${ad.id}">${escapeHtmlMa(ad.title)}</a>
                        </h5>
                        <p class="mb-1">${statusBadge(ad.status)}</p>
                        <small class="text-muted">${escapeHtmlMa(ad.category)} &middot; ${escapeHtmlMa(ad.location)}</small>
                        ${ad.price != null ? ` &middot; <strong>$${parseFloat(ad.price).toFixed(2)}</strong>` : ''}
                        ${ad.status === 'rejected' && ad.rejection_reason ? `<div class="alert alert-warning mt-2 mb-0 py-1"><small>Rejected: ${escapeHtmlMa(ad.rejection_reason)}</small></div>` : ''}
                    </div>
                    <div class="btn-group btn-group-sm">
                        ${['draft', 'rejected'].includes(ad.status) ? `<button class="btn btn-success btn-sm pay-btn" data-id="${ad.id}">Pay &amp; Publish</button>` : ''}
                        <a href="/ads/${ad.id}" class="btn btn-outline-primary btn-sm">View</a>
                        ${['draft', 'rejected'].includes(ad.status) ? `<a href="/create-ad?edit=${ad.id}" class="btn btn-outline-secondary btn-sm">Edit</a>` : ''}
                        ${!['archived'].includes(ad.status) ? `<button class="btn btn-outline-dark btn-sm archive-btn" data-id="${ad.id}">Archive</button>` : ''}
                        <button class="btn btn-outline-danger btn-sm delete-btn" data-id="${ad.id}">Delete</button>
                    </div>
                </div>
            </div>
        `).join('');

        container.querySelectorAll('.pay-btn').forEach(btn => {
            btn.addEventListener('click', () => payAndPublish(parseInt(btn.dataset.id), btn));
        });
        container.querySelectorAll('.archive-btn').forEach(btn => {
            btn.addEventListener('click', () => archiveAd(parseInt(btn.dataset.id)));
        });
        container.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', () => deleteAd(parseInt(btn.dataset.id)));
        });
    } catch (error) {
        container.innerHTML = '';
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.classList.remove('d-none');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    showPaymentBanner();
    loadMyAds();
});
