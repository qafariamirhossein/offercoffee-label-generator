#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from datetime import datetime
from woocommerce_api import WooCommerceAPI
from config import WOOCOMMERCE_CONFIG, LABEL_CONFIG
import platform

# Import label generation functions with platform detection
try:
    from label_main import generate_main_label
    from label_details import generate_details_label
    from label_mixed_linux import generate_mixed_label
except ImportError as e:
    print(f"⚠️ Warning: Could not import label generation modules: {e}")
    print("This might be due to missing dependencies. The script will continue with limited functionality.")
    # Create dummy functions to prevent crashes
    def generate_main_label(*args, **kwargs):
        print("❌ Label generation not available due to import errors")
        return False
    def generate_details_label(*args, **kwargs):
        print("❌ Label generation not available due to import errors")
        return False
    def generate_mixed_label(*args, **kwargs):
        print("❌ Label generation not available due to import errors")
        return False

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

# تنظیمات لاگ
def setup_logging():
    """تنظیم سیستم لاگ"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # نام فایل لاگ با تاریخ
    log_filename = f"{log_dir}/label_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # تنظیم فرمت لاگ
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

# راه‌اندازی لاگ
logger = setup_logging()

def print_label(image_path, save_when_print_fails=True):
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
        
        # اگر چاپ موفق بود و نیازی به ذخیره نیست، فایل را حذف کن
        if not save_when_print_fails:
            try:
                os.remove(image_path)
                logger.info(f"🗑️ فایل تصویر حذف شد: {image_path}")
            except Exception as e:
                logger.warning(f"⚠️ خطا در حذف فایل: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در چاپ - تصویر ذخیره شد: {e}")
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
    
    logger.info("🚀 شروع پردازش سفارشات...")
    
    # اتصال به WooCommerce
    wc_api = WooCommerceAPI(
        WOOCOMMERCE_CONFIG['site_url'],
        WOOCOMMERCE_CONFIG['consumer_key'],
        WOOCOMMERCE_CONFIG['consumer_secret']
    )
    
    # دریافت سفارشات
    logger.info("📥 دریافت سفارشات از WooCommerce...")
    orders = wc_api.get_orders(status='processing')
    
    if not orders:
        logger.warning("❌ هیچ سفارش پردازش نشده‌ای یافت نشد.")
        return
    
    logger.info(f"✅ {len(orders)} سفارش یافت شد.")
    
    # ایجاد پوشه خروجی
    os.makedirs(LABEL_CONFIG['output_dir'], exist_ok=True)
    
    # پردازش هر سفارش
    for order in orders:
        order_id = order['id']
        logger.info(f"📦 شروع پردازش سفارش {order_id}...")
        
        # دریافت جزئیات کامل سفارش
        order_details = wc_api.get_order_details(order_id)
        if not order_details:
            logger.error(f"❌ خطا در دریافت جزئیات سفارش {order_id}")
            continue
            
        try:
            # بررسی نوع سفارش
            if is_mixed_order(order_details):
                logger.info(f"🔀 سفارش {order_id} یک سفارش میکس است - تولید برچسب میکس...")
                
                # تولید لیبل میکس
                mixed_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_mixed.jpg"
                generate_mixed_label(order_details, mixed_label_path)
                
                logger.info(f"✅ لیبل میکس سفارش {order_id} با موفقیت تولید شد")
                
                # چاپ لیبل میکس (ذخیره نکن اگر چاپ موفق بود)
                print_success = print_label(mixed_label_path, save_when_print_fails=False)
                if print_success:
                    logger.info(f"✅ لیبل میکس سفارش {order_id} چاپ شد")
                else:
                    logger.warning(f"⚠️ لیبل میکس سفارش {order_id} ذخیره شد (چاپ ناموفق)")
                
            else:
                logger.info(f"📦 سفارش {order_id} یک سفارش عادی است - تولید برچسب‌های معمولی...")
                
                # تولید لیبل‌های اصلی برای هر محصول
                line_items = order_details.get('line_items', [])
                logger.info(f"📋 {len(line_items)} محصول در سفارش یافت شد")
                
                # لیست تمام لیبل‌های تولید شده برای این سفارش
                all_labels = []
                
                # تولید تمام لیبل‌های پشت (back) برای این سفارش
                for i, item in enumerate(line_items):
                    # ایجاد لیبل پشت برای هر محصول
                    back_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_back_{i+1}.jpg"
                    logger.info(f"🏷️ تولید لیبل پشت برای محصول {i+1}: {item.get('name', 'نامشخص')}")
                    
                    # ایجاد کپی از order_details با فقط این محصول
                    single_product_order = order_details.copy()
                    single_product_order['line_items'] = [item]
                    
                    generate_main_label(single_product_order, back_label_path)
                    all_labels.append(back_label_path)
                
                # تولید تمام لیبل‌های جزئیات برای این سفارش
                for i, item in enumerate(line_items):
                    # ایجاد لیبل جزئیات برای هر محصول
                    details_label_path = f"{LABEL_CONFIG['output_dir']}/order_{order_id}_details_{i+1}.jpg"
                    logger.info(f"📋 تولید لیبل جزئیات برای محصول {i+1}: {item.get('name', 'نامشخص')}")
                    
                    # ایجاد کپی از order_details با فقط این محصول
                    single_product_order = order_details.copy()
                    single_product_order['line_items'] = [item]
                    
                    generate_details_label(single_product_order, details_label_path)
                    all_labels.append(details_label_path)
                
                # چاپ تمام لیبل‌های این سفارش به ترتیب
                logger.info(f"🖨️ شروع چاپ {len(all_labels)} لیبل برای سفارش {order_id}...")
                for i, label_path in enumerate(all_labels):
                    print_success = print_label(label_path, save_when_print_fails=False)
                    if print_success:
                        logger.info(f"✅ لیبل {i+1}/{len(all_labels)} چاپ شد: {os.path.basename(label_path)}")
                    else:
                        logger.warning(f"⚠️ لیبل {i+1}/{len(all_labels)} ذخیره شد: {os.path.basename(label_path)}")
                
                logger.info(f"✅ تمام لیبل‌های سفارش {order_id} پردازش شدند")
            
        except Exception as e:
            logger.error(f"❌ خطا در تولید لیبل‌های سفارش {order_id}: {e}")
            continue
    
    logger.info(f"🎉 پردازش کامل شد! لاگ‌ها در پوشه 'logs' ذخیره شدند.")

def main():
    """تابع اصلی"""
    logger.info("=" * 50)
    logger.info("🏪 سیستم تولید لیبل‌های سفارشات قهوه آفر")
    logger.info("=" * 50)
    
    # بررسی تنظیمات
    if (WOOCOMMERCE_CONFIG['site_url'] == 'https://yoursite.com' or 
        WOOCOMMERCE_CONFIG['consumer_key'] == 'ck_your_consumer_key_here' or
        WOOCOMMERCE_CONFIG['consumer_secret'] == 'cs_your_consumer_secret_here'):
        logger.error("❌ خطا: لطفاً تنظیمات WooCommerce را در فایل config.py تکمیل کنید.")
        logger.info("📝 مراحل:")
        logger.info("   1. وارد پنل مدیریت وردپرس شوید")
        logger.info("   2. به WooCommerce > Settings > Advanced > REST API بروید")
        logger.info("   3. کلید API جدید ایجاد کنید")
        logger.info("   4. اطلاعات را در config.py وارد کنید")
        return
    
    # شروع پردازش
    try:
        process_orders()
    except KeyboardInterrupt:
        logger.info("⏹️ عملیات توسط کاربر متوقف شد.")
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {e}")

if __name__ == "__main__":
    main()
