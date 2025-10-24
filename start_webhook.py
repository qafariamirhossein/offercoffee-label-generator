#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت کمکی برای اجرای آسان سرور webhook
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """بررسی وابستگی‌ها"""
    print("🔍 بررسی وابستگی‌ها...")
    
    try:
        import flask
        import requests
        from PIL import Image
        print("✅ وابستگی‌های اصلی موجود است")
        return True
    except ImportError as e:
        print(f"❌ وابستگی مفقود: {e}")
        print("💡 برای نصب وابستگی‌ها اجرا کنید: pip install -r requirements.txt")
        return False

def check_config():
    """بررسی تنظیمات"""
    print("🔍 بررسی تنظیمات...")
    
    try:
        from config import WOOCOMMERCE_CONFIG
        
        if (WOOCOMMERCE_CONFIG['site_url'] == 'https://yoursite.com' or 
            WOOCOMMERCE_CONFIG['consumer_key'] == 'ck_your_consumer_key_here' or
            WOOCOMMERCE_CONFIG['consumer_secret'] == 'cs_your_consumer_secret_here'):
            print("❌ لطفاً تنظیمات WooCommerce را در فایل config.py تکمیل کنید")
            return False
        
        print("✅ تنظیمات WooCommerce صحیح است")
        return True
        
    except Exception as e:
        print(f"❌ خطا در بررسی تنظیمات: {e}")
        return False

def check_webhook_secret():
    """بررسی کلید مخفی webhook"""
    print("🔍 بررسی کلید مخفی webhook...")
    
    try:
        with open('webhook_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'WEBHOOK_SECRET = "your_webhook_secret_here"' in content:
            print("⚠️ لطفاً کلید مخفی webhook را در فایل webhook_server.py تنظیم کنید")
            print("💡 خط زیر را پیدا کنید و تغییر دهید:")
            print('   WEBHOOK_SECRET = "your_webhook_secret_here"')
            print('   به:')
            print('   WEBHOOK_SECRET = "your_actual_secret_key"')
            return False
        
        print("✅ کلید مخفی webhook تنظیم شده است")
        return True
        
    except Exception as e:
        print(f"❌ خطا در بررسی کلید مخفی: {e}")
        return False

def create_directories():
    """ایجاد پوشه‌های لازم"""
    print("📁 ایجاد پوشه‌های لازم...")
    
    directories = ['labels', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ پوشه {directory} ایجاد شد")


def main():
    """تابع اصلی"""
    print("🚀 راه‌اندازی سرور Webhook قهوه آفر")
    print("="*50)
    
    # بررسی‌های اولیه
    if not check_dependencies():
        return False
    
    if not check_config():
        return False
    
    if not check_webhook_secret():
        return False
    
    # ایجاد پوشه‌ها
    create_directories()
    
    print("\n🎯 آماده برای اجرای سرور...")
    print("📡 سرور روی http://localhost:8080 اجرا خواهد شد")
    print("🔗 آدرس webhook: http://localhost:8080/webhook/new-order")
    print("🧪 تست: http://localhost:8080/health")
    print("\n⏳ در حال شروع سرور...")
    
    try:
        # اجرای سرور
        subprocess.run([sys.executable, 'webhook_server.py'])
    except KeyboardInterrupt:
        print("\n⏹️ سرور متوقف شد")
    except Exception as e:
        print(f"❌ خطا در اجرای سرور: {e}")

if __name__ == "__main__":
    main()
