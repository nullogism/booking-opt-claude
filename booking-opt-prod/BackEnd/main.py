import os
import uuid
import json
import logging
import re
from datetime import timedelta

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from google.cloud import storage
from google.auth import default as google_auth_default
from google.auth import impersonated_credentials

# ——————————————————————————
# App & Logging setup
# ——————————————————————————
app = FastAPI(title="BookingOpt Backend API")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("backend-api")

# ——————————————————————————
# Config via ENV (with sensible defaults)
# ——————————————————————————
JSON_BUCKET           = os.getenv("BOOKING_JSON_BUCKET", "booking-opt-json")
OPT_BUCKET            = os.getenv("BOOKING_OPT_BUCKET", "booking-opt-optimized")
PNG_BUCKET            = os.getenv("BOOKING_PNG_BUCKET", "booking-opt-plotted")
SIGNED_URL_TTL_MINUTES= int(os.getenv("SIGNED_URL_TTL_MINUTES", "60"))
SIGNING_SERVICE_ACCOUNT = os.getenv(
    "SIGNING_SERVICE_ACCOUNT",
    "booking-backend-sa@nullogism.iam.gserviceaccount.com"
)

# ——————————————————————————
# GCS clients
# ——————————————————————————
# Default client for uploads (Workload Identity)
gcs = storage.Client()

# Impersonated credentials + client for signing URLs
source_creds, _ = google_auth_default()
impersonated_creds = impersonated_credentials.Credentials(
    source_credentials=source_creds,
    target_principal=SIGNING_SERVICE_ACCOUNT,
    target_scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
    lifetime=3600,
)
signing_client = storage.Client(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    credentials=impersonated_creds,
)

def generate_signed_url(bucket_name: str, blob_name: str, minutes: int) -> str:
    """
    Generate a V4 signed GET URL valid for `minutes`.
    """
    blob = signing_client.bucket(bucket_name).blob(blob_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=minutes),
        method="GET",
    )

# ——————————————————————————
# Healthcheck
# ——————————————————————————
@app.get("/health")
async def health():
    return {"status": "ok"}

# ——————————————————————————
# Echo endpoint
# ——————————————————————————
@app.post("/api/echo")
async def echo(payload: dict):
    logger.info("Echo payload received: %s", payload)
    return {"message": "Payload received", "data": payload}

# ——————————————————————————
# Upload JSON → upload to GCS and return signed JSON URL + ProblemId
# ——————————————————————————
@app.post("/api/upload")
async def upload_json(file: UploadFile = File(...)):
    # 1) Read & parse
    try:
        contents = await file.read()
        data     = json.loads(contents)
        problem_id = data.get("ProblemId")  # case‑sensitive
    except Exception as e:
        logger.error("Failed to parse JSON %s: %s", file.filename, e)
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # 2) Construct validated filename with GUID
    job_guid = uuid.uuid4().hex[:6]
    original_filename_or_uuid = file.filename or str(uuid.uuid4()) # Fallback if file.filename is None
    
    base_name, original_ext = os.path.splitext(original_filename_or_uuid)

    # Determine the effective base name (e.g., "myfile" or "myfile.zip")
    effective_basename = base_name
    if original_ext and original_ext.lower() != ".json":
        effective_basename = base_name + original_ext # e.g., "myfile.zip"
    
    validated_filename = f"{effective_basename}_valid_{job_guid}.json"
    
    # Ensure it ends with .json (should be guaranteed by the f-string, but as a safeguard)
    if not validated_filename.endswith(".json"):
        # This path should ideally not be taken given the construction above.
        # If it ever is, it implies a logic error in effective_basename or job_guid.
        logger.warning(f"Filename construction for {validated_filename} unexpectedly did not end with .json, forcing it.")
        validated_filename = f"{validated_filename.split('.')[0]}_{job_guid}.json" # Attempt recovery

    # This line is a workaround from previous subtask due to tool issues.
    # Ideally, 'validated_filename' would be used directly in logger and return.
    # For now, we keep this assignment to minimize changes if tools fail on logger/return.
    filename = validated_filename 

    # 3) Upload to JSON bucket
    bucket = gcs.bucket(JSON_BUCKET)
    blob   = bucket.blob(validated_filename)
    blob.upload_from_string(contents, content_type="application/json")
    logger.info("Uploaded JSON to gs://%s/%s", JSON_BUCKET, filename)

    # 4) Return ProblemId
    return {
        "fileName": filename,
        "problemId": problem_id
    }

# ——————————————————————————
# Polling: has the PNG been generated? If so return both signed URLs + ProblemId
# ——————————————————————————
@app.get("/api/result")
async def check_result(
    fileName: str = Query(..., description="The JSON filename you uploaded")
):
    # Validate JSON filename
    if not fileName.endswith(".json"):
        raise HTTPException(status_code=400, detail="fileName must end with .json")

    # Parse fileName (e.g., UserUploadedFileName_valid_GUID.json)
    # Regex to capture: (basename)_(valid)_ (guid of 6 chars).json
    # Example: MyFile_valid_abc123.json
    match = re.match(r"^(.*?)_valid_([a-zA-Z0-9]{6})\.json$", fileName)
    
    if not match:
        logger.error(f"Could not parse GUID from fileName: {fileName}")
        # If this backend is called directly with a bad name not from /api/upload, this will catch it.
        raise HTTPException(status_code=400, detail=f"Invalid fileName format: {fileName}. Expected 'basename_valid_GUID.json'.")

    base_name_part = match.group(1)
    guid_part = match.group(2)

    optimized_json_name = f"{base_name_part}_optimized_{guid_part}.json"
    plotted_png_name = f"{base_name_part}_plotted_{guid_part}.png"

    # Check for plotted_png_name in PNG_BUCKET
    png_bucket = gcs.bucket(PNG_BUCKET)
    png_blob   = png_bucket.get_blob(plotted_png_name)
    if png_blob is None:
        return {"ready": False}

    # Read back the JSON to extract ProblemId
    problem_id_value = None
    json_bucket = gcs.bucket(JSON_BUCKET)
    json_blob   = json_bucket.get_blob(fileName)
    if json_blob:
        try:
            jtxt = json_blob.download_as_text()
            j   = json.loads(jtxt)
            problem_id_value = j.get("ProblemId")
        except Exception as e:
            logger.error("Failed to parse JSON %s: %s", fileName, e)

    # Generate fresh signed URLs for both
    signed_json_url = generate_signed_url(OPT_BUCKET, optimized_json_name, SIGNED_URL_TTL_MINUTES)
    signed_png_url  = generate_signed_url(PNG_BUCKET,  plotted_png_name, SIGNED_URL_TTL_MINUTES)

    return {
        "ready":           True,
        "jsonUrl":         signed_json_url,
        "imageUrl":        signed_png_url,
        "expiresInMinutes":SIGNED_URL_TTL_MINUTES,
        "problemId":       problem_id_value
    }