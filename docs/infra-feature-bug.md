# Infrastructure Features & Bugs

**Last Updated**: 2026-01-31 (Evening Session)
**Status**: Ready for Docker Build Testing

Track infrastructure, deployment, CI/CD, and operations tasks.

## Status Legend

- `[ ]` Not Started
- `[~]` In Progress
- `[x]` Completed
- `[!]` Blocked
- `[?]` Needs Discussion

## Priority Levels

- **P0**: Critical - Blocks deployment
- **P1**: High - Required for production
- **P2**: Medium - Important but not blocking
- **P3**: Low - Nice to have

---

## Phase 1: Local Development & Testing

### P0 - Critical Path Items

#### Docker Configuration
- [x] **Update docker-compose.yml with build contexts** (P0) - COMPLETED
  - ✅ Replaced placeholder images with build directives
  - ✅ API: build from ../app/api (bookingopt-api:latest)
  - ✅ Worker: build from ../app/worker (bookingopt-worker:latest)
  - ✅ Environment variables configured
  - **Completed**: 2026-01-31

- [x] **Create .env.example template** (P0) - COMPLETED
  - ✅ Template exists with all configuration options
  - ⏳ User will create .env from template when needed
  - **Completed**: 2026-01-31

- [ ] **Test local Docker Compose deployment** (P0) - PENDING DOCKER INSTALL
  - ⏳ Docker Desktop installing (user restarting)
  - ⏳ `docker compose build` not yet run
  - ⏳ Verify all services healthy
  - ⏳ Test API endpoints (health, optimize, jobs)
  - **Next**: After Docker Desktop restart
  - **See**: docs/RESTART-INSTRUCTIONS.md

#### Nginx Configuration
- [x] **Rate limits configured** (P1) - COMPLETED
  - ✅ Optimize endpoint: 12 req/min (burst 3)
  - ✅ General API: 10 req/sec (burst 20)
  - ✅ Job polling: 10 req/sec (burst 50)
  - ⏳ Will adjust based on actual usage patterns after testing
  - **Completed**: 2026-01-31

- [x] **SSL certificate directory created** (P1) - COMPLETED
  - ✅ hotel-optimizer-infra/nginx/ssl/ created
  - ✅ .gitkeep added
  - ✅ Already in .gitignore
  - **Completed**: 2026-01-31

### P1 - Required for Production

#### SSL/TLS Setup
- [ ] **Choose SSL certificate method** (P1)
  - **Options**:
    - Let's Encrypt (automated, free)
    - Cloudflare Origin Certificate (if using Cloudflare)
    - Manual certificate (datacenter-provided)
  - **Status**: `[?]` Needs decision
  - **Assignee**: TBD

- [ ] **Configure SSL in nginx.conf** (P1)
  - Uncomment HTTPS server block (lines 139-158)
  - Update server_name with actual domain
  - Configure HTTP → HTTPS redirect
  - Test SSL configuration
  - **Blockers**: Depends on SSL certificate choice
  - **Assignee**: TBD

#### Resource Limits & Optimization
- [ ] **Adjust Docker resource limits** (P1)
  - Review CPU/memory limits in docker-compose.yml
  - Test under load
  - Optimize based on actual optimizer memory usage
  - **Assignee**: TBD

- [ ] **Configure Redis persistence** (P1)
  - Decide on AOF vs RDB persistence
  - Configure backup schedule (if needed)
  - Test Redis recovery after restart
  - **Assignee**: TBD

---

## Phase 2: CI/CD Pipeline

### P0 - Critical for Automation

#### GitHub Actions - Build Pipeline
- [x] **Create .github/workflows/ci.yml** (P0) - COMPLETED
  - ✅ Triggers on push to main, pull requests
  - ✅ Lint & Type Check stage (ruff, black, mypy)
  - ✅ Unit Tests stage (pytest)
  - ✅ Docker Build stage (buildx with caching)
  - ✅ Integration Tests stage (docker compose)
  - ✅ Security Scan stage (Trivy, Safety)
  - **Completed**: 2026-01-31
  - **Next**: Will run automatically on next push

