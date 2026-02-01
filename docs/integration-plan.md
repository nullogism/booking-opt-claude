# BookingOpt-Prod Integration Plan

**Created**: 2026-01-31
**Status**: Analysis Complete - Ready for Integration

## Current Architecture (GCP-based)

The existing `BookingOpt-Prod` repository uses a **Google Cloud Platform (GCP)** event-driven architecture:

### Components

1. **BackEnd API** ([BackEnd/main.py](../booking-opt-prod/BackEnd/main.py))
   - **Framework**: FastAPI (already implemented!)
   - **Endpoints**:
     - `POST /api/upload` - Upload JSON problem data to GCS
     - `GET /api/result?fileName=...` - Poll for optimization results
     - `GET /health` - Health check
   - **Storage**: Google Cloud Storage (GCS) buckets
     - `booking-opt-json` - Input JSON files
     - `booking-opt-optimized` - Optimized results
     - `booking-opt-plotted` - PNG visualizations
   - **Auth**: GCP Workload Identity with service account impersonation

2. **Optimizer Worker** ([Optimizer/Optimizer/main.py](../booking-opt-prod/Optimizer/Optimizer/main.py))
   - **Trigger**: Google Cloud Pub/Sub subscription (`optimize-sub`)
   - **Process**:
     1. Receives message when JSON uploaded to GCS
     2. Downloads JSON from GCS
     3. Runs optimization via `SolverRunner.Run()`
     4. Uploads result to `booking-opt-optimized` bucket
     5. Acknowledges Pub/Sub message
   - **Dependencies**: scipy (custom `scippy:v0.1` base image)

3. **Plotter Function** ([optimize-plotter-function/](../booking-opt-prod/optimize-plotter-function/))
   - Triggered by optimized JSON upload
   - Generates PNG visualizations
   - Uploads to `booking-opt-plotted` bucket

4. **Frontend** ([FrontEnd/](../booking-opt-prod/FrontEnd/))
   - User interface (not needed for our backend-only deployment)

### Current Workflow

```
User → BackEnd API → GCS Upload → Pub/Sub → Optimizer → GCS Result
                                              ↓
                                          Plotter → GCS PNG
       ↑                                                  ↓
       Poll /api/result ←────────────────────────────────┘
       (returns signed URLs)
```

---

## Target Architecture (Docker Compose + Redis)

We need to **replace GCP services** with our portable Docker Compose stack:

### Components

1. **Nginx** (reverse proxy, rate limiting, SSL)
2. **API** (modified BackEnd with Redis Queue)
3. **Worker** (modified Optimizer using RQ)
4. **Redis** (job queue + result storage)

### Target Workflow

```
User → Nginx → API → Redis Queue → Worker → Redis Result
       ↑                                        ↓
       Poll /api/v1/jobs/{job_id} ─────────────┘
```

---

## Integration Strategy

### Phase 1: Adapt BackEnd API ✅ (Mostly Ready)

**Current State**: BackEnd already uses FastAPI with health check
**Changes Needed**:

1. **Remove GCS dependencies**
   - Replace `google-cloud-storage` with Redis
   - Remove service account impersonation

2. **Integrate job queue** (from [hotel-optimizer-infra/scripts/job_queue.py](../hotel-optimizer-infra/scripts/job_queue.py))
   - Replace `POST /api/upload` with `POST /api/v1/optimize`
   - Submit to Redis Queue instead of GCS
   - Return `job_id` instead of `fileName`

3. **Update polling endpoint**
   - Replace `GET /api/result` with `GET /api/v1/jobs/{job_id}`
   - Fetch from Redis instead of GCS
   - Return JSON result directly (no signed URLs needed)

4. **Keep health check** ✅
   - `GET /health` already exists

**Files to Modify**:
- [booking-opt-prod/BackEnd/main.py](../booking-opt-prod/BackEnd/main.py)
- [booking-opt-prod/BackEnd/requirements.txt](../booking-opt-prod/BackEnd/requirements.txt)
- [booking-opt-prod/BackEnd/Dockerfile](../booking-opt-prod/BackEnd/Dockerfile)

### Phase 2: Adapt Optimizer Worker

**Current State**: Pub/Sub subscriber waiting for messages
**Changes Needed**:

1. **Replace Pub/Sub with RQ Worker**
   - Remove `google.cloud.pubsub_v1`
   - Use RQ's `Worker` class
   - Listen to Redis queue instead

2. **Wrap SolverRunner in RQ job function**
   ```python
   def run_optimization_task(problem_data):
       success, result = SolverRunner.Run(problem_data)
       return {"success": success, "result": result}
   ```

