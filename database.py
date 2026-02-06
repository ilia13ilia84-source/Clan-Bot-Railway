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
        
        if DATABASE_URL and "postgres" in DATABASE_URL.lower():
            try:
                # استفاده از pg8000 (بدون نیاز به libpq)
                import pg8000.native
                
                result = urlparse(DATABASE_URL)
                
                logger.info(f"🔗 Connecting to PostgreSQL: {result.hostname}")
                
                # اتصال به PostgreSQL
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
                logger.info("✅ Connected to PostgreSQL using pg8000")
                
            except Exception as e:
                logger.error(f"❌ PostgreSQL connection failed: {str(e)[:100]}")
                self._use_sqlite_fallback()
        else:
            logger.warning("⚠️ DATABASE_URL not found, using SQLite")
            self._use_sqlite_fallback()
        
        self.init_db()
    
    def _use_sqlite_fallback(self):
        """استفاده از SQLite"""
        try:
            import sqlite3
            self.conn = sqlite3.connect(':memory:', check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.use_postgresql = False
            logger.info("✅ Using in-memory SQLite")
        except Exception as e:
            logger.error(f"❌ SQLite failed: {e}")
            raise
    
    def _execute_pg(self, query, *params):
        """اجرای کوئری در PostgreSQL"""
        try:
            return self.conn.run(query, *params)
        except Exception as e:
            logger.error(f"❌ PostgreSQL query error: {e}")
            raise
    
    def _execute_sqlite(self, query, params=None):
        """اجرای کوئری در SQLite"""
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor
        except Exception as e:
            logger.error(f"❌ SQLite query error: {e}")
            raise
    
    def init_db(self):
        """ساخت جداول"""
        try:
            if self.use_postgresql:
                # PostgreSQL
                self._execute_pg('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        is_admin BOOLEAN DEFAULT FALSE,
                        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
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
                # SQLite
                cursor = self._execute_sqlite('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        is_admin INTEGER DEFAULT 0,
                        join_date TEXT
                    )
                ''')
                
                cursor = self._execute_sqlite('''
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
        """افزودن کاربر"""
        try:
            if self.use_postgresql:
                self._execute_pg('''
                    INSERT INTO users (user_id, username, first_name)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO NOTHING
                ''', user_id, username, first_name)
                return True
            else:
                cursor = self._execute_sqlite('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, join_date)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, datetime.now().isoformat()))
                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error adding user: {e}")
            return False
    
    def set_admin(self, user_id, is_admin=True):
        """تنظیم ادمین"""
        try:
            if self.use_postgresql:
                self._execute_pg('''
                    UPDATE users SET is_admin = $1 WHERE user_id = $2
                ''', is_admin, user_id)
                return True
            else:
                cursor = self._execute_sqlite(
                    'UPDATE users SET is_admin = ? WHERE user_id = ?',
                    (1 if is_admin else 0, user_id)
                )
                self.conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Error setting admin: {e}")
            return False
    
    def is_admin(self, user_id):
        """بررسی ادمین"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('SELECT is_admin FROM users WHERE user_id = $1', user_id)
                return result[0][0] if result else False
            else:
                cursor = self._execute_sqlite('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                return row[0] == 1 if row else False
        except Exception as e:
            logger.error(f"❌ Error checking admin: {e}")
            return False
    
    def add_account(self, user_id, game_name, attack, defense):
        """افزودن اکانت"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('''
                    INSERT INTO accounts (user_id, game_name, attack, defense)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                ''', user_id, game_name, attack, defense)
                return result[0][0] if result else None
            else:
                cursor = self._execute_sqlite(
                    'INSERT INTO accounts (user_id, game_name, attack, defense, created_at) VALUES (?, ?, ?, ?, ?)',
                    (user_id, game_name, attack, defense, datetime.now().isoformat())
                )
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
                cursor = self._execute_sqlite(
                    'SELECT id, game_name, attack, defense FROM accounts WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC',
                    (user_id,)
                )
                
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
            logger.error(f"❌ Error getting user accounts: {e}")
            return []
    
    def get_account_count(self, user_id):
        """شمردن اکانت‌ها"""
        try:
            if self.use_postgresql:
                result = self._execute_pg(
                    'SELECT COUNT(*) FROM accounts WHERE user_id = $1 AND is_active = TRUE',
                    user_id
                )
                return result[0][0] if result else 0
            else:
                cursor = self._execute_sqlite(
                    'SELECT COUNT(*) FROM accounts WHERE user_id = ? AND is_active = 1',
                    (user_id,)
                )
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ Error getting account count: {e}")
            return 0
    
    def update_account(self, account_id, attack=None, defense=None, game_name=None):
        """به‌روزرسانی اکانت"""
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
                # برای pg8000 باید پارامترها جداگانه باشند
                self._execute_pg(f"UPDATE accounts SET {', '.join(updates)} WHERE id = $1", *params)
                return True
            else:
                query = f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?"
                cursor = self._execute_sqlite(query, tuple(params))
                self.conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"❌ Error updating account: {e}")
            return False
    
    def get_account(self, account_id):
        """دریافت اطلاعات اکانت"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('SELECT * FROM accounts WHERE id = $1', account_id)
                if result:
                    row = result[0]
                    return {
                        'id': row[0],
                        'user_id': row[1],
                        'game_name': row[2],
                        'attack': row[3],
                        'defense': row[4],
                        'is_active': row[5],
                        'created_at': row[6]
                    }
                return None
            else:
                cursor = self._execute_sqlite('SELECT * FROM accounts WHERE id = ?', (account_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"❌ Error getting account: {e}")
            return None
    
    def delete_account(self, account_id):
        """حذف اکانت"""
        try:
            if self.use_postgresql:
                self._execute_pg('UPDATE accounts SET is_active = FALSE WHERE id = $1', account_id)
                return True
            else:
                cursor = self._execute_sqlite(
                    'UPDATE accounts SET is_active = 0 WHERE id = ?',
                    (account_id,)
                )
                self.conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Error deleting account: {e}")
            return False
    
    def get_clan_stats(self):
        """آمار کلن"""
        try:
            if self.use_postgresql:
                # تعداد کاربران
                result = self._execute_pg('SELECT COUNT(DISTINCT user_id) FROM accounts WHERE is_active = TRUE')
                total_users = result[0][0] if result else 0
                
                # تعداد اکانت‌ها
                result = self._execute_pg('SELECT COUNT(*) FROM accounts WHERE is_active = TRUE')
                total_accounts = result[0][0] if result else 0
                
                # مجموع اتک
                result = self._execute_pg('SELECT COALESCE(SUM(attack), 0) FROM accounts WHERE is_active = TRUE')
                total_attack = result[0][0] if result else 0
                
                # مجموع دفاع
                result = self._execute_pg('SELECT COALESCE(SUM(defense), 0) FROM accounts WHERE is_active = TRUE')
                total_defense = result[0][0] if result else 0
                
            else:
                cursor = self._execute_sqlite('SELECT COUNT(DISTINCT user_id) FROM accounts WHERE is_active = 1')
                total_users = cursor.fetchone()[0] or 0
                
                cursor = self._execute_sqlite('SELECT COUNT(*) FROM accounts WHERE is_active = 1')
                total_accounts = cursor.fetchone()[0] or 0
                
                cursor = self._execute_sqlite('SELECT COALESCE(SUM(attack), 0) FROM accounts WHERE is_active = 1')
                total_attack = cursor.fetchone()[0] or 0
                
                cursor = self._execute_sqlite('SELECT COALESCE(SUM(defense), 0) FROM accounts WHERE is_active = 1')
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
        """رتبه‌بندی"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('''
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
                    LIMIT $1
                ''', limit)
                
                rankings = []
                for i, row in enumerate(result, 1):
                    rankings.append({
                        'rank': i,
                        'game_name': row[0],
                        'attack': row[1],
                        'defense': row[2],
                        'user_display': f"@{row[3]}" if row[3] else row[4],
                        'user_id': row[5]
                    })
                return rankings
            else:
                cursor = self._execute_sqlite('''
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
                
                rankings = []
                rows = cursor.fetchall()
                for i, row in enumerate(rows, 1):
                    rankings.append({
                        'rank': i,
                        'game_name': row[0],
                        'attack': row[1],
                        'defense': row[2],
                        'user_display': f"@{row[3]}" if row[3] else row[4],
                        'user_id': row[5]
                    })
                return rankings
        except Exception as e:
            logger.error(f"❌ Error getting rankings: {e}")
            return []
    
    def get_all_users(self):
        """همه کاربران"""
        try:
            if self.use_postgresql:
                result = self._execute_pg('''
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
                
                users = []
                for row in result:
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'is_admin': row[3],
                        'account_count': row[4]
                    })
                return users
            else:
                cursor = self._execute_sqlite('''
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
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'is_admin': row[3],
                        'account_count': row[4]
                    })
                return users
        except Exception as e:
            logger.error(f"❌ Error getting all users: {e}")
            return []
    
    def get_all_user_accounts(self, user_id):
        """همه اکانت‌های کاربر (برای ادمین)"""
        return self.get_user_accounts(user_id)
    
    def delete_user_accounts(self, user_id):
        """حذف همه اکانت‌های کاربر"""
        try:
            if self.use_postgresql:
                self._execute_pg('UPDATE accounts SET is_active = FALSE WHERE user_id = $1', user_id)
                return True
            else:
                cursor = self._execute_sqlite(
                    'UPDATE accounts SET is_active = 0 WHERE user_id = ?',
                    (user_id,)
                )
                self.conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Error deleting user accounts: {e}")
            return False
    
    def delete_single_account_admin(self, account_id):
        """حذف تک اکانت توسط ادمین"""
        return self.delete_account(account_id)

# ایجاد نمونه دیتابیس
db = Database()
