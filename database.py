#!/usr/bin/env python3
import os
import logging
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        # دریافت DATABASE_URL از محیط
        DATABASE_URL = os.environ.get("DATABASE_URL")
        
        if not DATABASE_URL:
            logger.error("❌ DATABASE_URL not found in environment variables")
            logger.error("💡 Please add DATABASE_URL to Railway Variables")
            raise ValueError("DATABASE_URL is required")
        
        logger.info(f"🔗 Found DATABASE_URL: {DATABASE_URL[:50]}...")
        
        try:
            # Parse the URL
            result = urlparse(DATABASE_URL)
            
            logger.info(f"📡 Connecting to PostgreSQL at {result.hostname}:{result.port}")
            
            # Connect using psycopg2
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            self.conn = psycopg2.connect(
                database=result.path[1:],  # Remove leading '/'
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port,
                cursor_factory=RealDictCursor,
                sslmode="require",
                connect_timeout=30
            )
            
            logger.info("✅ PostgreSQL connection established!")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist"""
        cursor = self.conn.cursor()
        
        try:
            logger.info("🛠️ Creating database tables...")
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create accounts table
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
            
            # Create indexes
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
            # Don't raise, try to continue
    
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
            
            # اضافه کردن تاریخ و ساعت بروزرسانی با تایم‌زون تهران
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
    
    def get_account(self, account_id):
        """Get account details"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM accounts WHERE id = %s', (account_id,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting account {account_id}: {e}")
            return None
    
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
                
                # تعیین آیکون کاراکتر
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
    
    def get_full_rankings(self):
        """Get all rankings (برای همه) - بدون محدودیت"""
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
                    (a.attack + a.defense) as total_power,
                    ROW_NUMBER() OVER (ORDER BY (a.attack + a.defense) DESC) as rank
                FROM accounts a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.is_active = TRUE
                ORDER BY total_power DESC
            ''')
            
            rankings = []
            rows = cursor.fetchall()
            
            for row in rows:
                user_display = f"@{row['username']}" if row['username'] else row['first_name']
                
                # تعیین آیکون کاراکتر
                character_icon = ""
                if row['character'] == 'cat':
                    character_icon = "🐱"
                elif row['character'] == 'dog':
                    character_icon = "🐶"
                elif row['character'] == 'frog':
                    character_icon = "🐸"
                
                rankings.append({
                    'rank': row['rank'],
                    'game_name': row['game_name'],
                    'attack': row['attack'],
                    'defense': row['defense'],
                    'character': row['character'],
                    'character_icon': character_icon,
                    'total_power': row['total_power'],
                    'user_display': user_display,
                    'user_id': row['user_id']
                })
            
            return rankings
        except Exception as e:
            logger.error(f"Error getting full rankings: {e}")
            return []
    
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
    
    def get_update_history(self, days=30):
        """Get accounts update history با زمان تهران"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(f'''
                SELECT 
                    DATE(last_updated AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tehran') as date,
                    COUNT(*) as update_count
                FROM accounts 
                WHERE last_updated >= NOW() - INTERVAL '{days} days'
                    AND is_active = TRUE
                GROUP BY DATE(last_updated AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tehran')
                ORDER BY date DESC
            ''')
            
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting update history: {e}")
            return []
    
    def get_accounts_updated_on_date(self, days_ago=0):
        """Get accounts updated on specific date با زمان تهران"""
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
                    a.last_updated AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tehran' as tehran_time
                FROM accounts a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.is_active = TRUE
                    AND DATE(a.last_updated AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tehran') = 
                        DATE(NOW() AT TIME ZONE 'Asia/Tehran') - INTERVAL '{days_ago} days'
                ORDER BY a.last_updated DESC
            ''')
        
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting accounts for {days_ago} days ago: {e}")
            return []
    
    def get_update_stats(self):
        """Get update statistics for today, yesterday, and 2 days ago با زمان تهران"""
        cursor = self.conn.cursor()
        try:
            stats = {}
            
            # امروز
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND DATE(last_updated AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tehran') = 
                        DATE(NOW() AT TIME ZONE 'Asia/Tehran')
            ''')
            stats['today'] = cursor.fetchone()['count'] or 0
            
            # دیروز
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND DATE(last_updated AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tehran') = 
                        DATE(NOW() AT TIME ZONE 'Asia/Tehran') - INTERVAL '1 day'
            ''')
            stats['yesterday'] = cursor.fetchone()['count'] or 0
            
            # دو روز پیش
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND DATE(last_updated AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tehran') = 
                        DATE(NOW() AT TIME ZONE 'Asia/Tehran') - INTERVAL '2 days'
            ''')
            stats['two_days_ago'] = cursor.fetchone()['count'] or 0
            
            # مجموع بروزرسانی‌های ۷ روز گذشته
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM accounts 
                WHERE is_active = TRUE 
                    AND last_updated >= NOW() - INTERVAL '7 days'
            ''')
            stats['last_7_days'] = cursor.fetchone()['count'] or 0
            
            return stats
        except Exception as e:
            logger.error(f"Error getting update stats: {e}")
            return {'today': 0, 'yesterday': 0, 'two_days_ago': 0, 'last_7_days': 0}

# Create database instance
try:
    db = Database()
    logger.info("🎉 Database initialized successfully!")
except Exception as e:
    logger.error(f"💥 Failed to initialize database: {e}")
    raise
