function escapeHtmlMod(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : text;
    return div.innerHTML;
}

const STATUS_COLORS = {
    draft: 'secondary',
    pending_review: 'warning',
    approved: 'info',
    rejected: 'danger',
    published: 'success',
    archived: 'dark',
};

function statusBadge(status) {
    const color = STATUS_COLORS[status] || 'secondary';
    return `<span class="badge bg-${color}">${escapeHtmlMod(status)}</span>`;
}

async function approveAd(adId, btn) {
    try {
        await API.approveAd(adId);
        loadModerationQueue();
    } catch (error) {
        alert('Approve failed: ' + error.message);
        btn.disabled = false;
    }
}

async function rejectAd(adId, btn) {
    const reason = prompt('Enter rejection reason:');
    if (reason === null) return;
    try {
        await API.rejectAd(adId, reason);
        loadModerationQueue();
    } catch (error) {
        alert('Reject failed: ' + error.message);
        btn.disabled = false;
    }
}

async function publishAd(adId, btn) {
    try {
        await API.publishAd(adId);
        loadModerationQueue();
    } catch (error) {
        alert('Publish failed: ' + error.message);
        btn.disabled = false;
    }
}

async function featureAd(adId, btn) {
    try {
        await API.featureAd(adId);
        loadModerationQueue();
    } catch (error) {
        alert('Feature toggle failed: ' + error.message);
        btn.disabled = false;
    }
}

async function loadModerationQueue() {
    const container = document.getElementById('mod-container');
    const errorDiv = document.getElementById('mod-error');
    const statusFilter = document.getElementById('status-filter').value;

    try {
        const params = {};
        if (statusFilter) params.status = statusFilter;
        const ads = await API.getAds(params);

        if (ads.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No ads in this queue.</div>';
            return;
        }

        container.innerHTML = ads.map(ad => `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h5>${escapeHtmlMod(ad.title)}</h5>
                            <p class="mb-1">${statusBadge(ad.status)}
                                ${ad.is_featured ? '<span class="badge bg-primary ms-1">Featured</span>' : ''}
                            </p>
                            <small class="text-muted">${escapeHtmlMod(ad.category)} &middot; ${escapeHtmlMod(ad.location)}</small>
                            ${ad.price != null ? ` &middot; <strong>$${parseFloat(ad.price).toFixed(2)}</strong>` : ''}
                            <p class="mt-2 mb-0 text-truncate" style="max-width:600px">${escapeHtmlMod(ad.description)}</p>
                        </div>
                        <div class="btn-group btn-group-sm flex-wrap" style="max-width:280px">
                            ${ad.status === 'pending_review' ? `
                                <button class="btn btn-success btn-sm" onclick="approveAd(${ad.id},this)">Approve</button>
                                <button class="btn btn-danger btn-sm" onclick="rejectAd(${ad.id},this)">Reject</button>
                            ` : ''}
                            ${ad.status === 'approved' ? `
                                <button class="btn btn-primary btn-sm" onclick="publishAd(${ad.id},this)">Publish</button>
                            ` : ''}
                            ${ad.status === 'published' ? `
                                <button class="btn btn-outline-primary btn-sm" onclick="featureAd(${ad.id},this)">
                                    ${ad.is_featured ? 'Unfeature' : 'Feature'}
                                </button>
                            ` : ''}
                            <a href="/ads/${ad.id}" class="btn btn-outline-secondary btn-sm">View</a>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '';
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('status-filter').addEventListener('change', loadModerationQueue);
    loadModerationQueue();
});
