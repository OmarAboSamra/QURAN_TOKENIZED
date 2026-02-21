"""
Celery tasks for Qur'an tokenization.

Provides background tasks that tokenize entire surahs, with support
for parallel chunking across multiple Celery workers.

Key tasks:
    tokenize_sura          – Tokenize one surah sequentially
    tokenize_sura_chunk    – Tokenize a range of verses (worker subtask)
    tokenize_sura_parallel – Split surah into chunks, fan out to workers
    combine_tokenization   – Callback that merges chunk results
"""
import time
from typing import Dict, List

from celery import chord, group
from celery.utils.log import get_task_logger

from backend.db import get_sync_session_maker
from backend.logging_config import get_logger
from backend.models import Token
from backend.services.tokenizer_service import TokenizerService
from backend.worker import celery_app

logger = get_task_logger(__name__)
structured_logger = get_logger(__name__)


@celery_app.task(bind=True, name="backend.tasks.tokenization_tasks.tokenize_sura")
def tokenize_sura(
    self,
    sura: int,
    correlation_id: str = None,
) -> Dict:
    """
    Tokenize a complete sura and store in database.
    
    Args:
        sura: Surah number (1-114)
        correlation_id: Optional tracking ID
        
    Returns:
        Dictionary with tokenization results
    """
    start_time = time.time()
    
    structured_logger.info(
        "tokenization_started",
        sura=sura,
        correlation_id=correlation_id,
        task_id=self.request.id,
    )
    
    try:
        # Update task state (only if running as Celery task)
        if self.request.id:
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "reading_text",
                    "sura": sura,
                    "progress": 0,
                },
            )
        
        # Initialize tokenizer
        tokenizer = TokenizerService()
        session_maker = get_sync_session_maker()
        session = session_maker()
        
        # Read Qur'an text for this sura
        # For now, we'll use a placeholder - in production, read from file
        if self.request.id:
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "tokenizing",
                    "sura": sura,
                    "progress": 20,
                },
            )
        
        # Tokenize (this will be implemented to read specific sura)
        tokens_data = tokenizer._tokenize_sura_text(sura, session)
        
        if self.request.id:
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "saving_to_db",
                    "sura": sura,
                    "progress": 80,
                    "tokens_count": len(tokens_data),
                },
            )
        
        # Commit transaction
        session.commit()
        
        duration = time.time() - start_time
        
        structured_logger.info(
            "tokenization_completed",
            sura=sura,
            tokens_count=len(tokens_data),
            duration_seconds=round(duration, 2),
            correlation_id=correlation_id,
            task_id=self.request.id,
        )
        
        return {
            "status": "success",
            "sura": sura,
            "tokens_count": len(tokens_data),
            "duration_seconds": round(duration, 2),
            "correlation_id": correlation_id,
        }
        
    except Exception as e:
        structured_logger.error(
            "tokenization_failed",
            sura=sura,
            error=str(e),
            correlation_id=correlation_id,
            task_id=self.request.id,
            exc_info=True,
        )
        raise
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="backend.tasks.tokenization_tasks.tokenize_sura_chunk",
)
def tokenize_sura_chunk(
    self,
    sura: int,
    start_aya: int,
    end_aya: int,
    correlation_id: str = None,
) -> Dict:
    """
    Tokenize a chunk of verses within a sura.
    
    Args:
        sura: Surah number
        start_aya: Starting ayah (inclusive)
        end_aya: Ending ayah (inclusive)
        correlation_id: Optional tracking ID
        
    Returns:
        Dictionary with chunk results
    """
    structured_logger.info(
        "chunk_tokenization_started",
        sura=sura,
        start_aya=start_aya,
        end_aya=end_aya,
        correlation_id=correlation_id,
    )
    
    try:
        from pathlib import Path
        from backend.config import get_settings
        from backend.models import Token, TokenStatus
        
        settings = get_settings()
        tokenizer = TokenizerService()
        session_maker = get_sync_session_maker()
        session = session_maker()
        
        # Read Quran text file
        quran_text_path = Path(settings.quran_data_path)
        if not quran_text_path.exists():
            raise FileNotFoundError(f"Quran text file not found: {quran_text_path}")
        
        tokens_count = 0
        with open(quran_text_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Parse line: sura|aya|text
                if "|" in line:
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        verse_sura = int(parts[0].strip())
                        verse_aya = int(parts[1].strip())
                        text = parts[2].strip()
                        
                        # Check if this verse is in our chunk
                        if verse_sura == sura and start_aya <= verse_aya <= end_aya:
                            # Check if verse already tokenized (skip if exists)
                            existing = session.query(Token).filter(
                                Token.sura == verse_sura,
                                Token.aya == verse_aya
                            ).first()
                            
                            if existing:
                                structured_logger.info(
                                    "verse_already_tokenized",
                                    sura=verse_sura,
                                    aya=verse_aya,
                                    message="Skipping already tokenized verse"
                                )
                                continue
                            
                            # Tokenize the verse
                            word_tokens = tokenizer.tokenize_verse(text, verse_sura, verse_aya)
                            
                            # Save to database
                            for word_token in word_tokens:
                                db_token = Token(
                                    sura=word_token.sura,
                                    aya=word_token.aya,
                                    position=word_token.position,
                                    text_ar=word_token.text_ar,
                                    normalized=word_token.normalized,
                                    status=TokenStatus.MISSING.value,
                                )
                                session.add(db_token)
                                tokens_count += 1
        
        try:
            session.commit()
        except Exception as commit_error:
            session.rollback()
            # Check if it's an IntegrityError (duplicate)
            if "UNIQUE constraint failed" in str(commit_error) or "IntegrityError" in str(type(commit_error)):
                structured_logger.warning(
                    "duplicate_tokens_detected",
                    sura=sura,
                    start_aya=start_aya,
                    end_aya=end_aya,
                    message="Some tokens already exist, skipping chunk",
                )
                # Return success with 0 tokens (already exists)
                return {
                    "status": "success",
                    "sura": sura,
                    "start_aya": start_aya,
                    "end_aya": end_aya,
                    "tokens_count": 0,
                    "note": "Already tokenized"
                }
            else:
                raise
        
        structured_logger.info(
            "chunk_tokenization_completed",
            sura=sura,
            start_aya=start_aya,
            end_aya=end_aya,
            tokens_count=tokens_count,
            correlation_id=correlation_id,
        )
        
        return {
            "status": "success",
            "sura": sura,
            "start_aya": start_aya,
            "end_aya": end_aya,
            "tokens_count": tokens_count,
        }
        
    except Exception as e:
        session.rollback()
        structured_logger.error(
            "chunk_tokenization_failed",
            sura=sura,
            start_aya=start_aya,
            end_aya=end_aya,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="backend.tasks.tokenization_tasks.tokenize_sura_parallel",
)
def tokenize_sura_parallel(
    self,
    sura: int,
    chunk_size: int = 20,
    correlation_id: str = None,
) -> Dict:
    """
    Tokenize a sura in parallel chunks for better performance.
    
    Args:
        sura: Surah number
        chunk_size: Number of ayahs per chunk
        correlation_id: Optional tracking ID
        
    Returns:
        Dictionary with overall results
    """
    structured_logger.info(
        "parallel_tokenization_started",
        sura=sura,
        chunk_size=chunk_size,
        correlation_id=correlation_id,
    )
    
    try:
        # Get total ayahs for this sura (hardcoded for now)
        # In production, read from metadata
        total_ayahs_map = {
            1: 7,  # Al-Fatiha
            2: 286,  # Al-Baqarah
            3: 200,  # Ali 'Imran
            # ... rest would be in config
        }
        
        total_ayahs = total_ayahs_map.get(sura, 100)
        
        # Create chunks
        chunks = []
        for start in range(1, total_ayahs + 1, chunk_size):
            end = min(start + chunk_size - 1, total_ayahs)
            chunks.append((start, end))
        
        if self.request.id:
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "chunking",
                    "sura": sura,
                    "total_chunks": len(chunks),
                    "progress": 10,
            },
        )
        
        # Execute chunks in parallel using chord (group + callback)
        # Use chord to aggregate results without blocking
        from celery import chord
        
        job = chord(
            tokenize_sura_chunk.s(
                sura,
                start,
                end,
                correlation_id=correlation_id,
            )
            for start, end in chunks
        )(finalize_tokenization.s(sura, correlation_id))
        
        structured_logger.info(
            "parallel_tokenization_queued",
            sura=sura,
            total_chunks=len(chunks),
            correlation_id=correlation_id,
        )
        
        return {
            "status": "queued",
            "sura": sura,
            "chunks_queued": len(chunks),
            "correlation_id": correlation_id,
            "finalization_job_id": job.id,
        }
        
    except Exception as e:
        structured_logger.error(
            "parallel_tokenization_failed",
            sura=sura,
            error=str(e),
            exc_info=True,
        )
        raise


@celery_app.task(name="backend.tasks.tokenization_tasks.finalize_tokenization")
def finalize_tokenization(results: List[Dict], sura: int, correlation_id: str = None) -> Dict:
    """
    Finalize tokenization after all chunks complete.
    
    Args:
        results: List of chunk results
        sura: Surah number
        correlation_id: Optional tracking ID
        
    Returns:
        Final summary
    """
    total_tokens = sum(r.get("tokens_count", 0) for r in results if r)
    chunks_processed = len([r for r in results if r and r.get("status") == "success"])
    
    structured_logger.info(
        "tokenization_finalized",
        sura=sura,
        total_tokens=total_tokens,
        chunks_processed=chunks_processed,
        correlation_id=correlation_id,
    )
    
    return {
        "status": "completed",
        "sura": sura,
        "total_tokens": total_tokens,
        "chunks_processed": chunks_processed,
        "correlation_id": correlation_id,
    }
