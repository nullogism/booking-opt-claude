"""
Integration tests for BookingOpt end-to-end workflow
Requires Docker Compose services running
"""

import json
import time
from pathlib import Path

import pytest
import requests

# Base URL for the API
BASE_URL = "http://localhost"


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete job submission to result retrieval"""

    @pytest.fixture(autouse=True)
    def check_services(self):
        """Ensure services are running before tests"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.RequestException:
            pytest.skip("Docker Compose services not running")

    def test_submit_and_retrieve_job(self):
        """
        End-to-end test:
        1. Submit optimization job
        2. Poll for status
        3. Retrieve results
        """
        # Load test data
        test_data_path = Path(__file__).parent / "test_data" / "SampleInput_2 (1).json"
        with open(test_data_path) as f:
            test_data = json.load(f)

        # Step 1: Submit job
        response = requests.post(
            f"{BASE_URL}/api/v1/optimize",
            json=test_data,
            headers={"X-User-ID": "integration-test-user"}
        )

        assert response.status_code == 200
        job_data = response.json()
        assert "job_id" in job_data
        job_id = job_data["job_id"]

        # Step 2: Poll for status (max 60 seconds)
        max_polls = 60
        poll_interval = 1  # second

        for _ in range(max_polls):
            response = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}")
            assert response.status_code == 200

            status_data = response.json()
            status = status_data["status"]

            if status == "completed":
                # Step 3: Verify results
                assert "result" in status_data
                assert status_data["result"] is not None
                assert status_data["result"].get("success") is not None
                break
            elif status == "failed":
                pytest.fail(f"Job failed: {status_data.get('error')}")
            elif status in ["queued", "running"]:
                time.sleep(poll_interval)
            else:
                pytest.fail(f"Unknown job status: {status}")
        else:
            pytest.fail(f"Job did not complete within {max_polls} seconds")

    def test_rate_limiting(self):
        """Test that rate limiting prevents excessive job submissions"""
        test_data_path = Path(__file__).parent / "test_data" / "SampleInput_2 (1).json"
        with open(test_data_path) as f:
            test_data = json.load(f)

        # Submit 4 jobs rapidly (limit is 3 concurrent per user)
        job_ids = []
        rate_limited = False

        for _ in range(4):
            response = requests.post(
                f"{BASE_URL}/api/v1/optimize",
                json=test_data,
                headers={"X-User-ID": "rate-limit-test-user"}
            )

            if response.status_code == 429:
                rate_limited = True
                break
            elif response.status_code == 200:
                job_ids.append(response.json()["job_id"])

        # Should have been rate limited on 4th request
        assert rate_limited or len(job_ids) <= 3

    def test_job_cancellation(self):
        """Test canceling a pending job"""
        test_data_path = Path(__file__).parent / "test_data" / "SampleInput_2 (1).json"
        with open(test_data_path) as f:
            test_data = json.load(f)

        # Submit job
        response = requests.post(
            f"{BASE_URL}/api/v1/optimize",
            json=test_data,
            headers={"X-User-ID": "cancel-test-user"}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Try to cancel
        response = requests.delete(
            f"{BASE_URL}/api/v1/jobs/{job_id}",
            headers={"X-User-ID": "cancel-test-user"}
        )

        # Should succeed (200) or fail if already running (400)
        assert response.status_code in [200, 400]


@pytest.mark.integration
class TestNginxRateLimiting:
    """Test nginx layer rate limiting"""

    def test_nginx_rate_limit(self):
        """Test nginx rate limiting on optimize endpoint"""
        try:
            # Make rapid requests to trigger nginx rate limit (12/min, burst 3)
            # So 16 requests should trigger rate limiting
            responses = []
            for i in range(16):
                try:
                    response = requests.post(
                        f"{BASE_URL}/api/v1/optimize",
                        json={"test": "data"},
                        headers={"X-User-ID": f"nginx-test-{i}"},
                        timeout=2
                    )
                    responses.append(response.status_code)
                except requests.exceptions.Timeout:
                    pass

            # Should have at least one 429 (Too Many Requests)
            assert 429 in responses

        except requests.exceptions.RequestException:
            pytest.skip("Nginx not configured or services not running")
