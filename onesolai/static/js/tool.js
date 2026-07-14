document.addEventListener('DOMContentLoaded', function() {
    // ═══════════════════════════════════
    // 1. DATA HYDRATION
    // ═══════════════════════════════════
    var urlParams = new URLSearchParams(window.location.search);
    var slug = urlParams.get('slug') || 'chatgpt-plus'; // Default to chatgpt-plus if no slug
    
    var data = toolsData[slug];
    if (!data) {
        // Fallback or error handling
        document.querySelector('.tool-page-main').innerHTML = '<h1 style="text-align:center; padding: 100px;">Tool not found</h1>';
        return;
    }

    // Top Section
    document.getElementById('toolLogo').src = data.logo;
    document.getElementById('toolName').textContent = data.name;
    document.getElementById('toolDeveloper').textContent = data.developer;
    document.getElementById('toolRating').textContent = data.rating;
    document.getElementById('toolReviewsCount').textContent = data.reviewsCount;
    document.getElementById('tabReviewsCount').textContent = data.reviewsCount;
    document.getElementById('toolUsersCount').textContent = data.usersCount;
    document.getElementById('toolPrice').textContent = data.price;

    // Overview
    document.getElementById('ovDesc').textContent = data.overview.description;
    
    var ovFeaturesHTML = '';
    data.overview.features.forEach(function(feat) {
        ovFeaturesHTML += `
            <li>
                <div class="ov-icon-circle"><i class="fas fa-check"></i></div>
                <span>${feat}</span>
            </li>
        `;
    });
    document.getElementById('ovFeatures').innerHTML = ovFeaturesHTML;

    // Features Tab
    var featHTML = '';
    if (data.features.length > 0) {
        data.features.forEach(function(feat) {
            featHTML += `
                <div class="feat-card">
                    <h4>${feat.title}</h4>
                    <p>${feat.desc}</p>
                </div>
            `;
        });
    } else {
        featHTML = '<p style="color: rgba(255,255,255,0.7);">More features coming soon.</p>';
    }
    // Add standard meta-features
    featHTML += `
        <div class="feat-card">
            <h4>Availability</h4>
            <p>${data.availability}</p>
        </div>
        <div class="feat-card">
            <h4>System Requirements</h4>
            <p>${data.systemReqs}</p>
        </div>
        <div class="feat-card">
            <h4>Supported Devices</h4>
            <p>${data.devices}</p>
        </div>
        <div class="feat-card">
            <h4>Languages</h4>
            <p>${data.languages}</p>
        </div>
        <div class="feat-card">
            <h4>Updates</h4>
            <p>${data.updates}</p>
        </div>
    `;
    document.getElementById('featGrid').innerHTML = featHTML;

    // Reviews Tab
    var revHTML = '';
    if (data.reviews.length > 0) {
        data.reviews.forEach(function(rev) {
            revHTML += `
                <div class="rev-card">
                    <div class="rev-header">
                        <div class="rev-user">
                            <div class="rev-avatar">${rev.name.charAt(0)}</div>
                            <div>
                                <span class="rev-name">${rev.name}</span>
                                <span class="rev-country">${rev.country}</span>
                            </div>
                        </div>
                        <div class="rev-meta" style="text-align: right;">
                            <div class="rev-rating">
                                <i class="fas fa-star"></i>
                                <i class="fas fa-star"></i>
                                <i class="fas fa-star"></i>
                                <i class="fas fa-star"></i>
                                <i class="fas fa-star"></i>
                            </div>
                            <span class="rev-date">${rev.date}</span>
                        </div>
                    </div>
                    <p class="rev-text">${rev.text}</p>
                </div>
            `;
        });
    } else {
        revHTML = '<p style="color: rgba(255,255,255,0.7);">No reviews yet.</p>';
    }
    document.getElementById('revWrap').innerHTML = revHTML;

    // FAQs Tab
    var faqsHTML = '';
    if (data.faqs.length > 0) {
        data.faqs.forEach(function(faq, index) {
            faqsHTML += `
                <div class="faq-item">
                    <button class="faq-q">
                        ${faq.q}
                        <i class="fas fa-chevron-down"></i>
                    </button>
                    <div class="faq-a">${faq.a}</div>
                </div>
            `;
        });
    } else {
        faqsHTML = '<p style="color: rgba(255,255,255,0.7);">No FAQs available.</p>';
    }
    document.getElementById('faqsList').innerHTML = faqsHTML;

    // Attach FAQ Events
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

    // Init indicator
    if (tabs.length > 0) updateIndicator(tabs[0]);

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
    
    if (data.gallery.length > 0) {
        var slidesHTML = '';
        var dotsHTML = '';
        data.gallery.forEach(function(img, index) {
            slidesHTML += `
                <div class="ss-slide ${index === 0 ? 'active' : ''}">
                    <img src="${img}" alt="Screenshot ${index+1}">
                </div>
            `;
            dotsHTML += `<div class="ss-dot ${index === 0 ? 'active' : ''}" data-index="${index}"></div>`;
        });
        ssTrack.innerHTML = slidesHTML;
        ssDotsContainer.innerHTML = dotsHTML;

        var ssSlides = document.querySelectorAll('.ss-slide');
        var ssDots = document.querySelectorAll('.ss-dot');
        var ssCurrentIndex = 0;
        var ssTotal = ssSlides.length;

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

        // Keyboard navigation (when gallery is in view)
        document.addEventListener('keydown', function(e) {
            var rect = ssTrack.getBoundingClientRect();
            if (rect.top >= 0 && rect.bottom <= window.innerHeight) {
                if (e.key === 'ArrowLeft') updateGallery(ssCurrentIndex - 1);
                if (e.key === 'ArrowRight') updateGallery(ssCurrentIndex + 1);
            }
        });
    } else {
        ssTrack.innerHTML = '<p style="color: rgba(255,255,255,0.7); text-align:center; padding: 100px 0;">No screenshots available</p>';
        document.getElementById('ssPrev').style.display = 'none';
        document.getElementById('ssNext').style.display = 'none';
    }

});
