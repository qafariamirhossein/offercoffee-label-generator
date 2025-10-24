from PIL import Image, ImageDraw, ImageFont, ImageWin
import win32print, win32ui, qrcode
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from datetime import datetime
import jdatetime  # برای تاریخ شمسی

# 🎯 تنظیمات
printer_name = "Godex G500"
FONT_EN = r"C:\Printservice\Galatican.ttf"
FONT_FA = r"C:\Printservice\BTITRBD.TTF"

# 📏 اندازه لیبل به پیکسل (203 DPI = 8px/mm)
LABEL_W, LABEL_H = int(80 * 8), int(100 * 8)

# 🧾 داده‌های متغیر
order_no = "8412"
today = jdatetime.date.today()
date = today.strftime("%Y/%m/%d")  # تاریخ شمسی امروز

# 🧱 ساخت تصویر
img = Image.new("RGB", (LABEL_W, LABEL_H), "white")
draw = ImageDraw.Draw(img)

# 📌 فونت‌ها
font_title = ImageFont.truetype(FONT_EN, 88)
font_brand = ImageFont.truetype(FONT_FA, 58)
font_bold = ImageFont.truetype(FONT_FA, 30)
font_medium = ImageFont.truetype(FONT_FA, 27)
font_small = ImageFont.truetype(FONT_FA, 24)
font_website = ImageFont.truetype(FONT_EN, 34)

# 📦 تابع کمکی برای اندازه متن
def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

# 🎨 عنوان انگلیسی - CENTER بالا
title_text = "OFFER COFFEE"
tw, th = text_size(draw, title_text, font_title)
draw.text(((LABEL_W - tw) / 2, 20), title_text, fill="black", font=font_title)

# 🎨 عنوان فارسی - CENTER زیر آن
brand_text = "قهوه آفر"
reshaped_brand = get_display(reshape(brand_text))
bw, bh = text_size(draw, reshaped_brand, font_brand)
draw.text(((LABEL_W - bw) / 2, 115), reshaped_brand, fill="black", font=font_brand)

# 🏢 آدرس‌ها
addresses = [
    "شعبه مرکزی: خ شریعتی، خ پلیس، خ اجاره دار، پ ۵۵۵",
    "شعبه ۲: خ بنی هاشم، خ رسول رحیمی، نبش خ اتحاد، پ ۱۷",
    "امور بازرگانی: خ شریعتی، خ پلیس، خ اجاره دار،",
    "کوچه چهل و پنجم، پلاک ۳۸  |  مرکز تماس: ۹۰۰۰۴۵۰۵"
]

y_address = 195
for line in addresses:
    reshaped_line = get_display(reshape(line))
    lw, lh = text_size(draw, reshaped_line, font_small)
    draw.text((LABEL_W - lw - 25, y_address), reshaped_line, font=font_small, fill="black")
    y_address += 33

# 📝 توضیحات شرکت
descriptions = [
    "قهوه آفر بزرگترین فروشگاه اینترنتی کشور",
    "عرضه کننده مرغوب ترین دانه قهوه",
    "قهوه فوری و تجهیزات"
]

y_desc = 335
for line in descriptions:
    reshaped_line = get_display(reshape(line))
    dw, dh = text_size(draw, reshaped_line, font_medium)
    draw.text((LABEL_W - dw - 25, y_desc), reshaped_line, font=font_medium, fill="black")
    y_desc += 38

# 📊 بخش پایین
bottom_start_y = 485

# 🔳 QR Code در سمت چپ پایین
qr = qrcode.make(order_no).resize((150, 150))
img.paste(qr, (40, bottom_start_y))

# 📄 اطلاعات سمت راست پایین
info_start_x = LABEL_W // 2 + 25
info_start_y = bottom_start_y + 10

production_text = f"تاریخ تولید: {date}"
expiry_text = "انقضا ۲ سال پس از تولید"
order_text = f"شماره سفارش: {order_no}"

for i, line in enumerate([production_text, expiry_text, order_text]):
    reshaped_line = get_display(reshape(line))
    draw.text((info_start_x, info_start_y + i * 40), reshaped_line, font=font_bold, fill="black")

# 🌐 وب‌سایت - وسط پایین
website_text = "www.offercoffee.ir"
ww, wh = text_size(draw, website_text, font_website)
draw.text(((LABEL_W - ww) / 2, LABEL_H - wh - 20), website_text, fill="black", font=font_website)

# 👀 نمایش پیش‌نمایش
img.show()

# در صورت تأیید چاپ شود
input("اگر از پیش‌نمایش راضی هستید، Enter را بزنید برای چاپ...")

try:
    hprinter = win32print.OpenPrinter(printer_name)
    pdc = win32ui.CreateDC()
    pdc.CreatePrinterDC(printer_name)
    pdc.StartDoc("Offer Coffee Label")
    pdc.StartPage()

    dib = ImageWin.Dib(img)
    dib.draw(pdc.GetHandleOutput(), (0, 0, LABEL_W, LABEL_H))

    pdc.EndPage()
    pdc.EndDoc()
    pdc.DeleteDC()

    print("✅ چاپ موفق انجام شد.")
except Exception as e:
    print(f"❌ خطا در چاپ: {e}")

# ذخیره نسخه پیش‌نمایش
img.save("label_preview.jpg")
print("📁 تصویر در 'label_preview.jpg' ذخیره شد.")
