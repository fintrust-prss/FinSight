# Phase 9 Deployment — Quick Reference

## TL;DR — Which Approach?

| Aspect | Cloud Build | GitHub Actions |
|--------|------------|-----------------|
| **Setup time** | ~5 min | ~10 min |
| **Vendor lock-in** | GCP-specific | Cloud-agnostic |
| **Best for** | GCP-first projects | Multi-cloud / GitHub-centric |
| **Cost** | ~120 free build minutes/day | Free (GitHub-hosted runners) |
| **Workflow visibility** | GCP Console | GitHub Repo → Actions tab |
| **Secret management** | GCP Secret Manager | GitHub Secrets |

**Recommendation:** Use **Cloud Build** if all your infrastructure is on GCP. Use **GitHub Actions** if you want to keep deployment logic in your repo and avoid GCP lock-in.

---

## Files Created

1. **`cloudbuild.yml`** — Cloud Build pipeline definition
2. **`.github/workflows/deploy.yml`** — GitHub Actions workflow
3. **`DEPLOYMENT_SETUP.md`** — Full setup guide with step-by-step instructions
4. **`scripts/setup-cloud-build.sh`** — Automated setup script (Linux/macOS)
5. **`scripts/setup-cloud-build.bat`** — Automated setup script (Windows)

---

## 60-Second Setup

### Using Cloud Build

```bash
# 1. Enable APIs and create secrets
bash scripts/setup-cloud-build.sh

# 2. Connect GitHub (follow the prompt)
gcloud builds connect \
  --repository-name=msme-financial-health-card \
  --github-owner=YOUR_GITHUB_USERNAME \
  --region=us-central1

# 3. Create Cloud SQL (if not done)
gcloud sql instances create msme-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-8192 \
  --region=us-central1

# 4. Update cloudbuild.yml with your database connection name
# 5. Push to main
git push origin main

# 6. Watch the build at: https://console.cloud.google.com/cloud-build/builds
```

### Using GitHub Actions

```bash
# 1. Create GCP service account and set up Workload Identity Federation
# (see DEPLOYMENT_SETUP.md Option B, Steps 1-3)

# 2. Add GitHub Secrets (WIF_PROVIDER, WIF_SERVICE_ACCOUNT, GCP_PROJECT_ID)
# (go to Repo → Settings → Secrets and variables → Actions)

# 3. Push to main
git push origin main

# 4. Watch the workflow at: Repo → Actions → Deploy to GCP Cloud Run
```

---

## What Each Pipeline Does

### 1️⃣ Lint & Test
- Backend: ruff, black, mypy, pytest (≥85% coverage required)
- Frontend: eslint, prettier, tsc, vitest
- Security: bandit (Python), npm audit (Node)

### 2️⃣ Build Docker Images
- Backend: FastAPI app (production target)
- Frontend: React + Vite (production target)

### 3️⃣ Push to Artifact Registry
- Images tagged with commit SHA and "latest"
- Stored in `us-central1-docker.pkg.dev/{project}/msme-healthcard/`

### 4️⃣ Deploy to Cloud Run
- Backend: 2 vCPU, 2 GB RAM, max 10 instances
- Frontend: 1 vCPU, 1 GB RAM, max 5 instances
- Environment variables configured automatically

### 5️⃣ Post-Deployment
- Health check endpoint verified
- Deployment URLs output to logs

---

## Configuration Files Explained

### `cloudbuild.yml`

**Key sections:**
- `steps` — Build and deploy commands
- `substitutions` — Configuration variables (customize here!)
- `images` — Artifact Registry image tags
- `options.machineType` — `N1_HIGHCPU_8` for faster builds

**To customize:**
```yaml
substitutions:
  _REGION: 'us-central1'                          # Change if using different region
  _REPOSITORY: 'msme-healthcard'                  # Artifact Registry repo name
  _DB_HOST: 'your-project:us-central1:msme-postgres'  # Cloud SQL instance
  _DB_NAME: 'msme_healthcard'                     # Database name
```

### `.github/workflows/deploy.yml`

**Key sections:**
- `jobs.lint-test-backend` — Backend linting and testing
- `jobs.lint-test-frontend` — Frontend linting and testing
- `jobs.build-push` — Build and push images (runs on main only)
- `jobs.deploy` — Deploy to Cloud Run

**To customize:**
```yaml
env:
  REGION: us-central1                 # Change if using different region
  ARTIFACT_REGISTRY: msme-healthcard  # Artifact Registry repo name
```