- [ ] **Set up GitHub Container Registry (GHCR)** (P1) - DEFERRED
  - ⏳ Currently building locally
  - ⏳ Will configure when ready for registry push
  - **Status**: Not needed until deployment phase

- [x] **Docker image tagging strategy** (P0) - DEFINED
  - ✅ Tag: `bookingopt-api:latest` / `bookingopt-worker:latest` (local)
  - ✅ Tag: `bookingopt-api:<git-sha>` (CI builds)
  - ⏳ Tag: `v<version>` (future releases)
  - **Completed**: 2026-01-31 (strategy defined)

#### GitHub Actions - Deployment Pipeline
- [ ] **Create .github/workflows/deploy.yml** (P1)
  - Trigger: manual or on successful CI
  - Deploy to staging environment
  - Run smoke tests
  - Manual approval gate for production
  - Deploy to production
  - **Assignee**: TBD
  - **Estimated Effort**: 6-8 hours

- [ ] **Configure deployment secrets** (P1)
  - SSH keys for datacenter deployment
  - GCP credentials (if using GCP)
  - Registry credentials
  - Add to GitHub Secrets
  - **Assignee**: TBD

#### Automated Testing in CI
- [x] **Add test stages to CI pipeline** (P1) - COMPLETED
  - ✅ Unit test stage with pytest
  - ✅ Integration test stage with docker compose
  - ✅ Build fails on test failures
  - ✅ Coverage reporting configured (optional)
  - **Completed**: 2026-01-31

- [x] **Add security scanning** (P2) - COMPLETED
  - ✅ Trivy vulnerability scanner (filesystem + images)
  - ✅ Safety dependency checker
  - ✅ SARIF upload to GitHub Security
  - ✅ Configured to continue on non-critical issues
  - **Completed**: 2026-01-31

---

## Phase 3: Production Deployment

### P0 - Critical for Production Launch

#### GCP Deployment (Staging/Testing)
- [ ] **Create GCP VM instance** (P0)
  - Type: e2-small
  - Region: europe-west1-b (Belgium)
  - OS: Container-Optimized OS or Debian
  - Firewall: Allow HTTP/HTTPS
  - **Assignee**: TBD

- [ ] **Deploy to GCP manually (first time)** (P0)
  - SSH to VM
  - Install Docker & Docker Compose
  - Clone repository or pull images
  - Start services
  - Verify deployment
  - **Assignee**: TBD
  - **Estimated Effort**: 2-3 hours

- [ ] **Test GCP deployment end-to-end** (P0)
  - Submit optimization job
  - Monitor job processing
  - Verify results retrieval
  - Check logs and metrics
  - **Assignee**: TBD

#### European Datacenter Deployment (Production Target)
- [ ] **Datacenter VM provisioning** (P0)
  - Coordinate with datacenter ops team
  - VM specs: 2+ vCPU, 4GB+ RAM, 20GB+ disk
  - OS: Debian 11+
  - Network: External access on ports 80/443
  - **Status**: `[?]` Waiting for datacenter coordination
  - **Assignee**: TBD

- [ ] **Datacenter network configuration** (P0)
  - Firewall rules for HTTP/HTTPS
  - Internal routing if needed
  - DNS setup for domain
  - **Blockers**: Depends on datacenter policies
  - **Assignee**: TBD

- [ ] **Install Docker on datacenter VM** (P1)
  - Install Docker Engine
  - Install Docker Compose plugin
  - Configure Docker to start on boot
  - **Assignee**: TBD

- [ ] **Configure automated deployment** (P1)
  - GitHub Actions SSH deployment
  - OR: Docker registry pull
  - Rolling update strategy
  - Rollback procedure
  - **Assignee**: TBD

### P1 - Required for Production

#### Domain & DNS
- [ ] **Register or configure domain** (P1)
  - Decide on domain name
  - Point DNS A record to datacenter IP
  - Configure CNAME if needed
  - **Status**: `[?]` Needs decision on domain
  - **Assignee**: TBD

- [ ] **SSL certificate provisioning** (P1)
  - Let's Encrypt certbot setup
  - OR: Datacenter-provided certificate
  - Configure auto-renewal (certbot cron)
  - **Assignee**: TBD

