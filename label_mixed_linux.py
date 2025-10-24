from PIL import Image, ImageDraw, ImageFont, features
import qrcode
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import jdatetime
import os

# 🎯 تنظیمات اصلی
FONT_EN = "Galatican.ttf"
FONT_FA = "BTitrBd.ttf"

LABEL_W, LABEL_H = int(80 * 8), int(100 * 8)  # 80x100mm در 203 DPI

def generate_mixed_label(order_details, output_path):
    """تولید برچسب میکس برای سفارش"""
    
    # استخراج اطلاعات از سفارش
    order_no = str(order_details.get('id', '0000'))
    
    # استخراج اطلاعات محصول میکس
    line_items = order_details.get('line_items', [])
    mixed_item = None
    for item in line_items:
        if 'ترکیبی' in item.get('name', '') or 'میکس' in item.get('name', ''):
            mixed_item = item
            break
    
    if not mixed_item:
        print("❌ هیچ محصول میکسی در سفارش یافت نشد")
        return False
    
    # استخراج ترکیبات از metadata
    composition_lines = []
    meta_data = mixed_item.get('meta_data', [])
    
    # استخراج ترکیبات از metadata (جستجو برای کلیدهایی که درصد دارند)
    for meta in meta_data:
        key = meta.get('key', '')
        value = meta.get('value', '')
        
        # اگر کلید شامل نام قهوه است و مقدار شامل درصد است
        if '%' in value and any(keyword in key.lower() for keyword in ['عربیکا', 'روبوستا', 'قهوه', 'arabica', 'robusta', 'coffee']):
            # اطمینان از نمایش صحیح علامت درصد
            if not value.endswith('٪'):
                value = value.replace('%', '٪')
            composition_lines.append(f"{key}: {value}")
    
    # اگر ترکیبات یافت نشد، از پیش‌فرض استفاده کن
    if not composition_lines:
        composition_lines = ["قهوه اسپرسو: ۵۰٪", "عربیکا برزیل سانتوز: ۵۰٪"]
    
    composition = '\n'.join(composition_lines)
    
    # استخراج وزن
    weight = "1000"  # پیش‌فرض
    for meta in meta_data:
        if meta.get('key') == 'weight':
            weight = meta.get('value', weight)
            break
    
    # استخراج آسیاب
    grind = "خیر"  # پیش‌فرض
    for meta in meta_data:
        if meta.get('key') == 'blend_coffee':
            grind = meta.get('value', grind)
            break
    
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
        font_website = ImageFont.truetype(FONT_EN, 34)
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

    # 🏷 عنوان انگلیسی
    title = "OFFER COFFEE"
    tw, th = text_size(title, font_title)
    draw.text(((LABEL_W - tw) / 2, 25), title, font=font_title, fill="black")

    # 🏷 عنوان فارسی
    brand = "قهوه آفر"
    bw, bh = fa_text_size(brand, font_brand)
    draw_fa_text(((LABEL_W - bw) / 2, 120), brand, font=font_brand, fill="black")

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
        draw_fa_text((LABEL_W - lw - 30, y_address), line, font=font_small)
        y_address += 33

    # 🧾 بخش ترکیبات
    y_comp = 380
    # Calculate the exact position where "ترکیبات:" starts
    comp_title = "ترکیبات:"
    comp_title_w, _ = fa_text_size(comp_title, font_bold)
    comp_start_x = LABEL_W - comp_title_w - 30  # 30px margin from right edge
    draw_fa_text((comp_start_x, y_comp), comp_title, font=font_bold)

    # Align all composition details to start exactly where "ترکیبات:" starts
    # Handle multi-line composition text
    composition_lines = composition.split('\n')
    y_comp_current = y_comp + 40

    # Calculate the maximum width needed for composition lines
    max_detail_width = max(fa_text_size(line, font_fa_regular_normal)[0] for line in composition_lines)

    # Adjust start position if details would go beyond right edge
    if comp_start_x + max_detail_width > LABEL_W - 30:
        comp_start_x = LABEL_W - max_detail_width - 30

    # Draw each line of composition
    for line in composition_lines:
        draw_fa_text((comp_start_x, y_comp_current), line, font=font_fa_regular_normal)
        y_comp_current += 40

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

    # 📋 جزئیات محصول (جایگزین QR)
    product_details = [
        f"وزن: {weight} گرم",
        f"آسیاب شود: {grind}", 
        "اسپرسوساز"
    ]
    y_details = y_comp - 10
    for detail in product_details:
        dw, dh = fa_text_size(detail, font_fa_regular_normal)
        draw_fa_text((60, y_details), detail, font=font_fa_regular_normal)
        y_details += 40

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
    scan_text = "برای ثبت سفارش مجدد محصول بارکد را اسکن کنید"
    sw, sh = fa_text_size(scan_text, font_fa_regular_small)
    draw_fa_text(((LABEL_W - sw) / 2, 590), scan_text, font=font_fa_regular_small)

    # ☕ توضیح پایانی
    desc_lines = [
        "قهوه آفر عرضه کننده مرغوب ترین دانه قهوه",
        "قهوه فوری و تجهیزات"
    ]
    y_desc = 660
    for line in desc_lines:
        lw, lh = fa_text_size(line, font_fa_regular_small)
        draw_fa_text(((LABEL_W - lw) / 2, y_desc), line, font=font_fa_regular_small)
        y_desc += 32

    # 🌐 وب‌سایت
    website = "www.offercoffee.ir"
    ww, wh = text_size(website, font_website)
    draw.text(((LABEL_W - ww) / 2, LABEL_H - wh - 25), website, font=font_website, fill="black")

    # 📤 ذخیره و نمایش
    img.save(output_path)
    print(f"✅ برچسب میکس سفارش {order_no} در '{output_path}' ذخیره شد.")
    return True

# تابع تست برای اجرای مستقل
def main():
    """تابع تست برای اجرای مستقل"""
    # داده‌های نمونه برای تست
    sample_order = {
        "id": 8412,
        "line_items": [
            {
                "name": "قهوه ترکیبی",
                "meta_data": [
                    {"key": "ترکیبات", "value": "قهوه اسپرسو: ۵۰٪\nعربیکا برزیل سانتوز: ۵۰٪"},
                    {"key": "وزن", "value": "1000"},
                    {"key": "آسیاب", "value": "خیر"}
                ]
            }
        ]
    }
    
    generate_mixed_label(sample_order, "test_mixed_label.jpg")

if __name__ == "__main__":
    main()