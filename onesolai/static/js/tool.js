document.addEventListener('DOMContentLoaded', function() {
    // ═══════════════════════════════════
    // 1. FAQ INTERACTIVITY
    // ═══════════════════════════════════
    document.querySelectorAll('.faq-q').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var parent = this.parentElement;
            parent.classList.toggle('active');
        });
    });

    // ═══════════════════════════════════
    // 2. TABS INTERACTIVITY
    // ═══════════════════════════════════
    var tabs = document.querySelectorAll('.tool-tab');
    var panes = document.querySelectorAll('.tab-pane');
    var indicator = document.getElementById('tabIndicator');

    function updateIndicator(activeTab) {
        if (!indicator) return;
        indicator.style.width = activeTab.offsetWidth + 'px';
        indicator.style.left = activeTab.offsetLeft + 'px';
    }

    // Set initial active tab
    var defaultTab = document.querySelector('.tool-tab.active');
    if (!defaultTab && tabs.length > 0) {
        defaultTab = tabs[0];
        defaultTab.classList.add('active');
        var targetPane = document.getElementById('tab-' + defaultTab.getAttribute('data-target'));
        if (targetPane) targetPane.classList.add('active');
    }
    
    // Init indicator
    if (defaultTab) updateIndicator(defaultTab);

    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            var target = this.getAttribute('data-target');
            
            // Update active classes on tabs
            tabs.forEach(function(t) { t.classList.remove('active'); });
            this.classList.add('active');
            
            // Move indicator
            updateIndicator(this);

            // Switch panes
            panes.forEach(function(pane) {
                if (pane.id === 'tab-' + target) {
                    pane.classList.add('active');
                } else {
                    pane.classList.remove('active');
                }
            });
        });
    });

    // Handle window resize for indicator
    window.addEventListener('resize', function() {
        var activeTab = document.querySelector('.tool-tab.active');
        if (activeTab) updateIndicator(activeTab);
    });

    // ═══════════════════════════════════
    // 3. SCREENSHOTS GALLERY
    // ═══════════════════════════════════
    var ssTrack = document.getElementById('ssTrack');
    var ssDotsContainer = document.getElementById('ssDots');
    var ssSlides = document.querySelectorAll('.ss-track img');
    
    if (ssSlides.length > 1 && ssTrack && ssDotsContainer) {
        // Build dots
        var dotsHTML = '';
        ssSlides.forEach(function(img, index) {
            dotsHTML += `<div class="ss-dot ${index === 0 ? 'active' : ''}" data-index="${index}"></div>`;
            img.style.minWidth = '100%';
            img.style.objectFit = 'cover';
        });
        ssDotsContainer.innerHTML = dotsHTML;

        var ssCurrentIndex = 0;
        var ssTotal = ssSlides.length;
        var ssDots = document.querySelectorAll('.ss-dot');

        function updateGallery(index) {
            ssCurrentIndex = index;
            if (ssCurrentIndex < 0) ssCurrentIndex = ssTotal - 1;
            if (ssCurrentIndex >= ssTotal) ssCurrentIndex = 0;

            ssTrack.style.transform = 'translateX(-' + (ssCurrentIndex * 100) + '%)';

            ssSlides.forEach(function(s, i) {
                s.classList.toggle('active', i === ssCurrentIndex);
                if (ssDots[i]) ssDots[i].classList.toggle('active', i === ssCurrentIndex);
            });
        }

        var btnPrev = document.getElementById('ssPrev');
        var btnNext = document.getElementById('ssNext');

        if (btnPrev) btnPrev.addEventListener('click', function() { updateGallery(ssCurrentIndex - 1); });
        if (btnNext) btnNext.addEventListener('click', function() { updateGallery(ssCurrentIndex + 1); });

        ssDots.forEach(function(dot) {
            dot.addEventListener('click', function() {
                updateGallery(parseInt(this.getAttribute('data-index')));
            });
        });

        // Swipe support
        var isDragging = false;
        var startPos = 0;
        var currentTranslate = 0;
        var prevTranslate = 0;

        var getPosX = function(e) { return e.type.includes('mouse') ? e.pageX : e.touches[0].clientX; };

        var touchStart = function(e) {
            isDragging = true;
            startPos = getPosX(e);
            prevTranslate = -ssCurrentIndex * ssTrack.clientWidth;
            ssTrack.style.transition = 'none';
        };

        var touchMove = function(e) {
            if (isDragging) {
                var currentPosition = getPosX(e);
                currentTranslate = prevTranslate + currentPosition - startPos;
                ssTrack.style.transform = 'translateX(' + currentTranslate + 'px)';
            }
        };

        var touchEnd = function() {
            isDragging = false;
            ssTrack.style.transition = 'transform 0.4s ease';

            var movedBy = currentTranslate - prevTranslate;
            if (movedBy < -50 && ssCurrentIndex < ssTotal - 1) ssCurrentIndex += 1;
            else if (movedBy > 50 && ssCurrentIndex > 0) ssCurrentIndex -= 1;
            
            updateGallery(ssCurrentIndex);
        };

        ssTrack.addEventListener('mousedown', touchStart);
        ssTrack.addEventListener('mousemove', touchMove);
        ssTrack.addEventListener('mouseup', touchEnd);
        ssTrack.addEventListener('mouseleave', function() { if(isDragging) touchEnd(); });
        
        ssTrack.addEventListener('touchstart', touchStart, {passive: true});
        ssTrack.addEventListener('touchmove', touchMove, {passive: true});
        ssTrack.addEventListener('touchend', touchEnd);

    } else if (ssTrack) {
        // If 0 or 1 screenshot, don't show navigation
        var btnPrev = document.getElementById('ssPrev');
        var btnNext = document.getElementById('ssNext');
        if (btnPrev) btnPrev.style.display = 'none';
        if (btnNext) btnNext.style.display = 'none';
        if (ssSlides.length === 1) {
            ssSlides[0].style.minWidth = '100%';
            ssSlides[0].style.objectFit = 'cover';
        }
    }

});
