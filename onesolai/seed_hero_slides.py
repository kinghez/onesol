import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onesolai.settings")
django.setup()

from core.models import HeroSlide

def seed_slides():
    if HeroSlide.objects.exists():
        print("Slides already exist.")
        return

    # Slide 1
    HeroSlide.objects.create(
        title_line_1="Premium AI & SaaS",
        title_line_2_start="Tools.",
        title_line_2_highlight="Affordable",
        title_line_2_end="for",
        title_line_3="Everyone in Africa.",
        description="Get access to 100+ premium AI and SaaS tools<br>at the best prices. Pay in your local currency<br>and get instant access.",
        primary_button_text="Browse Tools",
        primary_button_url="/tools/",
        secondary_button_text="How It Works",
        secondary_button_url="#",
        show_features_block=True,
        order=1,
        is_active=True
    )
    
    # Slide 2
    HeroSlide.objects.create(
        title_line_1="Unlock the Power of AI.",
        title_line_2_start="Access Affordable,",
        title_line_2_highlight="Powerful",
        title_line_2_end="",
        title_line_3="AI & SaaS Tools in Africa.",
        description="Automate, Create, and Scale with OneSol AI Hub.<br>Direct access with instant local payments.",
        primary_button_text="Explore Our AI Tools",
        primary_button_url="/tools/",
        primary_button_icon="fas fa-compass",
        secondary_button_text="Learn More",
        secondary_button_url="#",
        show_features_block=False,
        order=2,
        is_active=True
    )
    print("Successfully created default hero slides.")

if __name__ == "__main__":
    seed_slides()
