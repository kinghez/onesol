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


def deterministic_clean_credentials(raw_text: str, tool_name: str = "") -> str:
    """
    Fallback deterministic parser to structure messy credentials if AI service is unavailable.
    Handles activation links, JSON blocks, pipe-separated accounts, colon-separated credentials, and license keys.
    """
    if not raw_text or not raw_text.strip():
        return raw_text

    raw_text = raw_text.strip()

    # Clean leading wrappers
    clean_raw = re.sub(r'^(\[Auto-Fulfilled Credentials\]\s*)?', '', raw_text).strip()
    clean_raw = re.sub(r'^(Code:\s*)+', '', clean_raw).strip()

    # 0. Check for Direct Activation / Claim Links (e.g. Gemini Pro from Akunding or Stock Lara)
    lines = [l.strip() for l in clean_raw.splitlines() if l.strip()]
    cleaned_lines = [re.sub(r'^(Code|Link|User|URL):\s*', '', l, flags=re.I).strip() for l in lines]
    urls = [l for l in cleaned_lines if l.startswith(('http://', 'https://'))]
    if urls and len(urls) == len(cleaned_lines):
        if len(urls) == 1:
            return (
                f"🔗 Subscription Activation Link\n\n"
                f"Product: {tool_name or 'Software Tool'}\n\n"
                f"Activation Link:\n{urls[0]}\n\n"
                f"👉 Instructions:\n"
                f"Open or copy the link above into your browser to claim and activate your subscription."
            )
        else:
            links_formatted = "\n\n".join(f"Link {i+1}:\n{u}" for i, u in enumerate(urls))
            return (
                f"🔗 Subscription Activation Links\n\n"
                f"Product: {tool_name or 'Software Tool'}\n\n"
                f"{links_formatted}\n\n"
                f"👉 Instructions:\n"
                f"Open each link above in your browser to activate your subscriptions."
            )

    # 1. Check for JSON blocks (single JSON object, list of objects, or line-by-line JSON)
    json_objects = []
    s_idx = clean_raw.find('{')
    e_idx = clean_raw.rfind('}')
    if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
        try:
            parsed = json.loads(clean_raw[s_idx:e_idx+1])
            if isinstance(parsed, dict) and any(k in parsed for k in ['email', 'password', 'pass', 'user', '2fa', 'tokens', 'code', 'uid', 'account_id']):
                json_objects.append(parsed)
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        json_objects.append(item)
        except Exception:
            pass

    if not json_objects:
        for line in clean_raw.splitlines():
            s = line.find('{')
            e = line.rfind('}')
            if s != -1 and e != -1 and e > s:
                try:
                    obj = json.loads(line[s:e+1])
                    if isinstance(obj, dict):
                        json_objects.append(obj)
                except Exception:
                    pass

    if json_objects:
        outputs = []
        for i, acc in enumerate(json_objects):
            title = f"{tool_name} — Account {i+1}" if len(json_objects) > 1 and tool_name else ("🔐 Login Credentials" if len(json_objects) == 1 else f"Account {i+1}")
            email = acc.get('email') or acc.get('user') or acc.get('username') or acc.get('mail') or ''
            password = acc.get('password') or acc.get('pass') or acc.get('pwd') or ''
            two_fa = acc.get('2fa') or acc.get('two_factor') or acc.get('secret') or acc.get('totp') or ''
            account_id = acc.get('account_id') or acc.get('uid') or acc.get('id') or ''

            lines_out = [title, ""]
            if email:
                lines_out.append(f"Email: {email}")
            if password:
                lines_out.append(f"Password: {password}")
            if two_fa:
                lines_out.append(f"2FA Secret Key: {two_fa}")
            if account_id:
                lines_out.append(f"Account ID: {account_id}")
            if two_fa:
                lines_out.append("\n👉 2FA Code Generator: Paste key at https://2fa.live")
            outputs.append("\n".join(lines_out).strip())
        return "\n\n----------------------------------------\n\n".join(outputs)

    # 2. Try line-by-line pipe or colon extraction
    raw_lines = [l.strip() for l in clean_raw.splitlines() if l.strip()]
    parsed_accounts = []
    for line in raw_lines:
        clean_l = re.sub(r'^\d+[\.\)]\s*', '', line) # Strip leading "1. " or "1) "
        clean_l = re.sub(r'^(Code|User):\s*', '', clean_l, flags=re.I)

        # Check for pipe separated
        if '|' in clean_l:
            raw_parts = [p.strip() for p in re.split(r'\s*\|\s*', clean_l) if p.strip()]
            parts = [re.sub(r'^(User|Pass|Password|Email|Username|Pwd|Key|2FA):\s*', '', p, flags=re.I).strip() for p in raw_parts]
        elif ':' in clean_l and '@' in clean_l and not clean_l.startswith('http') and not '{' in clean_l:
            raw_parts = [p.strip() for p in clean_l.split(':') if p.strip()]
            parts = [re.sub(r'^(User|Pass|Password|Email|Username|Pwd|Key|2FA):\s*', '', p, flags=re.I).strip() for p in raw_parts]
        else:
            parts = []

        if len(parts) >= 2:
            email = None
            password = None
            two_fa = None
            account_id = None
            for p in parts:
                if '@' in p and '.' in p and not email:
                    email = p
                elif re.match(r'^[A-Z0-9]{16,64}$', p) and not two_fa and not p.lower().startswith('http'):
                    two_fa = p
                elif re.match(r'^\d{10,20}$', p) and not account_id:
                    account_id = p
                elif not password:
                    password = p
                elif not two_fa:
                    two_fa = p

            if email or password:
                parsed_accounts.append({
                    'email': email or parts[0],
                    'password': password or (parts[1] if len(parts) > 1 else ''),
                    'two_fa': two_fa or (parts[2] if len(parts) > 2 else ''),
                    'account_id': account_id or ''
                })

    if parsed_accounts:
        outputs = []
        for i, acc in enumerate(parsed_accounts):
            title = f"{tool_name} — Account {i+1}" if len(parsed_accounts) > 1 and tool_name else ("🔐 Login Credentials" if len(parsed_accounts) == 1 else f"Account {i+1}")
            lines_out = [title, ""]
            if len(parsed_accounts) > 1:
                if acc['email']:
                    lines_out.append(f"Email:\n{acc['email']}\n")
                if acc['password']:
                    lines_out.append(f"Password:\n{acc['password']}\n")
                if acc['two_fa']:
                    lines_out.append(f"2FA Secret Key:\n{acc['two_fa']}")
                    lines_out.append("\n👉 2FA Code Generator: Paste key at https://2fa.live")
                if acc.get('account_id'):
                    lines_out.append(f"\nAccount ID: {acc['account_id']}")
            else:
                if acc['email']:
                    lines_out.append(f"Email: {acc['email']}")
                if acc['password']:
                    lines_out.append(f"Password: {acc['password']}")
                if acc['two_fa']:
                    lines_out.append(f"2FA Secret Key: {acc['two_fa']}")
                    lines_out.append("\n👉 2FA Code Generator: Paste key at https://2fa.live")
                if acc.get('account_id'):
                    lines_out.append(f"Account ID: {acc['account_id']}")
            outputs.append("\n".join(lines_out).strip())
        return "\n\n----------------------------------------\n\n".join(outputs)

    # 3. If single license key or activation code
    return f"🔑 Access Key / Details\n\nProduct: {tool_name or 'Software Tool'}\n\nDetails:\n{clean_raw}"


