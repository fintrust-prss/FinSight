# Environment Variables & Secrets Management

## Overview

This file documents how to manage environment variables and secrets for both Cloud Build and GitHub Actions pipelines.

---

## Secrets Storage

### GCP Secret Manager (for Cloud Build)

All sensitive data should be stored in GCP Secret Manager, not in `cloudbuild.yml` or environment variables.

**Available secrets:**
```
postgres-password      # PostgreSQL password
postgres-user          # PostgreSQL username
jwt-secret             # JWT signing key
api-key                # (if using third-party APIs)
```

**Access secrets in Cloud Build:**

In `cloudbuild.yml`:
```yaml
env:
  - 'POSTGRES_PASSWORD=${_POSTGRES_PASSWORD}'
```

Or in steps:
```yaml
steps:
  - name: 'gcr.io/cloud-builders/gke-deploy'
    env:
      - 'POSTGRES_PASSWORD=${_POSTGRES_PASSWORD}'
```

### GitHub Secrets (for GitHub Actions)

Sensitive data stored as GitHub repository secrets (not to be confused with GCP Secret Manager).

**To add:**
1. Go to **Repo → Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add secret name and value

**Available secrets:**
```
GCP_PROJECT_ID         # GCP Project ID
GCP_SA_KEY             # (if using service account key)
WIF_PROVIDER           # Workload Identity Federation provider
WIF_SERVICE_ACCOUNT    # Service account email
DB_HOST                # Cloud SQL connection string
DB_USER                # Database username
DB_PASS                # Database password
JWT_SECRET             # JWT signing key
```

---

## Backend Environment Variables

### Production (Cloud Run)

These are set during deployment by the pipeline. **Do not commit to `.env`.**

```bash
# Database
POSTGRES_HOST=<cloud-sql-connection-name>  # Format: project:region:instance
POSTGRES_PORT=5432
POSTGRES_DB=msme_healthcard
POSTGRES_USER=msme_app                     # From Secret Manager
POSTGRES_PASSWORD=<secret>                 # From Secret Manager

# Application
CLOUD_PROVIDER=gcp                         # Adapter selector
APP_ENV=production
SECRET_KEY=<random-jwt-key>                # From Secret Manager

# Optional: Logging & Monitoring
LOG_LEVEL=info
SENTRY_DSN=<sentry-url>                    # Error tracking (optional)
```

### Local Development

Create `.env.local` (gitignored):

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=msme_healthcard
POSTGRES_USER=msme_app
POSTGRES_PASSWORD=change_me_in_production
CLOUD_PROVIDER=gcp
APP_ENV=development
```

**Use:**
```bash
cd backend
source .env.local  # Linux/macOS
set -a && source .env.local && set +a
# or use python-dotenv to load from file
```

---

## Frontend Environment Variables

### Production (Cloud Run)

These are set during deployment:

```bash
VITE_API_BASE_URL=https://msme-backend-xxxxx.run.app  # Backend URL
VITE_APP_ENV=production
```

### Local Development

Create `.env.local` in `frontend/` (gitignored):

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_ENV=development
```

**Use:**
```bash
cd frontend
npm run dev
# Vite automatically loads .env.local
```

---

## Secret Rotation

### Rotate PostgreSQL Password

```bash
# 1. Generate new password (copy somewhere safe!)
NEW_PASSWORD="new-secure-password-here"

# 2. Update GCP Secret Manager
echo -n "$NEW_PASSWORD" | gcloud secrets versions add postgres-password --data-file=-

# 3. Update password in Cloud SQL
gcloud sql users set-password msme_app \
  --instance=msme-postgres \
  --password="$NEW_PASSWORD"

# 4. Redeploy Cloud Run services to pick up new password
gcloud run deploy msme-backend --region=us-central1  # Re-triggers deployment
```

### Rotate JWT Secret

```bash
# 1. Generate new JWT secret
NEW_JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Store in GCP Secret Manager
echo -n "$NEW_JWT_SECRET" | gcloud secrets versions add jwt-secret --data-file=-

# 3. Redeploy services
gcloud run deploy msme-backend --region=us-central1
gcloud run deploy msme-frontend --region=us-central1
```

---

## Setting Secrets for Cloud Build

### Option 1: GCP Secret Manager (Recommended)

```bash
# Create secrets
echo -n "your-postgres-password" | gcloud secrets create postgres-password --data-file=-
echo -n "your-jwt-secret" | gcloud secrets create jwt-secret --data-file=-

# Grant Cloud Build service account access
PROJECT_ID=$(gcloud config get-value project)
BUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

gcloud secrets add-iam-policy-binding postgres-password \
  --member=serviceAccount:${BUILD_SA} \
  --role=roles/secretmanager.secretAccessor

gcloud secrets add-iam-policy-binding jwt-secret \
  --member=serviceAccount:${BUILD_SA} \
  --role=roles/secretmanager.secretAccessor
```

### Option 2: Cloud Build Substitutions

In `cloudbuild.yml`:
```yaml
substitutions:
  _POSTGRES_PASSWORD: 'will-be-overridden'

# And in Cloud Build trigger settings, set:
# _POSTGRES_PASSWORD = [value from Secret Manager or pass at build time]
```

