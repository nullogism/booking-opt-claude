"""
Pytest configuration and fixtures for BookingOpt tests
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def test_data_dir():
    """Path to test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_optimization_request(test_data_dir):
    """Load sample optimization request from test data"""
    sample_file = test_data_dir / "SampleInput_2 (1).json"
    with open(sample_file) as f:
        return json.load(f)


@pytest.fixture
def sample_problem_id():
    """Sample problem ID for testing"""
    return "test_problem_123"
