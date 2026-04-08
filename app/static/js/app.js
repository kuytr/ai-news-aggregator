/**
 * app.js - AI News Aggregator Frontend JavaScript
 *
 * Handles:
 * - Category checkbox auto-submit
 * - Toast notifications
 * - OTP input enhancement
 * - Article card animations
 */

document.addEventListener('DOMContentLoaded', function () {

    // ---- Category checkbox labels: toggle active class visually ----
    document.querySelectorAll('.category-check-label input').forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            const label = this.closest('.category-check-label');
            if (this.checked) {
                label.classList.add('active');
            } else {
                label.classList.remove('active');
            }
        });
    });

    // ---- OTP Input: auto-advance on 6 chars ----
    const otpInput = document.querySelector('.otp-input');
    if (otpInput) {
        otpInput.addEventListener('input', function () {
            // Remove non-numeric characters
            this.value = this.value.replace(/\D/g, '');

            // Auto-submit when 6 digits entered
            if (this.value.length === 6) {
                const form = this.closest('form');
                if (form) {
                    // Small delay for UX
                    setTimeout(() => form.submit(), 300);
                }
            }
        });

        // Focus the OTP field automatically
        otpInput.focus();
    }

    // ---- Fade-in animation for article cards ----
    const cards = document.querySelectorAll('.article-card');
    const observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.1 }
    );

    cards.forEach(function (card, i) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = `opacity 0.4s ease ${i * 0.05}s, transform 0.4s ease ${i * 0.05}s, box-shadow 0.25s, border-color 0.25s`;
        observer.observe(card);
    });

    // ---- Toast notification helper ----
    window.showToast = function (message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        const toast = document.createElement('div');
        const colorMap = { info: '#00d4ff', success: '#00c853', error: '#ff5252', warning: '#ff9800' };
        toast.className = 'toast-notification';
        toast.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; z-index: 9999;
            background: #1a1a2e; border: 1px solid ${colorMap[type] || colorMap.info};
            color: #e0e0f0; padding: 12px 20px; border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            font-size: 14px; max-width: 300px;
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    };

    function createToastContainer() {
        const el = document.createElement('div');
        el.id = 'toast-container';
        document.body.appendChild(el);
        return el;
    }

    // ---- Navbar scroll effect ----
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 50) {
                navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.5)';
            } else {
                navbar.style.boxShadow = 'none';
            }
        });
    }

    // ---- Active nav link highlighting ----
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function (link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
            link.style.color = 'var(--accent)';
        }
    });
});

// CSS animation for toast
const style = document.createElement('style');
style.textContent = `
@keyframes slideIn {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
}`;
document.head.appendChild(style);
