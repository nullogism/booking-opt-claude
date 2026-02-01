# RESTART INSTRUCTIONS - BookingOpt Testing Session

**Last Updated**: 2026-01-31
**Session Status**: Ready for Docker Desktop Testing
**Next Claude Instance**: Start here to pick up where we left off

## 🎯 Current Project State

### What's Been Completed ✅

1. **Hybrid Integration Complete** (Commit: 0e9b6be)
   - API service: FastAPI with Redis Queue integration
   - Worker service: RQ Worker with scipy-based optimizer
   - Core optimizer modules copied from BookingOpt-Prod
   - Docker Compose configuration updated
   - All infrastructure in place

2. **Testing Infrastructure Complete** (Commit: 2e73a53)
   - Unit tests (pytest) for API endpoints
   - Integration tests for end-to-end workflows
   - GitHub Actions CI/CD pipeline
   - Linting (Ruff), formatting (Black), type checking (MyPy)
   - Helper scripts (run-tests.sh, quick-test.sh)
   - Comprehensive TESTING.md documentation

3. **Repository Status**
   - GitHub: https://github.com/nullogism/booking-opt-claude.git
   - Branch: main
   - All code committed and pushed
   - CI/CD workflow ready (will run on next push)

### What's Pending ⏳

1. **Docker Desktop Installation** (User restarting computer)
2. **Local Docker Build Testing** - PRIMARY NEXT TASK
3. **End-to-End Job Testing** - Verify optimizer produces valid results
4. **Visualization Validation** - Confirm booking arrangement outputs are correct
5. **CI/CD Practice Deployment** - Deploy to VM in datacenter

## 📋 Architecture Overview

```
Internet → Nginx:80 → API:8000 → Redis:6379 → Worker (Scipy Optimizer)
                                                  ↓
                                          SolverRunner.Run()
                                                  ↓
                                        Room Assignment Results
```

**Key Files:**
- `app/api/main.py` - FastAPI REST API
- `app/worker/worker.py` - RQ worker that calls optimizer
- `app/worker/optimizer/SolverRunner.py` - Core optimization logic
- `hotel-optimizer-infra/docker-compose.yml` - Service orchestration
- `app/tests/test_data/` - Sample JSON inputs

**Input Format:**
```json
{
  "ProblemId": "...",
  "MinimumStay": 5.0,
  "Reservations": [{"Name": "1", "Arrival": "2026-02-20", "Length": 9.0, ...}],
  "NewReservations": [],
  "MinimumStayByDay": {}
}
```

## 🚀 IMMEDIATE NEXT STEPS

### Step 1: Verify Docker Desktop

```powershell
# User should run after restart
docker --version
docker compose version
```

Expected: Docker version 24.x.x, Compose v2.x.x

### Step 2: Build Docker Images (5-10 minutes)

```powershell
cd c:\Users\benh6\OneDrive\Desktop\greeks\hotel-optimizer-infra
docker compose build
```

**Watch for:**
- ✅ API image builds successfully
- ✅ Worker image builds (scipy compilation takes longest)
- ❌ Errors related to scipy dependencies (gcc, gfortran, libopenblas)
- ❌ Import errors in optimizer modules

**If Build Fails:**
- Check `app/worker/Dockerfile` - ensure build dependencies installed
- Check `app/worker/requirements.txt` - scipy version compatibility
- Check `app/worker/optimizer/` - all modules copied correctly
- Verify import paths in `worker.py` (line 13: `from optimizer import SolverRunner`)

### Step 3: Start Services

```powershell
docker compose up -d
```

**Verify all 4 containers running:**
```powershell
docker compose ps
```

Expected output:
```
NAME                    STATUS
nginx                   Up (healthy)
api                     Up (healthy)
worker                  Up
redis                   Up (healthy)
```

### Step 4: Test Health Endpoint

```powershell
curl http://localhost/health
```

Expected:
```json
{"status":"healthy","version":"1.0.0","timestamp":"..."}
```

### Step 5: Submit Test Optimization Job

```powershell
# Load test data
$testData = Get-Content "c:\Users\benh6\OneDrive\Desktop\greeks\app\tests\test_data\SampleInput_2 (1).json" -Raw

# Submit job
$response = Invoke-RestMethod -Method Post `
  -Uri "http://localhost/api/v1/optimize" `
  -Headers @{"Content-Type"="application/json"; "X-User-ID"="test-session"} `
  -Body $testData

