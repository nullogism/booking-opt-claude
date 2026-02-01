"""
BookingOpt Worker - Redis Queue Worker
Processes room optimization jobs from Redis queue
"""

import logging
import os
import sys
from typing import Any

import redis
from rq import Worker

# Add optimizer module to path
sys.path.insert(0, os.path.dirname(__file__))

# Import optimizer modules
from optimizer import SolverRunner
from optimizer.FeasibilitySolverRunner import FeasibilityRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("bookingopt-worker")

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


def run_optimization_task(
    hotel_id: str,
    optimization_params: dict[str, Any],
    user_id: str = None
) -> dict[str, Any]:
    """
    Run the booking optimization algorithm.

    This is the RQ worker task that gets called from the queue.

    Args:
        hotel_id: Problem ID from the request
        optimization_params: Full problem data (Reservations, MinimumStay, etc.)
        user_id: User who submitted the job

    Returns:
        Dict with success status and result/error
    """
    from rq import get_current_job
    job = get_current_job()

    logger.info(f"Starting optimization for problem {hotel_id}, user {user_id}")

    try:
        # Update progress
        job.meta["progress"] = 0
        job.save_meta()

        # Route to appropriate solver based on input
        # FeasibilityRunner handles scenarios with new reservations
        if "NewReservations" in optimization_params and len(optimization_params.get("NewReservations", [])) > 0:
            logger.info(f"Using FeasibilityRunner for problem {hotel_id} (has NewReservations)")
            runner = FeasibilityRunner()
            success, result = runner.Run(optimization_params, returnDict=True)
        else:
            logger.info(f"Using standard SolverRunner for problem {hotel_id}")
            # SolverRunner.Run expects the full JSON payload
            success, result = SolverRunner.Run(optimization_params, ReturnDict=True)

        if not success:
            logger.error(f"Optimization failed for {hotel_id}: {result}")
            return {
                "success": False,
                "error": "Optimization failed",
                "details": result,
                "problem_id": hotel_id
            }

        # Update progress to 100%
        job.meta["progress"] = 100
        job.save_meta()

        logger.info(f"Optimization completed successfully for {hotel_id}")

        return {
            "success": True,
            "result": result,
            "problem_id": hotel_id
        }

    except Exception as e:
        logger.error(f"Optimization error for {hotel_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "problem_id": hotel_id
        }


def run_worker():
    """
    Start the RQ worker process.

    This listens to the 'optimization' queue and processes jobs.
    """
    logger.info(f"Connecting to Redis at {REDIS_URL}")
    redis_conn = redis.from_url(REDIS_URL)

    worker = Worker(
        queues=["optimization"],
        connection=redis_conn
    )
    logger.info("BookingOpt worker started, listening to 'optimization' queue")
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    run_worker()
