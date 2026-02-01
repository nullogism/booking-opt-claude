# Cloud Function handler that listens for JSON uploads to GCS,
# parses the payload into the structures that plot.py expects,
# generates a PNG via ProcessOutput module, and writes it back to another bucket.

import os
import logging
import re

import json
from types import SimpleNamespace
from datetime import datetime, timedelta
import io

from google.cloud import storage
import functions_framework

import ProcessOutput
from cloudevents.http import CloudEvent


# Initialize clients and bucket once per instance
storage_client = storage.Client()
PLOT_BUCKET = os.getenv("PLOT_BUCKET", "booking-opt-plotted")
plot_bucket = storage_client.bucket(PLOT_BUCKET)


@functions_framework.http
def health(request):
    """Simple health check for GET / (default Cloud Run probe)."""
    if request.method == "GET":
        return ("OK", 200)
    # If someone POSTs JSON here, just reject
    return ("Not Found", 404)


@functions_framework.cloud_event
def process_json_upload(cloud_event: CloudEvent):
    """
    Triggered by GCS finalize event on booking-opt-optimized/*.json.
    Reads the JSON, generates a plot, and writes the PNG to booking-opt-plotted.
    """
    data       = cloud_event.data
    src_bucket = data.get("bucket")
    name       = data.get("name")

    # Only process .json files from the optimized bucket
    if src_bucket != "booking-opt-optimized" or not name.lower().endswith(".json"):
        logging.info("Skipping event: bucket=%s, name=%s", src_bucket, name)
        return

    # Step 1: Download and parse JSON
    try:
        blob    = storage_client.bucket(src_bucket).blob(name)
        text    = blob.download_as_text()
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        logging.error("Invalid JSON in gs://%s/%s: %s", src_bucket, name, e)
        return
    except Exception:
        logging.exception("Failed to download or parse JSON gs://%s/%s", src_bucket, name)
        raise  # let Cloud Functions retry on transient errors

    # Step 2: Generate the plot
    try:
        img_buf = ProcessOutput.Run(payload)
        img_buf.seek(0)
    except Exception:
        logging.exception("Plot generation failed for %s", name)
        raise

    # Step 3: Upload the PNG
    try:
        # Parse input filename (e.g., UserUploadedFileName_optimized_GUID.json)
        # Regex to capture: (basename)_(optimized)_(guid of 6 chars).json
        match = re.match(r"^(.*?)_optimized_([a-zA-Z0-9]{6})\.json$", name)

        if not match:
            logging.error(f"Could not parse GUID from input filename: {name} in bucket {src_bucket}. Expected 'basename_optimized_GUID.json'.")
            # Skip plotting for malformed names.
            return

        base_name_part = match.group(1)
        guid_part = match.group(2)

        # Construct the output PNG name, e.g., UserUploadedFileName_plotted_GUID.png
        png_name = f"{base_name_part}_plotted_{guid_part}.png"
        
        out_blob = plot_bucket.blob(png_name)
        out_blob.upload_from_file(img_buf, content_type="image/png")
        logging.info("Uploaded plot to gs://%s/%s", PLOT_BUCKET, png_name)
    except Exception:
        logging.exception("Failed to upload PNG for %s to bucket %s", name, PLOT_BUCKET)
        raise