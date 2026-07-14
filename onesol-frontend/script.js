/* =============================================
   OneSol AI Hub – JavaScript
   Canvas background + Hero parallax + Particles
   ============================================= */

document.addEventListener('DOMContentLoaded', function () {

    // ═══════════════════════════════════
    // 1. BACKGROUND CANVAS (grid + particles)
    // ═══════════════════════════════════
    var canvas = document.getElementById('bgCanvas');
    if (canvas) {
        var ctx = canvas.getContext('2d');
        var bgParticles = [];
        var W, H;

        function resize() {
            W = canvas.width = window.innerWidth;
            H = canvas.height = window.innerHeight;
        }
    resize();
    window.addEventListener('resize', resize);

    // Cached grid
    var gridImg = null;

    function buildGrid() {
        var c = document.createElement('canvas');
        c.width = W;
        c.height = H * 2;
        var g = c.getContext('2d');
        var sp = 90;

        g.strokeStyle = 'rgba(49,92,255,0.025)';
        g.lineWidth = 0.5;

        for (var x = 0; x < c.width; x += sp) {
            g.beginPath();
            g.moveTo(x, 0);
            g.lineTo(x, c.height);
            g.stroke();
        }
        for (var y = 0; y < c.height; y += sp) {
            g.beginPath();
            g.moveTo(0, y);
            g.lineTo(c.width, y);
            g.stroke();
        }

        g.fillStyle = 'rgba(93,134,255,0.04)';
        for (var x2 = sp; x2 < c.width; x2 += sp * 4) {
            for (var y2 = sp; y2 < c.height; y2 += sp * 4) {
                if (Math.sin(x2 * 0.1 + y2 * 0.13) > 0.4) {
                    g.beginPath();
                    g.arc(x2, y2, 1.5, 0, Math.PI * 2);
                    g.fill();
                }
            }
        }

        gridImg = c;
    }
    buildGrid();
    window.addEventListener('resize', function () {
        resize();
        buildGrid();
        initBgParticles();
    });

    // Background particles
    var bgColors = [
        { r: 93, g: 134, b: 255 },
        { r: 80, g: 110, b: 230 },
        { r: 110, g: 80, b: 220 },
        { r: 217, g: 182, b: 122 },
        { r: 255, g: 255, b: 255 },
    ];
    var bgWeights = [30, 22, 18, 10, 20];

    function pickBgColor() {
        var total = 0;
        for (var i = 0; i < bgWeights.length; i++) total += bgWeights[i];
        var r = Math.random() * total;
        for (var j = 0; j < bgWeights.length; j++) {
            r -= bgWeights[j];
            if (r <= 0) return bgColors[j];
        }
        return bgColors[0];
    }

    function BgParticle(initial) { this.reset(initial); }

    BgParticle.prototype.reset = function (initial) {
        this.x = Math.random() * W;
        this.y = initial ? Math.random() * H : -5;
        this.size = Math.random() * 1.6 + 0.2;
        this.vx = (Math.random() - 0.5) * 0.12;
        this.vy = Math.random() * 0.08 + 0.01;
        this.baseAlpha = Math.random() * 0.45 + 0.15;
        this.alpha = this.baseAlpha;
        this.da = (Math.random() - 0.5) * 0.006;
        this.col = pickBgColor();
        this.isStar = (this.col.r === 255 && this.col.g === 255 && this.size < 0.9);
    };

    BgParticle.prototype.update = function () {
        this.x += this.vx;
        this.y += this.vy;
        this.alpha += this.da;
        if (this.alpha < 0.08 || this.alpha > 0.58) this.da *= -1;
        if (this.y > H + 10 || this.x < -15 || this.x > W + 15) this.reset(false);
    };

    BgParticle.prototype.draw = function () {
        var c = this.col;
        if (this.isStar) {
            ctx.strokeStyle = 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + this.alpha + ')';
            ctx.lineWidth = 0.4;
            var s = this.size * 1.8;
            ctx.beginPath();
            ctx.moveTo(this.x - s, this.y);
            ctx.lineTo(this.x + s, this.y);
            ctx.moveTo(this.x, this.y - s);
            ctx.lineTo(this.x, this.y + s);
            ctx.stroke();
        } else {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + this.alpha + ')';
            ctx.fill();
            if (this.size > 1) {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size * 2.8, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + (this.alpha * 0.08) + ')';
                ctx.fill();
            }
        }
    };

    function initBgParticles() {
        var area = W * H;
        var count = Math.min(Math.floor(area / 8000), 140);
        bgParticles = [];
        for (var i = 0; i < count; i++) {
            bgParticles.push(new BgParticle(true));
        }
    }
    initBgParticles();

        function canvasLoop() {
            ctx.clearRect(0, 0, W, H);
            if (gridImg) ctx.drawImage(gridImg, 0, 0, W, H);
            for (var i = 0; i < bgParticles.length; i++) {
                bgParticles[i].update();
                bgParticles[i].draw();
            }
            requestAnimationFrame(canvasLoop);
        }
        canvasLoop();
    }

    // ═══════════════════════════════════
    // 2. NAVBAR SCROLL
    // ═══════════════════════════════════
    var nav = document.getElementById('nav');
    window.addEventListener('scroll', function () {
        if (nav) {
            if (window.scrollY > 50) {
                nav.classList.add('scrolled');
            } else {
                nav.classList.remove('scrolled');
            }
        }
    }, { passive: true });


    // ═══════════════════════════════════
    // 3. MOBILE MENU
    // ═══════════════════════════════════
    var mob = document.getElementById('navMob');
    var links = document.getElementById('navLinks');

    if (mob && links) {
        mob.addEventListener('click', function () {
            links.classList.toggle('active');
        });
        links.querySelectorAll('.nav-a').forEach(function (a) {
            a.addEventListener('click', function () {
                links.classList.remove('active');
            });
        });
    }


    // ═══════════════════════════════════
    // 4. HERO IMAGE MOUSE PARALLAX
    // ═══════════════════════════════════
    var heroEl = document.getElementById('heroIllust');
    var heroImg = heroEl ? heroEl.querySelector('.hero-image') : null;
    var maxMove = 12; // px
    var currentX = 0;
    var currentY = 0;
    var targetX = 0;
    var targetY = 0;
    var lerp = 0.06; // smooth interpolation factor

    if (heroEl && heroImg) {
        document.addEventListener('mousemove', function (e) {
            // Normalize mouse position to -1 to 1
            var nx = (e.clientX / window.innerWidth - 0.5) * 2;
            var ny = (e.clientY / window.innerHeight - 0.5) * 2;
            targetX = nx * maxMove;
            targetY = ny * maxMove;
        });

        function parallaxLoop() {
            // Smooth lerp towards target
            currentX += (targetX - currentX) * lerp;
            currentY += (targetY - currentY) * lerp;

            // Apply transform (combined with the float animation via CSS)
            heroImg.style.transform = 'translate(' + currentX.toFixed(2) + 'px,' + currentY.toFixed(2) + 'px)';

            requestAnimationFrame(parallaxLoop);
        }
        parallaxLoop();
    }


    // ═══════════════════════════════════
    // 4.5 HERO CAROUSEL
    // ═══════════════════════════════════
    var heroCarousel = document.getElementById('heroCarousel');
    var heroTrack = document.getElementById('heroTrack');
    var heroSlides = document.querySelectorAll('.hero-slide');
    if (heroCarousel && heroTrack && heroSlides.length > 1) {
        var currentIndex = 0;
        var totalSlides = heroSlides.length;
        var heroDots = document.querySelectorAll('.h-dot');
        var autoplayInterval;
        
        var updateCarousel = function(index) {
            currentIndex = index;
            if (currentIndex < 0) currentIndex = totalSlides - 1;
            if (currentIndex >= totalSlides) currentIndex = 0;
            
            heroTrack.style.transform = 'translateX(-' + (currentIndex * (100 / totalSlides)) + '%)';
            
            heroSlides.forEach(function(s, i) {
                s.classList.toggle('active', i === currentIndex);
                if (heroDots[i]) heroDots[i].classList.toggle('active', i === currentIndex);
            });
        };

        var nextSlide = function() { updateCarousel(currentIndex + 1); };
        var prevSlide = function() { updateCarousel(currentIndex - 1); };

        var prevBtn = document.getElementById('heroPrev');
        var nextBtn = document.getElementById('heroNext');
        if (prevBtn) prevBtn.addEventListener('click', prevSlide);
        if (nextBtn) nextBtn.addEventListener('click', nextSlide);

        heroDots.forEach(function(dot) {
            dot.addEventListener('click', function() {
                updateCarousel(parseInt(this.getAttribute('data-index')));
            });
        });

        var startAutoplay = function() {
            clearInterval(autoplayInterval);
            autoplayInterval = setInterval(nextSlide, 6000);
        };
        var stopAutoplay = function() { clearInterval(autoplayInterval); };

        startAutoplay();
        heroCarousel.addEventListener('mouseenter', stopAutoplay);
        heroCarousel.addEventListener('mouseleave', startAutoplay);

        document.addEventListener('keydown', function(e) {
            if (window.scrollY < window.innerHeight) {
                if (e.key === 'ArrowLeft') prevSlide();
                if (e.key === 'ArrowRight') nextSlide();
            }
        });

        var isDragging = false;
        var startPos = 0;
        var currentTranslate = 0;
        var prevTranslate = 0;
        var animationID;

        var getPositionX = function(e) { return e.type.includes('mouse') ? e.pageX : e.touches[0].clientX; };

        var setSliderPosition = function() { heroTrack.style.transform = 'translateX(' + currentTranslate + 'px)'; };

        var animation = function() {
            setSliderPosition();
            if (isDragging) requestAnimationFrame(animation);
        };

        var touchStart = function(e) {
            isDragging = true;
            startPos = getPositionX(e);
            prevTranslate = -currentIndex * (heroTrack.clientWidth / totalSlides);
            animationID = requestAnimationFrame(animation);
            heroTrack.style.transition = 'none';
            stopAutoplay();
        };

        var touchMove = function(e) {
            if (isDragging) {
                var currentPosition = getPositionX(e);
                currentTranslate = prevTranslate + currentPosition - startPos;
            }
        };

        var touchEnd = function() {
            isDragging = false;
            cancelAnimationFrame(animationID);
            heroTrack.style.transition = 'transform 600ms ease';

            var movedBy = currentTranslate - prevTranslate;
            
            if (movedBy < -100 && currentIndex < totalSlides - 1) currentIndex += 1;
            else if (movedBy > 100 && currentIndex > 0) currentIndex -= 1;
            else if (movedBy < -100 && currentIndex === totalSlides - 1) currentIndex = 0;
            else if (movedBy > 100 && currentIndex === 0) currentIndex = totalSlides - 1;
            
            updateCarousel(currentIndex);
            startAutoplay();
        };

        heroTrack.addEventListener('mousedown', touchStart);
        heroTrack.addEventListener('mousemove', touchMove);
        heroTrack.addEventListener('mouseup', touchEnd);
        heroTrack.addEventListener('mouseleave', function() { if (isDragging) touchEnd(); });

        heroTrack.addEventListener('touchstart', touchStart, {passive: true});
        heroTrack.addEventListener('touchmove', touchMove, {passive: true});
        heroTrack.addEventListener('touchend', touchEnd);
    }


    // ═══════════════════════════════════
    // 5. CARD 3D TILT
    // ═══════════════════════════════════
    document.querySelectorAll('.card').forEach(function (card) {
        card.addEventListener('mousemove', function (e) {
            var r = card.getBoundingClientRect();
            var x = e.clientX - r.left;
            var y = e.clientY - r.top;
            var cx = r.width / 2;
            var cy = r.height / 2;
            var rx = ((y - cy) / cy) * 3;
            var ry = ((cx - x) / cx) * 3;
            card.style.transform = 'translateY(-5px) perspective(800px) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg)';
        });
        card.addEventListener('mouseleave', function () {
            card.style.transform = '';
        });
    });


    // ═══════════════════════════════════
    // 6. HERO TEXT STAGGER
    // ═══════════════════════════════════
    var hLines = document.querySelectorAll('.hero-h1 > span');
    hLines.forEach(function (el, i) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(12px)';
        el.style.transition = 'opacity .6s ease ' + (0.3 + i * 0.14) + 's, transform .6s ease ' + (0.3 + i * 0.14) + 's';
        setTimeout(function () {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, 80);
    });
    // ═══════════════════════════════════
    // 6. HERO TEXT STAGGER
    // ═══════════════════════════════════
    var hLines = document.querySelectorAll('.hero-h1 > span');
    hLines.forEach(function (el, i) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(12px)';
        el.style.transition = 'opacity .6s ease ' + (0.3 + i * 0.14) + 's, transform .6s ease ' + (0.3 + i * 0.14) + 's';
        setTimeout(function () {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, 80);
    });

    // ═══════════════════════════════════
    // 6.5 REUSABLE TOOL CARD COMPONENT
    // ═══════════════════════════════════
    function getSecondaryPrice(priceStr) {
        const num = parseInt(priceStr.replace(/,/g, ''), 10);
        if (isNaN(num)) return "";
        const ghs = Math.round(num / 42.85);
        const kes = Math.round(num / 3.57);
        return `₵${ghs.toLocaleString()} GHS / Ksh ${kes.toLocaleString()} KES`;
    }

    window.createToolCard = function(tool, count = 0, extraStyle = "") {
        let badgeHtml = '';
        if (tool.badge) {
            let badgeClass = '';
            if (tool.badge === 'Popular') badgeClass = 'badge-pop';
            else if (tool.badge === 'Best Seller') badgeClass = 'badge-best';
            else if (tool.badge === 'New') badgeClass = 'badge-new';
            badgeHtml = `<div class="tt-badge ${badgeClass}">${tool.badge}</div>`;
        }

        const secPrice = getSecondaryPrice(tool.price);
        const description = tool.desc || tool.description || tool.category;
        const slug = tool.name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');

        return `
            <div class="tt-card fade-in card" style="animation-delay: ${count * 0.05}s; ${extraStyle}">
                <div class="tt-card-header">
                    <img src="${tool.icon}" alt="${tool.name}" class="tt-logo">
                    <h3 class="tt-name">${tool.name}</h3>
                </div>
                <p class="tt-description">${description}</p>
                <div class="tt-price-section">
                    <div class="tt-price-label">MONTHLY</div>
                    <div class="tt-price">
                        <span class="tt-price-val">NGN ${tool.price}</span> <span class="tt-price-mo">/ mo</span>
                    </div>
                    <div class="tt-price-secondary">${secPrice}</div>
                </div>
                <div class="tt-badges-container">
                    ${badgeHtml}
                </div>
                <button class="tt-buy-btn" onclick="window.location.href='tool.html?slug=${slug}'">Buy Now</button>
            </div>
        `;
    };

    // Helper to re-bind 3D tilt after dynamic injection
    function bindCardTilt(container) {
        if (!container) return;
        container.querySelectorAll('.card').forEach(function (card) {
            card.addEventListener('mousemove', function (e) {
                var r = card.getBoundingClientRect();
                var x = e.clientX - r.left;
                var y = e.clientY - r.top;
                var cx = r.width / 2;
                var cy = r.height / 2;
                var rx = ((y - cy) / cy) * 3;
                var ry = ((cx - x) / cx) * 3;
                card.style.transform = 'translateY(-4px) perspective(800px) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg)';
            });
            card.addEventListener('mouseleave', function () {
                card.style.transform = '';
            });
        });
    }

    // ═══════════════════════════════════
    // 6.6 TOP TOOLS DATA (from index.html)
    // ═══════════════════════════════════
    const topToolsGrid = document.getElementById('topToolsGrid');
    if (topToolsGrid) {
        const topToolsData = [
            { name: "ChatGPT Plus", category: "AI Chatbot", price: "5,500", rating: "4.8", badge: "Popular", icon: "assets/images/logos/chatgpt.svg" },
            { name: "Midjourney", category: "AI Image Generation", price: "6,800", rating: "4.9", badge: "Best Seller", icon: "assets/images/logos/midjourney.svg" },
            { name: "Canva Pro", category: "Design", price: "4,200", rating: "4.8", badge: "Popular", icon: "assets/images/logos/canva.svg" },
            { name: "Grammarly Premium", category: "Writing Assistant", price: "3,200", rating: "4.7", badge: null, icon: "assets/images/logos/grammarly.svg" },
            { name: "Notion Plus", category: "Productivity", price: "4,000", rating: "4.7", badge: null, icon: "assets/images/logos/notion.svg" },
            { name: "Claude Pro", category: "AI Assistant", price: "6,500", rating: "4.9", badge: null, icon: "assets/images/logos/claude.svg" }
        ];
        
        let html = '';
        topToolsData.forEach((tool, index) => {
            html += window.createToolCard(tool, index);
        });
        topToolsGrid.innerHTML = html;
        bindCardTilt(topToolsGrid);
    }

    // ═══════════════════════════════════
    // 7. POPULAR THIS WEEK (Dynamic Cards & Tabs)
    // ═══════════════════════════════════
    const popularThisWeek = [
      {
        name: "Copy.ai Pro",
        category: "AI Chatbots",
        description: "AI Copywriting",
        price: "3,000",
        rating: "4.6",
        badge: "Popular",
        icon: "assets/images/logos/copyai.svg"
      },
      {
        name: "Jasper",
        category: "Writing",
        description: "AI Content Creator",
        price: "4,500",
        rating: "4.8",
        badge: null,
        icon: "assets/images/logos/jasper.svg"
      },
      {
        name: "Suno Pro",
        category: "AI Music Generation",
        description: "AI Music Generation",
        price: "4,200",
        rating: "4.7",
        badge: "New",
        icon: "assets/images/logos/suno.svg"
      },
      {
        name: "Pictory",
        category: "Video Creation",
        description: "AI Video Creation",
        price: "3,500",
        rating: "4.6",
        badge: null,
        icon: "assets/images/logos/pictory.svg"
      },
      {
        name: "Descript",
        category: "Audio & Video Editor",
        description: "Audio & Video Editor",
        price: "4,000",
        rating: "4.6",
        badge: "Popular",
        icon: "assets/images/logos/descript.svg"
      },
      {
        name: "ElevenLabs",
        category: "AI Voice Generation",
        description: "AI Voice Generation",
        price: "3,800",
        rating: "4.8",
        badge: null,
        icon: "assets/images/logos/elevenlabs.svg"
      }
    ];

    const pwGrid = document.getElementById('pwGrid');
    const pwTabs = document.querySelectorAll('.pw-tab');

    if (pwGrid && pwTabs.length > 0) {
        // Render cards
        function renderCards(filter) {
            pwGrid.innerHTML = '';
            
            let count = 0;
            popularThisWeek.forEach((item, index) => {
                if (filter !== 'all' && item.category !== filter) return;
                
                count++;
                pwGrid.insertAdjacentHTML('beforeend', window.createToolCard(item, count));
            });
            
            // Re-bind 3D tilt to new cards
            bindCardTilt(pwGrid);
        }

        renderCards('all');

        // Tab click events
        pwTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                // Update active class
                pwTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                const filter = tab.getAttribute('data-filter');
                
                // Animate out current cards
                const currentCards = pwGrid.querySelectorAll('.tt-card');
                currentCards.forEach(c => {
                    c.classList.add('filtered-out');
                    c.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                });
                
                // Wait for animation then re-render
                setTimeout(() => {
                    renderCards(filter);
                }, 250);
            });
        });
    }

    // ═══════════════════════════════════
    // 8. ALL TOOLS PAGE (tools.html)
    // ═══════════════════════════════════
    const allToolsGrid = document.getElementById('allToolsGrid');
    if (allToolsGrid) {
        const allToolsData = [
            { name: "ChatGPT Plus", desc: "AI Chatbot", price: "5,500", rating: "4.8", badge: "Popular", icon: "assets/images/logos/chatgpt.svg" },
            { name: "Midjourney", desc: "AI Image Generation", price: "6,800", rating: "4.9", badge: "Best Seller", icon: "assets/images/logos/midjourney.svg" },
            { name: "Canva Pro", desc: "Design", price: "4,200", rating: "4.8", badge: "Popular", icon: "assets/images/logos/canva.svg" },
            { name: "Grammarly Premium", desc: "Writing Assistant", price: "3,200", rating: "4.7", badge: null, icon: "assets/images/logos/grammarly.svg" },
            { name: "Notion Plus", desc: "Productivity", price: "4,000", rating: "4.7", badge: null, icon: "assets/images/logos/notion.svg" },
            { name: "Claude Pro", desc: "AI Assistant", price: "6,500", rating: "4.9", badge: "New", icon: "assets/images/logos/claude.svg" },
            { name: "Copy.ai", desc: "Copywriting", price: "3,000", rating: "4.6", badge: "Popular", icon: "assets/images/logos/copyai.svg" },
            { name: "Jasper", desc: "AI Content", price: "4,500", rating: "4.8", badge: "Popular", icon: "assets/images/logos/jasper.svg" },
            { name: "Adobe Firefly", desc: "AI Design", price: "4,200", rating: "4.7", badge: "New", icon: "assets/images/logos/adobefirefly.svg" }
        ];

        let html = '';
        allToolsData.forEach(tool => {
            html += window.createToolCard(tool, 0, "opacity:1; transform:none; pointer-events:auto;");
        });
        allToolsGrid.innerHTML = html;

        // Apply 3D tilt to newly generated cards
        bindCardTilt(allToolsGrid);
    }

    // ═══════════════════════════════════
    // 9. HORIZONTAL SCROLL NAVIGATION
    // ═══════════════════════════════════
    document.querySelectorAll('.tt-grid-wrapper').forEach(wrapper => {
        const grid = wrapper.querySelector('.tt-grid');
        const btnPrev = wrapper.querySelector('.tt-nav-btn.prev');
        const btnNext = wrapper.querySelector('.tt-nav-btn.next');

        if (!grid) return;

        // Scroll event to toggle prev button visibility
        grid.addEventListener('scroll', () => {
            if (btnPrev) {
                if (grid.scrollLeft > 20) {
                    btnPrev.classList.add('visible');
                } else {
                    btnPrev.classList.remove('visible');
                }
            }
        });

        // Next button click
        if (btnNext) {
            btnNext.addEventListener('click', () => {
                grid.scrollBy({ left: 300, behavior: 'smooth' });
            });
        }

        // Prev button click
        if (btnPrev) {
            btnPrev.addEventListener('click', () => {
                grid.scrollBy({ left: -300, behavior: 'smooth' });
            });
        }
    });

});
