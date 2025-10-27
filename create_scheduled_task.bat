@echo off
REM حذف task قبلی اگر وجود داشته باشد
schtasks /Delete /TN "OfferCoffee Cron" /F 2>nul

REM ایجاد task جدید با استفاده از batch file
schtasks /Create /TN "OfferCoffee Cron" /SC MINUTE /MO 15 /TR "%~dp0run_offercoffee.bat" /RL HIGHEST /RU SYSTEM

echo Scheduled task created successfully!
schtasks /Query /TN "OfferCoffee Cron" /V /FO LIST

