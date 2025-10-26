#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cron-friendly processor for WooCommerce orders.
- Fetches recently paid orders
- Generates labels (mixed or per-item back + details)
- Skips already-processed orders using a local state file
- Logs to logs/ with UTF-8
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Set

# Ensure we run from the project root (so relative font files work)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# Local imports
from woocommerce_api import WooCommerceAPI
from config import WOOCOMMERCE_CONFIG, LABEL_CONFIG
from label_main import generate_main_label
from label_details import generate_details_label
from label_mixed import generate_mixed_label

# Import printing functionality
try:
    import win32print, win32ui
    from PIL import Image, ImageWin
    PRINTING_AVAILABLE = True
except ImportError:
    PRINTING_AVAILABLE = False

# تنظیمات چاپگر
PRINTER_NAME = "Godex G500"  # نام چاپگر


# -----------------------
# Helpers
# -----------------------
def ensure_directories() -> None:
    os.makedirs(LABEL_CONFIG.get('output_dir', 'labels'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)


def setup_logger() -> logging.Logger:
    ensure_directories()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logfile = os.path.join('logs', f'cron_processor_{timestamp}.log')

    # Try to ensure stdout is UTF-8 (cron often runs with minimal locales)
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    logger = logging.getLogger('cron_processor')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler(logfile, encoding='utf-8')
    sh = logging.StreamHandler(sys.stdout)

    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.info('🚀 شروع پردازش زمان‌بندی‌شده سفارشات')
    logger.info(f'📁 مسیر پروژه: {BASE_DIR}')
    return logger


def print_label(image_path: str, logger: logging.Logger) -> bool:
    """چاپ لیبل با مدیریت حالت وجود چندین چاپگر"""
    try:
        if not PRINTING_AVAILABLE:
            logger.info(f"💾 چاپگر در دسترس نیست - تصویر ذخیره شد: {image_path}")
            return True
            
        # بررسی وجود چاپگر با لیست دقیق‌تر چاپگرها
        try:
            all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            printer_names = [printer[2] for printer in all_printers]
            logger.info(f"🖨️ چاپگرهای در دسترس: {', '.join(printer_names) if printer_names else 'هیچ'}")
            
            # جستجوی دقیق‌تر نام چاپگر (با در نظر گیری حروف کوچک و بزرگ)
            matching_printer = None
            for printer_name in printer_names:
                if PRINTER_NAME.lower() in printer_name.lower() or printer_name.lower() in PRINTER_NAME.lower():
                    matching_printer = printer_name
                    logger.info(f"✅ چاپگر مورد نظر یافت شد: {matching_printer}")
                    break
            
            if not matching_printer:
                logger.warning(f"⚠️ چاپگر '{PRINTER_NAME}' در لیست چاپگرهای موجود نیست")
                logger.warning(f"📋 چاپگرهای موجود: {printer_names}")
                return True
            
            # بارگذاری و چاپ تصویر
            img = Image.open(image_path)
            
            # باز کردن چاپگر
            hprinter = win32print.OpenPrinter(matching_printer)
            pdc = win32ui.CreateDC()
            pdc.CreatePrinterDC(matching_printer)
            pdc.StartDoc("Offer Coffee Label")
            pdc.StartPage()
            
            dib = ImageWin.Dib(img)
            dib.draw(pdc.GetHandleOutput(), (0, 0, img.width, img.height))
            
            pdc.EndPage()
            pdc.EndDoc()
            pdc.DeleteDC()
            
            logger.info(f"✅ لیبل با موفقیت چاپ شد: {os.path.basename(image_path)}")
            return True
            
        except Exception as printer_error:
            logger.error(f"❌ خطا در دسترسی به چاپگر: {printer_error}")
            return False
        
    except Exception as e:
        logger.error(f"❌ خطا در چاپ - تصویر ذخیره شد: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def is_payment_completed(order_details: Dict[str, Any], logger: logging.Logger) -> bool:
    try:
        payment_status = str(order_details.get('status', '')).lower()
        payment_method = order_details.get('payment_method', '')
        paid_statuses = ['processing', 'on-hold']

        if payment_status not in paid_statuses:
            logger.info(f"⏭️ سفارش {order_details.get('id')} پرداخت نشده (status={payment_status})")
            return False
        if not payment_method:
            logger.info(f"⏭️ سفارش {order_details.get('id')} روش پرداخت نامشخص")
            return False
        try:
            total = float(order_details.get('total', 0))
        except Exception:
            total = 0.0
        if total <= 0:
            logger.info(f"⏭️ سفارش {order_details.get('id')} مبلغ نامعتبر: {total}")
            return False
        return True
    except Exception as e:
        logger.error(f"❌ خطا در بررسی پرداخت سفارش {order_details.get('id', 'نامشخص')}: {e}")
        return False


def is_mixed_order(order_details: Dict[str, Any]) -> bool:
    for item in order_details.get('line_items', []):
        name = str(item.get('name', '')).lower()
        for kw in ['ترکیبی', 'میکس', 'combine', 'mixed', 'blend']:
            if kw in name:
                return True
    return False


def load_processed_ids(path: str) -> Set[int]:
    if not os.path.exists(path):
        return set()
    ids: Set[int] = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(int(line))
            except ValueError:
                continue
    return ids


def save_processed_ids(path: str, ids: Set[int]) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        for oid in sorted(ids):
            f.write(f"{oid}\n")
    os.replace(tmp, path)


def validate_config(logger: logging.Logger) -> bool:
    site = WOOCOMMERCE_CONFIG.get('site_url', '')
    ck = WOOCOMMERCE_CONFIG.get('consumer_key', '')
    cs = WOOCOMMERCE_CONFIG.get('consumer_secret', '')
    if (not site or site == 'https://yoursite.com' or
        ck == 'ck_your_consumer_key_here' or cs == 'cs_your_consumer_secret_here'):
        logger.error('❌ لطفاً مقادیر WOOCOMMERCE_CONFIG را در config.py تکمیل کنید')
        return False
    return True


def get_paid_orders(api: WooCommerceAPI, logger: logging.Logger, per_page: int = 15) -> List[Dict[str, Any]]:
    # Fetch multiple statuses considered paid
    orders_summary: List[Dict[str, Any]] = []
    for status in ['processing', 'on-hold']:
        try:
            part = api.get_orders(status=status, per_page=per_page) or []
            if part:
                logger.info(f"📥 {len(part)} سفارش ({status}) دریافت شد")
            orders_summary.extend(part)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت سفارشات ({status}): {e}")
    return orders_summary


def process_order(order_details: Dict[str, Any], logger: logging.Logger) -> bool:
    try:
        order_id = order_details.get('id')
        output_dir = LABEL_CONFIG.get('output_dir', 'labels')
        os.makedirs(output_dir, exist_ok=True)

        all_labels = []  # لیست تمام لیبل‌های تولید شده

        if is_mixed_order(order_details):
            logger.info(f"🔀 سفارش {order_id} میکس است - تولید لیبل میکس")
            mixed_path = os.path.join(output_dir, f"order_{order_id}_mixed.jpg")
            ok = generate_mixed_label(order_details, mixed_path)
            if ok:
                logger.info(f"✅ لیبل میکس تولید شد: {mixed_path}")
                all_labels.append(mixed_path)
            else:
                logger.warning(f"⚠️ تولید لیبل میکس ناموفق برای سفارش {order_id}")
                return False
        else:
            # Normal order: back + details per line item
            line_items = order_details.get('line_items', [])
            if not line_items:
                logger.info(f"⏭️ سفارش {order_id} آیتمی ندارد")
                return False

            generated = 0

            # Back labels
            for i, item in enumerate(line_items):
                back_path = os.path.join(output_dir, f"order_{order_id}_back_{i+1}.jpg")
                single = dict(order_details)
                single['line_items'] = [item]
                generate_main_label(single, back_path)
                all_labels.append(back_path)
                generated += 1
                logger.info(f"✅ لیبل پشت {i+1}/{len(line_items)}: {back_path}")

            # Details labels
            for i, item in enumerate(line_items):
                details_path = os.path.join(output_dir, f"order_{order_id}_details_{i+1}.jpg")
                single = dict(order_details)
                single['line_items'] = [item]
                generate_details_label(single, details_path)
                all_labels.append(details_path)
                generated += 1
                logger.info(f"✅ لیبل جزئیات {i+1}/{len(line_items)}: {details_path}")

            logger.info(f"🎉 در مجموع {generated} لیبل برای سفارش {order_id} تولید شد")

        # چاپ تمام لیبل‌های تولید شده
        if all_labels and PRINTING_AVAILABLE:
            logger.info(f"🖨️ شروع چاپ {len(all_labels)} لیبل برای سفارش {order_id}...")
            printed_count = 0
            for i, label_path in enumerate(all_labels):
                print_success = print_label(label_path, logger)
                if print_success:
                    printed_count += 1
                    logger.info(f"✅ لیبل {i+1}/{len(all_labels)} چاپ شد: {os.path.basename(label_path)}")
                else:
                    logger.warning(f"⚠️ لیبل {i+1}/{len(all_labels)} چاپ نشد: {os.path.basename(label_path)}")
            logger.info(f"📊 {printed_count}/{len(all_labels)} لیبل با موفقیت چاپ شد")
        elif not PRINTING_AVAILABLE:
            logger.info("💾 ماژول چاپ در دسترس نیست - لیبل‌ها فقط ذخیره شدند")
        else:
            logger.info("💾 لیبل‌ها فقط ذخیره شدند (چاپگر فعال نشد)")

        return len(all_labels) > 0
    except Exception as e:
        logger.error(f"❌ خطا در پردازش سفارش {order_details.get('id', 'نامشخص')}: {e}")
        return False


def main() -> int:
    logger = setup_logger()

    if not validate_config(logger):
        return 1

    # Init API
    api = WooCommerceAPI(
        WOOCOMMERCE_CONFIG['site_url'],
        WOOCOMMERCE_CONFIG['consumer_key'],
        WOOCOMMERCE_CONFIG['consumer_secret'],
    )

    # Load state
    state_path = os.path.join('data', 'processed_orders.txt')
    processed_ids = load_processed_ids(state_path)
    logger.info(f"🗂️ {len(processed_ids)} سفارش قبلاً پردازش شده‌اند")

    # Fetch candidates
    summaries = get_paid_orders(api, logger, per_page=100)
    if not summaries:
        logger.info('ℹ️ هیچ سفارشی یافت نشد')
        return 0

    # Process each unique order (newest first)
    seen: Set[int] = set()
    processed_this_run = 0

    for summary in summaries:
        try:
            oid = int(summary.get('id'))
        except Exception:
            continue
        if oid in seen:
            continue
        seen.add(oid)

        if oid in processed_ids:
            logger.info(f"⏭️ سفارش {oid} قبلاً پردازش شده است")
            continue

        # Get full details
        details = api.get_order_details(oid)
        if not details:
            logger.warning(f"⚠️ جزئیات سفارش {oid} یافت نشد")
            continue

        if not is_payment_completed(details, logger):
            continue

        if process_order(details, logger):
            processed_ids.add(oid)
            processed_this_run += 1
            save_processed_ids(state_path, processed_ids)

    logger.info(f"✅ پردازش تکمیل شد - {processed_this_run} سفارش جدید")
    return 0


def test_order_statuses():
    """تست وضعیت‌های سفارشات بدون نیاز به API"""
    print("🔍 وضعیت‌های سفارشات که به عنوان پرداخت شده در نظر گرفته می‌شوند:")
    statuses = ['processing', 'on-hold', 'shipped', 'delivered', 'fulfilled']
    for i, status in enumerate(statuses, 1):
        print(f"   {i}. {status}")
    
    print("\n📝 برای تست کامل، کلیدهای API را در config.py تنظیم کنید:")
    print("   1. وارد پنل مدیریت وردپرس شوید")
    print("   2. به WooCommerce > Settings > Advanced > REST API بروید")
    print("   3. یک کلید جدید ایجاد کنید")
    print("   4. کلیدها را در فایل config.py قرار دهید")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test-statuses':
        test_order_statuses()
        sys.exit(0)
    
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\n⏹️ عملیات متوقف شد.')
        sys.exit(130)
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")
        sys.exit(1)


