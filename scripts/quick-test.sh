#!/bin/bash
# Quick smoke test for BookingOpt

set -e

echo "🧪 Quick Smoke Test for BookingOpt"
echo "==================================="

# Check if services are running
if ! curl -s http://localhost/health > /dev/null 2>&1; then
    echo "❌ Services not running. Please start with:"
    echo "   cd hotel-optimizer-infra && docker compose up -d"
    exit 1
fi

echo "✅ Health check passed"

# Submit test job
echo "📤 Submitting test optimization job..."
RESPONSE=$(curl -s -X POST http://localhost/api/v1/optimize \
  -H "Content-Type: application/json" \
  -H "X-User-ID: smoke-test" \
  -d @app/tests/test_data/SampleInput_2\ \(1\).json)

JOB_ID=$(echo $RESPONSE | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
    echo "❌ Failed to submit job"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "✅ Job submitted: $JOB_ID"

# Poll for result
echo "⏳ Waiting for job to complete..."
MAX_WAIT=60
COUNTER=0

while [ $COUNTER -lt $MAX_WAIT ]; do
    STATUS_RESPONSE=$(curl -s http://localhost/api/v1/jobs/$JOB_ID)
    STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

    if [ "$STATUS" = "completed" ]; then
        echo "✅ Job completed successfully!"
        echo "Result: $STATUS_RESPONSE" | jq . 2>/dev/null || echo "$STATUS_RESPONSE"
        exit 0
    elif [ "$STATUS" = "failed" ]; then
        echo "❌ Job failed"
        echo "Response: $STATUS_RESPONSE"
        exit 1
    fi

    echo "  Status: $STATUS (${COUNTER}s elapsed)"
    sleep 2
    COUNTER=$((COUNTER + 2))
done

echo "⏱️ Job did not complete within ${MAX_WAIT}s"
echo "Last status: $STATUS_RESPONSE"
exit 1
