import requests
import json
from datetime import datetime
import jdatetime

class WooCommerceAPI:
    def __init__(self, site_url, consumer_key, consumer_secret):
        self.site_url = site_url.rstrip('/')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.api_url = f"{self.site_url}/wp-json/wc/v3"
        
    def get_orders(self, status='processing', per_page=10):
        """دریافت سفارشات از WooCommerce"""
        url = f"{self.api_url}/orders"
        params = {
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret,
            'status': status,
            'per_page': per_page,
            'orderby': 'date',
            'order': 'desc'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت سفارشات: {e}")
            return []
    
    def get_order_details(self, order_id):
        """دریافت جزئیات یک سفارش خاص"""
        url = f"{self.api_url}/orders/{order_id}"
        params = {
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت جزئیات سفارش {order_id}: {e}")
            return None

    def get_product(self, product_id: int):
        """دریافت جزئیات یک محصول (برای گرفتن permalink/slug)"""
        url = f"{self.api_url}/products/{product_id}"
        params = {
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت محصول {product_id}: {e}")
            return None
