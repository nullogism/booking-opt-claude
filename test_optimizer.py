import requests
import json
import time

# Load test data
with open("booking-opt-prod/TestJSON/SampleInput_3.json") as f:
    test_data = json.load(f)

print("=" * 60)
print("Testing Merged Optimizer with SampleInput_3.json")
print("=" * 60)

# Submit optimization job
response = requests.post(
    "http://localhost/api/v1/optimize",
    json=test_data,
    headers={"X-User-ID": "test-user", "Content-Type": "application/json"}
)

print(f"\n📤 Submit Status: {response.status_code}")
if response.status_code != 200:
    print(f"❌ Failed to submit job: {response.text}")
    exit(1)

job_data = response.json()
print(f"Job ID: {job_data['job_id']}")
print(f"Status: {job_data['status']}")

job_id = job_data["job_id"]

# Poll for completion
print("\n⏳ Polling for completion...")
for i in range(30):
    time.sleep(2)
    status_response = requests.get(f"http://localhost/api/v1/jobs/{job_id}")
    job_status = status_response.json()

    status_str = job_status['status']
    print(f"  [{i+1}/30] Status: {status_str}", end="")
    if "progress" in job_status and job_status["progress"]:
        print(f" ({job_status['progress']}%)", end="")
    print()

    if job_status["status"] == "completed":
        print("\n" + "=" * 60)
        print("✅ JOB COMPLETED SUCCESSFULLY!")
        print("=" * 60)

        # Check for new fields from merged optimizer
        if "result" in job_status and job_status["result"]:
            result = job_status["result"]

            print("\n📊 Checking for new optimizer fields:")
            print(f"  InitialMinStays:     {'✅' if 'InitialMinStays' in result else '❌'}")
            print(f"  QualityComparison:   {'✅' if 'QualityComparison' in result else '❌'}")
            print(f"  StaysAvoidedByCa:    {'✅' if 'StaysAvoidedByCa' in result else '❌'}")
            print(f"  StaysAvoidedByCd:    {'✅' if 'StaysAvoidedByCd' in result else '❌'}")
            print(f"  StaysAvoidedByMax:   {'✅' if 'StaysAvoidedByMax' in result else '❌'}")

            if 'QualityComparison' in result and result['QualityComparison']:
                print(f"\n📈 Quality Comparison (Before vs After):")
                print(json.dumps(result['QualityComparison'], indent=2))

            if 'StaysAvoidedByCa' in result:
                print(f"\n🚫 Restriction Impact:")
                print(f"  Stays avoided by ClosedArrivals:   {result.get('StaysAvoidedByCa', 0)}")
                print(f"  Stays avoided by ClosedDepartures: {result.get('StaysAvoidedByCd', 0)}")
                print(f"  Stays avoided by MaxStay:          {result.get('StaysAvoidedByMax', 0)}")

            print(f"\n⏱️  Processing Times:")
            print(f"  Initial Optimization: {result.get('InitialOptimizationTime', 0):.2f}s")
            print(f"  Total Time:           {result.get('TotalTime', 0):.2f}s")

            print("\n✅ Merge verification: NEW OPTIMIZER FEATURES WORKING!")
        break
    elif job_status["status"] == "failed":
        print(f"\n❌ Job failed!")
        if "error" in job_status:
            print(f"Error: {job_status['error']}")
        if "result" in job_status and job_status["result"]:
            print(f"Details: {json.dumps(job_status['result'], indent=2)}")
        break
else:
    print("\n⏰ Timeout: Job did not complete in 60 seconds")
