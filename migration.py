#!/usr/bin/env python3
import os
import logging
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not found in environment variables")
        logger.error("💡 Please set DATABASE_URL first")
        return False
    
    try:
        result = urlparse(DATABASE_URL)
        
        logger.info(f"🔗 Connecting to PostgreSQL at {result.hostname}:{result.port}")
        
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            sslmode="require",
            connect_timeout=30
        )
        
        cursor = conn.cursor()
        
        logger.info("🔄 Checking current database structure...")
        
        # بررسی وجود فیلدها
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'accounts'
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"📊 Existing columns: {existing_columns}")
        
        # اضافه کردن فیلد character اگر وجود ندارد
        if 'character' not in existing_columns:
            logger.info("➕ Adding 'character' column to accounts table...")
            cursor.execute('''
                ALTER TABLE accounts 
                ADD COLUMN character TEXT DEFAULT 'none'
            ''')
            logger.info("✅ 'character' column added successfully")
        else:
            logger.info("✓ 'character' column already exists")
        
        # اضافه کردن فیلد last_updated اگر وجود ندارد
        if 'last_updated' not in existing_columns:
            logger.info("➕ Adding 'last_updated' column to accounts table...")
            cursor.execute('''
                ALTER TABLE accounts 
                ADD COLUMN last_updated DATE DEFAULT CURRENT_DATE
            ''')
            logger.info("✅ 'last_updated' column added successfully")
        else:
            logger.info("✓ 'last_updated' column already exists")
        
        # ایجاد ایندکس برای last_updated
        logger.info("🔧 Creating index for last_updated...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_accounts_last_updated 
            ON accounts(last_updated)
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("🎉 Database migration completed successfully!")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ PostgreSQL Error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n✨ Migration successful! Your bot should work now.")
    else:
        print("\n⚠️ Migration failed. Please check the logs above.")
