import json
import time
import requests
import logging
from core.models import SiteSettings

logger = logging.getLogger(__name__)

def refine_product_copy(raw_name, raw_desc):
    """
    Calls OpenRouter API to clean and refine the product name and description.
    Handles rate limits using exponential backoff and sleep.
    Returns a dictionary with 'name', 'short_description', and 'description'.
    """
    settings = SiteSettings.get()
    api_key = settings.openrouter_api_key.strip()
    model = settings.openrouter_model.strip()

    if not api_key:
        return None

    prompt = f"""You are an expert copywriter and retail merchandiser.
I will provide you with a raw product name and description obtained from a B2B wholesale API.
Your job is to rewrite it into a clean, compelling, and professional B2C retail product format.

Rules:
1. TITLE FORMAT: The title MUST enable the user to immediately identify the core product provider (e.g., ChatGPT, Claude, Canva, Adobe).
2. TITLE DURATION: The title MUST include the subscription duration if present in the raw data (e.g., 12M, 30d, 1yr, 1 Month).
3. NO WARRANTY IN TITLE: The word "warranty" (or any variation like "full warranty", "no warranty", "24h warranty") MUST NEVER appear in the generated title. Move all warranty information into the description/features instead.
4. REMOVE JARGON: Remove all B2B/wholesale jargon (e.g., "login with 2 devices", "no refunds", "change pass freely", "API base URL", "KEY check page", "telegram links", "Source3", "canboso").
5. REMOVE LINKS: Do NOT include any URLs, contact info, or instructions on how to use it unless it's essential for the feature list.
6. PROFESSIONAL DESCRIPTION: The description should clearly highlight the value proposition and features. Write it professionally and format it using HTML tags (e.g. <ul><li>...</li></ul>, <br>, <strong>...</strong>) so it renders beautifully on the frontend.
7. SHORT DESCRIPTION: Create a very brief 'short_description' (max 150 chars).
8. JSON ONLY: Output ONLY valid JSON, with exactly these three keys: "name", "short_description", "description". No markdown blocks or extra text.

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
                # Rate limited
                delay = base_delay * (2 ** attempt)
                logger.warning(f"OpenRouter rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            
            # OpenRouter might wrap in markdown blocks despite instructions
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
                
            result = json.loads(content)
            
            # Ensure required keys exist
            return {
                "name": result.get("name", raw_name),
                "short_description": result.get("short_description", ""),
                "description": result.get("description", raw_desc)
            }
            
        except Exception as e:
            logger.error(f"AI Refinement Error (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
            else:
                return None
    
    return None
