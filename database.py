#!/usr/bin/env python3
import os
import logging
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ========== اول دکوراتور رو تعریف کن ==========
def with_connection(func):
    """دکوراتور برای auto reconnect"""
    def wrapper(self, *args, **kwargs):
        self.ensure_connection()
        return func(self, *args, **kwargs)
    return wrapper
# =============================================

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self._init_database()
    
    def connect(self):
        """برقراری اتصال به دیتابیس با خودکار fix برای Railway"""
        DATABASE_URL = os.environ.get("DATABASE_URL")
        
        if not DATABASE_URL:
            logger.error("❌ DATABASE_URL not found in environment variables")
            logger.error("💡 Please add DATABASE_URL to Railway Variables")
            raise ValueError("DATABASE_URL is required")
        
        logger.info(f"🔗 Original DATABASE_URL: {DATABASE_URL[:50]}...")
        
        # ========== رفع مشکل Railway Internal DNS ==========
        if 'postgres.railway.internal' in DATABASE_URL:
            DATABASE_URL = DATABASE_URL.replace('postgres.railway.internal', 'viaduct.proxy.rlwy.net')
            logger.info("🔄 Changed internal URL to public URL")
        
        logger.info(f"🔗 Modified DATABASE_URL: {DATABASE_URL[:50]}...")
        
        # تلاش برای اتصال با چندین بار تلاش
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = urlparse(DATABASE_URL)
                
                port = result.port or 5432
                
                logger.info(f"📡 Attempt {retry_count + 1}/{max_retries}: Connecting to {result.hostname}:{port}")
                
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                self.conn = psycopg2.connect(
                    database=result.path[1:],
                    user=result.username,
                    password=result.password,
                    host=result.hostname,
                    port=port,
                    cursor_factory=RealDictCursor,
                    sslmode="require",
                    connect_timeout=60,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5
                )
                
                logger.info("✅ PostgreSQL connection established successfully!")
                return
                
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Attempt {retry_count} failed: {e}")
                
                if retry_count < max_retries:
                    wait_time = retry_count * 2
                    logger.info(f"⏳ Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"💥 All {max_retries} attempts failed")
                    raise
    
    def ensure_connection(self):
        """بررسی و برقراری مجدد اتصال"""
        try:
            if self.conn is None or self.conn.closed:
                logger.warning("⚠️ Connection is closed, reconnecting...")
                self.connect()
                return
            
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            
        except Exception as e:
            logger.error(f"⚠️ Connection error: {e}")
            logger.info("🔄 Attempting to reconnect...")
            
            try:
                if self.conn:
                    try:
                        self.conn.close()
                    except:
                        pass
                    self.conn = None
                
                self.connect()
                logger.info("✅ Reconnected successfully!")
                
            except Exception as reconnect_error:
                logger.error(f"❌ Failed to reconnect: {reconnect_error}")
                raise
    
    def _init_database(self):
        """Create tables if they don't exist"""
        self.ensure_connection()
        cursor = self.conn.cursor()
        
        try:
            logger.info("🛠️ Creating database tables...")
            
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
                    character TEXT DEFAULT 'none',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_accounts_user_id 
                ON accounts(user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_accounts_active 
                ON accounts(is_active)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_accounts_last_updated 
                ON accounts(last_updated)
            ''')
            
            self.conn.commit()
            logger.info("✅ Database tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            self.conn.rollback()
            raise
    
    @with_connection
    def add_user(self, user_id, username, first_name):
        """Add or update user"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name
            ''', (user_id, username, first_name))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False
    
    @with_connection
    def set_admin(self, user_id, is_admin=True):
        """Set user as admin"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                UPDATE users SET is_admin = %s WHERE user_id = %s
            ''', (is_admin, user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting admin for {user_id}: {e}")
            return False
    
    @with_connection
    def is_admin(self, user_id):
        """Check if user is admin"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            return result['is_admin'] if result else False
        except Exception as e:
            logger.error(f"Error checking admin for {user_id}: {e}")
            return False
    
    @with_connection
    def add_account(self, user_id, game_name, attack, defense):
        """Add new game account"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO accounts (user_id, game_name, attack, defense)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (user_id, game_name, attack, defense))
            
            result = cursor.fetchone()
            self.conn.commit()
            return result['id'] if result else None
        except Exception as e:
            logger.error(f"Error adding account for {user_id}: {e}")
            return None
    
    @with_connection
    def get_user_accounts(self, user_id):
        """Get user's accounts"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, game_name, attack, defense, character
                FROM accounts 
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
            ''', (user_id,))
            
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting accounts for {user_id}: {e}")
            return []
    
    @with_connection
    def get_account_count(self, user_id):
        """Count user's accounts"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT COUNT(*) 
                FROM accounts 
                WHERE user_id = %s AND is_active = TRUE
            ''', (user_id,))
            
            result = cursor.fetchone()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Error counting accounts for {user_id}: {e}")
            return 0
    
    @with_connection
    def update_account(self, account_id, attack=None, defense=None, game_name=None, character=None):
        """Update account"""
        cursor = self.conn.cursor()
        try:
            updates = []
            params = []
            
            if attack is not None:
                updates.append("attack = %s")
                params.append(attack)
            
            if defense is not None:
                updates.append("defense = %s")
                params.append(defense)
            
            if game_name is not None:
                updates.append("game_name = %s")
                params.append(game_name)
            
            if character is not None:
                updates.append("character = %s")
                params.append(character)
            
            updates.append("last_updated = CURRENT_TIMESTAMP")
            
            if not updates:
                return False
            
            params.append(account_id)
            query = f"UPDATE accounts SET {', '.join(updates)} WHERE id = %s"
            
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating account {account_id}: {e}")
            return False
    
    @with_connection
    def get_account(self, account_id):
        """Get account details"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM accounts WHERE id = %s', (account_id,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting account {account_id}: {e}")
            return None
    
    @with_connection
    def delete_account(self, account_id):
        """Delete account (soft delete)"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                UPDATE accounts 
                SET is_active = FALSE 
                WHERE id = %s
            ''', (account_id,))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting account {account_id}: {e}")
            return False
    
    @with_connection
    def get_clan_stats(self):
        """Get clan statistics"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM accounts WHERE is_active = TRUE')
            total_users = cursor.fetchone()['count'] or 0
            
            cursor.execute('SELECT COUNT(*) FROM accounts WHERE is_active = TRUE')
            total_accounts = cursor.fetchone()['count'] or 0
            
            cursor.execute('SELECT COALESCE(SUM(attack), 0) FROM accounts WHERE is_active = TRUE')
            total_attack = cursor.fetchone()['coalesce'] or 0
            
            cursor.execute('SELECT COALESCE(SUM(defense), 0) FROM accounts WHERE is_active = TRUE')
            total_defense = cursor.fetchone()['coalesce'] or 0
            
            return {
                'total_users': total_users,
                'total_accounts': total_accounts,
                'total_attack': total_attack,
                'total_defense': total_defense
            }
        except Exception as e:
            logger.error(f"Error getting clan stats: {e}")
            return {'total_users': 0, 'total_accounts': 0, 'total_attack': 0, 'total_defense': 0}
    
    @with_connection
    def get_rankings(self, limit=10):
        """Get rankings"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT 
                    a.game_name,
                    a.attack,
                    a.defense,
                    a.character,
                    u.username,
                    u.first_name,
                    u.user_id
                FROM accounts a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.is_active = TRUE
                ORDER BY (a.attack + a.defense) DESC
                LIMIT %s
            ''', (limit,))
            
            rankings = []
            rows = cursor.fetchall()
            
            for i, row in enumerate(rows, 1):
                user_display = f"@{row['username']}" if row['username'] else row['first_name']
                
                character_icon = ""
                if row['character'] == 'cat':
                    character_icon = "🐱"
                elif row['character'] == 'dog':
                    character_icon = "🐶"
                elif row['character'] == 'frog':
                    character_icon = "🐸"
                
                rankings.append({
                    'rank': i,
                    'game_name': row['game_name'],
                    'attack': row['attack'],
                    'defense': row['defense'],
                    'character': row['character'],
                    'character_icon': character_icon,
                    'user_display': user_display,
                    'user_id': row['user_id']
                })
            
            return rankings
        except Exception as e:
            logger.error(f"Error getting rankings: {e}")
            return []
    
    @with_connection
    def get_full_rankings(self):
        """Get all rankings"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT 
                    a.game_name,
                    a.attack,
                    a.defense,
                    a.character,
                    u.username,
                    u.first_name,
                    u.user_id,
                    (a.attack + a.defense) as total
                FROM accounts a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.is_active = TRUE
                ORDER BY total DESC
            ''')
            
            rankings = []
            rows = cursor.fetchall()
            
            current_rank = 0
            last_total = -1
            rank_skip = 0
            
            for row in rows:
                current_total = row['total']
                
                if current_total != last_total:
                    current_rank += 1 + rank_skip
                    rank_skip = 0
                else:
                    rank_skip += 1
                
                last_total = current_total
                
                user_display = f"@{row['username']}" if row['username'] else row['first_name']
                
                character_icon = ""
                if row['character'] == 'cat':
                    character_icon = "🐱"
                elif row['character'] == 'dog':
                    character_icon = "🐶"
                elif row['character'] == 'frog':
                    character_icon = "🐸"
                
                rankings.append({
                    'rank': current_rank,
                    'game_name': row['game_name'],
                    'attack': row['attack'],
                    'defense': row['defense'],
                    'character': row['character'],
                    'character_icon': character_icon,
                    'user_display': user_display,
                    'user_id': row['user_id'],
                    'total': row['total']
                })
            
            return rankings
        except Exception as e:
            logger.error(f"Error getting full rankings: {e}")
            return []
    
    @with_connection
    def get_all_users(self):
        """Get all users"""
        cursor = self.conn.cursor()
        try:
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
            
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    @with_connection
    def get_update_history(self, days=7):
        cursor = self.conn.cursor()
        try:
            cursor.execute(f'''
                SELECT 
                    DATE(last_updated + INTERVAL '3:30' HOUR TO MINUTE) as date,
                    COUNT(*) as update_count
                FROM accounts 
                WHERE last_updated >= NOW() - INTERVAL '{days} days'
                    AND is_active = TRUE
                GROUP BY DATE(last_updated + INTERVAL '3:30' HOUR TO MINUTE)
                ORDER BY date DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting update history: {e}")
            return []
    
    @with_connection
    def get_accounts_updated_on_date(self, days_ago=0):
        cursor = self.conn.cursor()
        try:
            cursor.execute(f'''
                SELECT 
                    a.game_name,
                    a.attack,
                    a.defense,
                    a.character,
                    u.username,
                    u.first_name,
                    u.user_id,
                    a.last_updated + INTERVAL '3:30' HOUR TO MINUTE as tehran_time
                FROM accounts a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.is_active = TRUE
                    AND DATE(a.last_updated + INTERVAL '3:30' HOUR TO MINUTE) = 
                        CURRENT_DATE - INTERVAL '{days_ago} days'
                ORDER BY a.last_updated DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []
    
    @with_connection
    def get_update_stats(self):
        cursor = self.conn.cursor()
        try:
            stats = {}
            
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND DATE(last_updated + INTERVAL '3:30' HOUR TO MINUTE) = CURRENT_DATE
            ''')
            stats['today'] = cursor.fetchone()['count'] or 0
            
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND DATE(last_updated + INTERVAL '3:30' HOUR TO MINUTE) = CURRENT_DATE - INTERVAL '1 day'
            ''')
            stats['yesterday'] = cursor.fetchone()['count'] or 0
            
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND DATE(last_updated + INTERVAL '3:30' HOUR TO MINUTE) = CURRENT_DATE - INTERVAL '2 days'
            ''')
            stats['two_days_ago'] = cursor.fetchone()['count'] or 0
            
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND last_updated >= NOW() - INTERVAL '7 days'
            ''')
            stats['last_7_days'] = cursor.fetchone()['count'] or 0
            
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND last_updated > created_at
            ''')
            stats['total_updates'] = cursor.fetchone()['count'] or 0
            
            return stats
        except Exception as e:
            logger.error(f"Error getting update stats: {e}")
            return {'today': 0, 'yesterday': 0, 'two_days_ago': 0, 'last_7_days': 0, 'total_updates': 0}


# Create database instance
try:
    logger.info("🚀 Initializing database...")
    db = Database()
    logger.info("🎉 Database initialized successfully!")
except Exception as e:
    logger.error(f"💥 Failed to initialize database: {e}")
    raise
