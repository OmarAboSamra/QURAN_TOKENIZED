"""Celery tasks for database backup and maintenance."""
import gzip
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

from celery.utils.log import get_task_logger

from backend.cache import get_cache
from backend.config import get_settings
from backend.logging_config import get_logger
from backend.worker import celery_app

logger = get_task_logger(__name__)
structured_logger = get_logger(__name__)
settings = get_settings()


@celery_app.task(name="backend.tasks.backup_tasks.backup_database")
def backup_database() -> Dict:
    """
    Create nightly database backup with compression.
    
    Returns:
        Dictionary with backup results
    """
    start_time = datetime.now()
    
    structured_logger.info("database_backup_started")
    
    try:
        # Create backups directory
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"quran_db_{timestamp}.sql"
        compressed_file = backup_dir / f"quran_db_{timestamp}.sql.gz"
        
        if settings.is_postgresql:
            # PostgreSQL backup using pg_dump
            db_url = settings.database_url
            
            # Extract connection details (simplified - use proper parsing in production)
            cmd = [
                "pg_dump",
                "--dbname", db_url,
                "--file", str(backup_file),
                "--format=plain",
                "--verbose",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes max
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
                
        elif settings.is_sqlite:
            # SQLite backup using .dump
            db_path = settings.database_url.replace("sqlite:///", "")
            
            cmd = [
                "sqlite3",
                db_path,
                ".dump",
            ]
            
            with open(backup_file, "w", encoding="utf-8") as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=1800,
                )
            
            if result.returncode != 0:
                raise Exception(f"sqlite3 dump failed: {result.stderr}")
        
        # Compress backup
        with open(backup_file, "rb") as f_in:
            with gzip.open(compressed_file, "wb", compresslevel=9) as f_out:
                f_out.writelines(f_in)
        
        # Remove uncompressed file
        backup_file.unlink()
        
        # Get file sizes
        compressed_size = compressed_file.stat().st_size
        compressed_size_mb = round(compressed_size / (1024 * 1024), 2)
        
        # Clean up old backups (keep last 7 days)
        cleanup_old_backups(backup_dir, days=7)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        structured_logger.info(
            "database_backup_completed",
            backup_file=str(compressed_file),
            size_mb=compressed_size_mb,
            duration_seconds=round(duration, 2),
        )
        
        return {
            "status": "success",
            "backup_file": str(compressed_file),
            "size_mb": compressed_size_mb,
            "duration_seconds": round(duration, 2),
        }
        
    except Exception as e:
        structured_logger.error(
            "database_backup_failed",
            error=str(e),
            exc_info=True,
        )
        raise


def cleanup_old_backups(backup_dir: Path, days: int = 7) -> int:
    """
    Remove backups older than specified days.
    
    Args:
        backup_dir: Directory containing backups
        days: Number of days to keep
        
    Returns:
        Number of files deleted
    """
    cutoff = datetime.now().timestamp() - (days * 86400)
    deleted = 0
    
    for backup_file in backup_dir.glob("quran_db_*.sql.gz"):
        if backup_file.stat().st_mtime < cutoff:
            backup_file.unlink()
            deleted += 1
            structured_logger.info(
                "old_backup_deleted",
                file=str(backup_file),
            )
    
    return deleted


@celery_app.task(name="backend.tasks.backup_tasks.cleanup_old_cache")
def cleanup_old_cache() -> Dict:
    """
    Clean up expired cache entries.
    
    Returns:
        Dictionary with cleanup results
    """
    structured_logger.info("cache_cleanup_started")
    
    try:
        cache = get_cache()
        
        # This is handled automatically by Redis TTL
        # But we can force cleanup of specific patterns if needed
        
        structured_logger.info("cache_cleanup_completed")
        
        return {
            "status": "success",
            "message": "Cache cleanup completed (TTL-based)",
        }
        
    except Exception as e:
        structured_logger.error(
            "cache_cleanup_failed",
            error=str(e),
            exc_info=True,
        )
        raise


@celery_app.task(name="backend.tasks.backup_tasks.export_sura_csv")
def export_sura_csv(sura: int, page: int = None) -> Dict:
    """
    Export sura tokens to CSV file.
    
    Args:
        sura: Surah number
        page: Optional page number for chunked export
        
    Returns:
        Dictionary with export results
    """
    structured_logger.info(
        "csv_export_started",
        sura=sura,
        page=page,
    )
    
    try:
        from backend.db import get_sync_session_maker
        from backend.repositories.token_repository import TokenRepository
        import csv
        
        token_repo = TokenRepository()
        session_maker = get_sync_session_maker()
        session = session_maker()
        
        # Get tokens
        if page:
            skip = (page - 1) * 1000
            tokens = token_repo.get_filtered(
                session,
                sura=sura,
                skip=skip,
                limit=1000,
            )
            filename = f"data/quran_tokens_sura{sura}_p{page}.csv"
        else:
            tokens = token_repo.get_filtered(session, sura=sura, skip=0, limit=10000)
            filename = f"data/quran_tokens_sura{sura}.csv"
        
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        
        # Write CSV
        with open(filename, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "sura", "aya", "position",
                "text_ar", "normalized", "root", "status"
            ])
            
            for token in tokens:
                writer.writerow([
                    token.id,
                    token.sura,
                    token.aya,
                    token.position,
                    token.text_ar,
                    token.normalized,
                    token.root or "",
                    token.status,
                ])
        
        structured_logger.info(
            "csv_export_completed",
            sura=sura,
            page=page,
            filename=filename,
            tokens_count=len(tokens),
        )
        
        return {
            "status": "success",
            "sura": sura,
            "page": page,
            "filename": filename,
            "tokens_count": len(tokens),
        }
        
    except Exception as e:
        structured_logger.error(
            "csv_export_failed",
            sura=sura,
            page=page,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        session.close()
