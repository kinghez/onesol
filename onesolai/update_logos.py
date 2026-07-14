import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')
django.setup()

from products.models import Tool

# Map slug -> local static path filename (files already exist in static/assets/images/logos/)
logo_map = {
    'chatgpt-plus':       'chatgpt.svg',
    'canva-pro':          'canva.svg',
    'midjourney':         'midjourney.svg',
    'grammarly-premium':  'grammarly.svg',
    'notion-plus':        'notion.svg',
    'claude-pro':         'claude.svg',
    'gemini-advanced':    'adobefirefly.svg',   # placeholder until gemini svg added
    'perplexity-pro':     'copyai.svg',          # placeholder until perplexity svg added
}

updated = 0
for slug, filename in logo_map.items():
    # Store relative static path that Django will serve at /static/assets/images/logos/...
    static_path = f'/static/assets/images/logos/{filename}'
    count = Tool.objects.filter(slug=slug).update(image_url=static_path)
    if count:
        print(f"  Updated: {slug} -> {static_path}")
        updated += count
    else:
        print(f"  NOT FOUND: {slug}")

print(f"\nDone. {updated} tool(s) updated.")
