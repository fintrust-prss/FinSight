# Phase 9 Deployment Setup Guide

## Overview

This guide covers two deployment options for GCP Cloud Run:

1. **Cloud Build** — Native GCP build service (recommended for GCP-first projects)
2. **GitHub Actions** — Native GitHub CI/CD (recommended if you want GitHub-controlled pipeline)

Both achieve the same outcome: build, test, push to Artifact Registry, and deploy to Cloud Run.

---

## Option A: Cloud Build (Recommended for GCP-first)

### Prerequisites

- GCP Project with billing enabled
- `gcloud` CLI installed locally
- GitHub repository connected to Cloud Build

### Step 1: Connect GitHub Repository to Cloud Build

```bash
gcloud builds connect --repository-name=msme-financial-health-card \
  --github-owner=YOUR_GITHUB_USERNAME \
  --region=us-central1
```

This will prompt you to authorize GitHub and select the repo. Once connected, Cloud Build can read your repo and trigger builds.

### Step 2: Create Artifact Registry Repository

```bash
gcloud artifacts repositories create msme-healthcard \
  --repository-format=docker \
  --location=us-central1 \
  --description="MSME Financial Health Card — Docker images"
```

### Step 3: Enable Required APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  sql.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### Step 4: Set up Cloud SQL secrets (if not already done)

```bash
# Create Postgres user password secret
echo -n "your-secure-password-here" | gcloud secrets create postgres-password --data-file=-

# Create Postgres user secret
echo -n "msme_app" | gcloud secrets create postgres-user --data-file=-
```

### Step 5: Grant Cloud Build service account access to secrets

```bash
PROJECT_ID=$(gcloud config get-value project)
BUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

# Grant access to secrets
gcloud secrets add-iam-policy-binding postgres-password \
  --member=serviceAccount:${BUILD_SA} \
  --role=roles/secretmanager.secretAccessor

gcloud secrets add-iam-policy-binding postgres-user \
  --member=serviceAccount:${BUILD_SA} \
  --role=roles/secretmanager.secretAccessor
```

### Step 6: Create Cloud Build Trigger

```bash
gcloud builds triggers create github \
  --repo-name=msme-financial-health-card \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern='^main$' \
  --build-config=cloudbuild.yml \
  --name=msme-main-deploy \
  --region=us-central1 \
  --substitutions="_REGION=us-central1,_REPOSITORY=msme-healthcard,_DB_HOST=PROJECT:us-central1:msme-postgres,_DB_PORT=5432,_DB_NAME=msme_healthcard,_BACKEND_URL=msme-backend-xxxx.run.app"
```

### Step 7: Update cloudbuild.yml substitutions

Edit `cloudbuild.yml` and update these values with your actual GCP resources:

```yaml
substitutions:
  _REGION: 'us-central1'
  _REPOSITORY: 'msme-healthcard'
  _DB_HOST: 'your-project-id:us-central1:msme-postgres'  # Cloud SQL connection name
  _DB_PORT: '5432'
  _DB_NAME: 'msme_healthcard'
  _BACKEND_URL: 'msme-backend-xxxx.run.app'  # Will be auto-generated, can leave as template
```

### Step 8: (Optional) Set Cloud SQL Proxy for connections

If your backend needs to connect to Cloud SQL, add to `cloudbuild.yml`:

```yaml
# In substitutions or env vars:
substitutions:
  _CLOUDSQL_INSTANCES: 'your-project:us-central1:msme-postgres'
```

### Step 9: Test the trigger

Push a commit to main:

```bash
git add cloudbuild.yml
git commit -m "Add Cloud Build deployment configuration"
git push origin main
```

Then monitor the build:

```bash
gcloud builds log --stream
```

---

## Option B: GitHub Actions (Recommended for GitHub-centric teams)

### Prerequisites

- GitHub repository with Actions enabled
- GCP Service Account with appropriate roles
- Workload Identity Federation set up (recommended) or service account key

### Step 1: Create GCP Service Account

```bash
PROJECT_ID=$(gcloud config get-value project)

gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

SA_EMAIL="github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

### Step 2: Grant roles to service account

```bash
# Cloud Run Deploy
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/run.developer

# Artifact Registry Push
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/artifactregistry.writer

# Cloud SQL Client (if needed)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/cloudsql.client

# Secret Manager
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/secretmanager.secretAccessor

