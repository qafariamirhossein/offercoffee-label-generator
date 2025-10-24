#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from woocommerce_api import WooCommerceAPI
from config import WOOCOMMERCE_CONFIG, LABEL_CONFIG
from label_main import generate_main_label
from label_details import generate_details_label
from label_mixed_linux import generate_mixed_label

# Import printing functionality
try:
    import win32print, win32ui
    from PIL import ImageWin
    PRINTING_AVAILABLE = True
except ImportError:
    PRINTING_AVAILABLE = False
    print("⚠️ ماژول‌های چاپ در دسترس نیستند - فقط ذخیره تصاویر انجام می‌شود")

# تنظیمات چاپگر
PRINTER_NAME = "Godex G500"  # نام چاپگر

def print_label(image_path):
    """چاپ لیبل یا ذخیره به عنوان فالبک"""
    try:
        if not PRINTING_AVAILABLE:
            print(f"💾 چاپگر در دسترس نیست - تصویر ذخیره شد: {image_path}")
            return True
            
        # بررسی وجود چاپگر
        printers = [printer[2] for printer in win32print.EnumPrinters(2)]
        if PRINTER_NAME not in printers:
            print(f"⚠️ چاپگر '{PRINTER_NAME}' یافت نشد - تصویر ذخیره شد: {image_path}")
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
        
        print(f"✅ لیبل با موفقیت چاپ شد: {image_path}")
        return True
        
    except Exception as e:
        print(f"❌ خطا در چاپ - تصویر ذخیره شد: {e}")
        return False

def is_mixed_order(order_details):
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

def process_orders():
    """پردازش سفارشات و تولید لیبل‌ها"""
    
    print("🚀 شروع پردازش سفارشات...")
    
    # اتصال به WooCommerce
    wc_api = WooCommerceAPI(
        WOOCOMMERCE_CONFIG['site_url'],
        WOOCOMMERCE_CONFIG['consumer_key'],
        WOOCOMMERCE_CONFIG['consumer_secret']
    )
    
    # دریافت سفارشات
    print("📥 دریافت سفارشات از WooCommerce...")
    orders = wc_api.get_orders(status='processing')
    
    if not orders:
        print("❌ هیچ سفارش پردازش نشده‌ای یافت نشد.")
        return
    
    print(f"✅ {len(orders)} سفارش یافت شد.")
    
    # ایجاد پوشه خروجی
    os.makedirs(LABEL_CONFIG['output_dir'], exist_ok=True)
    
    # پردازش هر سفارش
    for order in orders:
        order_id = order['id']
        print(f"\n📦 پردازش سفارش {order_id}...")
        
        # دریافت جزئیات کامل سفارش
        order_details = wc_api.get_order_details(order_id)
        if not order_details:
            print(f"❌ خطا در دریافت جزئیات سفارش {order_id}")
            continue
            
        try:
            # بررسی نوع سفارش
            if is_mixed_order(order_details):
                print(f"🔀 سفارش {order_id} یک سفارش میکس است - تولید برچسب میکس...")
                
                # تولید لیبل میکس
                mixed_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_mixed.jpg"
                generate_mixed_label(order_details, mixed_label_path)
                
                print(f"✅ لیبل میکس سفارش {order_id} با موفقیت تولید شد")
                print(f"   📁 لیبل میکس: {mixed_label_path}")
                
                # چاپ لیبل میکس
                print_label(mixed_label_path)
                
            else:
                print(f"📦 سفارش {order_id} یک سفارش عادی است - تولید برچسب‌های معمولی...")
                
                # تولید لیبل اصلی
                main_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_main.jpg"
                print(f"🏷️ تولید لیبل اصلی...")
                generate_main_label(order_details, main_label_path)
                
                # چاپ لیبل اصلی
                print_label(main_label_path)
                
                # تولید لیبل‌های جزئیات برای هر محصول
                line_items = order_details.get('line_items', [])
                print(f"📋 {len(line_items)} محصول در سفارش یافت شد")
                
                generated_detail_labels = []
                for i, item in enumerate(line_items):
                    # ایجاد لیبل جزئیات برای هر محصول
                    details_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_details_{i+1}.jpg"
                    print(f"📋 تولید لیبل جزئیات برای محصول {i+1}: {item.get('name', 'نامشخص')}")
                    
                    # ایجاد کپی از order_details با فقط این محصول
                    single_product_order = order_details.copy()
                    single_product_order['line_items'] = [item]
                    
                    generate_details_label(single_product_order, details_label_path)
                    generated_detail_labels.append(details_label_path)
                    
                    # چاپ لیبل جزئیات
                    print_label(details_label_path)
                
                print(f"✅ لیبل‌های سفارش {order_id} با موفقیت تولید شدند")
                print(f"   📁 لیبل اصلی: {main_label_path}")
                for i, detail_path in enumerate(generated_detail_labels):
                    print(f"   📁 لیبل جزئیات {i+1}: {detail_path}")
            
        except Exception as e:
            print(f"❌ خطا در تولید لیبل‌های سفارش {order_id}: {e}")
            continue
    
    print(f"\n🎉 پردازش کامل شد! لیبل‌ها در پوشه '{LABEL_CONFIG['output_dir']}' ذخیره شدند.")

def main():
    """تابع اصلی"""
    print("=" * 50)
    print("🏪 سیستم تولید لیبل‌های سفارشات قهوه آفر")
    print("=" * 50)
    
    # بررسی تنظیمات
    if (WOOCOMMERCE_CONFIG['site_url'] == 'https://yoursite.com' or 
        WOOCOMMERCE_CONFIG['consumer_key'] == 'ck_your_consumer_key_here' or
        WOOCOMMERCE_CONFIG['consumer_secret'] == 'cs_your_consumer_secret_here'):
        print("❌ خطا: لطفاً تنظیمات WooCommerce را در فایل config.py تکمیل کنید.")
        print("📝 مراحل:")
        print("   1. وارد پنل مدیریت وردپرس شوید")
        print("   2. به WooCommerce > Settings > Advanced > REST API بروید")
        print("   3. کلید API جدید ایجاد کنید")
        print("   4. اطلاعات را در config.py وارد کنید")
        return
    
    # شروع پردازش
    try:
        process_orders()
    except KeyboardInterrupt:
        print("\n⏹️ عملیات توسط کاربر متوقف شد.")
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")

if __name__ == "__main__":
    main()
