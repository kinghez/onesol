import requests
import base64
import json
import logging
from .models import Vendor, VendorProduct

logger = logging.getLogger(__name__)

class VendorException(Exception):
    pass


class BaseVendorService:
    def __init__(self, vendor: Vendor):
        self.vendor = vendor

    def get_balance(self) -> float:
        raise NotImplementedError

    def fetch_products(self) -> list:
        """Returns a list of dicts to sync products"""
        raise NotImplementedError

    def purchase(self, vendor_product_id: str, quantity: int, buyer_info: str = "") -> dict:
        """
        Executes a purchase.
        Returns dict:
        {
            'status': 'completed' | 'pending_manual' | 'failed',
            'codes': ['CODE1', 'CODE2'], # If instant
            'order_id': 'VendorOrderID',
            'error': 'Optional error message'
        }
        """
        raise NotImplementedError

    def _request_with_retry(self, method, url, max_retries=4, retry_delay=15, **kwargs):
        """
        Executes an HTTP request with automatic retry for 503 (Render.com cold start / service waking up).
        Render free-tier services spin down after inactivity and return 503 for ~30-60s on the first request.
        """
        import time
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                if method == "get":
                    resp = requests.get(url, timeout=60, **kwargs)
                else:
                    resp = requests.post(url, timeout=60, **kwargs)

                if resp.status_code == 503:
                    # Check if service is SUSPENDED (not just sleeping)
                    body_text = ""
                    try:
                        body_text = resp.text.lower()
                    except Exception:
                        pass
                    if "suspended" in body_text:
                        logger.error(
                            f"Vendor server is SUSPENDED. URL: {url}. "
                            f"Please contact vendor to reinstate service."
                        )
                        raise VendorException(
                            f"Vendor server is SUSPENDED on Render.com. "
                            f"Please contact vendor to restore service at: {url}"
                        )
                    logger.warning(
                        f"Vendor API 503 on attempt {attempt}/{max_retries} for {url}. "
                        f"Waiting {retry_delay}s before retry..."
                    )
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    else:
                        resp.raise_for_status()
                    continue

                resp.raise_for_status()
                return resp

            except requests.exceptions.Timeout as e:
                last_exc = e
                logger.warning(f"Vendor API timeout on attempt {attempt}/{max_retries} for {url}. Retrying...")
                if attempt < max_retries:
                    time.sleep(retry_delay)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 503 and attempt < max_retries:
                    logger.warning(f"Vendor API 503 HTTPError attempt {attempt}/{max_retries}. Waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                    last_exc = e
                else:
                    raise
            except requests.RequestException as e:
                last_exc = e
                if attempt < max_retries:
                    logger.warning(f"Vendor API request error attempt {attempt}/{max_retries}: {e}. Retrying...")
                    time.sleep(retry_delay)
                else:
                    raise

        if last_exc:
            raise last_exc


class AkundingService(BaseVendorService):
    def _headers(self):
        return {"Authorization": f"Bearer {self.vendor.api_key}"}
        
    def _get_base_url(self):
        url = self.vendor.base_url.rstrip('/')
        return url if url else "https://akunding.shop/api"

    def get_balance(self) -> float:
        try:
            url = f"{self._get_base_url()}/v1/me"
            response = self._request_with_retry("get", url, headers=self._headers(), max_retries=3, retry_delay=5)
            data = response.json()
            return float(data.get('balance', 0))
        except Exception as e:
            logger.error(f"Akunding get_balance error: {e}")
            return 0.0

    def fetch_products(self) -> list:
        url = f"{self._get_base_url()}/v1/products"
        response = self._request_with_retry("get", url, headers=self._headers(), params={"include_out_of_stock": "true"}, max_retries=3, retry_delay=5)
        products_data = response.json()
        
        parsed_products = []
        for p in products_data:
            stock_num = p.get('stock', 0)
            is_available = p.get('available', True)
            stock_str = str(stock_num) if (is_available and stock_num) else '0'

            parsed_products.append({
                'vendor_product_id': str(p.get('id')),
                'name': p.get('name', 'Unknown Akunding Product'),
                'description': p.get('description', ''),
                'price': p.get('your_price') or p.get('base_price') or p.get('price'),
                'stock': stock_str,
                'is_manual': False,
                'raw_data': p
            })
        return parsed_products

    def purchase(self, vendor_product_id: str, quantity: int, buyer_info: str = "") -> dict:
        import uuid
        import time
        url = f"{self._get_base_url()}/v1/orders"
        payload = {
            "product_id": int(vendor_product_id),
            "quantity": quantity
        }
        headers = self._headers()
        ik = str(uuid.uuid4())
        headers["Idempotency-Key"] = ik
        headers["X-Idempotency-Key"] = ik
        try:
            response = self._request_with_retry("post", url, json=payload, headers=headers, max_retries=3, retry_delay=10)
            data = response.json()
            order_id = str(data.get('id', ''))
            
            def _extract_codes(order_dict):
                raw_items = order_dict.get('items', [])
                found_codes = []
                if isinstance(raw_items, list):
                    for item in raw_items:
                        if isinstance(item, str):
                            found_codes.append(item)
                        elif isinstance(item, dict):
                            c = item.get('code') or item.get('url') or item.get('link')
                            if c:
                                found_codes.append(c)
                if not found_codes and order_dict.get('codes'):
                    found_codes = order_dict.get('codes')
                return found_codes

            codes = _extract_codes(data)

            # If status is "paid", partner delivery is in progress: check order again up to 2 times
            if not codes and data.get('status') == 'paid' and order_id:
                logger.info(f"Akunding order #{order_id} is 'paid' (delivery in progress). Polling for items...")
                for attempt in range(2):
                    time.sleep(8)
                    try:
                        check_res = self._request_with_retry("get", f"{self._get_base_url()}/v1/orders/{order_id}", headers=self._headers(), max_retries=2, retry_delay=3)
                        check_data = check_res.json()
                        codes = _extract_codes(check_data)
                        if codes or check_data.get('status') == 'delivered':
                            data = check_data
                            break
                    except Exception as poll_err:
                        logger.warning(f"Error checking Akunding order #{order_id} delivery status: {poll_err}")

            return {
                'status': 'completed' if codes else 'pending_manual',
                'codes': codes,
                'order_id': order_id,
                'error': None
            }
        except requests.RequestException as e:
            err_msg = str(e)
            if e.response is not None:
                if e.response.status_code == 402:
                    try:
                        short_val = e.response.json().get('detail', {}).get('short', '')
                        err_msg = f"Insufficient Akunding wallet balance. Please top up at least {short_val} USDT in @Akunding_store_bot."
                    except Exception:
                        err_msg = "Insufficient Akunding wallet balance. Please top up in @Akunding_store_bot."
                else:
                    err_msg = f"{e.response.status_code}: {e.response.text}"
            logger.error(f"Akunding purchase failed: {err_msg}")
            return {'status': 'failed', 'error': err_msg}


class ShopBotService(BaseVendorService):
    def __init__(self, vendor: Vendor):
        super().__init__(vendor)
        self.api_key = vendor.api_key
        self.api_url = vendor.base_url.rstrip('/') if vendor.base_url else ""
        
        if self.api_key.startswith('conn_'):
            try:
                data = json.loads(base64.b64decode(self.api_key.replace("conn_", "")))
                self.api_key = data["k"]
                if not self.api_url:
                    self.api_url = data["u"].rstrip('/')
            except Exception as e:
                logger.error(f"Failed to decode connection code: {e}")

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    def get_balance(self) -> float:
        response = self._request_with_retry("get", f"{self.api_url}/balance", headers=self._headers())
        data = response.json()
        return float(data.get('balance', 0))

    def fetch_products(self) -> list:
        response = self._request_with_retry("get", f"{self.api_url}/products", headers=self._headers())
        products_data = response.json().get('products', [])
        
        parsed_products = []
        for p in products_data:
            parsed_products.append({
                'vendor_product_id': str(p.get('id')),
                'name': p.get('name_en') or p.get('name_ar') or 'Unknown ShopBot Product',
                'description': p.get('desc_en') or p.get('desc_ar') or '',
                'price': p.get('store_price') or p.get('price'),
                'stock': str(p.get('stock', 'unlimited')),
                'is_manual': p.get('is_manual', False),
                'raw_data': p
            })
        return parsed_products

    def purchase(self, vendor_product_id: str, quantity: int, buyer_info: str = "") -> dict:
        url = f"{self.api_url}/purchase"
        payload = {
            "product_id": vendor_product_id,
            "qty": quantity
        }
        if buyer_info:
            payload["buyer_info"] = buyer_info
            
        try:
            response = requests.post(url, json=payload, headers=self._headers())
            if response.status_code != 200:
                err_data = response.json() if response.content else {}
                err_msg = err_data.get('error', response.text)
                return {'status': 'failed', 'error': err_msg}
                
            data = response.json()
            if not data.get('success'):
                return {'status': 'failed', 'error': str(data)}
                
            return {
                'status': data.get('status', 'completed'), # "completed" or "pending_manual"
                'codes': data.get('codes', []),
                'order_id': str(data.get('order_id', '')),
                'error': None
            }
        except requests.RequestException as e:
            return {'status': 'failed', 'error': str(e)}


class CanbosoService(BaseVendorService):
    def _headers(self):
        return {
            "Accept": "application/json"
        }
        
    def _get_base_url(self):
        url = self.vendor.base_url.rstrip('/') if self.vendor.base_url else ""
        if url:
            if not url.endswith('/v2') and '/v2/' not in url:
                url = f"{url}/v2"
            return url
        return "https://canboso.com/api/v2"

    def get_balance(self) -> float:
        try:
            url = f"{self._get_base_url()}/telegram-buyer/balance"
            response = self._request_with_retry("get", url, headers=self._headers(), params={"key": self.vendor.api_key}, max_retries=3, retry_delay=5)
            if response.status_code == 200:
                data = response.json()
                return float(data.get('balanceUsd', data.get('balance', 0)))
        except Exception as e:
            logger.error(f"Canboso get_balance error: {e}")
        return 0.0

    def fetch_products(self) -> list:
        url = f"{self._get_base_url()}/telegram-buyer/products"
        response = self._request_with_retry("get", url, headers=self._headers(), params={"key": self.vendor.api_key}, max_retries=3, retry_delay=5)
        response.raise_for_status()
        data = response.json()
        
        products_data = data.get('products', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        
        parsed_products = []
        for p in products_data:
            p_id = str(p.get('productId') or p.get('_id') or p.get('id', ''))
            
            price_val = None
            if isinstance(p.get('price'), dict):
                price_val = p['price'].get('amount')
            else:
                price_val = p.get('usdPricing') or p.get('pricing') or p.get('price')

            avail = p.get('availability', {})
            stock_val = str(avail.get('available', p.get('stats', {}).get('available', 'unlimited')))
            if stock_val is None or stock_val == 'None':
                stock_val = 'unlimited'

            parsed_products.append({
                'vendor_product_id': p_id,
                'name': p.get('name') or p.get('product_name', 'Unknown Canboso Product'),
                'description': p.get('description', ''),
                'price': price_val,
                'stock': stock_val,
                'is_manual': p.get('productType') != 'account',
                'raw_data': p
            })
        return parsed_products

    def purchase(self, vendor_product_id: str, quantity: int, buyer_info: str = "") -> dict:
        import uuid
        url = f"{self._get_base_url()}/telegram-buyer/purchase"
        payload = {
            "key": self.vendor.api_key,
            "product_id": vendor_product_id,
            "quantity": quantity
        }
        headers = self._headers()
        ik = str(uuid.uuid4())
        headers["Idempotency-Key"] = ik
        headers["X-Idempotency-Key"] = ik
        try:
            response = self._request_with_retry("post", url, json=payload, headers=headers, max_retries=3, retry_delay=5)
            if response.status_code != 200:
                err_data = response.json() if response.content else {}
                err_msg = err_data.get('message') or err_data.get('error', response.text)
                return {'status': 'failed', 'error': err_msg}
                
            data = response.json()
            if not data.get('success', True):
                return {'status': 'failed', 'error': data.get('message', str(data))}
                
            order_data = data.get('order', {})
            delivery_data = data.get('delivery', {})
            accounts = delivery_data.get('accounts', []) if isinstance(delivery_data, dict) else []
            
            codes = []
            for acc in accounts:
                if isinstance(acc, dict):
                    u = acc.get('user', '')
                    p = acc.get('password', '')
                    if u or p:
                        codes.append(f"User: {u} | Pass: {p}")
                elif isinstance(acc, str):
                    codes.append(acc)
                    
            status_str = order_data.get('status', 'completed')
            return {
                'status': 'completed' if codes or status_str == 'completed' else 'pending_manual',
                'codes': codes,
                'order_id': str(order_data.get('orderCode') or data.get('id', '')),
                'error': None
            }
        except requests.RequestException as e:
            err_msg = str(e)
            if e.response is not None:
                err_msg = f"{e.response.status_code}: {e.response.text}"
            return {'status': 'failed', 'error': err_msg}



def get_vendor_service(vendor: Vendor) -> BaseVendorService:
    if vendor.api_type == 'akunding':
        return AkundingService(vendor)
    elif vendor.api_type == 'shopbot':
        return ShopBotService(vendor)
    elif vendor.api_type == 'canboso':
        return CanbosoService(vendor)
    raise VendorException("Unknown Vendor API Type")
