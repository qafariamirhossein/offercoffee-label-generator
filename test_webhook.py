#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت تست webhook برای شبیه‌سازی سفارش جدید
"""

import requests
import json
import hmac
import hashlib
import base64
from datetime import datetime

# تنظیمات
WEBHOOK_URL = "http://localhost:5443/webhook/new-order"
WEBHOOK_SECRET = "your_webhook_secret_here"  # باید با سرور یکسان باشد

def create_test_signature(payload: bytes, secret: str) -> str:
    """ایجاد امضای تست"""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

def create_test_order():
    """ایجاد داده‌های تست سفارش"""
    return {
        "id": 9999,
        "number": "9999",
        "status": "processing",
        "total": "150000",
        "currency": "IRR",
        "date_created": datetime.now().isoformat(),
        "billing": {
            "first_name": "احمد",
            "last_name": "محمدی",
            "address_1": "تهران، خیابان ولیعصر",
            "city": "تهران",
            "phone": "09123456789"
        },
        "line_items": [
            {
                "id": 1,
                "name": "قهوه عربیکا برزیل",
                "quantity": 2,
                "total": "100000",
                "meta_data": [
                    {"key": "weight", "value": "500"},
                    {"key": "grinding_grade", "value": "متوسط"}
                ]
            },
            {
                "id": 2,
                "name": "قهوه روبوستا اندونزی",
                "quantity": 1,
                "total": "50000",
                "meta_data": [
                    {"key": "weight", "value": "250"},
                    {"key": "grinding_grade", "value": "درشت"}
                ]
            }
        ]
    }

def create_test_mixed_order():
    """ایجاد سفارش میکس تست"""
    return {
        "id": 9998,
        "number": "9998",
        "status": "processing",
        "total": "200000",
        "currency": "IRR",
        "date_created": datetime.now().isoformat(),
        "billing": {
            "first_name": "فاطمه",
            "last_name": "احمدی",
            "address_1": "اصفهان، خیابان چهارباغ",
            "city": "اصفهان",
            "phone": "09187654321"
        },
        "line_items": [
            {
                "id": 1,
                "name": "قهوه ترکیبی میکس",
                "quantity": 1,
                "total": "200000",
                "meta_data": [
                    {"key": "ترکیبات", "value": "قهوه اسپرسو: ۵۰٪\nعربیکا برزیل سانتوز: ۵۰٪"},
                    {"key": "weight", "value": "1000"},
                    {"key": "blend_coffee", "value": "خیر"}
                ]
            }
        ]
    }

def test_webhook_connection():
    """تست اتصال به سرور"""
    print("🔍 تست اتصال به سرور...")
    
    try:
        response = requests.get("http://localhost:5443/health", timeout=5)
        if response.status_code == 200:
            print("✅ سرور در حال اجرا است")
            return True
        else:
            print(f"❌ سرور پاسخ نامناسب داد: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ سرور در حال اجرا نیست")
        print("💡 ابتدا سرور را اجرا کنید: python webhook_server.py")
        return False
    except Exception as e:
        print(f"❌ خطا در اتصال: {e}")
        return False

def test_regular_order():
    """تست سفارش عادی"""
    print("\n📦 تست سفارش عادی...")
    
    order_data = create_test_order()
    payload = json.dumps(order_data, ensure_ascii=False).encode('utf-8')
    signature = create_test_signature(payload, WEBHOOK_SECRET)
    
    headers = {
        'Content-Type': 'application/json',
        'X-WC-Webhook-Signature': signature
    }
    
    try:
        response = requests.post(WEBHOOK_URL, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("✅ سفارش عادی با موفقیت پردازش شد")
            print(f"📄 پاسخ: {response.json()}")
            return True
        else:
            print(f"❌ خطا در پردازش سفارش: {response.status_code}")
            print(f"📄 پاسخ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ خطا در ارسال درخواست: {e}")
        return False

def test_mixed_order():
    """تست سفارش میکس"""
    print("\n🔀 تست سفارش میکس...")
    
    order_data = create_test_mixed_order()
    payload = json.dumps(order_data, ensure_ascii=False).encode('utf-8')
    signature = create_test_signature(payload, WEBHOOK_SECRET)
    
    headers = {
        'Content-Type': 'application/json',
        'X-WC-Webhook-Signature': signature
    }
    
    try:
        response = requests.post(WEBHOOK_URL, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("✅ سفارش میکس با موفقیت پردازش شد")
            print(f"📄 پاسخ: {response.json()}")
            return True
        else:
            print(f"❌ خطا در پردازش سفارش میکس: {response.status_code}")
            print(f"📄 پاسخ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ خطا در ارسال درخواست: {e}")
        return False

def test_invalid_signature():
    """تست امضای نامعتبر"""
    print("\n🔒 تست امضای نامعتبر...")
    
    order_data = create_test_order()
    payload = json.dumps(order_data, ensure_ascii=False).encode('utf-8')
    
    headers = {
        'Content-Type': 'application/json',
        'X-WC-Webhook-Signature': 'invalid_signature'
    }
    
    try:
        response = requests.post(WEBHOOK_URL, data=payload, headers=headers, timeout=10)
        
        if response.status_code == 403:
            print("✅ امضای نامعتبر به درستی رد شد")
            return True
        else:
            print(f"❌ انتظار کد 403، دریافت شد: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ خطا در تست امضا: {e}")
        return False

def main():
    """تابع اصلی تست"""
    print("🧪 تست سیستم Webhook قهوه آفر")
    print("="*50)
    
    # بررسی اتصال
    if not test_webhook_connection():
        return
    
    # تست‌های مختلف
    tests = [
        ("سفارش عادی", test_regular_order),
        ("سفارش میکس", test_mixed_order),
        ("امضای نامعتبر", test_invalid_signature)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔬 {test_name}...")
        result = test_func()
        results.append((test_name, result))
    
    # خلاصه نتایج
    print("\n" + "="*50)
    print("📊 خلاصه نتایج:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ موفق" if result else "❌ ناموفق"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} تست موفق بود")
    
    if passed == len(results):
        print("🎉 همه تست‌ها موفق بود! سیستم آماده است.")
    else:
        print("⚠️ برخی تست‌ها ناموفق بود. لطفاً مشکلات را بررسی کنید.")

if __name__ == "__main__":
    main()
