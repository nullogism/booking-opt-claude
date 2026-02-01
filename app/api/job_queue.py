"""
Job Queue Integration for Hotel Optimizer

This module provides a simple job queue using Redis Queue (RQ).
Add this to your existing application to handle long-running optimization jobs.

Installation:
    pip install rq redis

Usage in your Flask/FastAPI app:
    from job_queue import enqueue_optimization, get_job_status

    # Submit job (returns immediately)
    job_id = enqueue_optimization(hotel_id="hotel123", params={...})
    
    # Poll for status
    status = get_job_status(job_id)
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import redis
from rq import Queue, Worker
from rq.job import Job

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MAX_JOB_DURATION = int(os.getenv("MAX_JOB_DURATION", "120"))  # seconds
MAX_QUEUED_JOBS_PER_USER = int(os.getenv("MAX_QUEUED_JOBS_PER_USER", "3"))
JOB_RESULT_TTL = int(os.getenv("JOB_RESULT_TTL", "3600"))  # 1 hour

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class JobResult:
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Redis connection pool (reuse connections)
_redis_pool = None


def get_redis_connection() -> redis.Redis:
    """Get Redis connection from pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(REDIS_URL)
    return redis.Redis(connection_pool=_redis_pool)


def get_queue() -> Queue:
    """Get the RQ job queue."""
    return Queue("optimization", connection=get_redis_connection())


# =============================================================
# RATE LIMITING (Application Level)
# =============================================================

def check_user_rate_limit(user_id: str) -> tuple[bool, str]:
    """
    Check if user has exceeded their job queue limit.
    
    Returns:
        (allowed: bool, reason: str)
    """
    r = get_redis_connection()
    queue = get_queue()
    
    # Count user's pending/running jobs
    user_job_key = f"user_jobs:{user_id}"
    active_jobs = r.scard(user_job_key)
    
    if active_jobs >= MAX_QUEUED_JOBS_PER_USER:
        return False, f"Maximum {MAX_QUEUED_JOBS_PER_USER} concurrent jobs allowed"
    
    return True, "ok"


def track_user_job(user_id: str, job_id: str):
    """Track a job as belonging to a user."""
    r = get_redis_connection()
    user_job_key = f"user_jobs:{user_id}"
    r.sadd(user_job_key, job_id)
    # Auto-expire the set after max job duration + buffer
    r.expire(user_job_key, MAX_JOB_DURATION + 300)


def untrack_user_job(user_id: str, job_id: str):
    """Remove job from user's active set."""
    r = get_redis_connection()
    user_job_key = f"user_jobs:{user_id}"
    r.srem(user_job_key, job_id)


# =============================================================
# JOB SUBMISSION & STATUS
# =============================================================

def enqueue_optimization(
    user_id: str,
    hotel_id: str,
    optimization_params: Dict[str, Any],
    priority: str = "normal"
) -> JobResult:
    """
    Submit an optimization job to the queue.
    
    Args:
        user_id: ID of the user submitting the job
        hotel_id: Hotel to optimize
        optimization_params: Parameters for the optimization algorithm
        priority: "high", "normal", or "low"
    
    Returns:
        JobResult with job_id and initial status
    """
    # Check rate limit
    allowed, reason = check_user_rate_limit(user_id)
    if not allowed:
        return JobResult(
            job_id="",
            status=JobStatus.RATE_LIMITED,
            error=reason
        )
    
    queue = get_queue()

    # Enqueue the job
    # Reference the worker function as a string path since it's in the worker container
    job = queue.enqueue(
        "worker.run_optimization_task",  # The worker function path
        args=(hotel_id, optimization_params),
        kwargs={"user_id": user_id},
        job_timeout=MAX_JOB_DURATION,
        result_ttl=JOB_RESULT_TTL,
        failure_ttl=JOB_RESULT_TTL,
        meta={
            "user_id": user_id,
            "hotel_id": hotel_id,
            "submitted_at": datetime.utcnow().isoformat()
        }
    )
    
    # Track for rate limiting
    track_user_job(user_id, job.id)
    
    logger.info(f"Job {job.id} enqueued for user {user_id}, hotel {hotel_id}")
    
    return JobResult(
        job_id=job.id,
        status=JobStatus.QUEUED,
        created_at=datetime.utcnow()
    )


def get_job_status(job_id: str) -> JobResult:
    """
    Get the current status of a job.
    
    Args:
        job_id: The job ID returned from enqueue_optimization
    
    Returns:
        JobResult with current status and result (if completed)
    """
    try:
        job = Job.fetch(job_id, connection=get_redis_connection())
    except Exception as e:
        return JobResult(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=f"Job not found: {str(e)}"
        )
    
    # Map RQ status to our status
    if job.is_queued:
        status = JobStatus.QUEUED
    elif job.is_started:
        status = JobStatus.RUNNING
    elif job.is_finished:
        status = JobStatus.COMPLETED
    elif job.is_failed:
        status = JobStatus.FAILED
    else:
        status = JobStatus.QUEUED
    
    return JobResult(
        job_id=job_id,
        status=status,
        result=job.result if job.is_finished else None,
        error=str(job.exc_info) if job.is_failed else None,
        progress=job.meta.get("progress"),
        created_at=job.enqueued_at,
        started_at=job.started_at,
        completed_at=job.ended_at
    )


def cancel_job(job_id: str, user_id: str) -> bool:
    """
    Cancel a pending job.
    
    Returns:
        True if cancelled, False if job was already running/completed
    """
    try:
        job = Job.fetch(job_id, connection=get_redis_connection())
        
        # Verify ownership
        if job.meta.get("user_id") != user_id:
            return False
        
        if job.is_queued:
            job.cancel()
            untrack_user_job(user_id, job_id)
            return True
        
        return False
    except Exception:
        return False


# =============================================================
# NOTE: Worker task is now in app/worker/worker.py
# The worker runs in a separate container with scipy dependencies
# =============================================================
