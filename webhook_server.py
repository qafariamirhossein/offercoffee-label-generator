#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سرور Webhook برای دریافت سفارشات جدید از WooCommerce
و تولید خودکار لیبل‌ها
"""

import os
import sys
import hmac
import hashlib
import base64
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from typing import Dict, Any, Optional

# Import existing modules
from woocommerce_api import WooCommerceAPI
from config import WOOCOMMERCE_CONFIG, LABEL_CONFIG
from label_main import generate_main_label
from label_details import generate_details_label
from label_mixed import generate_mixed_label

# Import printing functionality
try:
    import win32print, win32ui
    from PIL import ImageWin
    PRINTING_AVAILABLE = True
except ImportError:
    PRINTING_AVAILABLE = False
    print("⚠️ ماژول‌های چاپ در دسترس نیستند - فقط ذخیره تصاویر انجام می‌شود")

# تنظیمات
WEBHOOK_SECRET = "your_webhook_secret_here"  # این رو در WooCommerce هم بذار
PRINTER_NAME = "Godex G500"  # نام چاپگر

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    تأیید امضای webhook برای امنیت
    
    Args:
        payload: بدنه درخواست
        signature: امضای دریافتی از header
        secret: کلید مخفی webhook
        
    Returns:
        True اگر امضا معتبر باشد
    """
    if not signature:
        return False
    
    try:
        # محاسبه امضای مورد انتظار
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).digest()
        
        # تبدیل به base64
        expected_b64 = base64.b64encode(expected_signature).decode('utf-8')
        
        # مقایسه امن
        return hmac.compare_digest(signature, expected_b64)
    except Exception as e:
        logger.error(f"خطا در تأیید امضا: {e}")
        return False

def print_label(image_path: str) -> bool:
    """چاپ لیبل یا ذخیره به عنوان فالبک"""
    try:
        if not PRINTING_AVAILABLE:
            logger.info(f"💾 چاپگر در دسترس نیست - تصویر ذخیره شد: {image_path}")
            return True
            
        # بررسی وجود چاپگر
        printers = [printer[2] for printer in win32print.EnumPrinters(2)]
        if PRINTER_NAME not in printers:
            logger.warning(f"⚠️ چاپگر '{PRINTER_NAME}' یافت نشد - تصویر ذخیره شد: {image_path}")
            return True
        
        # بارگذاری تصویر
        from PIL import Image
        img = Image.open(image_path)
        
        # چاپ
        hprinter = win32print.OpenPrinter(PRINTER_NAME)
        pdc = win32ui.CreateDC()
        pdc.CreatePrinterDC(PRINTER_NAME)
        pdc.StartDoc("Offer Coffee Label")
        pdc.StartPage()
        
        dib = ImageWin.Dib(img)
        dib.draw(pdc.GetHandleOutput(), (0, 0, img.width, img.height))
        
        pdc.EndPage()
        pdc.EndDoc()
        pdc.DeleteDC()
        
        logger.info(f"✅ لیبل با موفقیت چاپ شد: {image_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در چاپ - تصویر ذخیره شد: {e}")
        return False

def is_mixed_order(order_details: Dict[str, Any]) -> bool:
    """تشخیص سفارش‌های میکس بر اساس نام محصولات"""
    line_items = order_details.get('line_items', [])
    
    for item in line_items:
        product_name = item.get('name', '').lower()
        # بررسی کلمات کلیدی که نشان‌دهنده سفارش میکس هستند
        mixed_keywords = ['ترکیبی', 'میکس', 'combine', 'mixed', 'blend']
        
        for keyword in mixed_keywords:
            if keyword in product_name:
                return True
    
    return False

