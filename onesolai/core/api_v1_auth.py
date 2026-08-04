import time
import logging
from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
from accounts.models import APIKey

logger = logging.getLogger(__name__)

RATE_LIMIT_PER_MINUTE = 60


def api_v1_auth(require_secret=False):
    """
    Decorator for /api/v1/ endpoints.
    Verifies Bearer or X-API-KEY token against APIKey model.
    Enforces 60 requests/minute rate limit.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Extract API Key from Authorization or X-API-KEY header
            auth_header = request.headers.get('Authorization') or request.headers.get('X-API-KEY')
            if not auth_header:
                return JsonResponse({
                    'error': 'Unauthorized',
                    'message': 'API Key is missing. Pass Authorization: Bearer sk_live_... or X-API-KEY header.'
                }, status=401)

            api_token = auth_header.replace('Bearer ', '').strip()

            # 2. Look up APIKey in database
            api_key = APIKey.objects.filter(secret_key=api_token, is_active=True).first()
            is_secret = True

            if not api_key:
                # Try public key
                api_key = APIKey.objects.filter(public_key=api_token, is_active=True).first()
                is_secret = False

            if not api_key:
                return JsonResponse({
                    'error': 'Unauthorized',
                    'message': 'Invalid or inactive API Key.'
                }, status=401)

            # 3. Check scope requirement
            if require_secret and not is_secret:
                return JsonResponse({
                    'error': 'Forbidden',
                    'message': 'This endpoint requires a Secret Key (sk_live_...). Public Key (pk_live_...) is read-only.'
                }, status=403)

            # 4. Rate Limiting (60 req/min per key)
            current_minute = int(time.time() // 60)
            cache_key = f"api_v1_rate_{api_key.id}_{current_minute}"
            req_count = cache.get(cache_key, 0)

            if req_count >= RATE_LIMIT_PER_MINUTE:
                response = JsonResponse({
                    'error': 'Rate Limit Exceeded',
                    'message': f'Maximum {RATE_LIMIT_PER_MINUTE} requests per minute exceeded. Please slow down.'
                }, status=429)
                response['Retry-After'] = '60'
                return response

            cache.set(cache_key, req_count + 1, timeout=70)

            # 5. Attach User and Key metadata to request
            request.api_user = api_key.user
            request.api_key = api_key
            request.is_secret_key = is_secret

            # Update last_used_at timestamp (throttled)
            now = timezone.now()
            if not api_key.last_used_at or (now - api_key.last_used_at).total_seconds() > 300:
                api_key.last_used_at = now
                api_key.save(update_fields=['last_used_at'])

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
