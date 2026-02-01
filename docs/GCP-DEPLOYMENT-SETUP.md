# GCP Deployment Setup Guide

## Overview

This guide documents the setup of automated deployment to Google Cloud Platform using GitHub Actions.

## Architecture

- **VM Location**: us-central1-a (Iowa) for cost savings and lower latency
- **VM Type**: e2-small (2 vCPU, 2GB RAM)
- **OS**: Debian 11
- **Deployment Method**: GitHub Actions with automated dependency checking
- **External IP**: 34.136.100.73

## Service Account Setup

A dedicated service account has been created for GitHub Actions deployments:

- **Account**: github-actions-deployer@booking-opt-docker-compose.iam.gserviceaccount.com
- **Roles**:
  - `roles/compute.instanceAdmin.v1` - Manage VM instances
  - `roles/iam.serviceAccountUser` - Act as service accounts
  - `roles/compute.osLogin` - SSH access to VMs

## GitHub Secrets Configuration

Add the following secret to your GitHub repository:

### 1. Navigate to Repository Settings

Go to: https://github.com/nullogism/booking-opt-claude/settings/secrets/actions

### 2. Add GCP_SA_KEY Secret

1. Click "New repository secret"
2. Name: `GCP_SA_KEY`
3. Value: Copy the entire JSON key content from `/tmp/github-actions-key.json` in WSL

**To retrieve the service account key:**

```bash
# In WSL
cat /tmp/github-actions-key.json
```

Copy the entire JSON output (including the curly braces) and paste it as the secret value in GitHub.

## Deployment Workflow

The GitHub Actions workflow (`.github/workflows/deploy-gcp.yml`) automates:

1. **Dependency Checking**
   - Checks if Docker is installed on the VM
   - Installs Docker and Docker Compose if missing
   - Checks if Git is installed
   - Installs Git if missing

2. **Code Deployment**
   - Clones repository on first run
   - Pulls latest changes on subsequent runs
   - Stops existing containers
   - Builds and starts new containers

3. **Health Verification**
   - Waits for services to start
   - Checks health endpoint
   - Displays deployment info

## Running a Deployment

### Via GitHub Actions UI

1. Go to: https://github.com/nullogism/booking-opt-claude/actions
2. Select "Deploy to GCP VM" workflow
3. Click "Run workflow"
4. Choose environment: `staging` or `production`
5. Click "Run workflow"

### Via Command Line (after pushing changes)

```bash
# Commit and push changes
git add .
git commit -m "Deploy updates"
git push origin main

# Manually trigger deployment
gh workflow run deploy-gcp.yml -f environment=staging
```

## Accessing the Deployed Application

After successful deployment:

- **API Base URL**: http://34.136.100.73
- **Health Endpoint**: http://34.136.100.73/health
- **Optimization API**: http://34.136.100.73/api/v1/optimize

## Testing the Deployment

```bash
# Health check
curl http://34.136.100.73/health

# Run optimization test
python test_optimizer.py
# (Update the URL in test_optimizer.py to http://34.136.100.73)
```

## Security Roadmap

The current deployment is functional but requires security hardening:

### Phase 1: Network Security
- [ ] Restrict firewall rules to specific source IPs (not 0.0.0.0/0)
- [ ] Implement VPC network isolation
- [ ] Configure private IPs with Cloud NAT for egress
- [ ] Add Cloud Armor for DDoS protection

### Phase 2: Application Security
- [ ] Add HTTPS/TLS certificates (Let's Encrypt)
- [ ] Implement API authentication (API keys or OAuth)
- [ ] Add rate limiting
- [ ] Set up Web Application Firewall (WAF) rules

### Phase 3: Infrastructure Security
- [ ] Enable VPC Flow Logs for monitoring
- [ ] Set up Cloud Logging and Monitoring
- [ ] Configure Security Command Center
- [ ] Implement secret management (Cloud Secret Manager)

## Cost Optimization Roadmap

### Phase 1: Monitoring
- [ ] Set up billing alerts
- [ ] Configure budget notifications
- [ ] Analyze data transfer costs

### Phase 2: Optimization
- [ ] Evaluate Cloud CDN for static assets
- [ ] Consider committed use discounts for production
- [ ] Optimize VM sizing based on actual usage
- [ ] Implement auto-scaling if needed

### Phase 3: Regional Strategy
- [ ] Analyze traffic patterns for regional placement
- [ ] Plan migration to European datacenter for GDPR
- [ ] Evaluate multi-region deployment costs

## Troubleshooting

### SSH into VM

```bash
# From WSL
~/google-cloud-sdk/bin/gcloud compute ssh bookingopt-staging \
  --project=booking-opt-docker-compose \
  --zone=us-central1-a
```

### View Docker Logs

```bash
# After SSH-ing into VM
cd ~/booking-opt
docker compose logs -f
```

### Restart Services

```bash
# After SSH-ing into VM
cd ~/booking-opt
docker compose restart
```

### Manual Deployment

```bash
# After SSH-ing into VM
cd ~/booking-opt
git pull origin main
docker compose down
docker compose up -d --build
```

## Infrastructure Details

### VM Specifications
- **Name**: bookingopt-staging
- **Zone**: us-central1-a
- **Machine Type**: e2-small (2 vCPU, 2GB RAM)
- **Boot Disk**: 20GB standard persistent disk
- **OS**: Debian 11
- **Network Tags**: bookingopt-server

### Firewall Rules
- **Rule Name**: allow-bookingopt-http
- **Ports**: TCP 80, 443
- **Source**: 0.0.0.0/0 (⚠️ TEMPORARY - needs lockdown)
- **Target**: Instances with tag `bookingopt-server`

### Costs (Approximate)
- VM (e2-small, us-central1): ~$13/month
- Disk (20GB standard): ~$1/month
- Network egress: Variable (first 1GB/month free, then $0.12/GB)
- **Estimated Total**: ~$15-20/month for light usage

## Next Steps

1. Add `GCP_SA_KEY` secret to GitHub repository
2. Commit and push the deployment workflow
3. Run the deployment workflow
4. Test the deployed application
5. Implement security hardening (firewall restrictions, HTTPS, auth)
6. Set up monitoring and alerting
7. Plan migration to European datacenter for production

---

**Created**: 2026-02-01
**Last Updated**: 2026-02-01