#### Health Checks & Monitoring
- [ ] **Implement health check monitoring** (P1)
  - Uptime monitoring service (UptimeRobot, Pingdom, or self-hosted)
  - Alert on downtime
  - **Assignee**: TBD

- [ ] **Configure alerting** (P1)
  - Email or Slack notifications
  - Alert on: service down, high error rate, queue backup
  - **Assignee**: TBD

#### Backup & Recovery
- [ ] **Redis backup strategy** (P1)
  - Daily snapshots of Redis data
  - Backup retention policy (7-30 days)
  - Test restore procedure
  - **Assignee**: TBD

- [ ] **Disaster recovery plan** (P2)
  - Document recovery steps
  - Backup docker-compose.yml and configs
  - Test full recovery from backup
  - **Assignee**: TBD

---

## Phase 4: Monitoring & Observability

### P2 - Post-Launch Enhancements

#### Logging Infrastructure
- [ ] **Centralized log aggregation** (P2)
  - Options: Loki, ELK stack, or cloud logging
  - Collect logs from all containers
  - Search and filter capabilities
  - **Status**: `[?]` Decide on logging solution
  - **Assignee**: TBD

- [ ] **Log rotation and retention** (P2)
  - Configure Docker log rotation
  - Retain logs for 30 days
  - Archive if needed for compliance
  - **Assignee**: TBD

#### Metrics & Dashboards
- [ ] **Prometheus for metrics collection** (P2)
  - Add Prometheus to docker-compose.yml
  - Scrape metrics from API /metrics endpoint
  - Node exporter for system metrics
  - **Assignee**: TBD

- [ ] **Grafana dashboards** (P2)
  - System resource usage (CPU, memory, disk)
  - Application metrics (job queue depth, processing time)
  - Error rates and status codes
  - **Assignee**: TBD

- [ ] **Lightweight alternative to Prometheus/Grafana** (P3)
  - If full Prometheus stack is overkill
  - Consider: Netdata, Glances, or simple scripts
  - **Assignee**: TBD

#### Performance Optimization
- [ ] **Enable Nginx caching** (P2)
  - Cache GET /api/v1/jobs/{job_id} responses
  - Short TTL (10-30 seconds)
  - Reduce backend load
  - **Assignee**: TBD

- [ ] **Optimize Docker image size** (P2)
  - Use multi-stage builds
  - Remove unnecessary dependencies
  - Target < 500MB final image
  - **Assignee**: TBD

- [ ] **Database connection pooling** (P3)
  - If PostgreSQL added later
  - Redis connection pooling already implemented
  - **Assignee**: TBD

---

## Phase 5: Scaling & Cost Optimization

### P3 - Future Enhancements

#### Horizontal Scaling
- [ ] **Multi-worker scaling** (P3)
  - `docker-compose up -d --scale worker=3`
  - Load balancing across workers
  - Monitor queue depth to auto-scale
  - **Assignee**: TBD

- [ ] **Multi-region deployment** (P3)
  - Deploy to multiple EU datacenters
  - DNS-based load balancing
  - Data replication strategy
  - **Blockers**: Requires higher traffic volume to justify
  - **Assignee**: TBD

#### Cost Optimization
- [ ] **Review and optimize GCP costs** (P3)
  - Analyze egress traffic
  - Consider committed use discounts
  - Right-size VM based on actual usage
  - **Assignee**: TBD

- [ ] **Optimize Redis memory usage** (P3)
  - Tune maxmemory and eviction policy
  - Reduce job result TTL if possible
  - Monitor memory usage trends
  - **Assignee**: TBD

---

## Security Hardening

### P1 - Production Security

- [ ] **Implement rate limiting at application layer** (P1)
  - Already in nginx, but add app-level validation
  - Per-user and per-IP limits
  - **Status**: Partially implemented in job_queue.py
  - **Assignee**: TBD

- [ ] **Secure secrets management** (P1)
  - Move secrets out of .env file in production
  - Use GitHub Secrets for CI/CD
  - Consider: Vault, AWS Secrets Manager, or GCP Secret Manager
  - **Assignee**: TBD

