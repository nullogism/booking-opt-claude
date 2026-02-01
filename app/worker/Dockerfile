# BookingOpt Worker Service
FROM python:3.11-slim

# Install system dependencies for scipy/numpy compilation
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY worker.py .

# Copy optimizer modules
COPY optimizer/ optimizer/

# Set Python path
ENV PYTHONPATH=/app

# Run worker
CMD ["python", "worker.py"]
