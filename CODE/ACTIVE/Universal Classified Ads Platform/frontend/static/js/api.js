const API_BASE = '/api';

class API {
    static async request(endpoint, options = {}) {
        const token = localStorage.getItem('token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'An error occurred');
        }

        if (response.status === 204) {
            return null;
        }

        return response.json();
    }

    static async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    static async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    static async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    static async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    static async upload(endpoint, formData) {
        const token = localStorage.getItem('token');
        const headers = {};

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers,
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Upload failed');
        }

        return response.json();
    }

    static async login(email, password) {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);

        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Login failed');
        }

        return response.json();
    }

    static async register(name, email, password) {
        return this.post('/auth/register', { name, email, password });
    }

    static async getCurrentUser() {
        return this.get('/auth/me');
    }

    static async getAds(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/ads?${query}`);
    }

    static async getAd(id) {
        return this.get(`/ads/${id}`);
    }

    static async createAd(adData) {
        return this.post('/ads', adData);
    }

    static async updateAd(id, adData) {
        return this.put(`/ads/${id}`, adData);
    }

    static async deleteAd(id) {
        return this.delete(`/ads/${id}`);
    }

    static async submitAd(id) {
        return this.post(`/ads/${id}/submit`);
    }

    static async uploadAdImage(adId, file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.upload(`/ads/${adId}/media`, formData);
    }

    static async getAdMedia(adId) {
        return this.get(`/ads/${adId}/media/`);
    }

    static async archiveAd(id) {
        return this.post(`/ads/${id}/archive`);
    }

    static async approveAd(id) {
        return this.post(`/ads/${id}/approve`);
    }

    static async rejectAd(id, rejectionReason) {
        return this.post(`/ads/${id}/reject`, { rejection_reason: rejectionReason });
    }

    static async publishAd(id) {
        return this.post(`/ads/${id}/publish`);
    }

    static async featureAd(id) {
        return this.post(`/ads/${id}/feature`);
    }

    static async getCategories(includeInactive = false) {
        const query = includeInactive ? '?include_inactive=true' : '';
        return this.get(`/categories/${query}`);
    }

    static async createCategory(data) {
        return this.post('/categories/', data);
    }

    static async deleteCategory(id) {
        return this.delete(`/categories/${id}`);
    }

    static async getMyProfile() {
        return this.get('/users/me');
    }

    static async updateMyProfile(data) {
        return this.put('/users/me', data);
    }

    static async changePassword(currentPassword, newPassword) {
        return this.post('/users/me/change-password', {
            current_password: currentPassword,
            new_password: newPassword,
        });
    }

    static async getMyAds() {
        return this.get('/users/me/ads');
    }

    static async getAdminUsers() {
        return this.get('/admin/users');
    }

    static async getAdminStats() {
        return this.get('/admin/stats');
    }

    static async getPaymentConfig() {
        return this.get('/payments/config');
    }

    static async createCheckout(adId) {
        return this.post(`/payments/ads/${adId}/checkout`);
    }

    static async confirmSandboxPayment(paymentId) {
        return this.post(`/payments/sandbox/${paymentId}/confirm`);
    }

    static async getMyPayments() {
        return this.get('/payments/me');
    }
}