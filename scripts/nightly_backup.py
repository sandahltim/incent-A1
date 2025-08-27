#!/usr/bin/env python3
"""
Nightly Database Backup Script for Broadway Tent Incentive System
Creates timestamped backups and maintains retention policy
"""

import os
import sys
import sqlite3
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
import glob

# Add the parent directory to Python path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

def setup_logging():
    """Setup logging for backup operations"""
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'backup.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def create_backup(db_path, backup_dir, logger):
    """Create a timestamped backup of the database"""
    try:
        # Ensure backup directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"incentive.db.bak-{timestamp}"
        backup_path = backup_dir / backup_filename
        
        # Check if source database exists
        if not db_path.exists():
            logger.error(f"Source database not found: {db_path}")
            return False
        
        # Create backup using SQLite backup API for consistency
        logger.info(f"Starting backup: {db_path} -> {backup_path}")
        
        # Connect to source database
        source_conn = sqlite3.connect(str(db_path))
        
        # Create backup database connection
        backup_conn = sqlite3.connect(str(backup_path))
        
        # Perform backup
        source_conn.backup(backup_conn)
        
        # Close connections
        backup_conn.close()
        source_conn.close()
        
        # Verify backup file was created and has content
        if backup_path.exists() and backup_path.stat().st_size > 0:
            logger.info(f"Backup completed successfully: {backup_filename}")
            logger.info(f"Backup size: {backup_path.stat().st_size} bytes")
            return True
        else:
            logger.error(f"Backup file is empty or not created: {backup_path}")
            return False
            
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False

def cleanup_old_backups(backup_dir, retention_days, logger):
    """Remove backups older than retention_days"""
    try:
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # Find all backup files
        backup_pattern = backup_dir / "incentive.db.bak-*"
        backup_files = glob.glob(str(backup_pattern))
        
        removed_count = 0
        for backup_file in backup_files:
            backup_path = Path(backup_file)
            
            # Extract timestamp from filename
            try:
                # Expected format: incentive.db.bak-YYYYMMDD_HHMMSS
                filename = backup_path.name
                timestamp_str = filename.replace('incentive.db.bak-', '')
                backup_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                
                if backup_date < cutoff_date:
                    backup_path.unlink()
                    logger.info(f"Removed old backup: {filename}")
                    removed_count += 1
                    
            except ValueError:
                # Skip files that don't match expected format
                logger.warning(f"Skipping file with unexpected format: {filename}")
                continue
        
        if removed_count > 0:
            logger.info(f"Cleanup completed: removed {removed_count} old backup(s)")
        else:
            logger.info("No old backups to remove")
            
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")

def main():
    """Main backup routine"""
    logger = setup_logging()
    logger.info("=== Starting nightly backup routine ===")
    
    try:
        # Configuration
        db_path = Path(Config.INCENTIVE_DB_FILE)
        backup_dir = db_path.parent / 'backups'
        retention_days = 7  # Keep 7 days of backups
        
        logger.info(f"Database path: {db_path}")
        logger.info(f"Backup directory: {backup_dir}")
        logger.info(f"Retention policy: {retention_days} days")
        
        # Create backup
        backup_success = create_backup(db_path, backup_dir, logger)
        
        if backup_success:
            # Cleanup old backups
            cleanup_old_backups(backup_dir, retention_days, logger)
            logger.info("=== Backup routine completed successfully ===")
            sys.exit(0)
        else:
            logger.error("=== Backup routine failed ===")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Backup routine failed with exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()