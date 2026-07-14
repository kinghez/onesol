document.addEventListener('DOMContentLoaded', () => {
    const animatableElements = document.querySelectorAll('.card, .promo-banner, .stat-card');
    
    animatableElements.forEach((el, index) => {
        el.style.opacity = '0'; // Start hidden
        setTimeout(() => {
            el.classList.add('fade-up');
        }, index * 50); // Stagger by 50ms
    });
});
