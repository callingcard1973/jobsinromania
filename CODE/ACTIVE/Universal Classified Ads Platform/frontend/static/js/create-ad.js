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

document.addEventListener('DOMContentLoaded', () => {
    populateCategories();

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
            const ad = await API.createAd(adData);

            if (imagesInput.files.length > 0) {
                for (const file of imagesInput.files) {
                    try {
                        await API.uploadAdImage(ad.id, file);
                    } catch (uploadError) {
                        console.error('Failed to upload image:', uploadError);
                    }
                }
            }

            // Pay-to-publish: send the user to the ad page to pay & submit for review.
            window.location.href = `/ads/${ad.id}`;
        } catch (error) {
            errorDiv.textContent = error.message;
            errorDiv.classList.remove('d-none');
        }
    });
});