- [ ] **Regular security updates** (P1)
  - Automated Docker image rebuilds (weekly)
  - Dependabot for Python dependencies
  - Monitor security advisories
  - **Assignee**: TBD

- [ ] **Network security** (P2)
  - Restrict Redis port (only accessible internally)
  - Firewall rules on VM
  - VPN for SSH access (datacenter requirement?)
  - **Assignee**: TBD

- [ ] **Audit logging** (P2)
  - Log all API requests (without PII)
  - Track failed authentication attempts
  - GDPR-compliant audit trail
  - **Assignee**: TBD

---

## Known Infrastructure Issues

### Critical Issues
_None currently - new deployment_

### High Priority Issues
_None currently_

### Medium Priority Issues
- [ ] **Nginx configuration uses placeholder values** (P1)
  - server_name is `_` (wildcard)
  - Need to update with actual domain
  - **Impact**: SSL won't work without proper domain

### Low Priority Issues
_None currently_

---

## Technical Debt

- [ ] **Manual deployment process** (P1)
  - Current: Manual SSH and docker-compose up
  - Target: Automated CI/CD deployment
  - **Impact**: Slow deployments, human error risk

- [ ] **No automated backups** (P1)
  - Redis data loss risk
  - **Impact**: Job results lost on failure

- [ ] **Limited monitoring** (P2)
  - No real-time metrics
  - Manual log review required
  - **Impact**: Slow incident response

---

## Questions & Decisions Needed

1. **GitHub Repository**: Where is the repository hosted?
   - Need URL to configure CI/CD
   - **Status**: `[?]` To be created or identified

2. **Container Registry**: GHCR, Docker Hub, or GCP Artifact Registry?
   - Affects CI/CD pipeline configuration
   - **Status**: `[?]` Decision needed

3. **Datacenter Details**: VM specs and network configuration?
   - When will datacenter VM be available?
   - Network restrictions or VPN requirements?
   - **Status**: `[?]` Waiting for datacenter coordination

4. **Domain Name**: What domain will be used?
   - Needed for SSL certificate
   - Needed for nginx configuration
   - **Status**: `[?]` Decision needed

5. **Deployment Strategy**: Blue-green, rolling, or simple replace?
   - For zero-downtime deployments
   - **Status**: `[?]` Start simple, enhance later

6. **Monitoring Budget**: Can we allocate $5-10/month for monitoring tools?
   - Uptime monitoring, log aggregation
   - **Status**: `[?]` Within overall $25-50/month budget?

---

## Deployment Checklist (Pre-Production)

Use this checklist before deploying to production:

- [ ] Docker images built and pushed to registry
- [ ] .env file configured with production values
- [ ] SSL certificates provisioned and tested
- [ ] Domain DNS points to production server
- [ ] Firewall rules configured (ports 80, 443)
- [ ] Health checks passing
- [ ] Rate limits tested and validated
- [ ] Backup strategy implemented and tested
- [ ] Monitoring and alerting configured
- [ ] Rollback procedure documented and tested
- [ ] Load testing completed
- [ ] Security scan passed (no critical vulnerabilities)
- [ ] GDPR compliance reviewed
- [ ] Operations team trained on deployment

---

## Completed Items

_Items will be moved here as they are completed_

---

## CI/CD Pipeline Milestones

### Milestone 1: Manual Deployment (Current)
- Manual docker-compose up on local machine
- Manual testing
- No automation

### Milestone 2: Automated Build (Target: Week 1)
- GitHub Actions builds Docker image on push
- Automated tests run in CI
- Images pushed to registry

### Milestone 3: Automated Staging Deployment (Target: Week 2)
- Automated deployment to GCP staging environment
- Smoke tests after deployment
- Deployment notifications

### Milestone 4: Production CI/CD (Target: Week 3-4)
- Manual approval gate for production
- Automated deployment to European datacenter
- Rollback capability
- Health checks and monitoring

---

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Rate Limiting Guide](https://www.nginx.com/blog/rate-limiting-nginx/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

---

**Next Review Date**: TBD
**Owner**: TBD
