# BookingOpt - Hotel Room Optimization Platform

**Repository**: https://github.com/nullogism/booking-opt-claude.git
**Status**: Ready for Testing
**Deployment Target**: European Datacenter

## Architecture Overview

```
                    ┌─────────────────────────────────────────────────────┐
                    │                     Docker Host                      │
                    │                                                       │
  Internet ──────▶  │  ┌─────────┐    ┌─────────┐    ┌─────────┐          │
                    │  │  Nginx  │───▶│   API   │───▶│  Redis  │          │
                    │  │ :80/443 │    │  :8000  │    │  :6379  │          │
                    │  └─────────┘    └─────────┘    └────┬────┘          │
                    │       │                              │               │
                    │       │         Rate Limiting        │               │
                    │       │         + SSL Term           ▼               │
                    │       │                        ┌─────────┐          │
                    │       └───── (health) ────────│  Worker │          │
                    │                               │ (async) │          │
                    │                               └─────────┘          │
                    └─────────────────────────────────────────────────────┘
```

**Components:**
- **Nginx**: Reverse proxy, rate limiting, SSL termination, security headers
- **API**: Your optimizer image handling synchronous requests
- **Worker**: Same image processing async optimization jobs
- **Redis**: Job queue + rate limit state (lightweight, ~100MB max)

## Why NOT Kubernetes?

| Factor | Your Situation | K8s Requirement |
|--------|----------------|-----------------|
| Traffic | 1-2 operators | 100+ concurrent users |
| DevOps team | None | Dedicated team |
| Budget | $25-50/mo | $150+/mo (GKE minimum) |
| Complexity | Simple queue | Multi-region, auto-scaling |

**Verdict**: Docker Compose is the right choice. Portable, simple, fits budget.

## Quick Start

### 1. Clone and Configure

```bash
# Update docker-compose.yml with your image name
sed -i 's/your-optimizer-image:latest/YOUR_ACTUAL_IMAGE/g' docker-compose.yml
```

### 2. Start Services

```bash
# Development (HTTP only)
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 3. Test

```bash
# Health check
curl http://localhost/health

# Submit optimization (example)
curl -X POST http://localhost/api/v1/optimize \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -d '{
    "hotel_id": "hotel123",
    "date_range_start": "2025-02-01",
    "date_range_end": "2025-02-28",
    "room_types": ["standard", "deluxe"]
  }'

# Check job status
curl http://localhost/api/v1/jobs/{job_id}
```

## Deployment Options

### Option A: GCP Compute Engine (Recommended for now)

**Estimated cost: $13-25/month**

```bash
# Create VM in EU region (GDPR compliance)
gcloud compute instances create hotel-optimizer \
  --zone=europe-west1-b \
  --machine-type=e2-small \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --tags=http-server,https-server \
  --boot-disk-size=20GB

# Allow HTTP/HTTPS traffic
gcloud compute firewall-rules create allow-http \
  --allow tcp:80,tcp:443 \
  --target-tags=http-server,https-server

# SSH and deploy
gcloud compute ssh hotel-optimizer --zone=europe-west1-b
```

**Why e2-small over e2-micro?**
- Your 30s optimization jobs need burst CPU
- e2-micro's 0.25 vCPU limit will cause timeouts
- e2-small gives 0.5-2 vCPU burst capacity

### Option B: On-Premise Debian Server

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Deploy
cd /opt/hotel-optimizer
docker compose up -d
```

### Option C: Cloud Run (Not Recommended)

Your previous Cloud Run setup worked, but:
- 30-second jobs = high cost ($0.00002400/vCPU-second)
- Cold starts add latency
- Job queuing harder to implement

Cloud Run is better for sub-1s request workloads.

## Rate Limiting Configuration

### Nginx Layer (Edge)

| Endpoint | Limit | Burst | Effect |
|----------|-------|-------|--------|
| `/api/v1/optimize` | 12/min | 3 | Prevents spam |
| `/api/v1/jobs/*` | 10/sec | 50 | Lenient polling |
| All other | 10/sec | 20 | General protection |

### Application Layer

