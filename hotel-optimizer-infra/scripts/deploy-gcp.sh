#!/bin/bash
# deploy-gcp.sh - Deploy Hotel Optimizer to GCP Compute Engine
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Docker image pushed to a registry (GCR, Docker Hub, etc.)
#
# Usage:
#   ./deploy-gcp.sh [project-id] [zone]

set -euo pipefail

# Configuration
PROJECT_ID="${1:-$(gcloud config get-value project)}"
ZONE="${2:-europe-west1-b}"  # Belgium - GDPR compliant
INSTANCE_NAME="hotel-optimizer"
MACHINE_TYPE="e2-small"  # ~$13/month

echo "=== Hotel Optimizer GCP Deployment ==="
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "Instance: $INSTANCE_NAME"
echo ""

# Check if instance already exists
if gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
    echo "Instance already exists. Options:"
    echo "  1. SSH: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
    echo "  2. Delete: gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE"
    exit 0
fi

echo "Creating VM with Container-Optimized OS..."

# Create instance with Container-Optimized OS
gcloud compute instances create "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --image-family=cos-stable \
    --image-project=cos-cloud \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-standard \
    --tags=http-server,https-server \
    --metadata=startup-script='#!/bin/bash
# Install docker-compose
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v /usr/local/bin:/dist docker/compose:latest \
    cp /usr/local/bin/docker-compose /dist/docker-compose
chmod +x /usr/local/bin/docker-compose
'

echo ""
echo "Creating firewall rules..."

# Create firewall rules (idempotent)
gcloud compute firewall-rules create allow-http-https \
    --project="$PROJECT_ID" \
    --allow=tcp:80,tcp:443 \
    --target-tags=http-server,https-server \
    --description="Allow HTTP and HTTPS traffic" \
    2>/dev/null || echo "Firewall rule already exists"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. SSH into the instance:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "2. Copy your docker-compose files:"
echo "   gcloud compute scp --recurse ./* $INSTANCE_NAME:/home/\$USER/hotel-optimizer --zone=$ZONE"
echo ""
echo "3. Start the services:"
echo "   cd hotel-optimizer && docker-compose up -d"
echo ""
echo "4. Get the external IP:"
echo "   gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'"
echo ""

# Get and display the IP
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "External IP: $EXTERNAL_IP"
echo ""
echo "Estimated monthly cost: ~\$13-15 (e2-small + 20GB disk)"