3. **Fix base image issue**
   - Current Dockerfile uses `FROM scippy:v0.1` (custom image)
   - **Option A**: Use `python:3.11-slim` + install scipy/numpy
   - **Option B**: Build scippy image ourselves
   - **Recommendation**: Option A with standard scipy

**Files to Modify**:
- [booking-opt-prod/Optimizer/Optimizer/main.py](../booking-opt-prod/Optimizer/Optimizer/main.py) → Create new `worker.py`
- [booking-opt-prod/Optimizer/requirements.txt](../booking-opt-prod/Optimizer/requirements.txt)
- [booking-opt-prod/Optimizer/Dockerfile](../booking-opt-prod/Optimizer/Dockerfile)

### Phase 3: Handle Plotter (Optional)

**Current State**: Separate Cloud Function for visualization
**Options**:

1. **Defer to Phase 2**: Focus on core optimization first
2. **Integrate into Worker**: Generate PNG after optimization completes
3. **Separate Service**: Add plotter as another Docker service

**Recommendation**: Defer to post-MVP (Phase 2 features)

### Phase 4: Update docker-compose.yml

**Changes**:
1. Replace `your-optimizer-image:latest` with actual built images:
   - `api` service → `greeks-api:latest`
   - `worker` service → `greeks-optimizer:latest`
2. Add build context for local development:
   ```yaml
   api:
     build: ./booking-opt-prod/BackEnd
     image: greeks-api:latest

   worker:
     build: ./booking-opt-prod/Optimizer
     image: greeks-optimizer:latest
   ```

---

## Detailed File Changes

### 1. BackEnd API Changes

#### [booking-opt-prod/BackEnd/requirements.txt](../booking-opt-prod/BackEnd/requirements.txt)

**Remove**:
```
google-cloud-storage>=2.0
```

**Add**:
```
redis>=5.0.0
rq>=1.15.0
pydantic>=2.0.0
python-dotenv
```

#### [booking-opt-prod/BackEnd/main.py](../booking-opt-prod/BackEnd/main.py)

**Remove** (lines 9-11, 26-52):
- All GCS imports and clients
- Service account impersonation
- Bucket configuration

**Add**:
```python
from job_queue import enqueue_optimization, get_job_status, JobStatus
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
```

**Replace `/api/upload` endpoint** (lines 83-129):
```python
@app.post("/api/v1/optimize")
async def submit_optimization(
    problem_data: dict,
    x_user_id: str = Header("anonymous")
):
    """Submit optimization job to Redis Queue"""

    # Extract problem ID
    problem_id = problem_data.get("ProblemId")

    # Enqueue job
    result = enqueue_optimization(
        user_id=x_user_id,
        hotel_id=problem_id or "unknown",
        optimization_params=problem_data
    )

    if result.status == JobStatus.RATE_LIMITED:
        raise HTTPException(status_code=429, detail=result.error)

    return {
        "job_id": result.job_id,
        "status": result.status.value,
        "problem_id": problem_id
    }
```

**Replace `/api/result` endpoint** (lines 134-186):
```python
@app.get("/api/v1/jobs/{job_id}")
async def get_job_result(job_id: str):
    """Poll for job status and result"""

    result = get_job_status(job_id)

    if result.status == JobStatus.FAILED and "not found" in (result.error or ""):
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": result.job_id,
        "status": result.status.value,
        "progress": result.progress,
        "result": result.result,
        "error": result.error
    }
```

### 2. Optimizer Worker Changes

#### Create new file: [booking-opt-prod/Optimizer/worker.py](../booking-opt-prod/Optimizer/worker.py)

```python
"""
Redis Queue Worker for Booking Optimizer
Replaces Pub/Sub subscription with RQ worker
"""

import os
import json
import logging
from rq import Worker, Queue, Connection
import redis
from Optimizer.SolverRunner import Run

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("optimizer-worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

def run_optimization_task(problem_data, user_id=None):
    """
    Run optimization on problem data.
    Called by RQ worker from Redis queue.
    """
    logger.info(f"Starting optimization for user {user_id}")

    try:
        # Run the solver
        success, result = Run(problem_data)

        if not success:
            logger.error(f"Optimization failed: {result}")
            return {
                "success": False,
                "error": "Optimization failed",
                "details": result
            }

        logger.info("Optimization completed successfully")
        return {
            "success": True,
            "result": result,
            "problem_id": problem_data.get("ProblemId")
        }

    except Exception as e:
        logger.error(f"Optimization error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Connect to Redis
    redis_conn = redis.from_url(REDIS_URL)

    # Create worker for "optimization" queue
    with Connection(redis_conn):
        worker = Worker(["optimization"])
        logger.info("Optimizer worker started, listening to 'optimization' queue")
        worker.work()
```

