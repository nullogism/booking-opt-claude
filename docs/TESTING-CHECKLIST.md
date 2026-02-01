# Testing Checklist - BookingOpt API

**Purpose**: Validation tests to run before deploying to any environment (staging, production, etc.)

**Last Updated**: 2026-02-01

---

## Phase 1: Smoke Tests (Manual - Critical)

These tests verify basic functionality and should be run after any deployment.

### ✅ Test 1: Health Check
**Purpose**: Verify API is responding
**Method**: GET
**Endpoint**: `/health`
**Expected**: 200 OK, response body: `OK`
**Status**: PASSED (2026-02-01)

### ✅ Test 2: Submit Optimization Job
**Purpose**: Verify job submission and queueing
**Method**: POST
**Endpoint**: `/api/v1/optimize`
**Headers**:
- `Content-Type: application/json`
- `X-User-ID: test-user`

**Test Data**: Use SampleInput_3.json (27 reservations, 5 rooms)
**Expected**:
- 200 OK
- Response contains `job_id`, `status: queued`, `problem_id`

**Status**: PASSED (2026-02-01)

### ✅ Test 3: Check Job Status
**Purpose**: Verify job processing and result retrieval
**Method**: GET
**Endpoint**: `/api/v1/jobs/{job_id}`
**Expected**:
- Initially: `status: queued` or `status: running`
- After completion: `status: completed`, `progress: 100`, `result.success: true`
- Result contains `OptimizedPlan` with room assignments

**Status**: PASSED (2026-02-01)

### ⏳ Test 4: Cancel Job (Pending)
**Purpose**: Verify job cancellation
**Method**: DELETE
**Endpoint**: `/api/v1/jobs/{job_id}`
**Headers**: `X-User-ID: test-user` (must match job creator)
**Expected**: 200 OK, job status changes to `cancelled`
**Status**: NOT YET TESTED

### ⏳ Test 5: Rate Limiting (Pending)
**Purpose**: Verify rate limiting protection
**Test Cases**:
1. **Nginx Rate Limit**: Submit 15+ requests to `/api/v1/optimize` rapidly
   - Expected: Some requests return 429 (Too Many Requests)
2. **Application Rate Limit**: Submit 4+ concurrent jobs with same user ID
   - Expected: 4th job returns 429

**Status**: NOT YET TESTED

---

## Phase 2: Functional Tests (Recommended)

### Test 6: Adjacency Group Handling
**Purpose**: Verify optimizer handles adjacency constraints
**Test Data**: Use SampleInput_4.json (contains AdjacencyGroup constraints)
**Expected**: Reservations with same AdjacencyGroup assigned to adjacent rooms
**Status**: NOT YET TESTED

### Test 7: Locked Room Assignments
**Purpose**: Verify optimizer respects pre-assigned rooms
**Test Data**: Use input with `IsLocked: true` reservations
**Expected**: Locked reservations remain in assigned rooms
**Status**: NOT YET TESTED

### Test 8: Minimum Stay Constraints
**Purpose**: Verify minimum stay requirements enforced
**Test Data**: Use input with varying `MinimumStay` and `MinimumStayByDay` values
**Expected**: All assignments respect minimum stay rules
**Status**: NOT YET TESTED

### Test 9: Invalid Input Handling
**Purpose**: Verify API validates input correctly
**Test Cases**:
1. Missing required fields (no `Rooms`)
2. Invalid date formats
3. Negative length values
4. Invalid JSON

**Expected**: 422 Unprocessable Entity with descriptive error
**Status**: NOT YET TESTED

### Test 10: Empty/Edge Cases
**Purpose**: Verify handling of edge cases
**Test Cases**:
1. Zero reservations
2. Zero rooms
3. More reservations than available room capacity
4. Single room, multiple reservations

**Expected**: Graceful handling or appropriate error
**Status**: NOT YET TESTED

---

## Phase 3: Performance Tests (Optional)

### Test 11: Large Problem Performance
**Purpose**: Verify performance with realistic workload
**Test Data**: 50+ reservations, 10+ rooms
**Expected**: Completes within 60 seconds
**Status**: NOT YET TESTED

### Test 12: Concurrent Job Processing
**Purpose**: Verify multiple jobs can be processed simultaneously
**Test**: Submit 10 jobs from different users
**Expected**: All jobs complete successfully, no interference
**Status**: NOT YET TESTED

### Test 13: Worker Scalability
**Purpose**: Verify horizontal scaling
**Test**: Scale workers to 3 instances, submit 20 jobs
**Expected**: Jobs distributed across workers, all complete
**Status**: NOT YET TESTED

