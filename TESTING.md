# Testing Guide for BookingOpt

This document describes the testing strategy and how to run tests for the BookingOpt platform.

## Test Structure

```
app/tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_api.py              # Unit tests for API endpoints
├── test_integration.py      # End-to-end integration tests
├── test_data/               # Sample JSON test inputs
└── requirements.txt         # Testing dependencies
```

## Test Levels

### 1. Unit Tests (`test_api.py`)

**What**: Test individual API endpoints in isolation
**Requirements**: None (mocked dependencies)
**Speed**: Fast (<1s per test)

Tests:
- Health endpoint response
- Request validation (Pydantic models)
- Error handling
- Endpoint structure

Run unit tests:
```bash
pytest app/tests/test_api.py -v
```

### 2. Integration Tests (`test_integration.py`)

**What**: Test complete end-to-end workflow
**Requirements**: Docker Compose services running
**Speed**: Slow (30-60s per test)

Tests:
- Full job submission → processing → result retrieval
- Rate limiting (application layer)
- Job cancellation
- Nginx rate limiting

Run integration tests:
```bash
# Start services first
cd hotel-optimizer-infra
docker compose up -d

# Run tests
pytest app/tests/test_integration.py -v -m integration
```

### 3. Linting & Type Checking

**Linting (Ruff)**:
```bash
ruff check app/
```

**Formatting (Black)**:
```bash
# Check formatting
black --check app/

# Auto-format
black app/
```

**Type checking (MyPy)**:
```bash
mypy app/api app/worker
```

### 4. Security Testing

**Dependency scanning**:
```bash
pip install safety
safety check --file app/api/requirements.txt
safety check --file app/worker/requirements.txt
```

**Container scanning** (via Trivy):
```bash
trivy image bookingopt-api:latest
trivy image bookingopt-worker:latest
```

## Running Tests

### Quick Smoke Test

Test if the system is working end-to-end:

```bash
# Ensure services are running
cd hotel-optimizer-infra
docker compose up -d

# Run smoke test
bash ../scripts/quick-test.sh
```

### Full Test Suite

```bash
# Install dependencies
pip install -r app/tests/requirements.txt

# Run all tests
bash scripts/run-tests.sh --all
```

### Selective Testing

```bash
# Unit tests only
bash scripts/run-tests.sh

# Integration tests only
bash scripts/run-tests.sh --integration

# Linting only
bash scripts/run-tests.sh --lint

# Type checking only
bash scripts/run-tests.sh --type-check
```

### Manual Testing

```bash
# 1. Start services
cd hotel-optimizer-infra
docker compose up -d

# 2. Check health
curl http://localhost/health

# 3. Submit optimization job
curl -X POST http://localhost/api/v1/optimize \
  -H "Content-Type: application/json" \
  -H "X-User-ID: manual-test" \
  -d @app/tests/test_data/SampleInput_2\ \(1\).json

# 4. Get job status (replace JOB_ID)
curl http://localhost/api/v1/jobs/{JOB_ID}

# 5. View logs
docker compose logs -f api worker

# 6. Check Redis queue
docker compose exec redis redis-cli LLEN optimization
```

## CI/CD Pipeline

### GitHub Actions Workflow

The CI pipeline runs automatically on push/PR to `main`:

**Stages:**
1. **Lint & Type Check** - Ruff, Black, MyPy
2. **Unit Tests** - Fast API tests
3. **Build** - Docker images for API and Worker
4. **Integration Tests** - End-to-end with Docker Compose
5. **Security Scan** - Trivy vulnerability scanning

**Workflow file**: `.github/workflows/ci.yml`

**Local simulation**:
```bash
# Install act (GitHub Actions local runner)
# https://github.com/nektos/act

act -j lint
act -j unit-tests
act -j build
```

## Test Data

Sample inputs in `app/tests/test_data/`:
- `SampleInput_1.json` - Basic test case
- `SampleInput_2 (1).json` - Standard test case
- `SampleInput_3.json` - Complex scenario
- `SampleInput_4.json` - Edge case

All test data follows the format:
```json
{
  "ProblemId": "...",
  "MinimumStay": 5.0,
  "Reservations": [...],
  "NewReservations": [],
  "MinimumStayByDay": {}
}
```

## Writing Tests

### Unit Test Template

```python
def test_my_feature():
    """Test description"""
    # Arrange
    test_data = {...}

    # Act
    response = client.post("/api/v1/optimize", json=test_data)

    # Assert
    assert response.status_code == 200
    assert "job_id" in response.json()
```

### Integration Test Template

```python
@pytest.mark.integration
def test_my_integration():
    """Test description"""
    # Submit job
    response = requests.post(f"{BASE_URL}/api/v1/optimize", ...)
    job_id = response.json()["job_id"]

    # Poll for result
    # ... polling logic ...

    # Verify result
    assert result["success"] is True
```

## Troubleshooting

### "Services not running" error

```bash
cd hotel-optimizer-infra
docker compose up -d
docker compose ps  # Check all services are healthy
```

### "Redis connection refused"

```bash
docker compose logs redis  # Check Redis logs
docker compose restart redis
```

### "Job timeout in tests"

Increase timeout in test or check worker logs:
```bash
docker compose logs worker
```

### "Import errors in tests"

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in editable mode
pip install -e .
```

## Coverage Reports

Generate coverage report:
```bash
pytest app/tests/ --cov=app/api --cov=app/worker --cov-report=html

# View report
open htmlcov/index.html
```

## Performance Testing

### Load Testing (Optional)

Use `locust` for load testing:

```bash
pip install locust

# Create locustfile.py
# Run: locust -f locustfile.py --host=http://localhost
```

## Best Practices

1. **Test isolation**: Each test should be independent
2. **Fast unit tests**: Keep unit tests under 1s each
3. **Descriptive names**: Use clear, descriptive test names
4. **Fixtures**: Use pytest fixtures for common setup
5. **Markers**: Tag tests appropriately (`@pytest.mark.integration`)
6. **Assertions**: One logical assertion per test
7. **Cleanup**: Use fixtures with `yield` for cleanup

## Next Steps

- [ ] Add performance/load tests
- [ ] Add test for plotter integration (when implemented)
- [ ] Increase test coverage to >80%
- [ ] Add mutation testing (optional)
- [ ] Add contract testing for API (optional)
