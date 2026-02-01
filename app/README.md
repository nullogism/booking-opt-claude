# BookingOpt Application

This directory contains the application code for the hotel room optimization service.

## Structure

```
app/
├── api/                    # FastAPI service
│   ├── main.py            # API endpoints
│   ├── job_queue.py       # Redis Queue integration
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # API container build
│
├── worker/                # Optimization worker
│   ├── worker.py          # RQ worker process
│   ├── optimizer/         # Core optimization modules (from BookingOpt-Prod)
│   │   ├── SolverRunner.py
│   │   ├── Data/
│   │   ├── Models/
│   │   └── ...
│   ├── requirements.txt   # Worker dependencies (includes scipy)
│   └── Dockerfile         # Worker container build
│
└── tests/
    └── test_data/         # Sample JSON inputs for testing
```

## Services

### API Service (Port 8000)

FastAPI-based REST API for job submission and status polling.

**Endpoints:**
- `POST /api/v1/optimize` - Submit optimization job
- `GET /api/v1/jobs/{job_id}` - Get job status and results
- `DELETE /api/v1/jobs/{job_id}` - Cancel pending job
- `GET /health` - Health check

**Environment Variables:**
- `REDIS_URL` - Redis connection string (default: redis://redis:6379/0)
- `API_HOST` - Bind host (default: 0.0.0.0)
- `API_PORT` - Bind port (default: 8000)
- `MAX_QUEUED_JOBS_PER_USER` - Rate limit (default: 3)
- `JOB_RESULT_TTL` - Result expiration in seconds (default: 3600)

### Worker Service

RQ worker that processes optimization jobs from Redis queue.

**Key Features:**
- Imports core optimizer modules from `optimizer/`
- Calls `SolverRunner.Run()` with problem data
- Updates job progress in Redis
- Handles errors gracefully

**Environment Variables:**
- `REDIS_URL` - Redis connection string
- `MAX_JOB_DURATION` - Job timeout in seconds (default: 120)

## Dependencies

### API
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- redis>=5.0.0
- rq>=1.15.0
- pydantic>=2.0.0

### Worker
- redis>=5.0.0
- rq>=1.15.0
- numpy>=1.24.0
- scipy>=1.11.0

## Building Images

From the `hotel-optimizer-infra/` directory:

```bash
# Build API image
docker build -t bookingopt-api:latest ../app/api

# Build Worker image
docker build -t bookingopt-worker:latest ../app/worker

# Or use docker-compose to build both
docker-compose build
```

## Testing

Sample test data is available in `tests/test_data/`.

Example request:
```bash
curl -X POST http://localhost/api/v1/optimize \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -d @app/tests/test_data/SampleInput_2\ \(1\).json
```

## Input Format

The optimizer expects JSON payloads with this structure:

```json
{
  "ProblemId": "unique_id",
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
```

## Optimizer Modules

The `worker/optimizer/` directory contains the core optimization logic from BookingOpt-Prod:

- **SolverRunner.py** - Main optimization entry point
- **Data/** - Data models (Assignment, ProblemData, Reservation, Room)
- **Models/** - Optimization models
- **FixedPlanRestrictions/** - Constraint handling
- **SolverData/** - Solver utilities

These modules use scipy for linear programming and optimization calculations.

## Development

To modify the API:
1. Edit `api/main.py`
2. Rebuild: `docker-compose build api`
3. Restart: `docker-compose up -d api`

To modify the worker:
1. Edit `worker/worker.py` or optimizer modules
2. Rebuild: `docker-compose build worker`
3. Restart: `docker-compose up -d worker`

## Scaling Workers

To handle higher job volumes:

```bash
docker-compose up -d --scale worker=3
```

This will start 3 worker containers, all processing from the same Redis queue.
