"""API routes for pipeline management and background jobs."""
import uuid
from typing import Dict, Optional

from celery import chain
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.logging_config import get_logger
from backend.tasks.root_extraction_tasks import extract_roots_parallel
from backend.tasks.tokenization_tasks import tokenize_sura_parallel
from backend.worker import celery_app

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])
logger = get_logger(__name__)


# Response Models
class JobResponse(BaseModel):
    """Response model for job submission."""

    job_id: str
    correlation_id: str
    status: str
    sura: int
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    correlation_id: Optional[str] = None
    status: str  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    sura: int
    progress: int  # 0-100
    meta: Dict = {}
    result: Optional[Dict] = None


class PipelineStatusResponse(BaseModel):
    """Response model for complete pipeline status."""

    sura: int
    tokenization: Optional[JobStatusResponse] = None
    root_extraction: Optional[JobStatusResponse] = None
    overall_status: str
    overall_progress: int


# Endpoints
@router.post(
    "/tokenize",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start tokenization job",
    description="Queue a background job to tokenize a complete surah",
)
async def start_tokenization(
    sura: int = Query(..., ge=1, le=114, description="Surah number to tokenize"),
    chunk_size: int = Query(20, ge=5, le=50, description="Verses per chunk for parallel processing"),
) -> JobResponse:
    """
    Start a background tokenization job for a surah.
    
    This endpoint queues a Celery task that will:
    1. Split the surah into chunks
    2. Process chunks in parallel
    3. Store results in database
    
    The job runs asynchronously. Use /pipeline/status to check progress.
    """
    # Generate correlation ID for tracking
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "tokenization_job_queued",
        sura=sura,
        chunk_size=chunk_size,
        correlation_id=correlation_id,
    )
    
    try:
        # Queue the task
        task = tokenize_sura_parallel.apply_async(
            args=[sura, chunk_size, correlation_id],
            task_id=correlation_id,
        )
        
        return JobResponse(
            job_id=task.id,
            correlation_id=correlation_id,
            status="queued",
            sura=sura,
            message=f"Tokenization job queued for Surah {sura}",
        )
        
    except Exception as e:
        logger.error(
            "tokenization_job_failed",
            sura=sura,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue tokenization job: {str(e)}",
        )


@router.post(
    "/extract-roots",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start root extraction job",
    description="Queue a background job to extract roots for a surah",
)
async def start_root_extraction(
    sura: int = Query(..., ge=1, le=114, description="Surah number"),
    chunk_size: int = Query(50, ge=10, le=100, description="Tokens per chunk"),
) -> JobResponse:
    """
    Start a background root extraction job for a surah.
    
    Prerequisites:
    - Surah must already be tokenized
    
    The job runs asynchronously. Use /pipeline/status to check progress.
    """
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "root_extraction_job_queued",
        sura=sura,
        chunk_size=chunk_size,
        correlation_id=correlation_id,
    )
    
    try:
        task = extract_roots_parallel.apply_async(
            args=[sura, chunk_size, correlation_id],
            task_id=correlation_id,
        )
        
        return JobResponse(
            job_id=task.id,
            correlation_id=correlation_id,
            status="queued",
            sura=sura,
            message=f"Root extraction job queued for Surah {sura}",
        )
        
    except Exception as e:
        logger.error(
            "root_extraction_job_failed",
            sura=sura,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue root extraction job: {str(e)}",
        )


