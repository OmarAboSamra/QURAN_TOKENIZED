"""Celery tasks for root extraction."""
import time
from typing import Dict, List

from celery import group
from celery.utils.log import get_task_logger

from backend.db import get_sync_session_maker
from backend.logging_config import get_logger
from backend.models import Token
from backend.repositories.token_repository import TokenRepository
from backend.worker import celery_app
from backend.services.root_extractor_v2 import RootExtractionService

logger = get_task_logger(__name__)
structured_logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="backend.tasks.root_extraction_tasks.extract_roots_for_sura",
)
def extract_roots_for_sura(
    self,
    sura: int,
    correlation_id: str = None,
) -> Dict:
    """
    Extract roots for all tokens in a sura.
    
    Args:
        sura: Surah number
        correlation_id: Optional tracking ID
        
    Returns:
        Dictionary with extraction results
    """
    start_time = time.time()
    
    structured_logger.info(
        "root_extraction_started",
        sura=sura,
        correlation_id=correlation_id,
        task_id=self.request.id,
    )
    
    session = None
    
    try:
        # Only update state if running as Celery task (has task_id)
        if self.request.id:
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "loading_tokens",
                    "sura": sura,
                    "progress": 0,
                },
            )
        
        # Initialize services
        root_service = RootExtractionService()
        token_repo = TokenRepository()
        session_maker = get_sync_session_maker()
        session = session_maker()
        
        # Get all tokens for this sura that need roots
        tokens = token_repo.get_tokens_missing_roots_by_sura(session, sura)
        total_tokens = len(tokens)
        
        if total_tokens == 0:
            structured_logger.info(
                "no_tokens_to_process",
                sura=sura,
                correlation_id=correlation_id,
            )
            return {
                "status": "success",
                "sura": sura,
                "tokens_processed": 0,
                "message": "No tokens need root extraction",
            }
        
        if self.request.id:
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "extracting_roots",
                    "sura": sura,
                    "total_tokens": total_tokens,
                    "progress": 10,
                },
            )
        
        # Process tokens in batches
        batch_size = 50
        processed = 0
        updated = 0
        
        for i in range(0, total_tokens, batch_size):
            batch = tokens[i : i + batch_size]
            
            for token in batch:
                try:
                    # Extract root with location info for corpus extractor
                    root_result = root_service.extract_root_sync(
                        token.normalized,
                        sura=token.sura,
                        aya=token.aya,
                        position=token.position
                    )
                    
                    if root_result and root_result.get("root"):
                        token.root = root_result["root"]
                        token.root_sources = root_result.get("sources", {})
                        token.status = "verified"
                        updated += 1
                    
                    processed += 1
                    
                    # Update progress
                    if processed % 10 == 0 and self.request.id:
                        progress = 10 + int((processed / total_tokens) * 80)
                        self.update_state(
                            state="PROGRESS",
                            meta={
                                "status": "extracting_roots",
                                "sura": sura,
                                "processed": processed,
                                "total": total_tokens,
                                "progress": progress,
                            },
                        )
                
                except Exception as e:
                    structured_logger.warning(
                        "root_extraction_error_single_token",
                        token_id=token.id,
                        error=str(e),
                    )
                    continue
            
            # Commit batch
            session.commit()
        
        duration = time.time() - start_time
        
        structured_logger.info(
            "root_extraction_completed",
            sura=sura,
            tokens_processed=processed,
            tokens_updated=updated,
            duration_seconds=round(duration, 2),
            correlation_id=correlation_id,
        )
        
        return {
            "status": "success",
            "sura": sura,
            "tokens_processed": processed,
            "tokens_updated": updated,
            "duration_seconds": round(duration, 2),
            "correlation_id": correlation_id,
        }
        
    except Exception as e:
        structured_logger.error(
            "root_extraction_failed",
            sura=sura,
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="backend.tasks.root_extraction_tasks.extract_roots_chunk",
)
def extract_roots_chunk(
    self,
    token_ids: List[int],
    correlation_id: str = None,
) -> Dict:
    """
    Extract roots for a specific chunk of tokens.
    
    Args:
        token_ids: List of token IDs to process
        correlation_id: Optional tracking ID
        
    Returns:
        Dictionary with chunk results
    """
    structured_logger.info(
        "chunk_root_extraction_started",
        token_count=len(token_ids),
        correlation_id=correlation_id,
    )
    
    try:
        root_service = RootExtractionService()
        session_maker = get_sync_session_maker()
        session = session_maker()
        
        updated = 0
        
        for token_id in token_ids:
            token = session.get(Token, token_id)
            if not token:
                continue
            
            try:
                # Extract root with location info for corpus extractor
                root_result = root_service.extract_root_sync(
                    token.normalized,
                    sura=token.sura,
                    aya=token.aya,
                    position=token.position
                )
                
                if root_result and root_result.get("root"):
                    token.root = root_result["root"]
                    token.root_sources = root_result.get("sources", {})
                    token.status = "verified"
                    updated += 1
                    
            except Exception as e:
                structured_logger.warning(
                    "token_root_extraction_error",
                    token_id=token_id,
                    error=str(e),
                )
                continue
        
        session.commit()
        
        structured_logger.info(
            "chunk_root_extraction_completed",
            tokens_processed=len(token_ids),
            tokens_updated=updated,
            correlation_id=correlation_id,
        )
        
        return {
            "status": "success",
            "tokens_processed": len(token_ids),
            "tokens_updated": updated,
        }
        
    except Exception as e:
        structured_logger.error(
            "chunk_root_extraction_failed",
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="backend.tasks.root_extraction_tasks.extract_roots_parallel",
)
def extract_roots_parallel(
    self,
    sura: int,
    chunk_size: int = 50,
    correlation_id: str = None,
) -> Dict:
    """
    Extract roots in parallel chunks for better performance.
    
    Args:
        sura: Surah number
        chunk_size: Number of tokens per chunk
        correlation_id: Optional tracking ID
        
    Returns:
        Dictionary with overall results
    """
    structured_logger.info(
        "parallel_root_extraction_started",
        sura=sura,
        chunk_size=chunk_size,
        correlation_id=correlation_id,
    )
    
    try:
        # Get all tokens needing roots
        token_repo = TokenRepository()
        session_maker = get_sync_session_maker()
        session = session_maker()
        
        tokens = token_repo.get_tokens_missing_roots_by_sura(session, sura)
        token_ids = [t.id for t in tokens]
        
        if not token_ids:
            return {
                "status": "success",
                "message": "No tokens to process",
                "sura": sura,
            }
        
        # Create chunks
        chunks = []
        for i in range(0, len(token_ids), chunk_size):
            chunk = token_ids[i : i + chunk_size]
            chunks.append(chunk)
        
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "chunking",
                "sura": sura,
                "total_chunks": len(chunks),
                "progress": 10,
            },
        )
        
        # Execute chunks in parallel using chord
        from celery import chord
        
        job = chord(
            extract_roots_chunk.s(chunk, correlation_id=correlation_id)
            for chunk in chunks
        )(finalize_root_extraction.s(sura, correlation_id))
        
        structured_logger.info(
            "parallel_root_extraction_queued",
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
            "parallel_root_extraction_failed",
            sura=sura,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        session.close()


@celery_app.task(name="backend.tasks.root_extraction_tasks.finalize_root_extraction")
def finalize_root_extraction(results: List[Dict], sura: int, correlation_id: str = None) -> Dict:
    """
    Finalize root extraction after all chunks complete.
    
    Args:
        results: List of chunk results
        sura: Surah number
        correlation_id: Optional tracking ID
        
    Returns:
        Final summary
    """
    total_processed = sum(r.get("tokens_processed", 0) for r in results if r)
    total_updated = sum(r.get("tokens_updated", 0) for r in results if r)
    chunks_processed = len([r for r in results if r and r.get("status") == "success"])
    
    structured_logger.info(
        "root_extraction_finalized",
        sura=sura,
        total_processed=total_processed,
        total_updated=total_updated,
        chunks_processed=chunks_processed,
        correlation_id=correlation_id,
    )
    
    return {
        "status": "completed",
        "sura": sura,
        "tokens_processed": total_processed,
        "tokens_updated": total_updated,
        "chunks_processed": chunks_processed,
        "correlation_id": correlation_id,
    }
