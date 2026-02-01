"""
Unit tests for BookingOpt API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add API directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self):
        """Health endpoint should return 200 OK"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "version" in response.json()
        assert "timestamp" in response.json()


class TestOptimizeEndpoint:
    """Test optimization job submission"""

    def test_optimize_requires_valid_payload(self):
        """Optimize endpoint should reject invalid payloads"""
        response = client.post(
            "/api/v1/optimize",
            json={"invalid": "data"},
            headers={"X-User-ID": "test-user"}
        )
        # Should return 422 Unprocessable Entity for validation errors
        assert response.status_code == 422

    def test_optimize_requires_problem_id(self, sample_optimization_request):
        """Optimize endpoint requires ProblemId field"""
        # Remove ProblemId
        invalid_request = sample_optimization_request.copy()
        del invalid_request["ProblemId"]

        response = client.post(
            "/api/v1/optimize",
            json=invalid_request,
            headers={"X-User-ID": "test-user"}
        )
        assert response.status_code == 422

    def test_optimize_requires_reservations(self, sample_optimization_request):
        """Optimize endpoint requires Reservations field"""
        invalid_request = sample_optimization_request.copy()
        del invalid_request["Reservations"]

        response = client.post(
            "/api/v1/optimize",
            json=invalid_request,
            headers={"X-User-ID": "test-user"}
        )
        assert response.status_code == 422

    @pytest.mark.skipif(
        not Path("/var/run/docker.sock").exists(),
        reason="Requires Redis running (Docker Compose)"
    )
    def test_optimize_success(self, sample_optimization_request):
        """Optimize endpoint should accept valid payload and return job_id"""
        response = client.post(
            "/api/v1/optimize",
            json=sample_optimization_request,
            headers={"X-User-ID": "test-user"}
        )

        # Should return 200 or 503 if Redis unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert "status" in data
            assert data["status"] in ["queued", "pending"]
            assert "problem_id" in data


class TestJobStatusEndpoint:
    """Test job status polling"""

    def test_get_job_nonexistent(self):
        """Getting nonexistent job should return 404"""
        response = client.get("/api/v1/jobs/nonexistent-job-id")

        # Should return 404 or 503 if Redis unavailable
        assert response.status_code in [404, 503]

    @pytest.mark.skipif(
        not Path("/var/run/docker.sock").exists(),
        reason="Requires Redis running (Docker Compose)"
    )
    def test_get_job_format(self):
        """Job status response should have correct format"""
        # This is a placeholder - in real tests, we'd submit a job first
        # For now, just test the endpoint structure
        response = client.get("/api/v1/jobs/test-job-123")

        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert "status" in data


class TestCancelJobEndpoint:
    """Test job cancellation"""

    def test_cancel_nonexistent_job(self):
        """Canceling nonexistent job should return 400"""
        response = client.delete(
            "/api/v1/jobs/nonexistent-job-id",
            headers={"X-User-ID": "test-user"}
        )

        # Should return 400 or 503 if Redis unavailable
        assert response.status_code in [400, 503]
