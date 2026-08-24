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


class AkundingService(BaseVendorService):
    def _headers(self):
        return {"Authorization": f"Bearer {self.vendor.api_key}"}
        
    def _get_base_url(self):
        url = self.vendor.base_url.rstrip('/')
        return url if url else "https://akunding.shop/api"

    def get_balance(self) -> float:
        url = f"{self._get_base_url()}/v1/me"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        data = response.json()
        return float(data.get('balance', 0))

    def fetch_products(self) -> list:
        url = f"{self._get_base_url()}/v1/products"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        products_data = response.json()
        
        parsed_products = []
        for p in products_data:
            parsed_products.append({
                'vendor_product_id': str(p.get('id')),
                'name': p.get('name', 'Unknown Akunding Product'),
                'description': p.get('description', ''),
                'price': p.get('base_price') or p.get('price'),
                'stock': str(p.get('stock', 'unlimited')),
                'is_manual': False, # Akunding doesn't specify in openapi by default, assume instant
                'raw_data': p
            })
        return parsed_products

    def purchase(self, vendor_product_id: str, quantity: int, buyer_info: str = "") -> dict:
        import uuid
        url = f"{self._get_base_url()}/v1/orders"
        payload = {
            "product_id": int(vendor_product_id),
            "quantity": quantity
        }
        headers = self._headers()
        headers["X-Idempotency-Key"] = str(uuid.uuid4())
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            raw_items = data.get('items', [])
            codes = []
            if isinstance(raw_items, list):
                for item in raw_items:
                    if isinstance(item, str):
                        codes.append(item)
                    elif isinstance(item, dict):
                        c = item.get('code') or item.get('url') or item.get('link')
                        if c:
                            codes.append(c)
            if not codes and data.get('codes'):
                codes = data.get('codes')
                
            return {
                'status': 'completed' if codes else 'pending_manual',
                'codes': codes,
                'order_id': str(data.get('id', '')),
                'error': None
            }
        except requests.RequestException as e:
            err_msg = str(e)
            if e.response is not None:
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
                self.api_url = data["u"].rstrip('/')
            except Exception as e:
                logger.error(f"Failed to decode connection code: {e}")

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    def get_balance(self) -> float:
        response = requests.get(f"{self.api_url}/balance", headers=self._headers())
        response.raise_for_status()
        data = response.json()
        return float(data.get('balance', 0))

    def fetch_products(self) -> list:
        response = requests.get(f"{self.api_url}/products", headers=self._headers())
        response.raise_for_status()
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
            response = requests.get(url, headers=self._headers(), params={"key": self.vendor.api_key})
            if response.status_code == 200:
                data = response.json()
                return float(data.get('balanceUsd', data.get('balance', 0)))
        except Exception as e:
            logger.error(f"Canboso get_balance error: {e}")
        return 0.0

    def fetch_products(self) -> list:
        url = f"{self._get_base_url()}/telegram-buyer/products"
        response = requests.get(url, headers=self._headers(), params={"key": self.vendor.api_key})
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
        headers["X-Idempotency-Key"] = str(uuid.uuid4())
        try:
            response = requests.post(url, json=payload, headers=headers)
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
