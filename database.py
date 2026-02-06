#!/usr/bin/env python3
import os
import logging
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.use_postgresql = False
        
        # دریافت آدرس دیتابیس از Railway
        DATABASE_URL = os.environ.get("DATABASE_URL")
        
        if DATABASE_URL:
            logger.info(f"📦 DATABASE_URL found: {DATABASE_URL[:30]}...")
            try:
                # استفاده از psycopg2-binary (نیاز به libpq ندارد)
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                # تجزیه آدرس دیتابیس
                result = urlparse(DATABASE_URL)
                
                logger.info(f"🔗 Connecting to PostgreSQL: {result.hostname}")
                
                # اتصال به PostgreSQL
                self.conn = psycopg2.connect(
                    database=result.path[1:],
                    user=result.username,
                    password=result.password,
                    host=result.hostname,
                    port=result.port,
                    cursor_factory=RealDictCursor,
                    sslmode="require",
                    connect_timeout=10
                )
                
                self.use_postgresql = True
                logger.info("✅ Successfully connected to PostgreSQL on Railway")
                
            except ImportError as e:
                logger.error(f"❌ psycopg2 not installed. Error: {e}")
                logger.info("💡 Please add 'psycopg2-binary' to requirements.txt")
                self._use_sqlite_fallback()
            except Exception as e:
                logger.error(f"❌ PostgreSQL connection failed: {e}")
                self._use_sqlite_fallback()
        else:
            logger.warning("⚠️ DATABASE_URL not found, using SQLite fallback")
            self._use_sqlite_fallback()
        
        # مقداردهی اولیه دیتابیس
        self.init_db()
    
    def _use_sqlite_fallback(self):
        """استفاده از SQLite در حافظه به عنوان fallback"""
        try:
            import sqlite3
            self.conn = sqlite3.connect(':memory:', check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.use_postgresql = False
            logger.info("⚠️ Using in-memory SQLite (temporary)")
        except Exception as e:
            logger.error(f"❌ SQLite fallback also failed: {e}")
            raise
    
    def init_db(self):
        """ساخت جداول دیتابیس"""
        try:
            if self.use_postgresql:
                # ساخت جداول PostgreSQL
                cursor = self.conn.cursor()
                
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
                logger.info("✅ PostgreSQL tables created successfully")
                
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
                
                logger.info("✅ SQLite tables created successfully")
                
        except Exception as e:
            logger.error(f"❌ Error creating database tables: {e}")
            if self.use_postgresql:
                self.conn.rollback()
            raise
    
    def add_user(self, user_id, username, first_name):
        """افزودن کاربر جدید"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                ''', (user_id, username, first_name))
            else:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, join_date)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, datetime.now().isoformat()))
            
            self.conn.commit()
            logger.debug(f"✅ User {user_id} added/updated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding user {user_id}: {e}")
            if self.use_postgresql:
                self.conn.rollback()
            return False
    
    def set_admin(self, user_id, is_admin=True):
        """تنظیم کاربر به عنوان ادمین"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    UPDATE users 
                    SET is_admin = %s 
                    WHERE user_id = %s
                ''', (is_admin, user_id))
            else:
                cursor.execute('''
                    UPDATE users 
                    SET is_admin = ? 
                    WHERE user_id = ?
                ''', (1 if is_admin else 0, user_id))
            
            self.conn.commit()
            logger.debug(f"✅ User {user_id} admin status set to {is_admin}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting admin for user {user_id}: {e}")
            if self.use_postgresql:
                self.conn.rollback()
            return False
    
    def is_admin(self, user_id):
        """بررسی ادمین بودن کاربر"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    SELECT is_admin 
                    FROM users 
                    WHERE user_id = %s
                ''', (user_id,))
                row = cursor.fetchone()
                return row['is_admin'] if row else False
            else:
                cursor.execute('''
                    SELECT is_admin 
                    FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                return row[0] == 1 if row else False
                
        except Exception as e:
            logger.error(f"❌ Error checking admin for user {user_id}: {e}")
            return False
    
    def add_account(self, user_id, game_name, attack, defense):
        """افزودن اکانت جدید"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    INSERT INTO accounts (user_id, game_name, attack, defense)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                ''', (user_id, game_name, attack, defense))
                account_id = cursor.fetchone()['id']
            else:
                cursor.execute('''
                    INSERT INTO accounts (user_id, game_name, attack, defense, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, game_name, attack, defense, datetime.now().isoformat()))
                account_id = cursor.lastrowid
            
            self.conn.commit()
            logger.debug(f"✅ Account added for user {user_id}: {game_name}")
            return account_id
            
        except Exception as e:
            logger.error(f"❌ Error adding account for user {user_id}: {e}")
            if self.use_postgresql:
                self.conn.rollback()
            return None
    
    def get_user_accounts(self, user_id):
        """دریافت اکانت‌های کاربر"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    SELECT id, game_name, attack, defense
                    FROM accounts 
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                ''', (user_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                cursor.execute('''
                    SELECT id, game_name, attack, defense
                    FROM accounts 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Error getting accounts for user {user_id}: {e}")
            return []
    
    def get_account_count(self, user_id):
        """شمردن تعداد اکانت‌های کاربر"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM accounts 
                    WHERE user_id = %s AND is_active = TRUE
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM accounts 
                    WHERE user_id = ? AND is_active = 1
                ''', (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"❌ Error getting account count for user {user_id}: {e}")
            return 0
    
    def update_account(self, account_id, attack=None, defense=None, game_name=None):
        """به‌روزرسانی اطلاعات اکانت"""
        try:
            updates = []
            params = []
            
            if attack is not None:
                updates.append("attack = %s" if self.use_postgresql else "attack = ?")
                params.append(attack)
            
            if defense is not None:
                updates.append("defense = %s" if self.use_postgresql else "defense = ?")
                params.append(defense)
            
            if game_name is not None:
                updates.append("game_name = %s" if self.use_postgresql else "game_name = ?")
                params.append(game_name)
            
            if not updates:
                return False
            
            params.append(account_id)
            
            if self.use_postgresql:
                query = f"UPDATE accounts SET {', '.join(updates)} WHERE id = %s"
            else:
                query = f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?"
            
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"❌ Error updating account {account_id}: {e}")
            if self.use_postgresql:
                self.conn.rollback()
            return False
    
    def get_account(self, account_id):
        """دریافت اطلاعات یک اکانت"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    SELECT * FROM accounts WHERE id = %s
                ''', (account_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
            else:
                cursor.execute('''
                    SELECT * FROM accounts WHERE id = ?
                ''', (account_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"❌ Error getting account {account_id}: {e}")
            return None
    
    def delete_account(self, account_id):
        """حذف نرم اکانت"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    UPDATE accounts 
                    SET is_active = FALSE 
                    WHERE id = %s
                ''', (account_id,))
            else:
                cursor.execute('''
                    UPDATE accounts 
                    SET is_active = 0 
                    WHERE id = ?
                ''', (account_id,))
            
            self.conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"❌ Error deleting account {account_id}: {e}")
            if self.use_postgresql:
                self.conn.rollback()
            return False
    
    def get_clan_stats(self):
        """آمار کلی کلن"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) 
                    FROM accounts 
                    WHERE is_active = TRUE
                ''')
                total_users = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM accounts 
                    WHERE is_active = TRUE
                ''')
                total_accounts = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    SELECT COALESCE(SUM(attack), 0) 
                    FROM accounts 
                    WHERE is_active = TRUE
                ''')
                total_attack = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    SELECT COALESCE(SUM(defense), 0) 
                    FROM accounts 
                    WHERE is_active = TRUE
                ''')
                total_defense = cursor.fetchone()[0] or 0
                
            else:
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
    
    def get_rankings(self, limit=10):
        """دریافت رتبه‌بندی کاربران"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    SELECT 
                        a.game_name,
                        a.attack,
                        a.defense,
                        u.username,
                        u.first_name,
                        u.user_id
                    FROM accounts a
                    JOIN users u ON a.user_id = u.user_id
                    WHERE a.is_active = TRUE
                    ORDER BY (a.attack + a.defense) DESC
                    LIMIT %s
                ''', (limit,))
                rows = cursor.fetchall()
            else:
                cursor.execute('''
                    SELECT 
                        a.game_name,
                        a.attack,
                        a.defense,
                        u.username,
                        u.first_name,
                        u.user_id
                    FROM accounts a
                    JOIN users u ON a.user_id = u.user_id
                    WHERE a.is_active = 1
                    ORDER BY (a.attack + a.defense) DESC
                    LIMIT ?
                ''', (limit,))
                rows = cursor.fetchall()
            
            rankings = []
            for i, row in enumerate(rows, 1):
                if self.use_postgresql:
                    rankings.append({
                        'rank': i,
                        'game_name': row['game_name'],
                        'attack': row['attack'],
                        'defense': row['defense'],
                        'user_display': f"@{row['username']}" if row['username'] else row['first_name'],
                        'user_id': row['user_id']
                    })
                else:
                    rankings.append({
                        'rank': i,
                        'game_name': row['game_name'],
                        'attack': row['attack'],
                        'defense': row['defense'],
                        'user_display': f"@{row['username']}" if row['username'] else row['first_name'],
                        'user_id': row['user_id']
                    })
            
            return rankings
            
        except Exception as e:
            logger.error(f"❌ Error getting rankings: {e}")
            return []
    
    def get_all_users(self):
        """دریافت همه کاربران"""
        try:
            cursor = self.conn.cursor()
            
            if self.use_postgresql:
                cursor.execute('''
                    SELECT 
                        u.user_id,
                        u.username,
                        u.first_name,
                        u.is_admin,
                        COUNT(a.id) as account_count
                    FROM users u
                    LEFT JOIN accounts a ON u.user_id = a.user_id AND a.is_active = TRUE
                    GROUP BY u.user_id, u.username, u.first_name, u.is_admin
                    ORDER BY u.user_id
                ''')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                cursor.execute('''
                    SELECT 
                        u.user_id,
                        u.username,
                        u.first_name,
                        u.is_admin,
                        COUNT(a.id) as account_count
                    FROM users u
                    LEFT JOIN accounts a ON u.user_id = a.user_id AND a.is_active = 1
                    GROUP BY u.user_id
                    ORDER BY u.user_id
                ''')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Error getting all users: {e}")
            return []

# ایجاد نمونه دیتابیس
db = Database()
