#!/bin/bash
echo "🚀 Clan Bot - Railway Deployment"
echo "================================"
echo "Token: ${TOKEN:0:10}..."
echo "Admin ID: $ADMIN_ID"
echo "Database URL: ${DATABASE_URL:0:30}..."
echo ""

# ایجاد پوشه data برای جلوگیری از خطا
mkdir -p data 2>/dev/null

# اجرای ربات
exec python bot.py
