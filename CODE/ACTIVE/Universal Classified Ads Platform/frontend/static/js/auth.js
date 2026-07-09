async function updateAuthNav() {
    const authNav = document.getElementById('auth-nav');
    if (!authNav) return;

    const token = localStorage.getItem('token');
    
    if (token) {
        try {
            const user = await API.getCurrentUser();
            if (window.analytics) {
                window.analytics.identify(user.id || user.email, {
                    email: user.email,
                    name: user.name,
                    role: user.role,
                });
            }
            let links = `
                <span class="navbar-text me-3">Hello, ${user.name}</span>
                <a class="nav-link" href="/my-ads">My Ads</a>
                <a class="nav-link" href="/create-ad">Post Ad</a>
            `;
            if (user.role === 'moderator' || user.role === 'admin') {
                links += `<a class="nav-link" href="/moderation">Moderation</a>`;
            }
            if (user.role === 'admin') {
                links += `<a class="nav-link" href="/admin">Admin</a>`;
            }
            links += `<a class="nav-link" href="#" onclick="logout()">Logout</a>`;
            authNav.innerHTML = links;
        } catch (error) {
            localStorage.removeItem('token');
            authNav.innerHTML = `
                <a class="nav-link" href="/login">Login</a>
                <a class="nav-link" href="/register">Register</a>
            `;
        }
    } else {
        authNav.innerHTML = `
            <a class="nav-link" href="/login">Login</a>
            <a class="nav-link" href="/register">Register</a>
        `;
    }
}

function logout() {
    localStorage.removeItem('token');
    if (window.analytics) window.analytics.reset();
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', updateAuthNav);