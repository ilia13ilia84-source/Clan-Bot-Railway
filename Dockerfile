FROM python:3.11-slim

WORKDIR /app

# نصب سیستم dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل requirements
COPY requirements.txt .

# نصب Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# کپی بقیه فایل‌ها
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
