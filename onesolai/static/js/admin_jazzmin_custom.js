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

    // ─────────────────────────────────────────────────────────────────────
    //  INLINE STYLE INJECTION: Fix disabled/readonly/grayed-out admin fields
    //  Inject a <style> tag directly so it overrides ALL other stylesheets
    // ─────────────────────────────────────────────────────────────────────
    var fixStyle = document.createElement('style');
    fixStyle.id = 'onesol-readonly-fix';
    fixStyle.innerHTML = [
        /* Disabled/readonly inputs – dark bg + bright sky text */
        'input[disabled], input[readonly],',
        'input.disabled, textarea[disabled], textarea[readonly],',
        'select[disabled], select[readonly],',
        '.form-control[disabled], .form-control[readonly],',
        'fieldset[disabled] .form-control,',
        '.uneditable-input {',
        '    background-color: #1F0E45 !important;',
        '    color: #38BDF8 !important;',
        '    border: 1px solid rgba(142,108,255,0.45) !important;',
        '    opacity: 1 !important;',
        '    font-weight: 700 !important;',
        '    -webkit-text-fill-color: #38BDF8 !important;',
        '}',

        /* Django admin readonly fields rendered as <div class="readonly"> */
        'div.readonly, .readonly, p.readonly {',
        '    background-color: #1F0E45 !important;',
        '    color: #38BDF8 !important;',
        '    border: 1px solid rgba(142,108,255,0.45) !important;',
        '    border-radius: 8px !important;',
        '    padding: 8px 14px !important;',
        '    opacity: 1 !important;',
        '    font-weight: 700 !important;',
        '    display: block !important;',
        '}',

        /* All children of .readonly */
        'div.readonly *, .readonly * {',
        '    color: #38BDF8 !important;',
        '    -webkit-text-fill-color: #38BDF8 !important;',
        '}',

        /* Links inside readonly */
        'div.readonly a, .readonly a, .field-box a {',
        '    color: #7DD3FC !important;',
        '    -webkit-text-fill-color: #7DD3FC !important;',
        '    text-decoration: underline !important;',
        '    font-weight: 800 !important;',
        '}',
    ].join('\n');
    document.head.appendChild(fixStyle);

    // Also apply inline styles directly on DOM elements as a double-guarantee
    function applyReadonlyStyles() {
        // Apply to disabled/readonly inputs
        var disabledInputs = document.querySelectorAll(
            'input[disabled], input[readonly], textarea[disabled], textarea[readonly], select[disabled], select[readonly], .form-control[disabled], .form-control[readonly], .uneditable-input'
        );
        disabledInputs.forEach(function(el) {
            el.style.setProperty('background-color', '#1F0E45', 'important');
            el.style.setProperty('color', '#38BDF8', 'important');
            el.style.setProperty('border', '1px solid rgba(142,108,255,0.45)', 'important');
            el.style.setProperty('opacity', '1', 'important');
            el.style.setProperty('font-weight', '700', 'important');
        });

        // Apply to Django readonly divs
        var readonlyDivs = document.querySelectorAll('div.readonly, .readonly, p.readonly');
        readonlyDivs.forEach(function(el) {
            el.style.setProperty('background-color', '#1F0E45', 'important');
            el.style.setProperty('color', '#38BDF8', 'important');
            el.style.setProperty('border', '1px solid rgba(142,108,255,0.45)', 'important');
            el.style.setProperty('border-radius', '8px', 'important');
            el.style.setProperty('padding', '8px 14px', 'important');
            el.style.setProperty('opacity', '1', 'important');
            el.style.setProperty('font-weight', '700', 'important');
            // Also style all child elements
            el.querySelectorAll('*').forEach(function(child) {
                child.style.setProperty('color', '#38BDF8', 'important');
            });
        });
    }

    // Run immediately on DOM ready
    applyReadonlyStyles();

    // Run again after a short delay to catch any dynamically rendered content
    setTimeout(applyReadonlyStyles, 500);
});
