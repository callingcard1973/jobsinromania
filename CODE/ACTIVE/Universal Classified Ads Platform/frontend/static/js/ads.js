async function populateCategoryFilter() {
    const select = document.getElementById('category-filter');
    if (!select) return;
    try {
        const categories = await API.getCategories();
        select.innerHTML = '<option value="">All Categories</option>' +
            categories.map(c => `<option value="${c.slug}">${escapeHtml(c.name)}</option>`).join('');
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

async function loadAds() {
    const container = document.getElementById('ads-container');
    if (!container) return;

    try {
        const ads = await API.getAds();
        
        if (ads.length === 0) {
            container.innerHTML = '<div class="col-12"><div class="alert alert-info">No ads found</div></div>';
            return;
        }

        container.innerHTML = ads.map(ad => `
            <div class="col-md-4 mb-4">
                <div class="card ad-card h-100">
                    ${ad.is_featured ? '<span class="position-absolute top-0 end-0 badge badge-featured m-2">Featured</span>' : ''}
                    <div class="card-body">
                        <h5 class="card-title">${escapeHtml(ad.title)}</h5>
                        <p class="card-text text-truncate">${escapeHtml(ad.description)}</p>
                        <p class="card-text">
                            <small class="text-muted">
                                <i class="bi bi-geo-alt"></i> ${escapeHtml(ad.location)}
                            </small>
                        </p>
                        <p class="card-text">
                            <small class="text-muted">
                                Category: ${escapeHtml(ad.category)}
                            </small>
                        </p>
                        ${ad.price ? `<p class="price-tag">$${parseFloat(ad.price).toFixed(2)}</p>` : ''}
                        <a href="/ads/${ad.id}" class="btn btn-primary btn-sm">View Details</a>
                    </div>
                    <div class="card-footer">
                        <small class="text-muted">Posted: ${new Date(ad.created_at).toLocaleDateString()}</small>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<div class="col-12"><div class="alert alert-danger">Error loading ads: ${error.message}</div></div>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    populateCategoryFilter();
    loadAds();
});