# Greeks - Hotel Booking Optimization Platform

**Status**: Initial Setup
**Target Deployment**: European Datacenter
**Budget**: $25-50/month

## Project Overview

Greeks is a hotel booking optimization service that analyzes room availability and pricing configurations to provide data-driven recommendations for hotel management systems. The platform integrates with upstream hotel management software and provides optimized availability data for distribution to booking platforms (Booking.com, Kayak, etc.).

### Core Functionality

- **Optimization Engine**: Python-based algorithm that processes hotel configuration data (~30s processing time per job)
- **Async Job Queue**: Handles burst traffic from 1-2 operators running multiple optimization scenarios
- **API Layer**: RESTful API for job submission, status polling, and result retrieval
- **Rate Limiting**: Multi-layer protection against job spam and resource exhaustion

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Host (EU Datacenter)              │
│                                                               │
│  Internet ──▶ Nginx ──▶ API (FastAPI) ──▶ Redis Queue       │
│               :80/443    :8000                 :6379          │
│                            │                     │            │
│                            └─────────┬───────────┘            │
│                                      ▼                        │
│                                   Worker(s)                   │
│                              (Optimization Jobs)              │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Reverse Proxy** | Nginx | SSL termination, rate limiting, load balancing |
| **API Layer** | FastAPI + Uvicorn | REST endpoints, request validation |
| **Job Queue** | Redis + RQ | Async job processing, rate limit state |
| **Worker** | Python + RQ Worker | Background optimization processing |
| **Orchestration** | Docker Compose | Service management, networking |
| **CI/CD** | GitHub Actions (planned) | Automated testing, building, deployment |

## Project Goals

### Phase 1: Foundation (Current)
- [ ] Containerize Python optimization engine
- [ ] Integrate job queue system into application
- [ ] Local testing with Docker Compose
- [ ] Deploy to GCP e2-small for initial testing

### Phase 2: CI/CD Pipeline
- [ ] GitHub Actions workflow for Docker builds
- [ ] Automated testing (unit, integration, performance)
- [ ] Container registry setup (GCR or Docker Hub)
- [ ] Automated deployment to staging environment
- [ ] Health checks and rollback automation

