import os
import django
from django.core.files import File

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onesolai.settings")
django.setup()

from core.models import HeroSlide
from django.conf import settings

def fix_images():
    slides = HeroSlide.objects.all().order_by('order')
    if slides.count() < 2:
        print("Slides not found.")
        return

    slide1 = slides[0]
    slide2 = slides[1]

    # Path to static files
    img1_path = os.path.join(settings.BASE_DIR, 'static', 'assets', 'hero-image2.png')
    img2_path = os.path.join(settings.BASE_DIR, 'static', 'assets', 'images', 'hero-ai-platform.png')

    if os.path.exists(img1_path):
        with open(img1_path, 'rb') as f:
            slide1.image.save('hero-image2.png', File(f), save=True)
            print("Saved image for slide 1")
    else:
        print(f"Could not find {img1_path}")

    if os.path.exists(img2_path):
        with open(img2_path, 'rb') as f:
            slide2.image.save('hero-ai-platform.png', File(f), save=True)
            print("Saved image for slide 2")
    else:
        print(f"Could not find {img2_path}")

if __name__ == "__main__":
    fix_images()
