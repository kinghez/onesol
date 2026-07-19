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
        url = f"{self._get_base_url()}/v1/orders"
        payload = {
            "product_id": int(vendor_product_id),
            "quantity": quantity
        }
        try:
            response = requests.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()
            # Depending on actual API response, this may need adjustment:
            codes = data.get('codes', [])
            if not codes and 'items' in data: # sometimes orders return items
                codes = [item.get('code') for item in data.get('items', []) if item.get('code')]
                
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
        # For Canboso, we must pass App-Version header, and the api_key goes in the URL params!
        return {
            "App-Version": "2.0.0",
            "Accept": "application/json"
        }
        
    def _get_base_url(self):
        url = self.vendor.base_url.rstrip('/')
        return url if url else "https://canboso.com/api"

    def get_balance(self) -> float:
        try:
            url = f"{self._get_base_url()}/telegram-buyer/me"
            response = requests.get(url, headers=self._headers(), params={"api_key": self.vendor.api_key})
            if response.status_code == 200:
                return float(response.json().get('balance', 0))
        except:
            pass
        return 0.0

    def fetch_products(self) -> list:
        url = f"{self._get_base_url()}/telegram-buyer/products"
        response = requests.get(url, headers=self._headers(), params={"api_key": self.vendor.api_key})
        response.raise_for_status()
        # Response structure depends on actual API. Assuming list or {data: []}
        data = response.json()
        products_data = data.get('products', data.get('data', data)) if isinstance(data, dict) else data
        
        parsed_products = []
        for p in products_data:
            parsed_products.append({
                'vendor_product_id': str(p.get('_id', p.get('id', ''))),
                'name': p.get('product_name', p.get('name', 'Unknown Canboso Product')),
                'description': p.get('description', ''),
                'price': p.get('usdPricing', p.get('pricing', p.get('price'))),
                'stock': str(p.get('stats', {}).get('available', 'unlimited')),
                'is_manual': False,
                'raw_data': p
            })
        return parsed_products

    def purchase(self, vendor_product_id: str, quantity: int, buyer_info: str = "") -> dict:
        url = f"{self._get_base_url()}/telegram-buyer/purchase"
        payload = {
            "product_id": int(vendor_product_id) if vendor_product_id.isdigit() else vendor_product_id,
            "quantity": quantity
        }
        try:
            response = requests.post(url, json=payload, headers=self._headers(), params={"api_key": self.vendor.api_key})
            response.raise_for_status()
            data = response.json()
            
            codes = data.get('codes', [])
            if not codes and 'data' in data:
                # Sometimes payload is in data.code
                d = data['data']
                if 'code' in d:
                    codes = [d['code']]
                elif 'codes' in d:
                    codes = d['codes']
                    
            return {
                'status': 'completed' if codes else 'pending_manual',
                'codes': codes,
                'order_id': str(data.get('id', data.get('order_id', ''))),
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
