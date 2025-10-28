from PIL import Image, ImageDraw, ImageFont, features
import qrcode
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import jdatetime
import os

# ==============================
# ⚙️ تنظیمات کلی
# ==============================
FONT_EN = "Galatican.ttf"
FONT_FA = "BTitrBd.ttf"

# اندازه لیبل (بر اساس لیبل واقعی تصویر) - افزایش DPI برای کیفیت بهتر
LABEL_W, LABEL_H = int(617 * 1.2), int(800 * 1.2)  # 20% افزایش برای کیفیت بهتر چاپ

def generate_main_label(order_data, output_path):
    """تولید لیبل اصلی - ثابت برای همه سفارشات"""
    
    # استخراج اطلاعات از سفارش (فقط شماره سفارش)
    order_no = str(order_data['id'])
    today = jdatetime.date.today()
    date = today.strftime("%Y/%m/%d")
    
    # آدرس‌های ثابت شرکت
    address_lines = [
        "شعبه مرکزی: خ شریعتی، خ پلیس، خ اجاره دار پ۵۵۵",
        "شعبه ۲: خ بنی هاشم، خ رسول رحیمی، نبش خیابان اتحاد پلاک ۱۷",
        "امور بازرگانی: خ شریعتی، خ پلیس، خ اجاره دار",
        "کوچه چهل و پنجم، پلاک ۳۸",
        "پشتیبانی: ۹۰۰۰۴۵۰۵"
    ]

    # ساخت تصویر سفید
    img = Image.new("RGB", (LABEL_W, LABEL_H), "white")
    draw = ImageDraw.Draw(img)

    # ==============================
    # 🎨 تنظیم فونت‌ها
    # ==============================
    HAS_RAQM = features.check("raqm")

    font_title = ImageFont.truetype(FONT_EN, 88)  # Increased from 82
    font_brand = ImageFont.truetype(FONT_FA, 52)  # Increased from 48
    font_bold = ImageFont.truetype(FONT_FA, 30)   # Increased from 28
    font_medium = ImageFont.truetype(FONT_FA, 28) # Increased from 26
    font_small = ImageFont.truetype(FONT_FA, 26)  # Increased from 24
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
        ImageFont.truetype(_regular_fa_font_path, 24)
        if _regular_fa_font_path
        else font_small
    )

    # ==============================
    # 📏 توابع کمکی
    # ==============================
    def fa_shape(text):
        return text if HAS_RAQM else get_display(reshape(text))

    def draw_fa(draw, xy, text, font, fill="black"):
        kwargs = {"direction": "rtl", "language": "fa"} if HAS_RAQM else {}
        # Add text stroke for better clarity
        shaped_text = fa_shape(text)
        # Draw stroke (outline) in white first
        for adj in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            draw.text((xy[0] + adj[0], xy[1] + adj[1]), shaped_text, font=font, fill="white", **kwargs)
        # Draw main text
        draw.text(xy, shaped_text, font=font, fill=fill, **kwargs)

    def draw_text_with_stroke(draw, xy, text, font, fill="black"):
        """Draw English text with stroke for better clarity"""
        # Draw stroke (outline) in white first
        for adj in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            draw.text((xy[0] + adj[0], xy[1] + adj[1]), text, font=font, fill="white")
        # Draw main text
        draw.text(xy, text, font=font, fill=fill)

    def text_size(draw, text, font, fa=False):
        shaped = fa_shape(text) if fa else text
        kwargs = {"direction": "rtl", "language": "fa"} if fa and HAS_RAQM else {}
        bbox = draw.textbbox((0, 0), shaped, font=font, **kwargs)
        return bbox[2]-bbox[0], bbox[3]-bbox[1]

    # ==============================
    # 🧱 چیدمان متون
    # ==============================

    # 🔹 OFFER COFFEE
    t = "OFFER COFFEE"
    tw, th = text_size(draw, t, font_title)
    draw_text_with_stroke(draw, ((LABEL_W - tw) / 2, 25), t, font_title, fill="black")

    # 🔹 قهوه آفر
    brand = "قهوه آفر"
    bw, bh = text_size(draw, brand, font_brand, fa=True)
    draw_fa(draw, ((LABEL_W - bw) / 2, 120), brand, font_brand)

    # 🔹 آدرس‌ها - استفاده از اطلاعات مشتری
    y = 195
    for line in address_lines:
        lw, lh = text_size(draw, line, font_small, fa=True)
        draw_fa(draw, (LABEL_W - lw - 25, y), line, font_small)
        y += 33

    # 🔹 توضیحات
    desc = [
        "قهوه آفر بزرگترین فروشگاه اینترنتی کشور",
        "عرضه کننده مرغوب ترین دانه قهوه",
        "قهوه فوری و تجهیزات",
    ]
    # Add a little extra space before this section and render with a regular (non-bold) font if available
    y = 370
    for line in desc:
        lw, lh = text_size(draw, line, font_fa_regular_small, fa=True)
        draw_fa(draw, (LABEL_W - lw - 25, y), line, font_fa_regular_small)
        y += 37

    # ==============================
    # 📊 بخش پایین
    # ==============================

    bottom_y = 515

    # 🔳 QR - آدرس سایت
    qr = qrcode.make("https://offercoffee.ir").resize((150, 150))
    img.paste(qr, (45, bottom_y))

    # پروانه بهداشت بالای QR
    health_text = "پروانه بهداشت"
    hw, hh = text_size(draw, health_text, font_fa_regular_small, fa=True)
    health_x = 45 + (150 - hw) // 2  # وسط QR
    health_y = bottom_y - 30
    draw_fa(draw, (health_x, health_y), health_text, font_fa_regular_small)

    # شماره پروانه زیر QR
    permit_no = "14046488"
    pnw, pnh = text_size(draw, permit_no, font_fa_regular_small, fa=True)
    permit_x = 45 + (150 - pnw) // 2  # وسط QR
    permit_y = bottom_y + 150 + 3
    draw_fa(draw, (permit_x, permit_y), permit_no, font_fa_regular_small)

    # 🔸 متن‌ها - راست‌چین کردن همه متن‌ها
    info_y = bottom_y + 10
    infos = [
        f"تاریخ تولید: {date}",
        "انقضا ۲ سال پس از تولید",
        f"شماره سفارش: {order_no}"
    ]

    # راست‌چین کردن هر خط جداگانه
    right_margin = 25
    for i, line in enumerate(infos):
        lw, lh = text_size(draw, line, font_bold, fa=True)
        right_x = LABEL_W - right_margin - lw
        draw_fa(draw, (right_x, info_y + i * 42), line, font_bold)

    # 🔸 آدرس سایت در پایین صفحه
    website_text = "www.offercoffee.ir"
    website_w, website_h = text_size(draw, website_text, font_website)
    website_x = (LABEL_W - website_w) // 2  # وسط صفحه
    website_y = LABEL_H - website_h - 20  # 20 پیکسل از پایین
    draw_text_with_stroke(draw, (website_x, website_y), website_text, font_website, fill="black")

    # ==============================
    # 🖼 خروجی
    # ==============================
    # Save with high DPI for better print quality
    img.save(output_path, dpi=(300, 300), quality=95)
    print(f"✅ لیبل اصلی در {output_path} ذخیره شد")
    return True
