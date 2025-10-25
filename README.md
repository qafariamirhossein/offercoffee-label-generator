# ☕ سیستم تولید لیبل‌های خودکار قهوه آفر

سیستم پیشرفته برای تولید خودکار لیبل‌های سفارشات از WooCommerce و چاپ آن‌ها با webhook.

## 🚀 ویژگی‌ها

- ✅ **Webhook بلادرنگ**: دریافت فوری سفارشات جدید از WooCommerce
- 🏷️ **تولید خودکار لیبل**: لیبل اصلی، جزئیات و میکس
- 🖨️ **چاپ خودکار**: پشتیبانی از چاپگرهای مختلف
- 🔒 **امنیت بالا**: تأیید امضای webhook
- 📊 **لاگ‌گیری کامل**: ردیابی تمام عملیات
- 🧪 **تست‌های جامع**: ابزارهای تست و عیب‌یابی

## 📁 ساختار پروژه

```
offercoffee/
├── webhook_server.py          # سرور اصلی webhook
├── start_webhook.py           # اسکریپت راه‌اندازی آسان
├── test_webhook.py           # ابزار تست
├── requirements.txt          # وابستگی‌ها
├── README.md                 # این فایل
├── config.py                 # تنظیمات WooCommerce
├── woocommerce_api.py        # API ووکامرس
├── label_main.py             # تولید لیبل اصلی
├── label_details.py          # تولید لیبل جزئیات
├── label_mixed_linux.py      # تولید لیبل میکس
├── label_generator.py        # تولیدکننده کلی لیبل‌ها
├── main.py                   # اسکریپت اصلی (دستی)
├── labels/                   # پوشه خروجی لیبل‌ها
└── webhook.log              # فایل لاگ
```

## 🛠️ نصب و راه‌اندازی

### 1. ایجاد محیط مجازی (Virtual Environment)

```bash
python3 -m venv venv
source venv/bin/activate  # در Linux/Mac
# یا
venv\Scripts\activate     # در Windows
```

### 2. نصب وابستگی‌ها

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. تنظیم WooCommerce

فایل `config.py` را ویرایش کنید:

```python
WOOCOMMERCE_CONFIG = {
    'site_url': 'https://yoursite.com',
    'consumer_key': 'ck_your_consumer_key_here',
    'consumer_secret': 'cs_your_consumer_secret_here'
}
```

### 4. تنظیم کلید مخفی Webhook

در فایل `webhook_server.py`:

```python
WEBHOOK_SECRET = "your_super_secret_key_here"
```

### 5. اجرای سیستم

#### روش 1: اجرای آسان (پیشنهادی)

```bash
python start_webhook.py
```

#### روش 2: اجرای دستی

```bash
python webhook_server.py
```


## 🏪 تنظیم Webhook در WooCommerce

1. **WooCommerce → Settings → Advanced → Webhooks**
2. **Add Webhook**:
   - **Name**: New Order Webhook
   - **Status**: Active
   - **Topic**: Order created
   - **Delivery URL**: `https://your-domain.com/webhook/new-order`
   - **Secret**: `your_super_secret_key_here`
   - **API Version**: v3

## 🧪 تست سیستم

### تست اتصال

```bash
curl http://localhost:5443/health
```

### تست کامل

```bash
python test_webhook.py
```
### چاپگر

```python
PRINTER_NAME = "Godex G500"  # نام چاپگر شما
```

### پوشه خروجی

```python
LABEL_CONFIG = {
    'output_dir': 'labels',  # پوشه خروجی
}
```

## 🚀 استقرار در تولید

### 1. دامنه و SSL

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Systemd Service

```ini
[Unit]
Description=WooCommerce Webhook Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/offercoffee
ExecStart=/usr/bin/python3 webhook_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```
### شروع سریع:

1. `cd /offercoffee`
2. `python3 -m venv venv`
3. `source venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python start_webhook.py` - راه‌اندازی سرور
6. تنظیم webhook در WooCommerce
7. `python test_webhook.py` - تست سیستم

### خروج از محیط مجازی:

```bash
deactivate
```

**موفق باشید! ☕**