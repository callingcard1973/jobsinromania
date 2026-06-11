function escapeHtmlAdm(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : text;
    return div.innerHTML;
}

function slugify(text) {
    return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

async function loadStats() {
    const container = document.getElementById('stats-container');
    try {
        const stats = await API.getAdminStats();
        const items = [
            { label: 'Total Users', value: stats.total_users },
            { label: 'Total Ads', value: stats.total_ads },
            { label: 'Published', value: stats.published_ads || 0 },
            { label: 'Pending Review', value: stats.pending_review_ads || 0 },
        ];
        container.innerHTML = items.map(i => `
            <div class="col-md-3 mb-2">
                <div class="card text-center">
                    <div class="card-body">
                        <h3>${i.value}</h3>
                        <small class="text-muted">${i.label}</small>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">${escapeHtmlAdm(error.message)}</div>`;
    }
}

async function loadUsers() {
    const container = document.getElementById('users-container');
    try {
        const users = await API.getAdminUsers();
        container.innerHTML = `
            <table class="table table-sm table-striped">
                <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Joined</th></tr></thead>
                <tbody>${users.map(u => `
                    <tr>
                        <td>${u.id}</td>
                        <td>${escapeHtmlAdm(u.name)}</td>
                        <td>${escapeHtmlAdm(u.email)}</td>
                        <td><span class="badge bg-${u.role === 'admin' ? 'danger' : u.role === 'moderator' ? 'warning' : 'secondary'}">${u.role}</span></td>
                        <td>${new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                `).join('')}</tbody>
            </table>
        `;
    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">${escapeHtmlAdm(error.message)}</div>`;
    }
}

async function loadCategories() {
    const container = document.getElementById('categories-container');
    try {
        const cats = await API.getCategories(true);
        container.innerHTML = `
            <table class="table table-sm table-striped">
                <thead><tr><th>ID</th><th>Name</th><th>Slug</th><th>Active</th><th></th></tr></thead>
                <tbody>${cats.map(c => `
                    <tr>
                        <td>${c.id}</td>
                        <td>${escapeHtmlAdm(c.name)}</td>
                        <td><code>${escapeHtmlAdm(c.slug)}</code></td>
                        <td>${c.is_active ? '<span class="badge bg-success">Yes</span>' : '<span class="badge bg-secondary">No</span>'}</td>
                        <td>${c.is_active ? `<button class="btn btn-sm btn-outline-danger deactivate-btn" data-id="${c.id}">Deactivate</button>` : ''}</td>
                    </tr>
                `).join('')}</tbody>
            </table>
        `;
        container.querySelectorAll('.deactivate-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('Deactivate this category?')) return;
                try {
                    await API.deleteCategory(parseInt(btn.dataset.id));
                    loadCategories();
                } catch (error) {
                    alert(error.message);
                }
            });
        });
    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">${escapeHtmlAdm(error.message)}</div>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadUsers();
    loadCategories();

    document.getElementById('cat-slug').addEventListener('input', (e) => {
        // auto-fill slug from name if slug is empty
    });
    document.getElementById('cat-name').addEventListener('blur', (e) => {
        const slugField = document.getElementById('cat-slug');
        if (!slugField.value) slugField.value = slugify(e.target.value);
    });

    document.getElementById('add-cat-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('cat-name').value.trim();
        const slug = document.getElementById('cat-slug').value.trim() || slugify(name);
        const errorDiv = document.getElementById('cat-error');
        errorDiv.classList.add('d-none');
        try {
            await API.createCategory({ name, slug });
            document.getElementById('cat-name').value = '';
            document.getElementById('cat-slug').value = '';
            loadCategories();
        } catch (error) {
            errorDiv.textContent = error.message;
            errorDiv.classList.remove('d-none');
        }
    });
});