---

## Phase 4: Integration Tests (Automated)

### Test 14: End-to-End Workflow
**Purpose**: Automated integration test
**Location**: `app/tests/test_integration.py`
**Coverage**:
- Service startup and health
- Job submission
- Job processing
- Result retrieval
- Rate limiting

**Status**: IMPLEMENTED (runs in CI/CD)

### Test 15: API Contract Tests
**Purpose**: Verify API response schemas
**Location**: `app/tests/test_api.py`
**Coverage**:
- Request validation (Pydantic models)
- Response format validation
- Error response formats

**Status**: IMPLEMENTED (runs in CI/CD)

---

## Phase 5: Security Tests (Critical for Production)

### Test 16: Authentication (Not Yet Implemented)
**Purpose**: Verify authentication is required
**Status**: DEFERRED - Currently using X-User-ID header (insecure)
**Required Before Production**: YES

### Test 17: Rate Limit Bypass Attempts
**Purpose**: Verify rate limiting can't be bypassed
**Test Cases**:
1. Different IP addresses
2. Different user IDs
3. Request header manipulation

**Status**: NOT YET TESTED

### Test 18: Input Injection
**Purpose**: Verify protection against injection attacks
**Test Cases**:
1. SQL injection attempts in input fields
2. Script injection in string fields
3. Path traversal attempts

**Expected**: Input sanitized or rejected
**Status**: NOT YET TESTED

---

## Phase 6: Reliability Tests (Production Readiness)

### Test 19: Service Recovery
**Purpose**: Verify services recover from failures
**Test Cases**:
1. Stop worker, submit job, start worker → job processes
2. Restart Redis → jobs resume
3. Restart API → no data loss

**Status**: NOT YET TESTED

### Test 20: Data Persistence
**Purpose**: Verify job results persist through restart
**Test**: Submit job, get result, restart services, retrieve result
**Expected**: Result available for 1 hour (TTL)
**Status**: NOT YET TESTED

### Test 21: Error Handling
**Purpose**: Verify graceful failure handling
**Test Cases**:
1. Infeasible optimization problem
2. Solver timeout/failure
3. Redis connection loss during job

**Expected**: Appropriate error returned, no crashes
**Status**: NOT YET TESTED

---

## Test Data Files

Available test datasets:
- `app/tests/test_data/SampleInput_1.json` - Simple case
- `app/tests/test_data/SampleInput_2 (1).json` - Medium complexity
- `booking-opt-prod/TestJSON/SampleInput_3.json` - 27 reservations, 5 rooms, locked assignments
- `booking-opt-prod/TestJSON/SampleInput_4.json` - 53 reservations, 9 rooms, adjacency groups

---

## Pre-Deployment Checklist

Before deploying to any environment, verify:

### Critical Tests (Must Pass)
- [ ] Test 1: Health Check
- [ ] Test 2: Submit Optimization Job
- [ ] Test 3: Check Job Status (with valid results)
- [ ] Test 14: Automated Integration Tests (CI/CD)
- [ ] Test 15: API Contract Tests (CI/CD)

### Recommended Tests
- [ ] Test 4: Cancel Job
- [ ] Test 5: Rate Limiting
- [ ] Test 6: Adjacency Groups
- [ ] Test 7: Locked Assignments
- [ ] Test 9: Invalid Input Handling

### Production-Only Tests
- [ ] Test 16: Authentication (implement first!)
- [ ] Test 17: Rate Limit Security
- [ ] Test 19: Service Recovery
- [ ] Test 20: Data Persistence

---

## Testing Tools

- **Manual Testing**: Postman, curl
- **Automated Testing**: pytest, GitHub Actions
- **Load Testing**: Not yet implemented (consider: locust, k6)
- **Security Testing**: Not yet implemented (consider: OWASP ZAP)

---

## Test Result Log

| Date | Environment | Tests Run | Pass | Fail | Notes |
|------|-------------|-----------|------|------|-------|
| 2026-02-01 | Local Docker | 1, 2, 3 | 3 | 0 | Phase 1 complete, optimizer working |

---

## Future Test Additions

Tests to add as features are implemented:
- [ ] Plotter/visualization output validation
- [ ] Authentication and authorization tests
- [ ] Multi-user concurrent access tests
- [ ] Long-running job timeout tests
- [ ] Webhook/callback notification tests (if added)
- [ ] Database migration tests (if PostgreSQL added)

---

**Maintainers**: Update this document as new tests are added or requirements change.