**Pass at build time:**
```bash
gcloud builds submit \
  --substitutions="_POSTGRES_PASSWORD=my-password"
```

---

## Setting Secrets for GitHub Actions

### Create Required Secrets

```bash
# 1. Get values
PROJECT_ID=$(gcloud config get-value project)
WIF_PROVIDER="projects/YOUR_PROJECT_NUM/locations/global/workloadIdentityPools/github-actions/providers/github-provider"
WIF_SERVICE_ACCOUNT="github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# 2. Copy these values and add to GitHub Secrets:
echo "GCP_PROJECT_ID: $PROJECT_ID"
echo "WIF_PROVIDER: $WIF_PROVIDER"
echo "WIF_SERVICE_ACCOUNT: $WIF_SERVICE_ACCOUNT"
```

### Add Database Credentials (Optional)

If not using Cloud SQL Proxy:

1. Go to **Repo → Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add:
   - `DB_HOST`: Cloud SQL connection name
   - `DB_USER`: `msme_app`
   - `DB_PASS`: Your PostgreSQL password

Then reference in workflow:
```yaml
env:
  POSTGRES_HOST: ${{ secrets.DB_HOST }}
  POSTGRES_USER: ${{ secrets.DB_USER }}
  POSTGRES_PASSWORD: ${{ secrets.DB_PASS }}
```

---

## Cloud SQL Proxy Connection (Recommended for Cloud Build)

Instead of exposing Cloud SQL to the internet, use Cloud SQL Proxy:

### Setup Cloud SQL Proxy

```bash
# In Cloud Run deployment, add:
--add-cloudsql-instances=PROJECT:REGION:INSTANCE

# This injects the Cloud SQL Proxy and exposes DB at:
# localhost:5432
```

### Update connection in cloudbuild.yml

```yaml
substitutions:
  _CLOUD_SQL_INSTANCES: 'your-project:us-central1:msme-postgres'

steps:
  - name: 'gcr.io/cloud-builders/run'
    args:
      - 'deploy'
      - 'msme-backend'
      - '--add-cloudsql-instances=${_CLOUD_SQL_INSTANCES}'
      - '--set-env-vars'
      - 'POSTGRES_HOST=/cloudsql/${_CLOUD_SQL_INSTANCES}'
```

---

## Local Development with Secrets

### Load `.env` Files in Python

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv('.env.local')  # Load from local file

class Settings(BaseSettings):
    postgres_host: str = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_password: str = os.getenv('POSTGRES_PASSWORD')
    # ...
```

### Load `.env` Files in TypeScript

```typescript
// frontend/src/config.ts
import.meta.env.VITE_API_BASE_URL  // Automatically loaded from .env.local
```

---

## Secret Management Best Practices

### ✅ DO

- Store all secrets in GCP Secret Manager or GitHub Secrets
- Rotate secrets every 90 days
- Use strong, randomly-generated passwords (≥16 characters)
- Grant least-privilege access to secrets
- Audit secret access logs
- Version secrets (GCP allows multiple versions)
- Use different secrets per environment (dev/staging/prod)

### ❌ DON'T

- Commit secrets to git (use `.gitignore` for `.env` files)
- Pass secrets in logs or error messages
- Hardcode secrets in code
- Share secrets via email or Slack
- Use the same secret for multiple services
- Store secrets in Docker images (use build secrets instead)

---

## Viewing Secret Access Logs

```bash
# View all secret access
gcloud logging read "protoPayload.methodName=google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion" \
  --limit=50

# View access to specific secret
gcloud logging read "protoPayload.request.name=*postgres-password" \
  --limit=50
```

---

## Automated Secret Rotation (Advanced)

For production, consider using Cloud Functions to auto-rotate secrets:

```python
# Example: Auto-rotate password every 90 days
import google.cloud.secretmanager as secretmanager
import secrets
from google.cloud import sql_v1

def rotate_secret(project_id, secret_id):
    """Generate new password and update Secret Manager and Cloud SQL"""
    client = secretmanager.SecretManagerServiceClient()
    
    # Generate new password
    new_password = secrets.token_urlsafe(32)
    
    # Store in Secret Manager
    parent = client.secret_path(project_id, secret_id)
    response = client.add_secret_version(
        request={"parent": parent, "payload": {"data": new_password.encode("UTF-8")}}
    )
    
    # Update Cloud SQL user
    sql_admin = sql_v1.SqlUsersServiceClient()
    sql_admin.update(
        project_id=project_id,
        instance="msme-postgres",
        host="%",
        name="msme_app",
        body=sql_v1.User(password=new_password)
    )
    
    return f"Secret rotated: {response.name}"
```

Schedule this function to run daily/weekly using Cloud Scheduler.

---

## References

- [GCP Secret Manager](https://cloud.google.com/secret-manager/docs)
- [GitHub Secrets](https://docs.github.com/actions/security-guides/encrypted-secrets)
- [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy)
- [12-Factor App: Store Config in Environment](https://12factor.net/config)
