import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        DATABASE_URL = os.environ.get("DATABASE_URL", "")
        
        if DATABASE_URL and "postgres" in DATABASE_URL.lower():
            import psycopg2
            from psycopg2.extras import RealDictCursor
            from urllib.parse import urlparse
            
            result = urlparse(DATABASE_URL)
            self.conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port,
                cursor_factory=RealDictCursor
            )
            logger.info("✅ Connected to PostgreSQL on Railway")
            self.use_postgresql = True
        else:
            import sqlite3
            self.conn = sqlite3.connect('data/clan.db', check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info("✅ Using SQLite (Local)")
            self.use_postgresql = False
        
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        
        if self.use_postgresql:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
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
        else:
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
        logger.info("✅ Database tables initialized")
    
    def add_user(self, user_id, username, first_name):
        cursor = self.conn.cursor()
        try:
            if self.use_postgresql:
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                ''', (user_id, username, first_name))
            else:
                from datetime import datetime
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, join_date)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, datetime.now().isoformat()))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def set_admin(self, user_id, is_admin=True):
        cursor = self.conn.cursor()
        try:
            if self.use_postgresql:
                cursor.execute('UPDATE users SET is_admin = %s WHERE user_id = %s', 
                             (is_admin, user_id))
            else:
                cursor.execute('UPDATE users SET is_admin = ? WHERE user_id = ?', 
                             (1 if is_admin else 0, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting admin: {e}")
            return False
    
    def is_admin(self, user_id):
        cursor = self.conn.cursor()
        try:
            if self.use_postgresql:
                cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (user_id,))
                row = cursor.fetchone()
                return row['is_admin'] if row else False
            else:
                cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                return row[0] == 1 if row else False
        except Exception as e:
            logger.error(f"Error checking admin: {e}")
            return False
    
    def get_clan_stats(self):
        cursor = self.conn.cursor()
        try:
            if self.use_postgresql:
                cursor.execute('SELECT COUNT(DISTINCT user_id) FROM accounts WHERE is_active = TRUE')
                total_users = cursor.fetchone()[0] or 0
                
                cursor.execute('SELECT COUNT(*) FROM accounts WHERE is_active = TRUE')
                total_accounts = cursor.fetchone()[0] or 0
                
                cursor.execute('SELECT COALESCE(SUM(attack), 0) FROM accounts WHERE is_active = TRUE')
                total_attack = cursor.fetchone()[0]
                
                cursor.execute('SELECT COALESCE(SUM(defense), 0) FROM accounts WHERE is_active = TRUE')
                total_defense = cursor.fetchone()[0]
            else:
                cursor.execute('SELECT COUNT(DISTINCT user_id) FROM accounts WHERE is_active = 1')
                total_users = cursor.fetchone()[0] or 0
                
                cursor.execute('SELECT COUNT(*) FROM accounts WHERE is_active = 1')
                total_accounts = cursor.fetchone()[0] or 0
                
                cursor.execute('SELECT COALESCE(SUM(attack), 0) FROM accounts WHERE is_active = 1')
                total_attack = cursor.fetchone()[0] or 0
                
                cursor.execute('SELECT COALESCE(SUM(defense), 0) FROM accounts WHERE is_active = 1')
                total_defense = cursor.fetchone()[0] or 0
            
            return {
                'total_users': total_users,
                'total_accounts': total_accounts,
                'total_attack': total_attack,
                'total_defense': total_defense
            }
        except Exception as e:
            logger.error(f"Error getting clan stats: {e}")
            return {'total_users': 0, 'total_accounts': 0, 'total_attack': 0, 'total_defense': 0}
    
    def get_account_count(self, user_id):
        cursor = self.conn.cursor()
        try:
            if self.use_postgresql:
                cursor.execute('SELECT COUNT(*) FROM accounts WHERE user_id = %s AND is_active = TRUE', (user_id,))
            else:
                cursor.execute('SELECT COUNT(*) FROM accounts WHERE user_id = ? AND is_active = 1', (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting account count: {e}")
            return 0

db = Database()