# Service Account User
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/iam.serviceAccountUser
```

### Step 3a: (Recommended) Set up Workload Identity Federation

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
POOL_ID="github-actions"
PROVIDER_ID="github-provider"

# Create identity pool
gcloud iam workload-identity-pools create $POOL_ID \
  --project=$PROJECT_ID \
  --location=global \
  --display-name="GitHub Actions Pool"

# Create OIDC provider
gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID \
  --project=$PROJECT_ID \
  --location=global \
  --workload-identity-pool=$POOL_ID \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.aud=assertion.aud,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-condition="assertion.repository_owner == 'YOUR_GITHUB_ORG'"

# Get the WIF provider resource
WIF_PROVIDER="projects/${PROJECT_NUM}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

# Create service account binding
gcloud iam service-accounts add-iam-policy-binding \
  "github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --project=$PROJECT_ID \
  --role=roles/iam.workloadIdentityUser \
  --condition="resource.name == \"//${WIF_PROVIDER}/subject/repo:YOUR_GITHUB_ORG/msme-financial-health-card:ref:refs/heads/main\""

echo "WIF_PROVIDER: $WIF_PROVIDER"
echo "WIF_SERVICE_ACCOUNT: github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

### Step 3b: (Alternative) Use service account key

If WIF is not available:

```bash
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Base64 encode for GitHub secret
base64 -i github-actions-key.json | pbcopy  # macOS
# or
cat github-actions-key.json | base64 -w0  # Linux
```

### Step 4: Add GitHub Secrets

Go to **GitHub Repo → Settings → Secrets and variables → Actions** and add:

**If using Workload Identity Federation:**
- `GCP_PROJECT_ID` = your GCP project ID
- `WIF_PROVIDER` = `projects/PROJECT_NUM/locations/global/workloadIdentityPools/github-actions/providers/github-provider`
- `WIF_SERVICE_ACCOUNT` = `github-actions-sa@PROJECT_ID.iam.gserviceaccount.com`

**If using service account key (less secure):**
- `GCP_PROJECT_ID` = your GCP project ID
- `GCP_SA_KEY` = base64-encoded JSON key from step 3b

### Step 5: Update workflow file

The workflow needs these secrets defined. If using service account key instead of WIF, update `.github/workflows/deploy.yml`:

Replace this:
```yaml
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
```

With this (if using key):
```yaml
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
```

### Step 6: Add database credentials

```bash
# Add these as GitHub Secrets as well:
# DB_HOST: your-project:us-central1:msme-postgres
# DB_USER: msme_app
# DB_PASS: your-secure-password
```

### Step 7: Test the workflow

Push a commit to main:

```bash
git add .github/workflows/deploy.yml
git commit -m "Add GitHub Actions deployment workflow"
git push origin main
```

Monitor in GitHub: **Actions → Deploy to GCP Cloud Run**

---

## Deploying Cloud SQL (Database)

Both pipelines assume Cloud SQL exists. Create it first:

```bash
gcloud sql instances create msme-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-8192 \
  --region=us-central1 \
  --network=default \
  --backup-start-time=03:00 \
  --enable-bin-log

# Create database
gcloud sql databases create msme_healthcard \
  --instance=msme-postgres

# Create app user
gcloud sql users create msme_app \
  --instance=msme-postgres \
  --password
```

---

## Manual Testing

### Test Cloud Build locally

```bash
# Build backend
docker build -t msme-backend:test -f backend/Dockerfile --target production ./backend

# Build frontend
docker build -t msme-frontend:test -f frontend/Dockerfile --target production ./frontend
```

### Push to Artifact Registry manually

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1

# Configure Docker
gcloud auth configure-docker $REGION-docker.pkg.dev

# Tag and push
docker tag msme-backend:test $REGION-docker.pkg.dev/$PROJECT_ID/msme-healthcard/msme-backend:test
docker push $REGION-docker.pkg.dev/$PROJECT_ID/msme-healthcard/msme-backend:test
```

### Deploy to Cloud Run manually

```bash
gcloud run deploy msme-backend \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/msme-healthcard/msme-backend:test \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2
```

---

## Monitoring & Logs

### Cloud Build logs

```bash
gcloud builds log --stream
```

### Cloud Run logs

```bash
gcloud run services describe msme-backend --region=us-central1
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=msme-backend" --limit=50
```

### GitHub Actions logs

**GitHub Repo → Actions → [Workflow Run] → [Job] → Logs**

---

## Troubleshooting

### Build fails with "permission denied"

**Solution:** Ensure the service account has the required roles (see Step 2/3).

### Cloud Run deployment times out

**Solution:** Increase `--timeout` in the deployment command (default 300s).

### Images not found in Artifact Registry

**Solution:** Verify Artifact Registry repo exists and service account has `artifactregistry.writer` role.

### VITE_API_BASE_URL not set correctly

**Solution:** Update the GitHub Actions workflow or Cloud Build substitution to use the correct backend URL. You may need to fetch the backend URL after deployment and pass it to the frontend deployment.

---

## Next Steps

1. Choose between Cloud Build or GitHub Actions (or use both)
2. Set up the selected option following the steps above
3. Test with a push to main branch
4. Monitor the first deployment
5. Iterate on Dockerfile optimization if builds take too long

For production, consider:
- Adding deployment approvals
- Implementing canary deployments
- Setting up post-deployment smoke tests
- Adding rollback capabilities
