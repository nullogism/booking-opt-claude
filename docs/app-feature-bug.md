# Application Features & Bugs

**Last Updated**: 2026-01-31

Track application-level development tasks, features, bugs, and technical debt.

## Status Legend

- `[ ]` Not Started
- `[~]` In Progress
- `[x]` Completed
- `[!]` Blocked
- `[?]` Needs Discussion

## Priority Levels

- **P0**: Critical - Blocks deployment
- **P1**: High - Required for MVP
- **P2**: Medium - Important but not blocking
- **P3**: Low - Nice to have

---

## Phase 1: Foundation & Core Integration

### P0 - Critical Path Items

#### Application Containerization
- [ ] **Create Dockerfile for Python optimizer** (P0)
  - Base image: python:3.11-slim or alpine
  - Install dependencies from requirements.txt
  - Expose port 8000
  - Health check endpoint
  - **Blockers**: None
  - **Assignee**: TBD
  - **Estimated Effort**: 2-3 hours

- [ ] **Create requirements.txt** (P0)
  - fastapi>=0.104.0
  - uvicorn[standard]>=0.24.0
  - redis>=5.0.0
  - rq>=1.15.0
  - pydantic>=2.0.0
  - python-dotenv
  - [Your existing optimizer dependencies]
  - **Blockers**: Need to audit existing optimizer dependencies
  - **Assignee**: TBD

#### Job Queue Integration
- [ ] **Integrate job_queue.py into application** (P0)
  - Copy job_queue.py into app/ directory
  - Modify run_optimization_task() to call actual optimizer
  - Test Redis connectivity
  - Verify job submission and retrieval
  - **Blockers**: Need to understand current optimizer code structure
  - **Assignee**: TBD
  - **Estimated Effort**: 4-6 hours

- [ ] **Create FastAPI application entry point** (P0)
  - Create app/main.py based on example_api.py
  - Implement POST /api/v1/optimize endpoint
  - Implement GET /api/v1/jobs/{job_id} endpoint
  - Implement GET /health endpoint
  - Add CORS middleware for frontend integration
  - **Blockers**: Depends on job queue integration
  - **Assignee**: TBD
  - **Estimated Effort**: 3-4 hours

#### Worker Process Setup
- [ ] **Configure worker entry point** (P0)
  - Add worker command to Dockerfile
  - Verify WORKER_MODE environment variable handling
  - Test job processing from queue
  - **Blockers**: Depends on job queue integration
  - **Assignee**: TBD
  - **Estimated Effort**: 2 hours

### P1 - Required for MVP

#### API Enhancements
- [ ] **Implement request validation** (P1)
  - Pydantic models for all endpoints
  - Date range validation
  - Hotel ID format validation
  - Room type enumeration
  - **Assignee**: TBD

- [ ] **Add DELETE /api/v1/jobs/{job_id} endpoint** (P1)
  - Cancel pending jobs
  - Verify user ownership
  - Return appropriate error codes
  - **Assignee**: TBD

- [ ] **Implement authentication** (P1)
  - Replace X-User-ID header with proper auth
  - JWT tokens or API keys
  - User verification middleware
  - **Blockers**: Need to align with frontend auth strategy
  - **Assignee**: TBD
  - **Status**: `[?]` Needs discussion with frontend team

#### Error Handling
- [ ] **Robust error handling** (P1)
  - Try/catch in all endpoints
  - Structured error responses
  - Error logging without PII
  - Graceful degradation
  - **Assignee**: TBD

- [ ] **Job timeout handling** (P1)
  - Detect stalled jobs
  - Cleanup expired results
  - User-friendly timeout messages
  - **Assignee**: TBD

#### Configuration Management
- [ ] **Environment-based configuration** (P1)
  - Load .env file in application
  - Override with environment variables
  - Configuration validation on startup
  - **Assignee**: TBD

### P2 - Important Enhancements

#### Observability
- [ ] **Structured logging** (P2)
  - JSON log format
  - Log levels (DEBUG, INFO, WARNING, ERROR)
  - Request ID tracking
  - Performance metrics logging
  - **Assignee**: TBD

- [ ] **Metrics endpoint** (P2)
  - GET /metrics (Prometheus format optional)
  - Job queue depth
  - Processing times (p50, p95, p99)
  - Error rates
  - **Assignee**: TBD

#### Job Management
- [ ] **Job result pagination** (P2)
  - List jobs for a user
  - Filter by status, date range
  - Limit and offset parameters
  - **Assignee**: TBD

- [ ] **Job priority levels** (P2)
  - High/normal/low priority queues
  - Priority parameter in submit endpoint
  - Separate workers for priority queues
  - **Blockers**: `[?]` Is this needed for MVP?
  - **Assignee**: TBD

