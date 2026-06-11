let editingAdId = null;

async function populateCategories() {
    const select = document.getElementById('category');
    if (!select) return;
    try {
        const categories = await API.getCategories();
        select.innerHTML = '<option value="">Select Category</option>' +
            categories.map(c => `<option value="${c.slug}">${escapeHtmlCa(c.name)}</option>`).join('');
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

function escapeHtmlCa(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadAdForEdit(adId) {
    try {
        const ad = await API.getAd(adId);
        document.getElementById('title').value = ad.title || '';
        document.getElementById('description').value = ad.description || '';
        document.getElementById('category').value = ad.category || '';
        document.getElementById('price').value = ad.price ? parseFloat(ad.price) : '';
        document.getElementById('location').value = ad.location || '';
        document.getElementById('contact-info').value = ad.contact_info || '';
        document.getElementById('tags').value = ad.tags || '';
        // Update UI to show edit mode
        const header = document.querySelector('.card-header h4');
        if (header) header.textContent = 'Edit Ad';
        const submitBtn = document.querySelector('#create-ad-form button[type=submit]');
        if (submitBtn) submitBtn.textContent = 'Save Changes';
    } catch (error) {
        const errorDiv = document.getElementById('create-ad-error');
        errorDiv.textContent = 'Failed to load ad: ' + error.message;
        errorDiv.classList.remove('d-none');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    populateCategories();

    // Check if editing existing ad (?edit=ID)
    const params = new URLSearchParams(window.location.search);
    const editId = params.get('edit');
    if (editId) {
        editingAdId = parseInt(editId);
        // Wait for categories to load first, then populate ad data
        populateCategories().then(() => loadAdForEdit(editingAdId));
    }

    document.getElementById('create-ad-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const adData = {
            title: document.getElementById('title').value,
            description: document.getElementById('description').value,
            category: document.getElementById('category').value,
            price: document.getElementById('price').value ? parseFloat(document.getElementById('price').value) : null,
            location: document.getElementById('location').value,
            contact_info: document.getElementById('contact-info').value || null,
            tags: document.getElementById('tags').value || null,
        };

        const imagesInput = document.getElementById('images');
        const errorDiv = document.getElementById('create-ad-error');

        try {
            let ad;
            if (editingAdId) {
                // Update existing ad
                ad = await API.updateAd(editingAdId, adData);
            } else {
                // Create new ad
                ad = await API.createAd(adData);
            }

            if (imagesInput.files.length > 0) {
                for (const file of imagesInput.files) {
                    try {
                        await API.uploadAdImage(ad.id, file);
                    } catch (uploadError) {
                        console.error('Failed to upload image:', uploadError);
                    }
                }
            }

            // Go to ad detail page (pay flow or view)
            window.location.href = `/ads/${ad.id}`;
        } catch (error) {
            errorDiv.textContent = error.message;
            errorDiv.classList.remove('d-none');
        }
    });
});
