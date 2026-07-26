/* Admin Jazzmin Custom Enhancements for OneSol AI Hub */
document.addEventListener('DOMContentLoaded', function() {
    // Force logo and brand links in admin to redirect to the main site home page (/)
    const brandLinks = document.querySelectorAll('a.brand-link, #jazzy-logo, .sidebar-brand a, .navbar-brand');
    brandLinks.forEach(function(link) {
        link.setAttribute('href', '/');
        link.setAttribute('title', 'Go to OneSol AI Hub Home Page');
    });

    // Also delegate click event in case elements load dynamically
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a.brand-link, #jazzy-logo, .sidebar-brand a');
        if (link) {
            e.preventDefault();
            window.location.href = '/';
        }
    });

    // Ensure all API Key password fields have no reveal toggles
    document.querySelectorAll('input[type="password"]').forEach(function(input) {
        const parent = input.parentElement;
        if (parent) {
            const eyeIcons = parent.querySelectorAll('.show-password, .toggle-password, .fa-eye, .fa-eye-slash, .input-group-text');
            eyeIcons.forEach(function(icon) {
                icon.style.display = 'none';
                icon.style.pointerEvents = 'none';
            });
        }
    });
});