### Phase 3: Production Deployment
- [ ] Deploy to European datacenter (GDPR compliance)
- [ ] SSL/TLS certificate automation (Let's Encrypt)
- [ ] Monitoring and alerting (Prometheus/Grafana or lightweight alternative)
- [ ] Performance optimization and load testing
- [ ] Documentation for operations team

### Phase 4: Scale & Optimize
- [ ] Horizontal worker scaling based on queue depth
- [ ] Redis persistence and backup strategy
- [ ] Cost optimization review
- [ ] Performance benchmarking vs. GCP Cloud Run baseline

## Directory Structure

```
greeks/
├── docs/                           # Project documentation
│   ├── README.md                   # This file - project overview
│   ├── app-feature-bug.md          # Application feature/bug tracking
│   └── infra-feature-bug.md        # Infrastructure feature/bug tracking
│
├── hotel-optimizer-infra/          # Infrastructure configuration
│   ├── docker-compose.yml          # Service orchestration
│   ├── .env.example                # Environment template
│   ├── nginx/                      # Reverse proxy config
│   │   ├── nginx.conf              # Main nginx configuration
│   │   ├── proxy_params_common     # Shared proxy settings
│   │   └── ssl/                    # SSL certificates (gitignored)
│   └── scripts/                    # Deployment and integration helpers
│       ├── job_queue.py            # RQ integration module
│       ├── example_api.py          # FastAPI endpoint examples
│       └── deploy-gcp.sh           # GCP deployment script
│
├── app/                            # Application code (to be created)
│   ├── Dockerfile                  # Container build instructions
│   ├── requirements.txt            # Python dependencies
│   ├── main.py                     # FastAPI application entry point
│   ├── optimizer/                  # Core optimization engine
│   └── tests/                      # Test suite
│
├── .github/                        # GitHub Actions workflows (planned)
│   └── workflows/
│       ├── ci.yml                  # Build and test
│       └── deploy.yml              # Deployment automation
│
└── README.md                       # Quick start and setup instructions
```

## Development Workflow

### Current State
1. Infrastructure scaffold created (Docker Compose, Nginx, job queue templates)
2. Waiting for application code integration
3. Local testing environment not yet configured

### Target Workflow (Post-CI/CD)
1. Developer commits code to `main` branch
2. GitHub Actions triggers:
   - Run test suite
   - Build Docker images
   - Push to container registry (tag: `main-<sha>` and `latest`)
3. Automated deployment to staging environment
4. Manual approval for production deployment
5. Deployment with health checks and automatic rollback on failure

## Deployment Targets

### Current: GCP Testing
- **VM Type**: e2-small (0.5-2 vCPU burst, 2GB RAM)
- **Region**: europe-west1-b (Belgium)
- **Cost**: ~$13-15/month
- **Purpose**: Initial testing and validation

### Target: European Datacenter
- **Platform**: On-premise Debian Linux VM
- **Requirements**: Docker + Docker Compose
- **Network**: Internal datacenter network with external ingress
- **Deployment**: GitHub Actions SSH deployment or container registry pull
- **Portability**: Same Docker Compose setup as GCP

## GDPR Compliance

Since the platform operates in Europe and processes hotel booking data:

| Requirement | Implementation |
|-------------|----------------|
| **Data Residency** | All processing in EU region (Belgium or datacenter) |
| **Data Minimization** | Only process necessary booking/availability data |
| **Right to Erasure** | Job results expire after 1 hour (configurable) |
| **Logging** | No PII in logs; structured logging for debugging only |
| **Security** | TLS encryption, rate limiting, security headers |

## Performance Requirements

- **Job Processing Time**: ~30 seconds per optimization
- **Concurrent Jobs**: 3 per user, configurable worker scaling
- **API Response Time**: <100ms for status checks, <500ms for job submission
- **Uptime Target**: 99.9% (three nines)
- **Traffic Pattern**: Burst traffic (1-2 operators), low sustained load

## Cost Considerations

### Monthly Budget: $25-50

**Current Estimates:**
- GCP e2-small VM: $13-15/month
- Egress traffic (minimal): $1-2/month
- **Total GCP**: ~$15-17/month

**European Datacenter:**
- Infrastructure cost: $0 (company-provided VM)
- Only consider monitoring/alerting tools if needed

**Why NOT Kubernetes:**
- GKE minimum: ~$150/month (control plane + nodes)
- Operational complexity requires dedicated DevOps
- Traffic doesn't justify auto-scaling overhead
- Docker Compose meets all current requirements

## Key Technical Decisions

### 1. Docker Compose over Kubernetes
- **Reason**: 1-2 operators, low traffic, no dedicated DevOps team
- **Tradeoff**: Manual scaling vs. auto-scaling
- **Portability**: Easy migration to datacenter or other cloud providers

### 2. Redis Queue (RQ) over Celery
- **Reason**: Simpler setup, lighter weight, sufficient for use case
- **Tradeoff**: Fewer features vs. ease of maintenance
- **Scaling**: Can horizontally scale workers trivially

### 3. FastAPI over Flask
- **Reason**: Modern async support, auto-generated docs, type validation
- **Tradeoff**: Slightly newer ecosystem vs. better performance
- **Developer Experience**: Pydantic models, OpenAPI schema

### 4. Nginx over Traefik/Caddy
- **Reason**: Battle-tested, excellent rate limiting, familiar to ops teams
- **Tradeoff**: Manual config vs. less operational risk
- **Features**: Mature SSL, caching, compression support

## Testing Strategy

### Unit Tests
- Optimization algorithm correctness
- API endpoint validation
- Job queue operations

### Integration Tests
- End-to-end job submission and processing
- Rate limiting behavior
- Redis connectivity and failover

### Performance Tests
- Optimization job duration under load
- Concurrent job handling (stress test)
- API response time benchmarks

### Deployment Tests
- Docker Compose startup health
- Nginx rate limiting validation
- SSL certificate renewal (production)

## Monitoring & Observability

### Required Metrics
- Job queue depth (pending jobs)
- Job processing duration (p50, p95, p99)
- API response times
- Error rates (4xx, 5xx)
- System resources (CPU, memory, disk)

### Logging
- Structured JSON logs
- Log levels: DEBUG (dev), INFO (staging), WARNING (production)
- No PII in logs (GDPR)

### Alerts (Future)
- Queue depth > 10 jobs for > 5 minutes
- Job failure rate > 10%
- API error rate > 5%
- Disk usage > 80%

## Security Considerations

1. **Rate Limiting**: Nginx + application layer (defense in depth)
2. **SSL/TLS**: Let's Encrypt or datacenter-provided certificates
3. **Headers**: X-Frame-Options, CSP, X-Content-Type-Options
4. **Authentication**: Token-based (to be implemented)
5. **Network**: Internal Docker network, only nginx exposed
6. **Updates**: Regular security patches via CI/CD

## Contributing & Development

### Prerequisites
- Docker Desktop (Windows WSL2 or native Linux)
- Python 3.10+
- Git

### Getting Started
```bash
# Clone repository
git clone <repository-url>
cd greeks

# Review infrastructure
cd hotel-optimizer-infra
cat README.md

# Copy environment template
cp .env.example .env

# Start services (once app is containerized)
docker-compose up -d

# View logs
docker-compose logs -f

# Run tests (to be implemented)
pytest app/tests/
```

### Before Committing
- Run test suite: `pytest`
- Lint code: `ruff check app/`
- Format code: `black app/`
- Update relevant tracking docs (app-feature-bug.md or infra-feature-bug.md)

## Documentation Index

- [Application Features & Bugs](app-feature-bug.md) - Track app development tasks
- [Infrastructure Features & Bugs](infra-feature-bug.md) - Track deployment/ops tasks
- [Infrastructure README](../hotel-optimizer-infra/README.md) - Detailed infra docs

## Contact & Support

- **Project Lead**: TBD
- **DevOps**: TBD
- **Issue Tracking**: See app-feature-bug.md and infra-feature-bug.md
- **Deployment Questions**: Reference infra-feature-bug.md

---

**Last Updated**: 2026-01-31
**Version**: 0.1.0 (Initial Setup)