| Control | Default | Config |
|---------|---------|--------|
| Max concurrent jobs/user | 3 | `MAX_QUEUED_JOBS_PER_USER` |
| Job timeout | 120s | `MAX_JOB_DURATION` |
| Result TTL | 1 hour | `JOB_RESULT_TTL` |

**Defense in depth**: Even if someone bypasses nginx, the app enforces limits.

## Adding SSL/TLS

### Option 1: Certbot (Let's Encrypt)

```bash
# Install certbot
sudo apt-get install certbot

# Get certificate (stop nginx first)
docker-compose stop nginx
sudo certbot certonly --standalone -d your-domain.com

# Copy certs to nginx volume
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./nginx/ssl/

# Uncomment HTTPS server block in nginx/nginx.conf
# Restart
docker-compose up -d nginx
```

### Option 2: Cloudflare (Simpler)

1. Add domain to Cloudflare
2. Enable "Full" SSL mode
3. Use Cloudflare's origin certificate in nginx/ssl/

## Monitoring & Troubleshooting

### Health Checks

```bash
# All services healthy?
docker-compose ps

# Nginx status
curl http://localhost/nginx-status

# Redis connectivity
docker-compose exec redis redis-cli ping

# View job queue
docker-compose exec redis redis-cli LLEN optimization
```

### Common Issues

**Jobs timing out:**
```bash
# Increase worker resources in docker-compose.yml
# Or reduce MAX_JOB_DURATION if jobs shouldn't take 30s
```

**Rate limiting too aggressive:**
```nginx
# In nginx/nginx.conf, adjust:
limit_req_zone ... rate=20r/m;  # Increase from 12r/m
```

**Out of memory:**
```bash
# Check Redis memory
docker-compose exec redis redis-cli INFO memory

# Reduce maxmemory in docker-compose.yml redis command
```

## GDPR Considerations

Since this operates in the EU:

| Requirement | Implementation |
|-------------|----------------|
| Data residency | Deploy in `europe-west1` (Belgium) or similar |
| Logging | Don't log PII; review nginx access logs |
| Right to erasure | Ensure job results can be deleted |
| Data minimization | Only process necessary hotel data |

**Your service exposure is minimal** if you're only processing availability/pricing data without personal guest information. The GDPR burden is primarily on the frontend that handles user accounts.

## Scaling (When Needed)

For now, a single VM handles your 1-2 operators easily. When you grow:

### Horizontal: More Workers

```bash
# Scale to 2 workers
docker-compose up -d --scale worker=2
```

### Vertical: Bigger VM

```bash
# Resize VM (causes brief downtime)
gcloud compute instances stop hotel-optimizer
gcloud compute instances set-machine-type hotel-optimizer \
  --machine-type=e2-medium
gcloud compute instances start hotel-optimizer
```

### Eventually: Managed Container Service

When traffic justifies it (~$200/mo budget):
- GCP Cloud Run (if jobs become faster)
- GCP GKE Autopilot (if you need K8s features)
- AWS ECS Fargate (if moving to AWS)

## File Structure

```
hotel-optimizer-infra/
├── docker-compose.yml      # Main orchestration
├── nginx/
│   ├── nginx.conf          # Reverse proxy config
│   ├── proxy_params_common # Shared proxy settings
│   └── ssl/                # SSL certificates (mount point)
├── scripts/
│   ├── job_queue.py        # Job queue integration (copy to your app)
│   └── example_api.py      # FastAPI endpoint examples
└── docs/
    └── README.md           # This file
```

## Next Steps

1. **Replace image name** in docker-compose.yml
2. **Add job queue** to your app (see scripts/job_queue.py)
3. **Test locally** with docker-compose up
4. **Deploy to GCP** e2-small in europe-west1
5. **Add SSL** when you have a domain
6. **Monitor** and adjust rate limits based on real usage

## Support

Questions about this setup? The architecture is designed to be:
- **Portable**: Works on GCP, on-prem, any Docker host
- **Simple**: No K8s, no complex orchestration
- **Cheap**: Fits $25-50/mo budget
- **Secure**: Rate limiting, security headers, SSL-ready
