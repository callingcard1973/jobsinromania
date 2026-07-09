async function confirmPayment() {
    const params = new URLSearchParams(window.location.search);
    const paymentId = params.get('payment_id');
    const loading = document.getElementById('checkout-loading');
    const success = document.getElementById('checkout-success');
    const errorDiv = document.getElementById('checkout-error');
    const errorMsg = document.getElementById('checkout-error-msg');

    if (!paymentId) {
        loading.classList.add('d-none');
        errorDiv.classList.remove('d-none');
        errorMsg.textContent = 'No payment ID specified.';
        return;
    }

    try {
        await API.confirmSandboxPayment(parseInt(paymentId));
        loading.classList.add('d-none');
        success.classList.remove('d-none');
        setTimeout(() => { window.location.href = '/my-ads?paid=1'; }, 3000);
    } catch (error) {
        loading.classList.add('d-none');
        errorDiv.classList.remove('d-none');
        errorMsg.textContent = error.message;
    }
}

document.addEventListener('DOMContentLoaded', confirmPayment);
