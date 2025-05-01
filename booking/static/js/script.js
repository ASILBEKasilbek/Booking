document.addEventListener('DOMContentLoaded', () => {
    // Oddiy interaktivlik: masalan, xabarnomalarni yopish
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        alert.addEventListener('click', () => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        });
    });
});