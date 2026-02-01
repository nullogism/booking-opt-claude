"""
BookingOpt API - Redis Queue Based
Accepts room optimization requests and processes via worker queue
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import job queue functions
from job_queue import (
    enqueue_optimization,
    get_job_status,
    cancel_job,
    JobStatus,
    JobResult
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("bookingopt-api")

# FastAPI app
app = FastAPI(
    title="BookingOpt API",
    version="1.0.0",
    description="Hotel room optimization API with async job processing"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://localhost:8080",  # Alternative local port
        # Add production frontend domain when available
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# =============================================================
# REQUEST/RESPONSE MODELS
# =============================================================

class ReservationInput(BaseModel):
    """Individual reservation in the optimization problem"""
    Name: str
    Arrival: str  # Date string YYYY-MM-DD
    Length: float  # Duration in days
    AdjacencyGroup: str = "None"
    AssignedRoom: str = "None"


class RoomInput(BaseModel):
    """Individual room in the hotel"""
    RoomNumber: str
    RoomType: Optional[str] = None
    AdjacentRooms: list[str] = Field(default_factory=list)


class OptimizationRequest(BaseModel):
    """
    Request to optimize room assignments.
    Based on TestJSON sample format.
    """
    ProblemId: str = Field(..., description="Unique identifier for the problem")
    MinimumStay: float = Field(default=1.0, description="Minimum stay requirement in days")
    Reservations: list[ReservationInput] = Field(..., description="List of reservations to optimize")
    NewReservations: list[ReservationInput] = Field(default_factory=list, description="New reservations to add")
    MinimumStayByDay: Dict[str, float] = Field(default_factory=dict, description="Day-specific minimum stay rules")
    Rooms: list[RoomInput] = Field(..., description="List of available rooms")

    class Config:
        json_schema_extra = {
            "example": {
                "ProblemId": "hotel_12345_2026_02",
                "MinimumStay": 5.0,
                "Reservations": [
                    {
                        "Name": "1",
                        "Arrival": "2026-02-20",
                        "Length": 9.0,
                        "AdjacencyGroup": "None",
                        "AssignedRoom": "None"
                    }
                ],
                "NewReservations": [],
                "MinimumStayByDay": {}
            }
        }


class JobResponse(BaseModel):
    """Response for job status queries"""
    job_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None
    problem_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str


# =============================================================
# AUTHENTICATION (placeholder - implement proper auth later)
# =============================================================

async def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """
    Extract user ID from request headers.

    TODO: Replace with proper JWT/API key authentication in production
    """
    if x_user_id:
        return x_user_id

    # Fallback for development - DO NOT use in production
    return "anonymous"


# =============================================================
# ENDPOINTS
# =============================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint for load balancer and monitoring"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/api/v1/optimize", response_model=JobResponse, tags=["Optimization"])
async def submit_optimization(
    request: OptimizationRequest,
    user_id: str = Header(default="anonymous", alias="X-User-ID")
):
    """
    Submit a room optimization job.

    The job runs asynchronously. Poll /api/v1/jobs/{job_id} for status.

    Rate limits:
    - Maximum 3 concurrent jobs per user (application layer)
    - Maximum 12 requests/minute to this endpoint (nginx layer)
    """
    logger.info(f"Optimization request from user {user_id} for problem {request.ProblemId}")

    # Convert Pydantic model to dict for the optimizer
    optimization_params = request.model_dump()

    # Submit to queue
    result: JobResult = enqueue_optimization(
        user_id=user_id,
        hotel_id=request.ProblemId,
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
        problem_id=request.ProblemId,
        message=f"Job queued successfully. Poll /api/v1/jobs/{result.job_id} for status."
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

    response = JobResponse(
        job_id=result.job_id,
        status=result.status.value,
        progress=result.progress,
        result=result.result,
        error=result.error
    )

    # Extract ProblemId from result if available
    if result.result and isinstance(result.result, dict):
        response.problem_id = result.result.get("problem_id")

    return response


@app.delete("/api/v1/jobs/{job_id}", tags=["Jobs"])
async def cancel_job_endpoint(
    job_id: str,
    user_id: str = Header(default="anonymous", alias="X-User-ID")
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
    """Custom response for rate limiting"""
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
    logger.info("BookingOpt API starting up")
    # Initialize connections, warm caches, etc.


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("BookingOpt API shutting down")
    # Close connections, flush buffers, etc.


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000"))
    )
