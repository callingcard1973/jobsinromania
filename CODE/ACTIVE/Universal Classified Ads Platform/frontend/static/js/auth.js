async function updateAuthNav() {
    const authNav = document.getElementById('auth-nav');
    if (!authNav) return;

    const token = localStorage.getItem('token');
    
    if (token) {
        try {
            const user = await API.getCurrentUser();
            authNav.innerHTML = `
                <span class="navbar-text me-3">Hello, ${user.name}</span>
                <a class="nav-link" href="/ads">My Ads</a>
                <a class="nav-link" href="#" onclick="logout()">Logout</a>
            `;
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
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', updateAuthNav);