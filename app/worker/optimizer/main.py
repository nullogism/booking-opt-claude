
from google.cloud import pubsub_v1, storage
import SolverRunner as Runner
import json
import re

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path("nullogism", "optimize-sub")
storage_client = storage.Client()

def callback(message):
	data = json.loads(message.data.decode())
	bucket, name = data["bucket"], data["name"]
	
	match = re.match(r"^(.*?)_valid_([a-zA-Z0-9]{6}).json$", name)

	if match:
		base_name_part = match.group(1)
		guid_part = match.group(2)
	
		print(f"Optimizer: Base='{base_name_part}', GUID='{guid_part}'")
	
		output_filename = f"{base_name_part}_optimized_{guid_part}.json"
		print(f"Optimizer will output: '{output_filename}'")
	
		blob = storage_client.bucket(bucket).blob(name)
		raw_json = blob.download_as_bytes()
		success, result = Runner.Run(json.loads(raw_json))
		
		
		if not success:
			out_blob = storage_client.bucket("booking-opt-failures").blob(output_filename)
			out_blob.upload_from_string(json.dumps(result), content_type = "application/json")
			message.ack()
			
			return()
			
		out_blob = storage_client.bucket("booking-opt-optimized").blob(output_filename)
		out_blob.upload_from_string(json.dumps(result), content_type = "application/json")
		
		message.ack()
	
	
	else:
		print(f"Optimizer Error: Filename '{name}' not in expected format")
		message.ack()
	
	
	
future = subscriber.subscribe(subscription_path, callback = callback)

# keep the process alive
future.result()
