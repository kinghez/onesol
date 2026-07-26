import os

content = open('templates_admin_base.html').read()

# Replace navbar brand link
target1 = """                    <li class="nav-item">
                        <a href="{% url 'admin:index' %}" class="brand-link">
                            <img src="{% static jazzmin_settings.site_logo %}" alt="{{ jazzmin_settings.site_header }} Logo" class="{{ jazzmin_settings.site_logo_classes }} brand-image" style="opacity: .8; margin: 0 0 0 5px;">
                        </a>
                    </li>"""

replace1 = """                    <li class="nav-item">
                        <a href="{% url 'home' %}" class="brand-link" title="Go to OneSol AI Hub Home Page">
                            {% if site_settings.site_logo %}
                            <img src="{{ site_settings.site_logo.url }}" alt="{{ site_settings.site_name }} Logo" class="{{ jazzmin_settings.site_logo_classes }} brand-image" style="opacity: .9; max-height: 35px; width: auto; margin: 0 0 0 5px;">
                            {% else %}
                            <img src="{% static jazzmin_settings.site_logo %}" alt="{{ jazzmin_settings.site_header }} Logo" class="{{ jazzmin_settings.site_logo_classes }} brand-image" style="opacity: .9; margin: 0 0 0 5px;">
                            {% endif %}
                        </a>
                    </li>"""

# Replace sidebar brand link
target2 = """                <div class="sidebar-brand">
                    <a href="{% url 'admin:index' %}" class="brand-link {{ jazzmin_ui.brand_classes }}" id="jazzy-logo">
                        <img src="{% static jazzmin_settings.site_logo %}" alt="{{ jazzmin_settings.site_header }} Logo" class="{{ jazzmin_settings.site_logo_classes }} brand-image opacity-75 shadow">
                        <span class="brand-text fw-light">{{ jazzmin_settings.site_brand }}</span>
                    </a>
                </div>"""

replace2 = """                <div class="sidebar-brand">
                    <a href="{% url 'home' %}" class="brand-link {{ jazzmin_ui.brand_classes }}" id="jazzy-logo" title="Go to OneSol AI Hub Home Page">
                        {% if site_settings.site_logo %}
                        <img src="{{ site_settings.site_logo.url }}" alt="{{ site_settings.site_name }} Logo" class="{{ jazzmin_settings.site_logo_classes }} brand-image opacity-90 shadow" style="max-height: 35px; width: auto;">
                        {% else %}
                        <img src="{% static jazzmin_settings.site_logo %}" alt="{{ jazzmin_settings.site_header }} Logo" class="{{ jazzmin_settings.site_logo_classes }} brand-image opacity-90 shadow" style="max-height: 35px; width: auto;">
                        {% endif %}
                        <span class="brand-text fw-light">{{ site_settings.site_name }}</span>
                    </a>
                </div>"""

content = content.replace(target1, replace1)
content = content.replace(target2, replace2)

os.makedirs('templates/admin', exist_ok=True)
with open('templates/admin/base.html', 'w') as f:
    f.write(content)

print("Created templates/admin/base.html successfully!")