#### Performance
- [ ] **Database for job metadata** (P2)
  - PostgreSQL or SQLite for job history
  - Query job history beyond Redis TTL
  - Analytics on job patterns
  - **Blockers**: `[?]` Current Redis TTL sufficient?
  - **Assignee**: TBD

- [ ] **Optimization algorithm caching** (P2)
  - Cache results for identical inputs
  - TTL-based cache invalidation
  - Cache hit rate metrics
  - **Assignee**: TBD

### P3 - Nice to Have

- [ ] **Batch job submission** (P3)
  - Submit multiple hotels in one request
  - Batch status endpoint
  - **Assignee**: TBD

- [ ] **Scheduled jobs (cron-like)** (P3)
  - Start-of-day report generation
  - Periodic optimization runs
  - APScheduler or similar
  - **Assignee**: TBD

- [ ] **API versioning strategy** (P3)
  - /api/v2/ support
  - Deprecation notices
  - **Assignee**: TBD

- [ ] **OpenAPI documentation** (P3)
  - FastAPI auto-generated docs
  - Custom descriptions and examples
  - Available at /docs endpoint
  - **Assignee**: TBD

---

## Testing Requirements

### Unit Tests
- [ ] **Test optimization algorithm** (P1)
  - Input validation
  - Output format verification
  - Edge cases (empty input, invalid dates)
  - **Assignee**: TBD

- [ ] **Test job queue functions** (P1)
  - enqueue_optimization()
  - get_job_status()
  - cancel_job()
  - Rate limiting logic
  - **Assignee**: TBD

- [ ] **Test API endpoints** (P1)
  - POST /api/v1/optimize
  - GET /api/v1/jobs/{job_id}
  - DELETE /api/v1/jobs/{job_id}
  - Error cases (400, 404, 429)
  - **Assignee**: TBD

### Integration Tests
- [ ] **End-to-end job flow** (P1)
  - Submit job → queue → worker → result retrieval
  - Test with real Redis instance
  - Verify cleanup after completion
  - **Assignee**: TBD

- [ ] **Rate limiting behavior** (P1)
  - Verify 3 concurrent jobs per user limit
  - Test queue bursting
  - Verify 429 responses
  - **Assignee**: TBD

- [ ] **Docker Compose integration** (P1)
  - docker-compose up -d
  - All services healthy
  - Communication between services
  - **Assignee**: TBD

### Performance Tests
- [ ] **Load testing** (P2)
  - 10 concurrent job submissions
  - Measure queue processing time
  - Identify bottlenecks
  - **Tool**: locust, k6, or ab
  - **Assignee**: TBD

- [ ] **Stress testing** (P2)
  - Exceed rate limits intentionally
  - Test system under overload
  - Verify graceful degradation
  - **Assignee**: TBD

---

## Known Bugs

### Critical Bugs (Fix Immediately)
_None currently - new deployment_

### High Priority Bugs
_None currently_

### Medium Priority Bugs
_None currently_

### Low Priority Bugs
_None currently_

---

## Technical Debt

- [ ] **Replace placeholder authentication** (P1)
  - Current: X-User-ID header (insecure)
  - Target: JWT or API key authentication
  - **Impact**: Security risk in production

- [ ] **Add input sanitization** (P1)
  - Validate all user inputs
  - Prevent injection attacks
  - **Impact**: Security risk

- [ ] **Improve error messages** (P2)
  - User-friendly error descriptions
  - Avoid exposing internal details
  - **Impact**: Developer experience

---

## Questions & Decisions Needed

1. **Authentication Strategy**: What auth method does the frontend use?
   - JWT tokens?
   - API keys?
   - OAuth?
   - **Status**: `[?]` Waiting for frontend team input

2. **Database for Job History**: Do we need persistent job history beyond 1 hour?
   - Current: Redis with 1-hour TTL
   - Alternative: PostgreSQL for long-term storage
   - **Status**: `[?]` To be decided based on user requirements

3. **Scheduled Jobs**: Do we need start-of-day reports?
   - If yes, implement scheduler service
   - **Status**: `[?]` Mentioned in original chat, needs confirmation

4. **Frontend Integration**: CORS origins to allow?
   - Need production frontend domain
   - **Status**: `[?]` Waiting for frontend deployment info

---

## Completed Items

_Items will be moved here as they are completed_

---

## Notes

- Focus on P0 items first - they block deployment
- P1 items required for production-ready MVP
- P2/P3 can be deferred to post-MVP iterations
- Update this doc as new issues are discovered
- Link GitHub issues here when repository is created

**Next Review Date**: TBD
