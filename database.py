#!/usr/bin/env python3
import os
import logging
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.use_postgresql = False
        
        # دریافت آدرس دیتابیس
        DATABASE_URL = os.environ.get("DATABASE_URL")
        
        if DATABASE_URL:
            logger.info(f"📦 DATABASE_URL found, attempting PostgreSQL connection...")
            try:
                # استفاده از pg8000 (بدون نیاز به libpq)
                import pg8000.native
                
                # تجزیه آدرس دیتابیس
                result = urlparse(DATABASE_URL)
                
                logger.info(f"🔗 Connecting to: {result.hostname}:{result.port}")
                
                # اتصال به PostgreSQL با pg8000
                self.conn = pg8000.native.Connection(
                    user=result.username,
                    password=result.password,
                    host=result.hostname,
                    port=result.port,
                    database=result.path[1:],
                    ssl_context=True,
                    timeout=10
                )
                
                self.use_postgresql = True
                logger.info("✅ Successfully connected to PostgreSQL using pg8000")
                
            except ImportError as e:
                logger.error(f"❌ pg8000 not installed: {e}")
                self._use_sqlite_fallback()
            except Exception as e:
                logger.error(f"❌ PostgreSQL connection failed: {str(e)[:100]}")
                self._use_sqlite_fallback()
        else:
            logger.warning("⚠️ DATABASE_URL not found, using SQLite")
            self._use_sqlite_fallback()
        
        # مقداردهی اولیه دیتابیس
        self.init_db()
    
    def _use_sqlite_fallback(self):
        """استفاده از SQLite به عنوان fallback"""
        try:
            import sqlite3
            self.conn = sqlite3.connect(':memory:', check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.use_postgresql = False
            logger.info("⚠️ Using in-memory SQLite")
        except Exception as e:
            logger.error(f"❌ SQLite fallback failed: {e}")
            raise
    
    def _execute_pg(self, query, params=None):
        """اجرای کوئری در PostgreSQL"""
        try:
            if params:
                return self.conn.run(query, *params)
            else:
                return self.conn.run(query)
        except Exception as e:
            logger.error(f"❌ Query error: {e}")
            raise
    
    def init_db(self):
        """ساخت جداول دیتابیس"""
        try:
            if self.use_postgresql:
                # ساخت جداول PostgreSQL با pg8000
                
                # جدول users
                self._execute_pg('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        is_admin BOOLEAN DEFAULT FALSE,
                        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # جدول accounts
                self._execute_pg('''
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
                
                logger.info("✅ PostgreSQL tables created")
                
            else:
                # ساخت جداول SQLite
                cursor = self.conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        is_admin INTEGER DEFAULT 0,
                        join_date TEXT
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        game_name TEXT NOT NULL,
                        attack INTEGER DEFAULT 0,
                        defense INTEGER DEFAULT 0,
                        is_active INTEGER DEFAULT 1,
                        created_at TEXT
                    )
                ''')
                
                self.conn.commit()
                logger.info("✅ SQLite tables created")
                
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
    
    def add_user(self, user_id, username, first_name):
        """افزودن کاربر جدید"""
        try:
            if self.use_postgresql:
                self._execute_pg('''
                    INSERT INTO users (user_id, username, first_name)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO NOTHING
                ''', user_id, username, first_name)
            else:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, join_date)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, datetime.now().isoformat()))
                self.conn.commit()
            
            logger.debug(f"✅ User {user_id} added")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding user: {e}")
            return False
    
    def set_admin(self, user_id, is_admin=True):
        """تنظیم کاربر به عنوان ادمین"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('''
                    UPDATE users 
                    SET is_admin = $1 
                    WHERE user_id = $2
                ''', is_admin, user_id)
                return True
            else:
                cursor = self.conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET is_admin = ? 
                    WHERE user_id = ?
                ''', (1 if is_admin else 0, user_id))
                self.conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"❌ Error setting admin: {e}")
            return False
    
    def is_admin(self, user_id):
        """بررسی ادمین بودن کاربر"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('''
                    SELECT is_admin 
                    FROM users 
                    WHERE user_id = $1
                ''', user_id)
                return result[0][0] if result else False
            else:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT is_admin 
                    FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                return row[0] == 1 if row else False
                
        except Exception as e:
            logger.error(f"❌ Error checking admin: {e}")
            return False
    
    def add_account(self, user_id, game_name, attack, defense):
        """افزودن اکانت جدید"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('''
                    INSERT INTO accounts (user_id, game_name, attack, defense)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                ''', user_id, game_name, attack, defense)
                return result[0][0]
            else:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO accounts (user_id, game_name, attack, defense, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, game_name, attack, defense, datetime.now().isoformat()))
                self.conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"❌ Error adding account: {e}")
            return None
    
    def get_user_accounts(self, user_id):
        """دریافت اکانت‌های کاربر"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('''
                    SELECT id, game_name, attack, defense
                    FROM accounts 
                    WHERE user_id = $1 AND is_active = TRUE
                    ORDER BY created_at DESC
                ''', user_id)
                
                accounts = []
                for row in result:
                    accounts.append({
                        'id': row[0],
                        'game_name': row[1],
                        'attack': row[2],
                        'defense': row[3]
                    })
                return accounts
            else:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT id, game_name, attack, defense
                    FROM accounts 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                accounts = []
                for row in cursor.fetchall():
                    accounts.append({
                        'id': row[0],
                        'game_name': row[1],
                        'attack': row[2],
                        'defense': row[3]
                    })
                return accounts
                
        except Exception as e:
            logger.error(f"❌ Error getting accounts: {e}")
            return []
    
    def get_account_count(self, user_id):
        """شمردن تعداد اکانت‌های کاربر"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('''
                    SELECT COUNT(*) 
                    FROM accounts 
                    WHERE user_id = $1 AND is_active = TRUE
                ''', user_id)
                return result[0][0]
            else:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM accounts 
                    WHERE user_id = ? AND is_active = 1
                ''', (user_id,))
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"❌ Error getting account count: {e}")
            return 0
    
    def get_clan_stats(self):
        """آمار کلی کلن"""
        try:
            if self.use_postgresql:
                # تعداد کاربران
                result = self._execute_pg('''
                    SELECT COUNT(DISTINCT user_id) 
                    FROM accounts 
                    WHERE is_active = TRUE
                ''')
                total_users = result[0][0] if result else 0
                
                # تعداد اکانت‌ها
                result = self._execute_pg('''
                    SELECT COUNT(*) 
                    FROM accounts 
                    WHERE is_active = TRUE
                ''')
                total_accounts = result[0][0] if result else 0
                
                # مجموع اتک
                result = self._execute_pg('''
                    SELECT COALESCE(SUM(attack), 0) 
                    FROM accounts 
                    WHERE is_active = TRUE
                ''')
                total_attack = result[0][0] if result else 0
                
                # مجموع دفاع
                result = self._execute_pg('''
                    SELECT COALESCE(SUM(defense), 0) 
                    FROM accounts 
                    WHERE is_active = TRUE
                ''')
                total_defense = result[0][0] if result else 0
                
            else:
                cursor = self.conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) 
                    FROM accounts 
                    WHERE is_active = 1
                ''')
                total_users = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM accounts 
                    WHERE is_active = 1
                ''')
                total_accounts = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    SELECT COALESCE(SUM(attack), 0) 
                    FROM accounts 
                    WHERE is_active = 1
                ''')
                total_attack = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    SELECT COALESCE(SUM(defense), 0) 
                    FROM accounts 
                    WHERE is_active = 1
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

# ایجاد نمونه دیتابیس
db = Database()
