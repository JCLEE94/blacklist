#!/usr/bin/env python3
"""
Database schema migration script to add missing columns
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2 import sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment"""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://blacklist_user:blacklist_password_change_me@localhost:32543/blacklist"
    )


def get_existing_columns(cursor, table_name):
    """Get list of existing columns in a table"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position
    """, (table_name,))
    return [row[0] for row in cursor.fetchall()]


def migrate_blacklist_entries_table(cursor):
    """Add missing columns to blacklist_entries table"""
    logger.info("Migrating blacklist_entries table...")
    
    existing_columns = get_existing_columns(cursor, 'blacklist_entries')
    logger.info(f"Existing columns: {existing_columns}")
    
    # Define columns that should exist
    required_columns = {
        'first_seen': 'TEXT',
        'last_seen': 'TEXT', 
        'detection_date': 'DATE',
        'collection_date': 'TEXT',
        'detection_months': 'TEXT',
        'country': 'TEXT',
        'reason': 'TEXT',
        'reg_date': 'TEXT',
        'exp_date': 'TEXT',
        'view_count': 'INTEGER DEFAULT 0',
        'uuid': 'TEXT',
        'severity_score': 'REAL DEFAULT 0.0',
        'confidence_level': 'REAL DEFAULT 1.0',
        'tags': 'TEXT',
        'last_verified': 'TIMESTAMP',
        'verification_status': 'TEXT DEFAULT \'unverified\'',
        'expires_at': 'TIMESTAMP',
        'days_until_expiry': 'INTEGER DEFAULT 90',
        'source_details': 'TEXT'
    }
    
    added_columns = []
    
    for column_name, column_def in required_columns.items():
        if column_name not in existing_columns:
            try:
                alter_sql = f"ALTER TABLE blacklist_entries ADD COLUMN {column_name} {column_def}"
                cursor.execute(alter_sql)
                added_columns.append(column_name)
                logger.info(f"Added column: {column_name}")
            except Exception as e:
                logger.error(f"Failed to add column {column_name}: {e}")
    
    return added_columns


def create_missing_indexes(cursor):
    """Create missing indexes"""
    logger.info("Creating missing indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_country ON blacklist_entries(country)",
        "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_source ON blacklist_entries(source)",
        "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_detection_date ON blacklist_entries(detection_date)",
        "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_active ON blacklist_entries(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_expires_at ON blacklist_entries(expires_at)"
    ]
    
    created_indexes = []
    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
            index_name = index_sql.split("CREATE INDEX IF NOT EXISTS ")[1].split(" ON ")[0]
            created_indexes.append(index_name)
            logger.info(f"Created index: {index_name}")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
    
    return created_indexes


def verify_schema(cursor):
    """Verify the schema matches expectations"""
    logger.info("Verifying schema...")
    
    # Test the country column query that was failing
    try:
        cursor.execute("""
            SELECT COUNT(DISTINCT country) 
            FROM blacklist_entries 
            WHERE is_active = true AND country IS NOT NULL AND country != ''
        """)
        result = cursor.fetchone()[0]
        logger.info(f"Country query successful: {result} distinct countries")
        return True
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False


def main():
    """Main migration function"""
    database_url = get_database_url()
    logger.info(f"Connecting to database: {database_url.split('@')[0]}@[HIDDEN]")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        
        logger.info("🚀 Starting database schema migration...")
        
        # Migrate blacklist_entries table
        added_columns = migrate_blacklist_entries_table(cursor)
        
        # Create missing indexes
        created_indexes = create_missing_indexes(cursor)
        
        # Commit changes
        conn.commit()
        logger.info("✅ Migration changes committed")
        
        # Verify schema
        if verify_schema(cursor):
            logger.info("✅ Schema verification passed")
        else:
            logger.error("❌ Schema verification failed")
            return 1
        
        # Summary
        logger.info("🎉 Migration completed successfully!")
        logger.info(f"Added columns: {added_columns}")
        logger.info(f"Created indexes: {created_indexes}")
        
        cursor.close()
        conn.close()
        return 0
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())