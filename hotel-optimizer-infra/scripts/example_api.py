"""
Example FastAPI Integration

Shows how to add job queue endpoints to your existing FastAPI app.
Copy the relevant parts into your application.

Endpoints:
    POST /api/v1/optimize     - Submit optimization job
    GET  /api/v1/jobs/{id}    - Get job status
    DELETE /api/v1/jobs/{id}  - Cancel pending job
    GET  /health              - Health check
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

# Import from your job queue module
from job_queue import (
    enqueue_optimization,
    get_job_status,
    cancel_job,
    JobStatus,
    JobResult
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hotel Optimizer API",
    version="1.0.0",
    description="Optimization engine for hotel booking configurations"
)

# CORS - adjust origins for your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.com",  # Production frontend
        "http://localhost:3000",       # Local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# =============================================================
# REQUEST/RESPONSE MODELS
# =============================================================

class OptimizationRequest(BaseModel):
    """Request to start an optimization job."""
    hotel_id: str = Field(..., description="Hotel identifier")
    date_range_start: str = Field(..., description="Start date (YYYY-MM-DD)")
    date_range_end: str = Field(..., description="End date (YYYY-MM-DD)")
    room_types: list[str] = Field(default=["all"], description="Room types to optimize")
    constraints: Optional[Dict[str, Any]] = Field(default=None, description="Optimization constraints")

    class Config:
        json_schema_extra = {
            "example": {
                "hotel_id": "hotel_12345",
                "date_range_start": "2025-02-01",
                "date_range_end": "2025-02-28",
                "room_types": ["standard", "deluxe", "suite"],
                "constraints": {
                    "min_occupancy": 0.6,
                    "max_price_change_pct": 15
                }
            }
        }


class JobResponse(BaseModel):
    """Response for job status queries."""
    job_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str


# =============================================================
# AUTHENTICATION (placeholder - implement your own)
# =============================================================

async def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Extract user ID from request headers.
    
    Replace this with your actual authentication logic.
    In production, verify JWT tokens, API keys, etc.
    """
    if x_user_id:
        return x_user_id
    
    # Fallback for development - don't use in production
    return "anonymous"


# =============================================================
# ENDPOINTS
# =============================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint for load balancer."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/api/v1/optimize", response_model=JobResponse, tags=["Optimization"])
async def submit_optimization(
    request: OptimizationRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Submit an optimization job.
    
    The job runs asynchronously. Poll /api/v1/jobs/{job_id} for status.
    
    Rate limits:
    - Maximum 3 concurrent jobs per user
    - Nginx also enforces 12 requests/minute to this endpoint
    """
    logger.info(f"Optimization request from user {user_id} for hotel {request.hotel_id}")
    
    # Convert request to params dict for the optimizer
    optimization_params = {
        "date_range": {
            "start": request.date_range_start,
            "end": request.date_range_end
        },
        "room_types": request.room_types,
        "constraints": request.constraints or {}
    }
    
    # Submit to queue
    result: JobResult = enqueue_optimization(
        user_id=user_id,
        hotel_id=request.hotel_id,
        optimization_params=optimization_params
    )
    
    # Handle rate limiting
    if result.status == JobStatus.RATE_LIMITED:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": result.error,
                "retry_after": 30
            }
        )
    
    return JobResponse(
        job_id=result.job_id,
        status=result.status.value,
        message="Job queued successfully. Poll /api/v1/jobs/{job_id} for status."
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job(job_id: str):
    """
    Get the status of an optimization job.
    
    Poll this endpoint to check job progress and retrieve results.
    """
    result: JobResult = get_job_status(job_id)
    
    if result.status == JobStatus.FAILED and "not found" in (result.error or "").lower():
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(
        job_id=result.job_id,
        status=result.status.value,
        progress=result.progress,
        result=result.result,
        error=result.error
    )


@app.delete("/api/v1/jobs/{job_id}", tags=["Jobs"])
async def cancel_job_endpoint(
    job_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Cancel a pending optimization job.
    
    Only jobs in 'queued' status can be cancelled.
    """
    success = cancel_job(job_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel job. It may be running, completed, or not owned by you."
        )
    
    return {"message": "Job cancelled", "job_id": job_id}


# =============================================================
# ERROR HANDLERS
# =============================================================

@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc: HTTPException):
    """Custom response for rate limiting."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limited",
            "message": "Too many requests. Please slow down.",
            "retry_after": 30
        },
        headers={"Retry-After": "30"}
    )


# =============================================================
# STARTUP/SHUTDOWN
# =============================================================

@app.on_event("startup")
async def startup_event():
    logger.info("Hotel Optimizer API starting up")
    # Initialize connections, warm caches, etc.


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Hotel Optimizer API shutting down")
    # Close connections, flush buffers, etc.


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
