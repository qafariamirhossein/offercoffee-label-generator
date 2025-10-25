from PIL import Image, ImageDraw, ImageFont, features
import qrcode
import re
from urllib.parse import quote
from config import WOOCOMMERCE_CONFIG
from woocommerce_api import WooCommerceAPI
# QR code is used instead of barcode for product links
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import jdatetime
import os

# 🎯 تنظیمات اصلی
FONT_EN = "Galatican.ttf"
FONT_FA = "BTitrBd.ttf"

LABEL_W, LABEL_H = int(80 * 8), int(100 * 8)  # 80x100mm در 203 DPI

def generate_details_label(order_data, output_path):
    """تولید لیبل جزئیات بر اساس داده‌های سفارش"""
    
    # استخراج اطلاعات محصولات
    line_items = order_data['line_items']
    products_info = []
    
    for item in line_items:
        product_name = item['name']
        quantity = item['quantity']
        
        # استخراج جزئیات محصول از meta_data
        weight = "نامشخص"
        grinding = "نامشخص"
        
        for meta in item.get('meta_data', []):
            if meta['key'] == 'weight':
                weight = f"{meta['value']} گرم"
            elif meta['key'] == 'grinding_grade':
                grinding = meta['value']
        
        # ساخت اطلاعات محصول
        product_details = [
            product_name,
            f"وزن: {weight}",
            f"درجه آسیاب: {grinding}"
        ]
        
        products_info.extend(product_details)
        products_info.append("")  # خط خالی بین محصولات
    
    # اطلاعات سفارش
    order_no = str(order_data['id'])
    total = order_data['total']
    payment_method = order_data['payment_method_title']
    
    # 📅 تاریخ امروز
    today = jdatetime.date.today()
    date = today.strftime("%Y/%m/%d")

    # 🖼 ساخت تصویر
    img = Image.new("RGB", (LABEL_W, LABEL_H), "white")
    draw = ImageDraw.Draw(img)

    # 📚 بارگذاری فونت‌ها
    try:
        HAS_RAQM = features.check("raqm")
        font_title = ImageFont.truetype(FONT_EN, 88)
        font_brand = ImageFont.truetype(FONT_FA, 58)
        font_normal = ImageFont.truetype(FONT_FA, 26)
        font_small = ImageFont.truetype(FONT_FA, 22)
        font_bold = ImageFont.truetype(FONT_FA, 32)
        # Use OpenSans font from project root for website address (15% smaller)
        try:
            font_website = ImageFont.truetype("OpenSans-Regular.ttf", 61)
        except OSError:
            try:
                # Platform-specific fallback paths
                import platform
                if platform.system() == "Windows":
                    # Windows system fonts
                    font_website = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 61)
                else:
                    # Linux system fonts
                    font_website = ImageFont.truetype("/usr/share/fonts/open-sans/OpenSans-Regular.ttf", 61)
            except OSError:
                # Final fallback to default font
                font_website = ImageFont.load_default()
    except OSError:
        print("⚠️ فونت‌ها یافت نشدند، از پیش‌فرض استفاده می‌شود.")
        font_title = font_brand = font_normal = font_small = font_bold = font_website = ImageFont.load_default()
        HAS_RAQM = features.check("raqm")

    # Try to use a regular (non-bold) Persian/Arabic-capable font for non-bold sections
    def _find_regular_fa_font_path() -> str | None:
        import platform
        
        # Platform-specific font paths
        if platform.system() == "Windows":
            candidates = [
                # Windows system fonts
                "C:/Windows/Fonts/NotoSansArabic-Regular.ttf",
                "C:/Windows/Fonts/NotoNaskhArabic-Regular.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/tahoma.ttf",
                # Project/local fallbacks
                "NotoSansArabic-Regular.ttf",
                "NotoNaskhArabic-Regular.ttf",
                "Vazirmatn-Regular.ttf",
                "IRANSans.ttf",
                "Sahel.ttf",
                "DejaVuSans.ttf",
            ]
        else:  # Linux/Unix
            candidates = [
                # Light/Thin variants (preferred for thinner look)
                "/usr/share/fonts/noto/NotoSansArabic-ExtraLight.ttf",
                "/usr/share/fonts/noto/NotoSansArabic-Light.ttf",
                "/usr/share/fonts/noto/NotoNaskhArabic-Light.ttf",
                # Variable font (weight selection not supported directly, but can still look thinner)
                "/usr/share/fonts/google-noto-vf/NotoSansArabic[wght].ttf",
                # Regular Noto (widely available on Fedora)
                "/usr/share/fonts/noto/NotoSansArabic-Regular.ttf",
                "/usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf",
                # DejaVu (fallback, decent Arabic glyphs)
                "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                # Project/local fallbacks
                "NotoSansArabic-ExtraLight.ttf",
                "NotoSansArabic-Light.ttf",
                "NotoNaskhArabic-Light.ttf",
                "NotoSansArabic-Regular.ttf",
                "NotoNaskhArabic-Regular.ttf",
                "Vazirmatn-Regular.ttf",
                "IRANSans.ttf",
                "Sahel.ttf",
                "DejaVuSans.ttf",
            ]
        
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    _regular_fa_font_path = _find_regular_fa_font_path()
    font_fa_regular_small = (
        ImageFont.truetype(_regular_fa_font_path, 22)
        if _regular_fa_font_path
        else font_small
    )
    font_fa_regular_normal = (
        ImageFont.truetype(_regular_fa_font_path, 26)
        if _regular_fa_font_path
        else font_normal
    )

    # 🧰 توابع فارسی
    def fa_shape(text): return text if HAS_RAQM else get_display(reshape(text))
    def draw_fa_text(xy, text, font, fill="black"):
        kwargs = {"direction": "rtl", "language": "fa"} if HAS_RAQM else {}
        draw.text(xy, fa_shape(text), font=font, fill=fill, **kwargs)

    def text_size(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def fa_text_size(text, font):
        kwargs = {"direction": "rtl", "language": "fa"} if HAS_RAQM else {}
        shaped = fa_shape(text)
        bbox = draw.textbbox((0, 0), shaped, font=font, **kwargs)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    # وبسایت را به صورت خودکار تا بیشترین اندازه‌ای که جا شود بزرگ کن
    def autosize_website_font(text, max_width):
        import platform
        
        # تلاش از بزرگ به کوچک تا جا شود (بزرگتر از قبل)
        for size in range(220, 70, -2):
            try:
                fw = ImageFont.truetype("OpenSans-Regular.ttf", size)
            except OSError:
                try:
                    # Platform-specific fallback paths
                    if platform.system() == "Windows":
                        fw = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
                    else:
                        fw = ImageFont.truetype("/usr/share/fonts/open-sans/OpenSans-Regular.ttf", size)
                except OSError:
                    try:
                        if platform.system() == "Windows":
                            fw = ImageFont.truetype("C:/Windows/Fonts/calibri.ttf", size)
                        else:
                            fw = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", size)
                    except OSError:
                        fw = ImageFont.load_default()
            w, h = text_size(text, fw)
            if w <= max_width:
                return fw
        return font_website

    def slugify_fa(name: str) -> str:
        # ساده: فاصله‌ها به خط تیره، حذف کاراکترهای غیر مجاز به جز حروف فارسی/ارقام/خط تیره
        s = re.sub(r"\s+", "-", name.strip())
        s = re.sub(r"[^0-9A-Za-z\-\u0600-\u06FF]", "", s)
        return s

    # 🏷 عنوان انگلیسی
    title = "OFFER COFFEE"
    tw, th = text_size(title, font_title)
    draw.text(((LABEL_W - tw) / 2, 25), title, font=font_title, fill="black")

    # 🏷 عنوان فارسی
    brand = "قهوه آفر"
    bw, bh = fa_text_size(brand, font_brand)
    draw_fa_text(((LABEL_W - bw) / 2, 120), brand, font_brand, fill="black")

    # 🏢 آدرس‌ها
    addresses = [
        "شعبه مرکزی: خ پلیس، خ اجاره داری، پ ۵۵۵",
        "شعبه ۲: خ بنی‌هاشم، خ رسول‌رحیمی، اتحاد، پ ۱۷",
        "امور بازرگانی: خیابان شریعتی، خ پلیس، اجاره داری، ۳۸",
        "مرکز تماس: ۹۰۰۰۴۵۰۵ (خط ویژه بدون کد تماس) (رایگان)"
    ]
    y_address = 190
    for line in addresses:
        lw, lh = fa_text_size(line, font_small)
        draw_fa_text((LABEL_W - lw - 30, y_address), line, font_small)
        y_address += 33

    # 🧾 بخش محصولات سفارش
    y_comp = 380
    # Calculate the exact position where "ترکیبات:" starts
    comp_title = "ترکیبات:"
    comp_title_w, _ = fa_text_size(comp_title, font_bold)
    comp_start_x = LABEL_W - comp_title_w - 30  # 30px margin from right edge
    draw_fa_text((comp_start_x, y_comp), comp_title, font_bold)

    # محاسبه موقعیت مناسب برای محصولات (چپ‌تر از عنوان)
    product_start_x = 30  # 30px از سمت راست
    y_product = y_comp + 40
    
    for product in products_info:
        if product.strip():  # فقط خطوط غیرخالی را نمایش بده
            product_w, _ = fa_text_size(product, font_fa_regular_normal)
            # راست‌چین کردن متن محصول
            right_x = LABEL_W - product_start_x - product_w
            draw_fa_text((right_x, y_product), product, font_fa_regular_normal)
            y_product += 40
        else:
            y_product += 20  # خط خالی

    # اطلاعات اضافی سفارش حذف شد - فقط محصولات نمایش داده می‌شود

    # ➖ خط جداکننده بالا
    # Create dashed line by drawing multiple small segments
    x_start, x_end = 60, LABEL_W - 60
    y = 360
    dash_length = 8
    gap_length = 4
    current_x = x_start
    while current_x < x_end:
        end_x = min(current_x + dash_length, x_end)
        draw.line([(current_x, y), (end_x, y)], fill="black", width=2)
        current_x += dash_length + gap_length

    # 🔳 QR کد برای لینک محصول
    if line_items:
        first_product = line_items[0]
        # ساخت لینک محصول
        product_link = None
        # تلاش برای دریافت permalink از API
        try:
            wc_api = WooCommerceAPI(
                WOOCOMMERCE_CONFIG['site_url'],
                WOOCOMMERCE_CONFIG['consumer_key'],
                WOOCOMMERCE_CONFIG['consumer_secret']
            )
            product = wc_api.get_product(int(first_product['product_id']))
            if product and product.get('permalink'):
                product_link = product['permalink']
            elif product and product.get('slug'):
                product_link = f"{WOOCOMMERCE_CONFIG['site_url'].rstrip('/')}/product/{product['slug'].strip('/')}/"
        except Exception:
            product_link = None
        # در صورت عدم موفقیت، از نام محصول اسلاگ بساز
        if not product_link:
            slug = slugify_fa(first_product.get('name', ''))
            if slug:
                product_link = f"{WOOCOMMERCE_CONFIG['site_url'].rstrip('/')}/product/{slug}/"
            else:
                product_link = f"{WOOCOMMERCE_CONFIG['site_url'].rstrip('/')}"
        
        # تولید QR کد برای لینک محصول
        qr = qrcode.make(product_link).resize((150, 150))
        img.paste(qr, (60, y_comp + 20))
    else:
        # اگر محصولی نباشد، آدرس سایت را قرار بده
        fallback_text = "https://offercoffee.ir"
        qr = qrcode.make(fallback_text).resize((150, 150))
        img.paste(qr, (60, y_comp + 20))

    # ➖ خط جداکننده پایین
    # Create dashed line by drawing multiple small segments
    x_start, x_end = 60, LABEL_W - 60
    y = 650
    dash_length = 8
    gap_length = 4
    current_x = x_start
    while current_x < x_end:
        end_x = min(current_x + dash_length, x_end)
        draw.line([(current_x, y), (end_x, y)], fill="black", width=2)
        current_x += dash_length + gap_length

    # 📱 متن بالای خط جداکننده پایین
    scan_text = "برای مشاهده محصول در سایت بارکد را اسکن کنید"
    sw, sh = fa_text_size(scan_text, font_fa_regular_small)
    draw_fa_text(((LABEL_W - sw) / 2, 590), scan_text, font_fa_regular_small)

    # ☕ توضیح پایانی
    desc_lines = [
        "قهوه آفر عرضه کننده مرغوب ترین دانه قهوه",
        "قهوه فوری و تجهیزات"
    ]
    y_desc = 660
    for line in desc_lines:
        lw, lh = fa_text_size(line, font_fa_regular_small)
        draw_fa_text(((LABEL_W - lw) / 2, y_desc), line, font_fa_regular_small)
        y_desc += 32

    # 🌐 وب‌سایت - نمایش خیلی بزرگ‌تر با اندازه‌گذاری خودکار
    website = "www.offercoffee.ir"
    max_text_w = LABEL_W - 50  # حاشیه‌ها کمی کمتر برای بزرگ‌تر شدن متن
    font_website_big = autosize_website_font(website, max_text_w)
    ww, wh = text_size(website, font_website_big)
    draw.text(((LABEL_W - ww) / 2, LABEL_H - wh - 18), website, font=font_website_big, fill="black")

    # 📤 ذخیره و نمایش
    img.save(output_path)
    print(f"✅ لیبل جزئیات در {output_path} ذخیره شد")