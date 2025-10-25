from PIL import Image, ImageDraw, ImageFont, features
import qrcode
from arabic_reshaper import reshape
import jdatetime
import os

# Handle bidi import with fallback for Windows DLL issues
try:
    from bidi.algorithm import get_display
    BIDI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: bidi package not available ({e}). Using fallback for text shaping.")
    BIDI_AVAILABLE = False
    
    # Fallback function that just returns the text as-is
    def get_display(text):
        return text

# 🎯 تنظیمات اصلی
FONT_EN = "Galatican.ttf"
FONT_FA = "BTitrBd.ttf"

LABEL_W, LABEL_H = int(80 * 9.6), int(100 * 9.6)  # 80x100mm در 243 DPI (20% افزایش برای کیفیت بهتر)

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
        font_title = ImageFont.truetype(FONT_EN, 94)  # Increased from 88
        font_brand = ImageFont.truetype(FONT_FA, 62)  # Increased from 58
        font_normal = ImageFont.truetype(FONT_FA, 28) # Increased from 26
        font_small = ImageFont.truetype(FONT_FA, 24)  # Increased from 22
        font_bold = ImageFont.truetype(FONT_FA, 34)   # Increased from 32
        # Use OpenSans font from project root for website address (same as main/details)
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
        ImageFont.truetype(_regular_fa_font_path, 24)  # Increased from 22
        if _regular_fa_font_path
        else font_small
    )
    font_fa_regular_normal = (
        ImageFont.truetype(_regular_fa_font_path, 28)  # Increased from 26
        if _regular_fa_font_path
        else font_normal
    )

    # 🧰 توابع فارسی
    def fa_shape(text):
        if HAS_RAQM:
            return text
        elif BIDI_AVAILABLE:
            return get_display(reshape(text))
        else:
            # Fallback: just reshape without bidi processing
            try:
                return reshape(text)
            except:
                return text
    def draw_fa_text(xy, text, font, fill="black"):
        kwargs = {"direction": "rtl", "language": "fa"} if HAS_RAQM else {}
        # Add text stroke for better clarity
        shaped_text = fa_shape(text)
        # Draw stroke (outline) in white first
        for adj in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            draw.text((xy[0] + adj[0], xy[1] + adj[1]), shaped_text, font=font, fill="white", **kwargs)
        # Draw main text
        draw.text(xy, shaped_text, font=font, fill=fill, **kwargs)

    def draw_text_with_stroke(xy, text, font, fill="black"):
        """Draw English text with stroke for better clarity"""
        # Draw stroke (outline) in white first
        for adj in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            draw.text((xy[0] + adj[0], xy[1] + adj[1]), text, font=font, fill="white")
        # Draw main text
        draw.text(xy, text, font=font, fill=fill)

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
    draw_text_with_stroke(((LABEL_W - tw) / 2, 25), title, font_title, fill="black")

    # 🏷 عنوان فارسی
    brand = "قهوه آفر"
    bw, bh = fa_text_size(brand, font_brand)
    draw_fa_text(((LABEL_W - bw) / 2, 140), brand, font=font_brand, fill="black")  # Moved down from 120 to 140

    # 🏢 آدرس‌ها
    addresses = [
        "شعبه مرکزی: خ پلیس، خ اجاره داری، پ ۵۵۵",
        "شعبه ۲: خ بنی‌هاشم، خ رسول‌رحیمی، اتحاد، پ ۱۷",
        "امور بازرگانی: خیابان شریعتی، خ پلیس، اجاره داری، ۳۸",
        "مرکز تماس: ۹۰۰۰۴۵۰۵ (خط ویژه بدون کد تماس) (رایگان)"
    ]
    y_address = 210  # Moved down from 190 to 210
    for line in addresses:
        lw, lh = fa_text_size(line, font_small)
        draw_fa_text((LABEL_W - lw - 30, y_address), line, font=font_small)
        y_address += 40  # Increased spacing from 33 to 40

    # 🧾 بخش ترکیبات و جزئیات محصول - با تراز عمودی بهبود یافته
    y_center_section = 400  # موقعیت مرکزی برای بخش ترکیبات - moved down from 380 to 400
    
    # محاسبه موقعیت شروع بخش ترکیبات (سمت راست)
    comp_title = "ترکیبات:"
    comp_title_w, comp_title_h = fa_text_size(comp_title, font_bold)
    comp_start_x = LABEL_W - comp_title_w - 30  # 30px margin from right edge
    
    # محاسبه موقعیت شروع بخش جزئیات (سمت چپ) - کمی پایین‌تر برای تراز بهتر
    product_details = [
        f"وزن: {weight} گرم",
        f"آسیاب شود: {grind}", 
        "اسپرسوساز"
    ]
    
    # تراز عمودی: بخش ترکیبات در موقعیت اصلی، جزئیات کمی پایین‌تر
    y_comp = y_center_section
    y_details = y_center_section + 35  # 35 پیکسل پایین‌تر برای تراز بهتر
    
    # رسم عنوان ترکیبات
    draw_fa_text((comp_start_x, y_comp), comp_title, font=font_bold)
    
    # رسم جزئیات محصول (سمت چپ)
    for detail in product_details:
        dw, dh = fa_text_size(detail, font_fa_regular_normal)
        draw_fa_text((60, y_details), detail, font=font_fa_regular_normal)
        y_details += 40
    
    # رسم جزئیات ترکیبات (سمت راست)
    composition_lines = composition.split('\n')
    y_comp_current = y_comp + 40

    # محاسبه حداکثر عرض مورد نیاز برای خطوط ترکیبات
    max_detail_width = max(fa_text_size(line, font_fa_regular_normal)[0] for line in composition_lines)

    # تنظیم موقعیت شروع در صورت نیاز
    if comp_start_x + max_detail_width > LABEL_W - 30:
        comp_start_x = LABEL_W - max_detail_width - 30

    # رسم هر خط ترکیبات
    for line in composition_lines:
        draw_fa_text((comp_start_x, y_comp_current), line, font=font_fa_regular_normal)
        y_comp_current += 40

    # ➖ خط جداکننده بالا
    # Create dashed line by drawing multiple small segments
    x_start, x_end = 60, LABEL_W - 60
    y = 380  # Moved down from 360 to 380
    dash_length = 8
    gap_length = 4
    current_x = x_start
    while current_x < x_end:
        end_x = min(current_x + dash_length, x_end)
        draw.line([(current_x, y), (end_x, y)], fill="black", width=2)
        current_x += dash_length + gap_length

    # ➖ خط جداکننده پایین
    # Create dashed line by drawing multiple small segments
    x_start, x_end = 60, LABEL_W - 60
    y = 640  # Moved down from 620 to 640
    dash_length = 8
    gap_length = 4
    current_x = x_start
    while current_x < x_end:
        end_x = min(current_x + dash_length, x_end)
        draw.line([(current_x, y), (end_x, y)], fill="black", width=2)
        current_x += dash_length + gap_length


    # ☕ توضیح پایانی
    desc_lines = [
        "قهوه آفر عرضه کننده مرغوب ترین دانه قهوه",
        "قهوه فوری و تجهیزات"
    ]
    y_desc = 650  # Moved down from 630 to 650
    for line in desc_lines:
        lw, lh = fa_text_size(line, font_fa_regular_small)
        draw_fa_text(((LABEL_W - lw) / 2, y_desc), line, font=font_fa_regular_small)
        y_desc += 32

    # 🌐 وب‌سایت
    website = "www.offercoffee.ir"
    ww, wh = text_size(website, font_website)
    draw_text_with_stroke(((LABEL_W - ww) / 2, LABEL_H - wh - 45), website, font=font_website, fill="black")  # Moved up from 25 to 45

    # 📤 ذخیره و نمایش
    # Save with high DPI for better print quality
    img.save(output_path, dpi=(300, 300), quality=95)
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