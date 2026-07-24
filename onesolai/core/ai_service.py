import json
import time
import requests
import logging
import re
from core.models import SiteSettings

logger = logging.getLogger(__name__)


def clean_tool_title(title):
    """
    Cleans up title duration abbreviations and removes warranty jargon:
    - 12m / 12M -> 12 Months
    - 1m / 1M / 1mo -> 1 Month
    - 1y / 1Y / 1yr -> 1 Year
    - 7d / 7D -> 7 Days
    - Strips 'FW', 'FW-', 'Warranty', etc.
    """
    if not title:
        return title

    # Remove warranty jargon from title
    title = re.sub(r'(?i)\b(fw|fw-|full\s*warranty|warranty|24h-warranty|24h\s*warranty)\b', '', title)

    # Expand duration abbreviations (e.g. 12m -> 12 Months, 1m -> 1 Month, 1y -> 1 Year, 7d -> 7 Days)
    def replace_duration(match):
        num = match.group(1)
        unit = match.group(2).lower()
        if unit.startswith('y'):
            return f"{num} Year" if num == '1' else f"{num} Years"
        elif unit.startswith('m'):
            return f"{num} Month" if num == '1' else f"{num} Months"
        elif unit.startswith('d'):
            return f"{num} Day" if num == '1' else f"{num} Days"
        return match.group(0)

    title = re.sub(r'\b(\d+)\s*([mMyYdD](?:yr|mo|days|months)?)\b', replace_duration, title)

    # Clean double spaces, dashes, or trailing characters
    title = re.sub(r'\s+', ' ', title).strip(' -_,')
    return title


def refine_product_copy(raw_name, raw_desc, available_categories=None):
    """
    Calls OpenRouter API to clean and refine the product name, short description, 
    bulleted feature description, and assign the best matching category.
    Handles rate limits using exponential backoff and sleep.
    Returns a dictionary with 'name', 'short_description', 'description', and 'category'.
    """
    settings = SiteSettings.get()
    api_key = settings.openrouter_api_key.strip()
    model = settings.openrouter_model.strip()

    if not api_key:
        return None

    if available_categories is None:
        try:
            from products.models import Category
            available_categories = list(Category.objects.values_list('name', flat=True))
        except Exception:
            available_categories = []

    categories_str = ", ".join([f'"{c}"' for c in available_categories]) if available_categories else "General"

    prompt = f"""You are an expert copywriter and retail merchandiser.
I will provide you with a raw product name and description obtained from a B2B wholesale API.
Your job is to rewrite it into a clean, compelling, and professional B2C retail product format.

Rules:
1. TITLE FORMAT: The title MUST enable the user to immediately identify the core product provider (e.g., ChatGPT, Claude, Canva, Adobe, Gemini).
2. EXPAND DURATION IN TITLE: Convert all duration abbreviations in titles into full, clear words so users easily understand the plan duration:
   - "12m" / "12M" -> "12 Months"
   - "1m" / "1M" / "1mo" -> "1 Month"
   - "3m" / "3M" -> "3 Months"
   - "6m" / "6M" -> "6 Months"
   - "1y" / "1Y" / "1yr" -> "1 Year"
   - "7d" / "7D" -> "7 Days"
   - "30d" / "30D" -> "30 Days"
3. NO WARRANTY OR FW IN TITLE: The terms "warranty", "FW", "FW-", "full warranty", "24h warranty" MUST NEVER appear in the title. Move all warranty details into the description instead.
4. REMOVE JARGON: Remove all B2B/wholesale jargon (e.g., "login with 2 devices", "no refunds", "change pass freely", "API base URL", "KEY check page", "telegram links", "Source3", "canboso").
5. REMOVE LINKS: Do NOT include any URLs, contact info, or external links.
6. DESCRIPTION STRUCTURE: The 'description' MUST start with a short 1-2 sentence introductory summary (<p>...</p>), followed immediately by clean HTML bullet points (<ul><li>✓ Feature 1</li><li>✓ Feature 2</li>...</ul>) listing key features, plan specifications, access rules, and warranty.
7. SHORT DESCRIPTION: Create a plain text short description (1 sentence, max 150 chars) for card summaries.
8. CATEGORY SELECTION: Choose the single best matching category for this product from this exact list of categories: [{categories_str}]. If none fit perfectly, choose the closest match.
9. JSON ONLY: Output ONLY valid JSON with exactly these four keys: "name", "short_description", "description", "category". No markdown blocks or extra text.

Raw Name: {raw_name}
Raw Description: {raw_desc}
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": settings.site_url,
        "X-Title": settings.site_name,
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    max_retries = 3
    base_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            
            if response.status_code == 429:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"OpenRouter rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content'].strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
                
            result = json.loads(content)
            
            ai_name = result.get("name", raw_name)
            ai_name = clean_tool_title(ai_name)
            
            short_desc = result.get("short_description", "").strip()
            desc_body = result.get("description", raw_desc).strip()
            
            # Ensure description starts with the short intro paragraph before bulleted list
            if short_desc and not desc_body.startswith(short_desc) and not desc_body.startswith('<p>' + short_desc):
                full_description = f"<p>{short_desc}</p>\n{desc_body}"
            else:
                full_description = desc_body
            
            return {
                "name": ai_name,
                "short_description": short_desc,
                "description": full_description,
                "category": result.get("category", "")
            }
            
        except Exception as e:
            logger.error(f"AI Refinement Error (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
            else:
                return None
    
    return None