def clean_access_credentials(raw_credentials: str, tool_name: str = "") -> str:
    """
    Cleans messy vendor credentials into a neat, human-friendly presentation.
    - Pure activation / claim URLs are formatted instantly with 0ms latency.
    - Accounts, JSON dumps, and complex credentials are professionally formatted via OpenRouter AI.
    - Deterministic parser serves as a 100% reliable fallback.
    """
    if not raw_credentials or not str(raw_credentials).strip():
        return ""

    raw_credentials = str(raw_credentials).strip()

    # Clean wrappers
    cleaned_input = re.sub(r'^(\[Auto-Fulfilled Credentials\]\s*)?', '', raw_credentials).strip()
    cleaned_input = re.sub(r'^(Code:\s*)+', '', cleaned_input).strip()
    cleaned_input = re.sub(r'^(User:\s*)+', '', cleaned_input).strip()

    # Fast-path for pure activation / claim URLs (Akunding, Stock Lara, etc.)
    # Avoids unnecessary LLM calls, latency, rate-limits, or hallucinations on simple URLs!
    lines = [l.strip() for l in cleaned_input.splitlines() if l.strip()]
    cleaned_lines = [re.sub(r'^(Code|Link|User|URL):\s*', '', l, flags=re.I).strip() for l in lines]
    urls = [l for l in cleaned_lines if l.startswith(('http://', 'https://'))]
    if urls and len(urls) == len(cleaned_lines):
        return deterministic_clean_credentials(cleaned_input, tool_name=tool_name)

    settings = SiteSettings.get()
    api_key = settings.openrouter_api_key.strip() if settings else ""
    model = settings.openrouter_model.strip() if settings else "openrouter/free"
    site_name = settings.site_name if settings else "OneSol AI Hub"

    if api_key:
        prompt = f"""You are the automated fulfillment delivery assistant for {site_name}.
Your job is to format the raw vendor delivery data below into a clean, professional message for a customer who purchased "{tool_name or 'Software Tool'}".

Raw Vendor Data:
{cleaned_input}

INSTRUCTIONS:
Determine which ONE of the following 4 categories matches the data, and output ONLY that category. Do NOT output multiple categories or any "None" fields.

CATEGORY 1: If the data is an ACTIVATION / CLAIM / INVITE LINK (a URL starting with http:// or https://):
🔗 Subscription Activation Link

Product: {tool_name or 'Software Tool'}

Activation Link:
<exact URL from data>

👉 Instructions: Open or copy the link above into your browser to activate your subscription.

CATEGORY 2: If the data is SINGLE LOGIN CREDENTIALS:
🔐 Login Credentials

Email: <email from data>
Password: <password from data>
2FA Secret Key: <2fa key from data if present>
Account ID: <account id from data if present>
👉 2FA Code Generator: Paste key at https://2fa.live (include if 2FA key is present)

CATEGORY 3: If the data has MULTIPLE LOGIN ACCOUNTS:
For each account, extract the Email, Password, and 2FA Secret Key.
Format each account as:
{tool_name or 'Account'} — Account 1

Email:
<email from data>

Password:
<password from data>

2FA Secret Key:
<2fa key from data>

👉 2FA Code Generator: Paste key at https://2fa.live

{tool_name or 'Account'} — Account 2
...

CATEGORY 4: If the data is a LICENSE KEY / REDEMPTION CODE:
🔑 License Key / Activation Code

Product: {tool_name or 'Software Tool'}
Key: <exact code/key>

CRITICAL RULES:
- CHOOSE ONLY ONE CATEGORY. Never print multiple categories. Never output "None", "N/A", or "Not provided".
- Keep emails, usernames, and passwords EXACTLY as given in the data without removing any plus (+) signs, prefixes, or numbers.
- Never invent fake values. Use ONLY the exact details from the data.
- Omit internal JSON brackets, access tokens, session cookies, and refresh timestamps.
- Output ONLY the final message text. No markdown code blocks (no ```). No greeting, no conversational text.
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
            ]
        }

        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get('choices', [])
                    if choices:
                        text = choices[0].get('message', {}).get('content', '').strip()
                        # If the model triggered safety refusal or empty or hallucinations, fall back
                        bad_markers = ['user safety: unsafe', '<email>', '<password>', 'user@example.com', 'securepass123', 'not provided', ': none']
                        emoji_headers = sum(text.count(e) for e in ['🔐', '🔗', '🔑'])
                        if text and not any(bm in text.lower() for bm in bad_markers) and emoji_headers <= 1:
                            # Strip accidental code blocks
                            if text.startswith("```"):
                                text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
                                text = re.sub(r'\n?```$', '', text)
                            logger.info(f"OpenRouter successfully cleaned credentials for {tool_name}")
                            return text.strip()
                        else:
                            logger.warning(f"OpenRouter output rejected due to invalid/placeholder content for {tool_name}")
                elif response.status_code == 429 and attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    logger.warning(f"OpenRouter clean credentials returned {response.status_code}: {response.text[:200]}")
            except Exception as e:
                logger.warning(f"OpenRouter clean credentials error (Attempt {attempt+1}): {e}")

    # Fallback to deterministic regex/JSON cleaner
    logger.info(f"Using deterministic credentials cleaner for {tool_name}")
    return deterministic_clean_credentials(cleaned_input, tool_name=tool_name)
