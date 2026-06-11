let currentSkip = 0;
const PAGE_SIZE = 12;
let currentParams = {};

async function populateCategoryFilter() {
    const select = document.getElementById('category-filter');
    if (!select) return;
    try {
        const categories = await API.getCategories();
        select.innerHTML = '<option value="">All Categories</option>' +
            categories.map(c => `<option value="${c.slug}">${escapeHtmlAd(c.name)}</option>`).join('');
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

function collectFilters() {
    const params = { limit: PAGE_SIZE, skip: currentSkip };
    const cat = document.getElementById('category-filter')?.value;
    const loc = document.getElementById('location-filter')?.value;
    const minP = document.getElementById('min-price')?.value;
    const maxP = document.getElementById('max-price')?.value;
    const search = document.getElementById('search-filter')?.value;
    const featured = document.getElementById('featured-only')?.checked;
    if (cat) params.category = cat;
    if (loc) params.location = loc;
    if (minP) params.min_price = parseFloat(minP);
    if (maxP) params.max_price = parseFloat(maxP);
    if (search) params.search = search;
    if (featured) params.featured_only = true;
    return params;
}

async function loadAds() {
    const container = document.getElementById('ads-container');
    const paginationDiv = document.getElementById('pagination');
    if (!container) return;

    currentParams = collectFilters();

    try {
        const resp = await fetch('/api/ads/?' + new URLSearchParams(currentParams));
        if (!resp.ok) throw new Error('API error');
        const ads = await resp.json();
        const total = parseInt(resp.headers.get('X-Total-Count') || '0');

        if (ads.length === 0) {
            container.innerHTML = '<div class="col-12"><div class="alert alert-info">No ads found</div></div>';
            if (paginationDiv) paginationDiv.innerHTML = '';
            return;
        }

        container.innerHTML = ads.map(ad => `
            <div class="col-md-4 mb-4">
                <div class="card ad-card h-100">
                    ${ad.is_featured ? '<span class="position-absolute top-0 end-0 badge badge-featured m-2">Featured</span>' : ''}
                    <div class="card-body">
                        <h5 class="card-title">${escapeHtmlAd(ad.title)}</h5>
                        <p class="card-text text-truncate">${escapeHtmlAd(ad.description)}</p>
                        <p class="card-text">
                            <small class="text-muted">
                                ${escapeHtmlAd(ad.location)}
                            </small>
                        </p>
                        <p class="card-text">
                            <small class="text-muted">
                                Category: ${escapeHtmlAd(ad.category)}
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

        // Pagination
        if (paginationDiv) {
            const totalPages = Math.ceil(total / PAGE_SIZE);
            const currentPage = Math.floor(currentSkip / PAGE_SIZE) + 1;
            if (totalPages <= 1) {
                paginationDiv.innerHTML = `<small class="text-muted">${total} result${total !== 1 ? 's' : ''}</small>`;
            } else {
                let btns = `<small class="text-muted me-2">${total} results — page ${currentPage}/${totalPages}</small>`;
                if (currentSkip > 0) btns += `<button class="btn btn-sm btn-outline-primary me-1" id="prev-page">&larr; Prev</button>`;
                if (currentSkip + PAGE_SIZE < total) btns += `<button class="btn btn-sm btn-outline-primary" id="next-page">Next &rarr;</button>`;
                paginationDiv.innerHTML = btns;
                document.getElementById('prev-page')?.addEventListener('click', () => { currentSkip = Math.max(0, currentSkip - PAGE_SIZE); loadAds(); window.scrollTo(0,0); });
                document.getElementById('next-page')?.addEventListener('click', () => { currentSkip += PAGE_SIZE; loadAds(); window.scrollTo(0,0); });
            }
        }
    } catch (error) {
        container.innerHTML = `<div class="col-12"><div class="alert alert-danger">Error loading ads: ${error.message}</div></div>`;
    }
}

function escapeHtmlAd(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    populateCategoryFilter();

    const filterForm = document.getElementById('filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            currentSkip = 0;
            loadAds();
        });
    }

    loadAds();
});