---

## Environment Variables

### Backend (set in deployment)

```bash
POSTGRES_HOST=cloudsql-proxy  # Cloud SQL connection name or cloudsql-proxy
POSTGRES_PORT=5432
POSTGRES_DB=msme_healthcard
CLOUD_PROVIDER=gcp            # For adapter selection
APP_ENV=production
```

### Frontend (set in deployment)

```bash
VITE_API_BASE_URL=https://msme-backend-xxxx.run.app  # Backend URL
VITE_APP_ENV=production
```

---

## Common Deployment Scenarios

### Scenario 1: Deploy only backend

Edit `cloudbuild.yml` or `deploy.yml` and comment out the frontend deployment step.

### Scenario 2: Deploy to staging first, then production

Create two Cloud Run services: `msme-backend-staging` and `msme-backend-prod`. Add a manual approval step in the workflow.

### Scenario 3: Deploy from a different branch

In Cloud Build trigger or GitHub Actions, change `branch-pattern` or `on.push.branches`.

### Scenario 4: Deploy on schedule (nightly)

**Cloud Build:**
```yaml
# Add to cloudbuild.yml
onSchedule:
  schedule: "0 3 * * *"  # 3 AM UTC daily
```

**GitHub Actions:**
```yaml
on:
  schedule:
    - cron: '0 3 * * *'
```

---

## Monitoring & Debugging

### View Cloud Build logs

```bash
# Stream real-time logs
gcloud builds log --stream

# Get specific build logs
gcloud builds log BUILD_ID

# List recent builds
gcloud builds list --limit=10
```

### View GitHub Actions logs

Go to **Repo → Actions → [Workflow] → [Run] → [Job]**

### Check Cloud Run deployment status

```bash
# Get backend service status
gcloud run services describe msme-backend --region=us-central1

# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=msme-backend" --limit=50

# Get service URL
gcloud run services describe msme-backend --region=us-central1 --format='value(status.url)'
```

### Test the deployment

```bash
# Backend health check
curl https://msme-backend-xxxx.run.app/healthz

# Frontend (should redirect to login or dashboard)
curl https://msme-frontend-xxxx.run.app
```

---

## Troubleshooting

### Build fails: "permission denied" on secrets

**Solution:**
```bash
PROJECT_ID=$(gcloud config get-value project)
gcloud secrets add-iam-policy-binding postgres-password \
  --member=serviceAccount:${PROJECT_ID}@cloudbuild.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

### Frontend can't reach backend

**Solution:** Update `VITE_API_BASE_URL` in deployment config:
```bash
# Get backend URL
BACKEND_URL=$(gcloud run services describe msme-backend --region=us-central1 --format='value(status.url)')
echo "Use this for frontend VITE_API_BASE_URL: $BACKEND_URL"
```

### Build timeouts

**Solution:** Increase timeout in `cloudbuild.yml`:
```yaml
timeout: '7200s'  # 2 hours
```

### Images not found in Artifact Registry

**Solution:** Check repository exists:
```bash
gcloud artifacts repositories list --location=us-central1
```

---

## Security Best Practices

### 1. Use Workload Identity Federation (not service account keys)

GitHub Actions + GCP: Use WIF for keyless authentication.

### 2. Protect main branch

Set branch protection: Repo → Settings → Branches → Require pull request reviews.

### 3. Rotate secrets regularly

```bash
# Rotate postgres password
read -sp "New password: " NEW_PASS
echo -n "$NEW_PASS" | gcloud secrets versions add postgres-password --data-file=-
```

### 4. Use least-privilege IAM roles

Don't grant `Editor` role to service accounts. Grant only needed roles.

### 5. Review deployment logs

```bash
# Audit log of all deployments
gcloud logging read "resource.type=cloud_run_revision" --limit=100
```

---

## Next: Production Hardening

1. **Add canary deployments** — Deploy to 5% of traffic, monitor, then shift 100%
2. **Add smoke tests post-deployment** — Verify health endpoints
3. **Set up Cloud Armor** — DDoS/WAF protection
4. **Enable CI/CD approval gates** — Require manual approval before prod deployment
5. **Set up alerts** — CloudWatch/Cloud Monitoring for failed deployments

See `Phase7.md` for more details.

---

## References

- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Cloud Run Deployment Guide](https://cloud.google.com/run/docs/deploying)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