# Extract job ID
$jobId = $response.job_id
Write-Host "Job ID: $jobId"
Write-Host "Status: $($response.status)"
Write-Host "Problem ID: $($response.problem_id)"
```

### Step 6: Poll for Results

```powershell
# Poll every 2 seconds
for ($i = 0; $i -lt 60; $i++) {
    $status = Invoke-RestMethod -Uri "http://localhost/api/v1/jobs/$jobId"
    Write-Host "[$i] Status: $($status.status)"

    if ($status.status -eq "completed") {
        Write-Host "SUCCESS! Result:"
        $status | ConvertTo-Json -Depth 10
        break
    }
    elseif ($status.status -eq "failed") {
        Write-Host "FAILED! Error:"
        $status.error
        break
    }

    Start-Sleep -Seconds 2
}
```

### Step 7: Examine Results

**Critical Validation Points:**
1. ✅ Job completes (not stuck in "queued" or "running")
2. ✅ `status.result.success` is `true`
3. ✅ `status.result.result` contains optimization output
4. ✅ Room assignments are valid (all reservations assigned)
5. ✅ No constraint violations

**If Job Fails:**
```powershell
# Check worker logs
docker compose logs worker

# Check API logs
docker compose logs api

# Check Redis queue
docker compose exec redis redis-cli LLEN optimization
docker compose exec redis redis-cli LRANGE optimization 0 -1
```

## 🔍 What to Validate

### 1. Optimizer Functionality

**Expected Result Structure:**
```json
{
  "success": true,
  "result": {
    "ProblemId": "2222",
    "assignments": [...],
    "objective_value": ...,
    "solver_status": "optimal"
  },
  "problem_id": "2222"
}
```

**Validation Checklist:**
- [ ] All reservations from input are assigned
- [ ] Room assignments respect constraints (MinimumStay, etc.)
- [ ] No double-bookings (same room, overlapping dates)
- [ ] Adjacency groups handled correctly
- [ ] Solver reports "optimal" or "feasible" status

### 2. Visualization (Future)

**Note**: Plotter function was deferred (see `docs/integration-plan.md`)
- Original GCP had `optimize-plotter-function` for PNG generation
- Currently: Return JSON results only
- Future: Integrate plotter into worker (optional output)

**If you need to add plotter:**
- Copy `booking-opt-prod/optimize-plotter-function/` modules
- Integrate into `app/worker/worker.py` after optimization
- Generate PNG, encode as base64, include in result

### 3. Rate Limiting

**Test nginx rate limiting (12 req/min):**
```powershell
# Submit 15 rapid requests
for ($i = 0; $i -lt 15; $i++) {
    try {
        Invoke-RestMethod -Method Post -Uri "http://localhost/api/v1/optimize" `
          -Headers @{"Content-Type"="application/json"; "X-User-ID"="rate-test-$i"} `
          -Body $testData
        Write-Host "Request $i: Success"
    }
    catch {
        Write-Host "Request $i: RATE LIMITED (429)"
    }
}
```

Expected: Some requests return 429 Too Many Requests

**Test application rate limiting (3 concurrent jobs/user):**
```powershell
# Submit 4 jobs with same user ID
# 4th should be rate limited
```

## 🧪 Testing Workflows

### Unit Tests (No Docker Required)

```bash
cd c:\Users\benh6\OneDrive\Desktop\greeks
pip install -r app/tests/requirements.txt
pytest app/tests/test_api.py -v
```

### Integration Tests (Requires Docker Running)

```bash
pytest app/tests/test_integration.py -v -m integration
```

### Quick Smoke Test

```bash
bash scripts/quick-test.sh
```

## 🏗️ CI/CD Next Steps

Once local testing passes:

### 1. Verify GitHub Actions Pipeline

- Push any changes: `git push origin main`
- Check Actions tab: https://github.com/nullogism/booking-opt-claude/actions
- Pipeline should run: Lint → Unit Test → Build → Integration Test → Security

### 2. Create Deployment Workflow

**File**: `.github/workflows/deploy.yml`

**Stages:**
1. Build and tag images with version
2. Push to container registry (GHCR or Docker Hub)
3. SSH to target VM
4. Pull images and restart services
5. Run smoke tests
6. Rollback on failure

### 3. Target VM Setup

**Requirements:**
- Debian 11+ VM in European datacenter
- Docker + Docker Compose installed
- SSH access configured
- Domain name (for SSL)

**Deployment command:**
```bash
# On VM
cd /opt/booking-opt-claude
git pull origin main
cd hotel-optimizer-infra
docker compose pull
docker compose up -d
```

## 🐛 Known Issues / Watch For

### Issue 1: Scipy Import Errors
**Symptom**: Worker fails with `ImportError: libopenblas.so.0`
**Fix**: Check `app/worker/Dockerfile` build dependencies (lines 9-14)

### Issue 2: SolverRunner Import Path
**Symptom**: `ModuleNotFoundError: No module named 'optimizer'`
**Fix**: Check `app/worker/worker.py` line 13 and PYTHONPATH

### Issue 3: Job Hangs in "queued"
**Symptom**: Job never gets picked up by worker
**Causes:**
- Worker not running: `docker compose logs worker`
- Redis connection issue: `docker compose logs redis`
- Worker crashed: Check for exceptions in logs

### Issue 4: Optimization Fails (success=false)
**Symptom**: Job completes but `result.success` is `false`
**Causes:**
- Infeasible problem (constraints too strict)
- Scipy solver error (check `result.details`)
- Input validation failed in SolverRunner

## 📚 Key Documentation

- **[README.md](../README.md)** - Quick start guide
- **[TESTING.md](../TESTING.md)** - Complete testing documentation
- **[docs/integration-plan.md](integration-plan.md)** - GCP → Redis migration details
- **[docs/app-feature-bug.md](app-feature-bug.md)** - Application task tracking
- **[docs/infra-feature-bug.md](infra-feature-bug.md)** - Infrastructure task tracking

## 💬 User Context

**User**: Ben Hartman (benh6@nullogism.com)
**Company**: nullogism
**Project**: Hotel room booking optimization
**Traffic**: 1-2 operators, low volume
**Budget**: $25-50/month
**Target**: European datacenter deployment
**GDPR**: EU data residency required

**Original System (GCP):**
- Cloud Storage + Pub/Sub + Cloud Functions
- Worked but expensive for low traffic
- Custom scippy base image

**New System (This Project):**
- Redis Queue instead of Pub/Sub
- Redis storage instead of GCS
- Standard scipy from PyPI
- Portable (runs anywhere with Docker)

## ✅ Success Criteria

Before considering testing complete:

1. [ ] Docker images build without errors
2. [ ] All 4 services start and report healthy
3. [ ] API `/health` endpoint responds
4. [ ] Can submit optimization job
5. [ ] Worker picks up and processes job
6. [ ] Job completes with `success: true`
7. [ ] Results contain valid room assignments
8. [ ] Rate limiting works (nginx + application)
9. [ ] Integration tests pass
10. [ ] CI/CD pipeline passes on GitHub

## 🚦 Next Session Start Commands

```powershell
# 1. Open project
cd c:\Users\benh6\OneDrive\Desktop\greeks

# 2. Check Docker
docker --version

# 3. Build images
cd hotel-optimizer-infra
docker compose build

# 4. Start services
docker compose up -d

# 5. Test health
curl http://localhost/health

# 6. Submit test job (see Step 5 above for full command)
```

## 📝 Notes for Next Claude Instance

- User has Windows with WSL2 and Docker Desktop
- Repository: https://github.com/nullogism/booking-opt-claude.git
- All code is committed and pushed
- Testing infrastructure is complete but untested
- Primary blocker was Docker Desktop installation (user restarting)
- Focus on **validation of optimizer outputs** - this is critical
- Plotter function deferred to Phase 2 (docs/app-feature-bug.md)
- User wants to practice VM deployment after local testing

**Last User Message**: "test docker builds locally and test the workflows to confirm that viable outputs are being served by the optimizer function and we're getting valid hotel booking arrangement plots. Then, we should thoughtfully construct our CI/CD in GitHub Actions, so that we can practice deploying this whole application to a virtual machine in any datacenter."

---

**When User Returns**: Start with Step 1 (Verify Docker Desktop) and proceed through testing steps sequentially.