def process_new_order(order_data: Dict[str, Any]) -> bool:
    """
    پردازش سفارش جدید و تولید لیبل‌ها
    
    Args:
        order_data: داده‌های سفارش از WooCommerce
        
    Returns:
        True اگر پردازش موفق باشد
    """
    try:
        order_id = order_data.get('id')
        logger.info(f"📦 پردازش سفارش جدید: {order_id}")
        
        # ایجاد پوشه خروجی
        os.makedirs(LABEL_CONFIG['output_dir'], exist_ok=True)
        
        # بررسی نوع سفارش
        if is_mixed_order(order_data):
            logger.info(f"🔀 سفارش {order_id} یک سفارش میکس است - تولید برچسب میکس...")
            
            # تولید لیبل میکس
            mixed_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_mixed.jpg"
            generate_mixed_label(order_data, mixed_label_path)
            
            logger.info(f"✅ لیبل میکس سفارش {order_id} با موفقیت تولید شد")
            logger.info(f"   📁 لیبل میکس: {mixed_label_path}")
            
            # چاپ لیبل میکس
            print_label(mixed_label_path)
            
        else:
            logger.info(f"📦 سفارش {order_id} یک سفارش عادی است - تولید برچسب‌های معمولی...")
            
            # تولید لیبل‌های اصلی (back) برای هر محصول
            line_items = order_data.get('line_items', [])
            logger.info(f"📋 {len(line_items)} محصول در سفارش یافت شد")
            
            # لیست تمام لیبل‌های تولید شده برای این سفارش
            all_labels = []
            
            # تولید تمام لیبل‌های پشت (back) برای این سفارش
            for i, item in enumerate(line_items):
                # ایجاد لیبل پشت برای هر محصول
                back_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_back_{i+1}.jpg"
                logger.info(f"🏷️ تولید لیبل پشت برای محصول {i+1}: {item.get('name', 'نامشخص')}")
                
                # ایجاد کپی از order_data با فقط این محصول
                single_product_order = order_data.copy()
                single_product_order['line_items'] = [item]
                
                generate_main_label(single_product_order, back_label_path)
                all_labels.append(back_label_path)
            
            # تولید تمام لیبل‌های جزئیات برای این سفارش
            for i, item in enumerate(line_items):
                # ایجاد لیبل جزئیات برای هر محصول
                details_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_details_{i+1}.jpg"
                logger.info(f"📋 تولید لیبل جزئیات برای محصول {i+1}: {item.get('name', 'نامشخص')}")
                
                # ایجاد کپی از order_data با فقط این محصول
                single_product_order = order_data.copy()
                single_product_order['line_items'] = [item]
                
                generate_details_label(single_product_order, details_label_path)
                all_labels.append(details_label_path)
            
            # چاپ تمام لیبل‌های این سفارش به ترتیب
            logger.info(f"🖨️ شروع چاپ {len(all_labels)} لیبل برای سفارش {order_id}...")
            for i, label_path in enumerate(all_labels):
                print_success = print_label(label_path)
                if print_success:
                    logger.info(f"✅ لیبل {i+1}/{len(all_labels)} چاپ شد: {os.path.basename(label_path)}")
                else:
                    logger.warning(f"⚠️ لیبل {i+1}/{len(all_labels)} ذخیره شد: {os.path.basename(label_path)}")
            
            logger.info(f"✅ تمام لیبل‌های سفارش {order_id} پردازش شدند")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در پردازش سفارش {order_data.get('id', 'نامشخص')}: {e}")
        return False

@app.route('/webhook/new-order', methods=['POST'])
def handle_new_order():
    """
    دریافت webhook سفارش جدید از WooCommerce
    """
    try:
        # دریافت امضا از header
        signature = request.headers.get('X-WC-Webhook-Signature')
        
        # تأیید امضا
        if not verify_webhook_signature(request.data, signature, WEBHOOK_SECRET):
            logger.warning("❌ امضای webhook نامعتبر")
            return jsonify({"error": "Invalid signature"}), 403
        
        # دریافت داده‌های سفارش
        order_data = request.get_json()
        if not order_data:
            logger.error("❌ داده‌های سفارش یافت نشد")
            return jsonify({"error": "No order data"}), 400
        
        order_id = order_data.get('id')
        logger.info(f"📨 دریافت webhook برای سفارش: {order_id}")
        
        # پردازش سفارش
        if process_new_order(order_data):
            logger.info(f"✅ سفارش {order_id} با موفقیت پردازش شد")
            return jsonify({"status": "success", "order_id": order_id}), 200
        else:
            logger.error(f"❌ خطا در پردازش سفارش {order_id}")
            return jsonify({"status": "error", "order_id": order_id}), 500
            
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره در webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/webhook/test', methods=['GET'])
def test_webhook():
    """تست webhook"""
    return jsonify({
        "status": "ok",
        "message": "Webhook server is running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """بررسی سلامت سرور"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "printing_available": PRINTING_AVAILABLE
    })

@app.route('/', methods=['GET'])
def home():
    """صفحه اصلی"""
    return jsonify({
        "message": "WooCommerce Label Webhook Server",
        "endpoints": {
            "webhook": "/webhook/new-order",
            "test": "/webhook/test",
            "health": "/health"
        },
        "status": "running"
    })

if __name__ == '__main__':
    # بررسی تنظیمات
    if WEBHOOK_SECRET == "your_webhook_secret_here":
        logger.warning("⚠️ لطفاً WEBHOOK_SECRET را در فایل تنظیم کنید")
    
    if (WOOCOMMERCE_CONFIG['site_url'] == 'https://yoursite.com' or 
        WOOCOMMERCE_CONFIG['consumer_key'] == 'ck_your_consumer_key_here' or
        WOOCOMMERCE_CONFIG['consumer_secret'] == 'cs_your_consumer_secret_here'):
        logger.error("❌ لطفاً تنظیمات WooCommerce را در فایل config.py تکمیل کنید")
        sys.exit(1)
    
    logger.info("🚀 شروع سرور webhook...")
    logger.info("📡 سرور در حال اجرا روی http://0.0.0.0:5443")
    logger.info("🔗 آدرس webhook: http://your-server:5443/webhook/new-order")
    
    # اجرای سرور
    app.run(
        host='0.0.0.0',
        port=5443,
        debug=False
    )
