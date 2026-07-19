import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onesolai.settings")
django.setup()

from core.models import SiteSettings

settings = SiteSettings.get()
settings.openrouter_model = "openrouter/auto"  # actually, let me check if openrouter/auto or openrouter/free
# Wait, the search result said openrouter/free. Let's use openrouter/auto to be safe. Actually, the search result explicitly said `openrouter/free`. Let me just use openrouter/free.
settings.openrouter_model = "openrouter/free"
settings.save()
print("Updated OpenRouter model in DB to", settings.openrouter_model)
