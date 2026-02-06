#!/usr/bin/env python3
import os
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        # فقط از PostgreSQL در Railway استفاده می‌کنیم
        DATABASE_URL = os.environ.get("DATABASE_URL")
        
        if not DATABASE_URL:
            logger.error("❌ DATABASE_URL environment variable is required!")
            raise ValueError("DATABASE_URL is required for Railway deployment")
        
        # اتصال به PostgreSQL
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        try:
            result = urlparse(DATABASE_URL)
            self.conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port,
                cursor_factory=RealDictCursor
            )
            logger.info("✅ Successfully connected to PostgreSQL on Railway")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
        
        self.init_db()
    
    def init_db(self):
        """ساخت جداول در PostgreSQL"""
        cursor = self.conn.cursor()
        
        try:
            # جدول users
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول accounts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    game_name TEXT NOT NULL,
                    attack INTEGER DEFAULT 0,
                    defense INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ساخت ایندکس‌ها
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_accounts_user_id 
                ON accounts(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_accounts_active 
                ON accounts(is_active)
            ''')
            
            self.conn.commit()
            logger.info("✅ Database tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            self.conn.rollback()
            raise
    
    def add_user(self, user_id, username, first_name):
        """افزودن کاربر جدید"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id, username, first_name))
            
            self.conn.commit()
            logger.debug(f"✅ User {user_id} added/updated")
            return True
        except Exception as e:
            logger.error(f"❌ Error adding user {user_id}: {e}")
            self.conn.rollback()
            return False
    
    def set_admin(self, user_id, is_admin=True):
        """تنظیم کاربر به عنوان ادمین"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                UPDATE users 
                SET is_admin = %s 
                WHERE user_id = %s
            ''', (is_admin, user_id))
            
            self.conn.commit()
            logger.debug(f"✅ User {user_id} admin status set to {is_admin}")
            return True
        except Exception as e:
            logger.error(f"❌ Error setting admin for user {user_id}: {e}")
            self.conn.rollback()
            return False
    
    def is_admin(self, user_id):
        """بررسی ادمین بودن کاربر"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT is_admin 
                FROM users 
                WHERE user_id = %s
            ''', (user_id,))
            
            row = cursor.fetchone()
            return row['is_admin'] if row else False
        except Exception as e:
            logger.error(f"❌ Error checking admin for user {user_id}: {e}")
            return False
    
    def get_clan_stats(self):
        """آمار کلی کلن"""
        cursor = self.conn.cursor()
        try:
            # تعداد کاربران منحصر به فرد
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) 
                FROM accounts 
                WHERE is_active = TRUE
            ''')
            total_users = cursor.fetchone()[0] or 0
            
            # تعداد کل اکانت‌ها
            cursor.execute('''
                SELECT COUNT(*) 
                FROM accounts 
                WHERE is_active = TRUE
            ''')
            total_accounts = cursor.fetchone()[0] or 0
            
            # مجموع اتک
            cursor.execute('''
                SELECT COALESCE(SUM(attack), 0) 
                FROM accounts 
                WHERE is_active = TRUE
            ''')
            total_attack = cursor.fetchone()[0] or 0
            
            # مجموع دفاع
            cursor.execute('''
                SELECT COALESCE(SUM(defense), 0) 
                FROM accounts 
                WHERE is_active = TRUE
            ''')
            total_defense = cursor.fetchone()[0] or 0
            
            return {
                'total_users': total_users,
                'total_accounts': total_accounts,
                'total_attack': total_attack,
                'total_defense': total_defense
            }
        except Exception as e:
            logger.error(f"❌ Error getting clan stats: {e}")
            return {'total_users': 0, 'total_accounts': 0, 'total_attack': 0, 'total_defense': 0}
    
    def get_account_count(self, user_id):
        """شمردن تعداد اکانت‌های کاربر"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT COUNT(*) 
                FROM accounts 
                WHERE user_id = %s AND is_active = TRUE
            ''', (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ Error getting account count for user {user_id}: {e}")
            return 0

# ایجاد نمونه دیتابیس
db = Database()
