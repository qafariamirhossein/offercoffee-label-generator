#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime
from woocommerce_api import WooCommerceAPI
from config import WOOCOMMERCE_CONFIG

def fetch_and_save_orders():
    """دریافت سفارشات و ذخیره به صورت JSON"""
    
    print("🚀 شروع دریافت سفارشات از WooCommerce...")
    
    # اتصال به WooCommerce
    wc_api = WooCommerceAPI(
        WOOCOMMERCE_CONFIG['site_url'],
        WOOCOMMERCE_CONFIG['consumer_key'],
        WOOCOMMERCE_CONFIG['consumer_secret']
    )
    
    # دریافت سفارشات
    print("📥 دریافت سفارشات...")
    orders = wc_api.get_orders(status='processing', per_page=5)
    
    if not orders:
        print("❌ هیچ سفارش پردازش نشده‌ای یافت نشد.")
        return
    
    print(f"✅ {len(orders)} سفارش یافت شد.")
    
    # دریافت جزئیات کامل هر سفارش
    detailed_orders = []
    for i, order in enumerate(orders):
        order_id = order['id']
        print(f"📦 دریافت جزئیات سفارش {order_id}...")
        
        order_details = wc_api.get_order_details(order_id)
        if order_details:
            detailed_orders.append(order_details)
            print(f"✅ جزئیات سفارش {order_id} دریافت شد")
        else:
            print(f"❌ خطا در دریافت جزئیات سفارش {order_id}")
    
    # ذخیره به فایل JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"orders_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(detailed_orders, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 {len(detailed_orders)} سفارش در فایل '{output_file}' ذخیره شد.")
    print(f"📁 مسیر فایل: {os.path.abspath(output_file)}")
    
    # نمایش خلاصه سفارشات
    print("\n📋 خلاصه سفارشات:")
    for order in detailed_orders:
        order_id = order['id']
        customer_name = f"{order['billing']['first_name']} {order['billing']['last_name']}".strip()
        total = order['total']
        items_count = len(order['line_items'])
        
        print(f"  🛒 سفارش #{order_id}: {customer_name} - {total} تومان - {items_count} محصول")

def main():
    """تابع اصلی"""
    print("=" * 60)
    print("📥 سیستم دریافت و ذخیره سفارشات WooCommerce")
    print("=" * 60)
    
    # بررسی تنظیمات
    if (WOOCOMMERCE_CONFIG['site_url'] == 'https://yoursite.com' or 
        WOOCOMMERCE_CONFIG['consumer_key'] == 'ck_your_consumer_key_here' or
        WOOCOMMERCE_CONFIG['consumer_secret'] == 'cs_your_consumer_secret_here'):
        print("❌ خطا: لطفاً تنظیمات WooCommerce را در فایل config.py تکمیل کنید.")
        return
    
    try:
        fetch_and_save_orders()
    except KeyboardInterrupt:
        print("\n⏹️ عملیات توسط کاربر متوقف شد.")
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")

if __name__ == "__main__":
    main()