#### Update [booking-opt-prod/Optimizer/Dockerfile](../booking-opt-prod/Optimizer/Dockerfile)

**Replace**:
```dockerfile
FROM scippy:v0.1
```

**With**:
```dockerfile
FROM python:3.11-slim

# Install scipy and scientific computing dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*
```

**Update CMD**:
```dockerfile
CMD ["python", "worker.py"]
```

#### Update [booking-opt-prod/Optimizer/requirements.txt](../booking-opt-prod/Optimizer/requirements.txt)

**Remove**:
```
google-cloud-storage
google-cloud-pubsub
```

**Add**:
```
scipy>=1.11.0
redis>=5.0.0
rq>=1.15.0
```

**Keep**:
```
numpy
httpx>=0.23.0
```

---

## Migration Checklist

### Pre-Integration
- [x] Clone BookingOpt-Prod repository
- [x] Analyze existing architecture
- [x] Document integration plan (this file)

### Code Integration
- [ ] Copy `job_queue.py` into BackEnd directory
- [ ] Modify BackEnd/main.py (remove GCS, add RQ)
- [ ] Update BackEnd/requirements.txt
- [ ] Create Optimizer/worker.py
- [ ] Update Optimizer/Dockerfile (fix base image)
- [ ] Update Optimizer/requirements.txt

### Infrastructure Integration
- [ ] Update docker-compose.yml with build contexts
- [ ] Create .env file with Redis configuration
- [ ] Test local build: `docker-compose build`
- [ ] Test local run: `docker-compose up -d`

### Testing
- [ ] Submit test optimization job via API
- [ ] Verify job queued in Redis
- [ ] Verify worker picks up job
- [ ] Verify result returned via API
- [ ] Test rate limiting (submit >3 jobs)
- [ ] Test error handling (invalid input)

### Documentation
- [ ] Update README.md with new endpoints
- [ ] Document API changes (GCS → Redis)
- [ ] Update app-feature-bug.md with completed tasks

---

## API Endpoint Changes

### Before (GCP-based)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload` | POST | Upload JSON to GCS |
| `/api/result?fileName=X` | GET | Poll for result, return signed URLs |
| `/health` | GET | Health check |

### After (Redis-based)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/optimize` | POST | Submit job to Redis Queue |
| `/api/v1/jobs/{job_id}` | GET | Poll for result, return JSON directly |
| `/health` | GET | Health check (unchanged) |

---

## Dependencies to Remove

### BackEnd
- ❌ `google-cloud-storage`
- ❌ `google.auth`
- ❌ All GCS bucket references

### Optimizer
- ❌ `google-cloud-storage`
- ❌ `google-cloud-pubsub`
- ❌ Custom `scippy:v0.1` base image

---

## Dependencies to Add

### BackEnd
- ✅ `redis>=5.0.0`
- ✅ `rq>=1.15.0`
- ✅ `pydantic>=2.0.0`
- ✅ `python-dotenv`

### Optimizer
- ✅ `scipy>=1.11.0` (standard from PyPI)
- ✅ `redis>=5.0.0`
- ✅ `rq>=1.15.0`

---

## Questions to Resolve

1. **Plotter Integration**: Should we integrate the PNG plotter now or defer?
   - **Recommendation**: Defer - focus on core optimization first

2. **Result Storage**: Keep results in Redis (1hr TTL) or add persistent storage?
   - **Current Plan**: Redis with 1hr TTL (matches requirements)
   - **Future**: Add PostgreSQL if long-term job history needed

3. **Frontend**: Do we need to deploy the existing frontend?
   - **Assumption**: No - frontend team building new interface
   - **Action**: Skip FrontEnd directory for now

4. **Test Data**: Use TestJSON directory for integration testing?
   - **Recommendation**: Yes - use for pytest fixtures

---

## Next Steps

1. **Immediate**: Start code integration (modify BackEnd and Optimizer)
2. **Test**: Local Docker Compose deployment
3. **CI/CD**: Set up GitHub Actions pipeline
4. **Deploy**: GCP staging environment
5. **Production**: European datacenter deployment

---

**Integration Owner**: TBD
**Target Completion**: TBD
**Blockers**: None identified