@router.get(
    "/job/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Check the status of a specific background job",
)
async def get_job_status(
    job_id: str,
) -> JobStatusResponse:
    """
    Get the current status of a background job.
    
    Status values:
    - PENDING: Job is queued but not started
    - STARTED: Job has begun processing
    - PROGRESS: Job is in progress (check meta for details)
    - SUCCESS: Job completed successfully
    - FAILURE: Job failed (check result for error details)
    """
    try:
        task = AsyncResult(job_id, app=celery_app)
        
        # Get task info
        state = task.state
        info = task.info or {}
        
        # Extract sura from info
        sura = info.get("sura", 0) if isinstance(info, dict) else 0
        
        # Calculate progress
        if state == "PENDING":
            progress = 0
        elif state == "PROGRESS":
            progress = info.get("progress", 0) if isinstance(info, dict) else 50
        elif state == "SUCCESS":
            progress = 100
        elif state == "FAILURE":
            progress = 0
        else:
            progress = 10
        
        # Get result if completed
        result = None
        if state == "SUCCESS":
            result = task.result
        elif state == "FAILURE":
            result = {"error": str(task.result)}
        
        return JobStatusResponse(
            job_id=job_id,
            correlation_id=info.get("correlation_id") if isinstance(info, dict) else None,
            status=state,
            sura=sura,
            progress=progress,
            meta=info if isinstance(info, dict) else {},
            result=result,
        )
        
    except Exception as e:
        logger.error(
            "job_status_check_failed",
            job_id=job_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )


@router.get(
    "/status",
    response_model=PipelineStatusResponse,
    summary="Get pipeline status for surah",
    description="Check the status of all pipeline jobs for a specific surah",
)
async def get_pipeline_status(
    sura: int = Query(..., ge=1, le=114, description="Surah number"),
) -> PipelineStatusResponse:
    """
    Get the complete pipeline status for a surah.
    
    This endpoint checks:
    1. Tokenization job status (if any)
    2. Root extraction job status (if any)
    3. Overall pipeline progress
    
    Note: This is a simplified version. In production, you would
    store job IDs in a database and track them properly.
    """
    # In production, look up job IDs from database
    # For now, return a template response
    
    return PipelineStatusResponse(
        sura=sura,
        tokenization=None,
        root_extraction=None,
        overall_status="unknown",
        overall_progress=0,
    )


@router.post(
    "/process-sura",
    response_model=Dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process complete surah",
    description="Run full pipeline: tokenization → root extraction",
)
async def process_complete_sura(
    sura: int = Query(..., ge=1, le=114, description="Surah number"),
) -> Dict:
    """
    Process a complete surah through the full pipeline.
    
    This will:
    1. Queue tokenization job
    2. Queue root extraction job (depends on tokenization)
    3. Return job IDs for tracking
    
    The jobs run sequentially (root extraction waits for tokenization).
    """
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "full_pipeline_started",
        sura=sura,
        correlation_id=correlation_id,
    )
    
    try:
        # Create a chain: tokenization → root extraction
        # This ensures root extraction only runs after tokenization completes successfully
        pipeline = chain(
            tokenize_sura_parallel.signature(
                args=[sura, 20, correlation_id],
                task_id=f"tokenize-{correlation_id}",
            ),
            extract_roots_parallel.signature(
                args=[sura, 50, correlation_id],
                task_id=f"extract-{correlation_id}",
            ),
        )
        
        # Apply the chain
        result = pipeline.apply_async()
        
        return {
            "status": "queued",
            "sura": sura,
            "correlation_id": correlation_id,
            "tokenization_job_id": f"tokenize-{correlation_id}",
            "root_extraction_job_id": f"extract-{correlation_id}",
            "chain_id": result.id,
            "message": f"Full pipeline queued for Surah {sura}",
        }
        
    except Exception as e:
        logger.error(
            "full_pipeline_failed",
            sura=sura,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue pipeline: {str(e)}",
        )


@router.delete(
    "/job/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel job",
    description="Attempt to cancel a running job",
)
async def cancel_job(
    job_id: str,
) -> Dict:
    """
    Cancel a running background job.
    
    Note: Jobs that have already started may not be cancellable.
    """
    try:
        task = AsyncResult(job_id, app=celery_app)
        task.revoke(terminate=True)
        
        logger.info(
            "job_cancelled",
            job_id=job_id,
        )
        
        return {
            "status": "cancelled",
            "job_id": job_id,
            "message": "Job cancellation requested",
        }
        
    except Exception as e:
        logger.error(
            "job_cancellation_failed",
            job_id=job_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}",
        )
